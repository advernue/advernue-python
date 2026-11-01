import json
from decimal import Decimal

import httpx
import pytest

from advernue import Advernue, AdvernueError, AsyncAdvernue, from_money, to_money

ACTION = {"id": "act_1", "status": "succeeded"}


def make(handler, **kw):
    return Advernue("k_test", transport=httpx.MockTransport(handler), **kw)


def test_auth_and_get_query():
    seen = {}

    def h(req: httpx.Request) -> httpx.Response:
        seen["req"] = req
        return httpx.Response(200, json=[{"id": "c1"}])

    out = make(h).campaigns.list(client_id="cl_1", platform="meta")
    req = seen["req"]
    assert out == [{"id": "c1"}]
    assert req.headers["authorization"] == "Bearer k_test"
    assert req.url.path == "/v1/campaigns" and req.url.params["clientId"] == "cl_1"
    assert req.url.host == "api.advernue.com" and "idempotency-key" not in req.headers


def test_env_config(monkeypatch):
    monkeypatch.setenv("ADVERNUE_API_KEY", "envkey")
    monkeypatch.setenv("ADVERNUE_BASE_URL", "http://localhost:9/")
    c = Advernue()
    assert (c.api_key, c.base_url) == ("envkey", "http://localhost:9")
    monkeypatch.delenv("ADVERNUE_API_KEY")
    with pytest.raises(ValueError):
        Advernue()


def test_write_idempotency_dry_run_and_body():
    seen = []

    def h(req):
        seen.append(req)
        return httpx.Response(201, json=ACTION)

    c = make(h)
    body = {"adAccountId": "a1", "name": "N", "objective": "traffic"}
    c.campaigns.create(body, dry_run=True, idempotency_key="my-key")
    c.campaigns.create(body)
    assert seen[0].headers["idempotency-key"] == "my-key"
    assert seen[0].url.params["dry_run"] == "true"
    assert json.loads(seen[0].content) == body
    assert len(seen[1].headers["idempotency-key"]) == 36 and "dry_run" not in seen[1].url.params


def test_path_params_quoted_and_set_status():
    seen = []
    c = make(lambda r: (seen.append(r), httpx.Response(200, json=ACTION))[1])
    c.campaigns.set_status("a/b", {"status": "paused"})
    assert seen[0].url.raw_path.decode() == "/v1/campaigns/a%2Fb/status"


def test_error_envelope():
    err = {"error": {"code": "fx_rate_missing", "message": "no rate", "details": {"pair": "EURUSD"}}}
    with pytest.raises(AdvernueError) as e:
        make(lambda r: httpx.Response(422, json=err)).campaigns.get("x")
    assert (e.value.status_code, e.value.code, e.value.details) == (422, "fx_rate_missing", {"pair": "EURUSD"})


def test_retry_get_and_write_reuses_key():
    calls = []

    def h(req):
        calls.append(req)
        return httpx.Response(503, headers={"retry-after": "0"}) if len(calls) < 3 else httpx.Response(201, json=ACTION)

    c = make(h)
    assert c.campaigns.create({"adAccountId": "a", "name": "n", "objective": "traffic"}) == ACTION
    assert len({r.headers["idempotency-key"] for r in calls}) == 1 and len(calls) == 3


def test_retries_exhausted_raises():
    n = []

    def h(req):
        n.append(1)
        return httpx.Response(429, headers={"retry-after": "0"}, json={"error": {"code": "rate_limited", "message": "slow"}})

    with pytest.raises(AdvernueError) as e:
        make(h, max_retries=2).campaigns.list()
    assert e.value.code == "rate_limited" and len(n) == 3


def test_no_retry_on_4xx():
    n = []
    with pytest.raises(AdvernueError):
        make(lambda r: (n.append(1), httpx.Response(404, json={"error": {"code": "not_found", "message": "x"}}))[1]).campaigns.get("1")
    assert len(n) == 1


def test_money():
    assert to_money(Decimal("12.345678"), "usd") == {"micros": 12345678, "currency": "USD"}
    assert to_money("0.1", "EUR")["micros"] == 100000
    assert from_money({"micros": 12340000, "currency": "USD"}) == Decimal("12.34")
    with pytest.raises(TypeError):
        to_money(1.5, "USD")  # type: ignore[arg-type]


async def test_async_client_retries():
    n = []

    def h(req):
        n.append(req)
        return httpx.Response(500, headers={"retry-after": "0"}) if len(n) == 1 else httpx.Response(200, json={"groups": []})

    async with AsyncAdvernue("k", transport=httpx.MockTransport(h)) as c:
        out = await c.analytics.compare({"groupBy": "platform", "from": "2026-01-01", "to": "2026-01-31"})
    assert out == {"groups": []} and len(n) == 2
    assert n[0].headers["idempotency-key"] == n[1].headers["idempotency-key"]
