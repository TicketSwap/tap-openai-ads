from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from tap_openai_ads.streams import CampaignInsightsStream
from tap_openai_ads.tap import TapOpenAIAds

CONFIG = {"api_key": "test-key", "start_date": "2026-10-01"}
BASE = "https://api.ads.openai.com/v1"
YESTERDAY = (datetime.now(tz=timezone.utc).date() - timedelta(days=1)).isoformat()


def _insight(day: str) -> dict:
    return {
        "id": f"day={day}:entity_id=cmpn_1",
        "start_time": 1777075200,
        "end_time": 1777161600,
        "readable_time": day,
        "campaign_id": "cmpn_1",
        "campaign_name": "oaid-nl-uwc-serps-test",
        "impressions": 1200,
        "clicks": 36,
        "spend": 18.42,
    }


def _sync(requests_mock, capsys, state: dict | None = None) -> tuple[list[dict], list]:
    requests_mock.get(
        f"{BASE}/campaigns",
        json={"object": "list", "data": [{"id": "cmpn_1", "name": "x"}], "has_more": False},
    )
    insights = requests_mock.get(
        f"{BASE}/ad_account/insights",
        [
            {"json": {"data": [_insight("2026-10-21")], "last_id": "page_1", "has_more": True}},
            {"json": {"data": [_insight("2026-10-22")], "last_id": "page_2", "has_more": False}},
        ],
    )
    TapOpenAIAds(config=CONFIG, state=state).sync_all()
    messages = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    return messages, insights.request_history


def _query(request) -> dict[str, list[str]]:
    return parse_qs(urlparse(request.url).query)


def test_insights_request_paginates_and_authenticates(requests_mock, capsys):
    messages, requests = _sync(requests_mock, capsys)
    records = [
        m["record"] for m in messages if m.get("stream") == "campaign_insights" and "record" in m
    ]
    assert [r["readable_time"] for r in records] == ["2026-10-21", "2026-10-22"]
    assert records[0]["spend"] == 18.42

    first, second = requests
    assert first.headers["Authorization"] == "Bearer test-key"
    query = _query(first)
    assert query["fields[]"] == list(CampaignInsightsStream.fields)
    assert query["time_granularity"] == ["daily"]
    assert query["aggregation_level"] == ["campaign"]
    assert json.loads(query["time_ranges[]"][0]) == {
        "type": "date_range",
        "since": "2026-09-24",
        "until": YESTERDAY,
    }
    assert "after" not in query
    assert _query(second)["after"] == ["page_1"]

    bookmarks = [m["value"]["bookmarks"] for m in messages if m["type"] == "STATE"][-1]
    assert bookmarks["campaign_insights"]["replication_key_value"] == "2026-10-22"


def test_bookmark_rewinds_by_lookback(requests_mock, capsys):
    state = {
        "bookmarks": {
            "campaign_insights": {
                "replication_key": "readable_time",
                "replication_key_value": "2026-11-20",
            }
        }
    }
    _, requests = _sync(requests_mock, capsys, state)
    since = json.loads(_query(requests[0])["time_ranges[]"][0])["since"]
    assert since == "2026-11-13"
