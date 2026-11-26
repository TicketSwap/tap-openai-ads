# tap-openai-ads

Singer tap for [OpenAI (ChatGPT) Ads](https://developers.openai.com/ads), built with the
[Meltano Singer SDK](https://sdk.meltano.com). It extracts the streams behind the `openai_ads`
dbt models in `data-transformations`.

| Stream | Endpoint | Replication |
|---|---|---|
| `campaigns` | `GET /v1/campaigns` | Full table |
| `campaign_insights` | `GET /v1/ad_account/insights`, daily, campaign level | Incremental on `readable_time` |

Stream and field names match the dbt `source('openai_ads', ...)` tables, so don't rename them.
Each run re-pulls `lookback_days` before the bookmark, because OpenAI revises spend after the
fact, and stops at yesterday. Dates are in the ad account's timezone. Spend is in the account
currency, in major units. Delivery reporting keeps 365 days.

## Configuration

| Setting | Required | Description |
|---|---|---|
| `api_key` | yes | Advertiser API key from Ads Manager → Settings. Each key covers one ad account. |
| `start_date` | yes | First date to sync (`YYYY-MM-DD`). |
| `lookback_days` | no | Days before the bookmark to re-sync on each run (default 7). |

With `--config=ENV`, the tap reads these from `TAP_OPENAI_ADS_*` environment variables (see
`.env.example`).

## Development

```bash
uv sync
uv run pytest
uv run tap-openai-ads --about
cp .env.example .env
meltano run tap-openai-ads target-jsonl
```

`pytest` mocks the API, so it needs no key. A real run needs a valid API key.
