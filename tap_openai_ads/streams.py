from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, ClassVar

from singer_sdk import RESTStream
from singer_sdk import typing as th
from singer_sdk.authenticators import BearerTokenAuthenticator
from singer_sdk.pagination import BaseAPIPaginator

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

if TYPE_CHECKING:
    import requests
    from singer_sdk.helpers.types import Context


class LastIdPaginator(BaseAPIPaginator[str | None]):
    @override
    def get_next(self, response: requests.Response) -> str | None:
        body = response.json()
        return body["last_id"] if body.get("has_more") else None


class OpenAIAdsStream(RESTStream[str | None]):
    url_base = "https://api.ads.openai.com/v1"
    records_jsonpath = "$.data[*]"
    page_size = 500

    @property
    @override
    def authenticator(self) -> BearerTokenAuthenticator:
        return BearerTokenAuthenticator(token=self.config["api_key"])

    @override
    def get_new_paginator(self) -> LastIdPaginator:
        return LastIdPaginator(None)

    @override
    def get_url_params(
        self, context: Context | None, next_page_token: str | None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": self.page_size}
        if next_page_token:
            params["after"] = next_page_token
        return params


class CampaignsStream(OpenAIAdsStream):
    name = "campaigns"
    path = "/campaigns"
    primary_keys: ClassVar[tuple[str, ...]] = ("id",)
    replication_key = None
    schema = th.PropertiesList(
        th.Property("id", th.StringType, required=True),
        th.Property("name", th.StringType),
        th.Property("status", th.StringType),
        th.Property("bidding_type", th.StringType),
        th.Property(
            "budget", th.ObjectType(th.Property("lifetime_spend_limit_micros", th.IntegerType))
        ),
        th.Property("start_time", th.IntegerType),
        th.Property("end_time", th.IntegerType),
        th.Property("created_at", th.IntegerType),
        th.Property("updated_at", th.IntegerType),
    ).to_dict()


class CampaignInsightsStream(OpenAIAdsStream):
    name = "campaign_insights"
    path = "/ad_account/insights"
    primary_keys: ClassVar[tuple[str, ...]] = ("readable_time", "campaign_id")
    replication_key = "readable_time"
    is_sorted = False
    page_size = 2000
    fields: ClassVar[tuple[str, ...]] = (
        "metadata.readable_time",
        "campaign.id",
        "campaign.name",
        "campaign.impressions",
        "campaign.clicks",
        "campaign.spend",
    )
    schema = th.PropertiesList(
        th.Property("readable_time", th.DateType, required=True),
        th.Property("campaign_id", th.StringType, required=True),
        th.Property("campaign_name", th.StringType),
        th.Property("start_time", th.IntegerType),
        th.Property("end_time", th.IntegerType),
        th.Property("impressions", th.IntegerType),
        th.Property("clicks", th.IntegerType),
        th.Property("spend", th.NumberType),
    ).to_dict()

    def date_range(self, context: Context | None) -> tuple[date, date]:
        bookmark = self.get_starting_replication_key_value(context) or self.config["start_date"]
        since = date.fromisoformat(str(bookmark)[:10]) - timedelta(
            days=int(self.config.get("lookback_days", 7))
        )
        until = datetime.now(tz=timezone.utc).date() - timedelta(days=1)
        return min(since, until), until

    @override
    def get_url_params(
        self, context: Context | None, next_page_token: str | None
    ) -> dict[str, Any]:
        since, until = self.date_range(context)
        time_range = {"type": "date_range", "since": since.isoformat(), "until": until.isoformat()}
        return {
            **super().get_url_params(context, next_page_token),
            "time_granularity": "daily",
            "aggregation_level": "campaign",
            "fields[]": list(self.fields),
            "time_ranges[]": [json.dumps(time_range)],
        }
