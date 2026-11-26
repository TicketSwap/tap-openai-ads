from __future__ import annotations

import sys

from singer_sdk import Tap
from singer_sdk import typing as th

from tap_openai_ads import streams

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override


class TapOpenAIAds(Tap):
    name = "tap-openai-ads"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "api_key",
            th.StringType(nullable=False),
            required=True,
            secret=True,
            title="API Key",
            description="Advertiser API key from Ads Manager settings, scoped to one ad account.",
        ),
        th.Property(
            "start_date",
            th.DateType(nullable=False),
            required=True,
            title="Start Date",
            description="First date to sync, in YYYY-MM-DD format.",
        ),
        th.Property(
            "lookback_days",
            th.IntegerType,
            default=7,
            title="Lookback Days",
            description="Days before the bookmark to re-sync on each run.",
        ),
    ).to_dict()

    @override
    def discover_streams(self) -> list[streams.OpenAIAdsStream]:
        return [
            streams.CampaignsStream(self),
            streams.CampaignInsightsStream(self),
        ]


if __name__ == "__main__":
    TapOpenAIAds.cli()
