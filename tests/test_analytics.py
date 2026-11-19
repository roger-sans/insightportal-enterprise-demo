from math import isclose
import sqlite3

from fastapi.testclient import TestClient
import pytest
from sqlglot import parse

from insightportal.main import create_app
from insightportal.warehouse import CONTRACT, DOMAINS, ROOT, populate, seed_rows


@pytest.fixture
def api(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        yield client


def test_contract_matches_dimensional_warehouse():
    ids = [metric["id"] for domain in CONTRACT["domains"] for metric in domain["metrics"]]
    assert len(ids) == len(set(ids)) == 8
    assert len(DOMAINS) == 4
    ddl = (ROOT / "warehouse/schema.sql").read_text()
    assert len(parse(ddl, read="snowflake")) == 7
    assert len(parse((ROOT / "warehouse/snowflake/roles.sql").read_text(), read="snowflake")) == 4
    with sqlite3.connect(":memory:") as local:
        populate(local)
        for domain in DOMAINS.values():
            cols = {col[1] for col in local.execute(f"PRAGMA table_info({domain['table']})")}
            assert set(CONTRACT["grain"]) <= cols
            for metric in domain["metrics"]:
                assert set(filter(None, [metric["numerator"], metric["denominator"]])) <= cols


def test_local_snapshots_and_same_period_delta(api):
    doc = api.get("/api/v1/catalog").json()
    assert set(doc["years"]) == {"2025", "2026"}
    data = api.get("/api/v1/dashboard").json()
    assert [(q["id"], q["status"]) for q in data["quality"]] == [
        ("finance", "current"), ("commercial", "current"), ("operations", "late"), ("people", "current"),
    ]
    assert all(all(q["checks"].values()) and q["rows"] == 63 for q in data["quality"])
    assert len(data["metrics"]) == 8
    revenue = data["metrics"][0]
    assert revenue["value"] == sum(row["value"] for row in revenue["trend"]) == 4754057
    assert revenue["value"] == sum(row["value"] for row in revenue["sites"])
    assert revenue["previous"] == 4173623
    assert revenue["goal"] == 460000 * 9
    assert revenue["trend_goal"] == 460000


def test_ratio_pools_counts_and_drill_is_same_semantics(api):
    query = {"domain": "operations", "metrics": "on-time", "start": "2026-04", "end": "2026-09"}
    result = api.get("/api/v1/dashboard", params=query).json()["metrics"][0]
    rows = [r for r in seed_rows()["mart_operations"] if "2026-04" <= r[0] <= "2026-09"]
    expected = sum(r[2] for r in rows) / sum(r[3] for r in rows) * 100
    assert isclose(result["value"], expected, abs_tol=0.005)
    assert len(result["trend"]) == 6
    assert not isclose(result["value"], sum(row["value"] for row in result["sites"]) / 3, abs_tol=0.005)
    single = api.get("/api/v1/dashboard", params={**query, "start": "2026-07", "end": "2026-07"}).json()
    assert single["metrics"][0]["value"] == next(p["value"] for p in result["trend"] if p["month"] == "2026-07")
    regional = api.get("/api/v1/dashboard", params={**query, "site": "metro"}).json()["metrics"][0]
    assert regional["sites"] == [r for r in result["sites"] if r["id"] == "metro"]


def test_finance_and_commercial_measure_different_events(api):
    result = {r["id"]: r for r in api.get("/api/v1/dashboard").json()["metrics"]}
    assert result["bookings"]["value"] > result["revenue"]["value"]
    local = api.get("/api/v1/dashboard", params={"site":"metro", "metrics":"bookings"}).json()["metrics"][0]
    assert local["goal"] is None
    assert local["trend_goal"] is None


def test_2025_has_no_prior_comparison(api):
    query = {"start": "2025-01", "end": "2025-12", "metrics": "margin"}
    result = api.get("/api/v1/dashboard", params=query).json()["metrics"][0]
    assert len(result["trend"]) == 12
    assert result["previous"] is None
    assert result["delta"] is None


@pytest.mark.parametrize("query", [
    {"start": "2025-12", "end": "2026-01"}, {"end": "2026-12"}, {"start": "2026-10"},
    {"site": "unknown"}, {"domain": "people", "metrics": "margin"}, {"start": "recent"},
    {"metrics": ["revenue", "revenue"]}, {"metrics": "margin-without-contract"},
])
def test_unsupported_filters_are_rejected(api, query):
    assert api.get("/api/v1/dashboard", params=query).status_code == 422


@pytest.mark.parametrize(("change", "domain", "check"), [
    ("UPDATE mart_people SET eligible = 19, trained = 18 WHERE site_id = 'metro' AND month = '2026-07'",
     "people", "metric_invariants"),
    ("UPDATE mart_commercial SET won = closed + 1 WHERE site_id = 'metro' AND month = '2026-07'",
     "commercial", "metric_invariants"),
    ("UPDATE mart_finance SET revenue_cents = 'untyped' WHERE site_id = 'metro' AND month = '2026-07'",
     "finance", "metric_invariants"),
    ("DELETE FROM mart_finance WHERE site_id = 'metro' AND month = '2026-07'",
     "finance", "full_coverage"),
    ("UPDATE publication SET contract_version = '2.0.0' WHERE domain = 'operations'",
     "operations", "publication_contract"),
    ("UPDATE publication SET published_at = '2026-10-03T07:30:00Z' WHERE domain = 'finance'",
     "finance", "publication_contract"),
])
def test_quality_gates_block_only_the_affected_domain(tmp_path, change, domain, check):
    with TestClient(create_app(tmp_path)) as client:
        with sqlite3.connect(tmp_path / "analytics.db") as conn:
            conn.execute(change)
        response = client.get("/api/v1/dashboard").json()
        blocked = next(item for item in response["quality"] if item["id"] == domain)
        assert blocked["status"] == "blocked"
        assert blocked["checks"][check] is False
        metric_ids = {metric["id"] for metric in DOMAINS[domain]["metrics"]}
        assert not metric_ids & {r["id"] for r in response["metrics"]}
        assert len(response["metrics"]) == 6


def test_zero_denominator_is_unavailable_not_zero(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        with sqlite3.connect(tmp_path / "analytics.db") as conn:
            conn.execute("UPDATE mart_commercial SET closed = 0, won = 0 WHERE month = '2026-09'")
        query = {"start": "2026-09", "end": "2026-09", "domain": "commercial", "metrics": "win-rate"}
        response = client.get("/api/v1/dashboard", params=query).json()
        assert response["quality"][0]["status"] == "current"
        assert response["metrics"][0]["value"] is None
        assert response["metrics"][0]["delta"] is None


def test_warehouse_failure_returns_sanitized_error_without_fallback(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        with sqlite3.connect(tmp_path / "analytics.db") as conn:
            conn.execute("DROP TABLE mart_finance")
        response = client.get("/api/v1/dashboard")
        assert response.status_code == 503
        assert response.json() == {"detail": "Analytics source unavailable. Retry when service is restored."}
        assert client.get("/api/v1/requests").status_code == 200


def test_snowflake_mode_does_not_initialize_local_analytics(tmp_path, monkeypatch):
    def unavailable():
        raise RuntimeError("A simulated upstream connection failure")

    monkeypatch.setattr("insightportal.warehouse.snowflake_connection", unavailable)
    with TestClient(create_app(tmp_path, "snowflake")) as client:
        assert client.get("/health").json()["mode"] == "snowflake"
        assert client.get("/api/v1/dashboard").status_code == 503
        assert not (tmp_path / "analytics.db").exists()
