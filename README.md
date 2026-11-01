# advernue

Official Python SDK for [Advernue](https://advernue.com): one unified REST API over ~200 ad platforms, with one request shape for every platform.

```bash
pip install advernue
```

Python 3.10+, depends only on `httpx`. Sync (`Advernue`) and async (`AsyncAdvernue`) clients; request and response types are `TypedDict`s generated from the OpenAPI spec (`advernue.models`). Bodies keep the API's field names (`adAccountId`, `groupBy`), method names are snake_case, and tags are namespaces (`client.campaigns.list(...)`, `client.analytics.compare(...)`).

## Quickstart

```python
from advernue import Advernue

client = Advernue()  # reads ADVERNUE_API_KEY (and ADVERNUE_BASE_URL, default https://api.advernue.com)

for c in client.campaigns.list(platform="meta", status="active"):
    print(c["id"], c["name"])
```

Async:

```python
import asyncio
from advernue import AsyncAdvernue

async def main():
    async with AsyncAdvernue() as client:
        print(await client.campaigns.list())

asyncio.run(main())
```

## Compare platforms

```python
res = client.analytics.compare({
    "groupBy": "platform",
    "from": "2026-10-01",
    "to": "2026-10-31",
    "comparePrevious": True,
})
for g in res["groups"]:
    print(g["key"], g["metrics"])
```

## Cross-platform campaign, created paused

`crosspost.launch` creates one child campaign per ad account, paused, and activates them only once all succeed. Plan first with `dry_run`, then launch:

```python
from advernue import to_money

brief = {
    "name": "Autumn sale",
    "objective": "sales",
    "totalBudget": {"type": "lifetime", "amount": to_money("5000", "USD")},
    "split": {"type": "equal"},
    "targeting": {"countries": ["US", "DE"]},
    "creatives": [...],  # see advernue.models.CampaignBrief
    "destinationUrl": "https://example.com/sale",
    "targets": ["acc_meta_1", "acc_tiktok_1", "acc_google_1"],
}
plan = client.crosspost.launch(brief, dry_run=True)   # nothing is sent to platforms
result = client.crosspost.launch(brief, idempotency_key="autumn-sale-1")
```

For a single platform, `client.campaigns.create({...})` creates the campaign paused unless you pass `status`.

## Pacing

```python
pacing = client.analytics.pacing({"clientId": "cl_1", "tolerance": 0.05})
for c in pacing["campaigns"]:
    print(c["name"], c.get("status"))
```

## Breakdown by country

```python
rows = client.analytics.breakdown({
    "dimension": "geo_country",
    "from": "2026-10-01",
    "to": "2026-10-31",
    "byPlatform": True,
    "limit": 20,
})
```

## Writes: idempotency and dry runs

Every write method (POST, PATCH, PUT, DELETE) accepts `idempotency_key=` and `dry_run=`. They become the `Idempotency-Key` header and `?dry_run=true`. If you pass no key, a uuid4 is generated. Writes return the Action row; check `action["status"]` (`succeeded`, `pending_approval`, `denied`, `failed`, `dry_run`).

## Errors and retries

Non-2xx responses raise `AdvernueError` with `.status_code`, `.code`, `.message` and `.details`, built from the `{error: {code, message, details}}` envelope.

```python
from advernue import AdvernueError
try:
    client.campaigns.get("missing")
except AdvernueError as e:
    print(e.status_code, e.code, e.details)
```

429 and 5xx responses (and connection errors) are retried with backoff (`max_retries=2`, honours `Retry-After`). GET is always retried; writes are retried because every write carries an idempotency key, reused across attempts.

## Money

Money is `{micros, currency}` with integer micros. Use `Decimal`, never float:

```python
from decimal import Decimal
from advernue import to_money, from_money

to_money(Decimal("12.34"), "USD")                       # {"micros": 12340000, "currency": "USD"}
from_money({"micros": 12340000, "currency": "USD"})     # Decimal("12.34")
```

`to_money` raises `TypeError` for floats.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). MIT licensed.
