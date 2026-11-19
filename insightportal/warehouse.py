from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import json
import os
from pathlib import Path
from random import Random
import sqlite3

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = json.loads((ROOT / "contracts/metrics.v1.json").read_text(encoding="utf-8"))
DOMAINS = {domain["id"]: domain for domain in CONTRACT["domains"]}
SITES = {site["id"]: site["name"] for site in CONTRACT["sites"]}
METRICS = {metric["id"]: (domain, metric) for domain in DOMAINS.values() for metric in domain["metrics"]}
AS_OF = datetime.fromisoformat(CONTRACT["scenario_as_of"])
THROUGH_MONTH = "2026-09"
YEARS = {"2026": 9, "2025": 12}
MONTHS = [f"{year}-{month:02d}" for year, limit in sorted(YEARS.items()) for month in range(1, limit + 1)]


def seed_rows():
    """Generate the same complete dimensional grid on each database."""
    random = Random(26117)
    rows = {table: [] for table in ("mart_finance", "mart_commercial", "mart_operations", "mart_people")}
    for month in MONTHS:
        year, period = map(int, month.split("-"))
        season = [0.82, 0.86, 1.04, 0.96, 1.09, 1.16, 1.02, 0.92, 1.22, 1.12, 1.15, 1.00][period - 1]
        growth = 1.13 if year == 2026 else 1
        for site_id, size in zip(SITES, (1, 1.28, 0.73), strict=True):
            key = (month, site_id)
            revenue = round(151000 * size * season * growth * random.uniform(0.94, 1.06))
            gross = round(revenue * random.uniform(0.315, 0.42))
            rows["mart_finance"].append((*key, revenue * 100, gross * 100))
            bookings = round(173000 * size * season * growth * random.uniform(0.92, 1.08))
            closed = round(52 * size * season * growth)
            rows["mart_commercial"].append((*key, bookings * 100, round(closed * random.uniform(0.49, 0.67)), closed))
            completed = round(156 * size * season * growth * random.uniform(0.95, 1.05))
            reliability = (0.88 if year == 2025 else 0.91) + random.uniform(-0.01, 0.055)
            rows["mart_operations"].append((*key, round(completed * reliability), completed))
            eligible = round(106 * size * growth)
            compliance = (0.87 if year == 2025 else 0.91) + random.uniform(0.01, 0.045)
            scheduled = eligible * (20 + period % 3)
            absence = round(scheduled * random.uniform(0.024, 0.051))
            rows["mart_people"].append((*key, round(eligible * compliance), eligible, absence, scheduled))
    return {
        "dim_site": list(SITES.items()),
        "dim_month": [(month, int(month[:4])) for month in MONTHS],
        **rows,
        "publication": [
            ("finance", CONTRACT["version"], "2026-10-02T07:30:00Z", THROUGH_MONTH),
            ("commercial", CONTRACT["version"], "2026-10-02T09:10:00Z", THROUGH_MONTH),
            ("operations", CONTRACT["version"], "2026-10-01T15:00:00Z", THROUGH_MONTH),
            ("people", CONTRACT["version"], "2026-10-01T16:45:00Z", THROUGH_MONTH),
        ],
    }


def populate(connection):
    cursor = connection.cursor()
    schema = (ROOT / "warehouse/schema.sql").read_text(encoding="utf-8")
    for statement in schema.split(";"):
        if statement.strip():
            cursor.execute(statement)
    for table, rows in seed_rows().items():
        placeholders = ", ".join("?" for _ in rows[0])
        cursor.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)
    connection.commit()
    cursor.close()


class Warehouse:
    def __init__(self, path: Path, mode: str):
        if mode not in {"local", "snowflake"}:
            raise ValueError("WAREHOUSE_MODE must be local or snowflake")
        self.path = path
        self.mode = mode

    @contextmanager
    def connect(self):
        if self.mode == "local":
            connection = sqlite3.connect(self.path)
            connection.execute("PRAGMA foreign_keys = ON")
        else:
            connection = snowflake_connection()
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self):
        if self.mode != "local":
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                if not connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE name = 'publication' AND type = 'table'"
                ).fetchone():
                    populate(connection)
                else:
                    connection.commit()
            except Exception:
                connection.rollback()
                raise


def snowflake_connection():
    import snowflake.connector

    keys = ("account", "user", "password", "warehouse", "database", "schema", "role")
    config = {key: os.environ.get(f"SNOWFLAKE_{key.upper()}") for key in keys}
    if not all(config.values()):
        raise RuntimeError("Required Snowflake connection settings are missing")
    return snowflake.connector.connect(
        **config, paramstyle="qmark", login_timeout=10, network_timeout=20,
        session_parameters={"QUERY_TAG": "insightportal_demo", "STATEMENT_TIMEOUT_IN_SECONDS": 30},
    )


def quality(cursor, domain):
    table = domain["table"]
    columns = {column for metric in domain["metrics"]
               for column in (metric["numerator"], metric["denominator"]) if column}
    rules = [f"{col} IS NULL OR {col} < 0 OR CAST({col} AS BIGINT) <> {col}" for col in sorted(columns)]
    rules.extend(f"NOT ({check})" for check in domain["checks"])
    if domain["min_cohort"]:
        cohort = domain["min_cohort"]
        rules.append(f"{cohort['column']} < {cohort['minimum']}")
    invalid = cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {' OR '.join(rules)}").fetchone()[0]
    duplicate = cursor.execute(f"""
        SELECT COUNT(*) FROM (
            SELECT month, site_id FROM {table} GROUP BY month, site_id HAVING COUNT(*) > 1
        ) AS duplicates
    """).fetchone()[0]
    orphans = cursor.execute(f"""
        SELECT COUNT(*) FROM {table} AS f
        LEFT JOIN dim_month AS m ON f.month = m.month
        LEFT JOIN dim_site AS s ON f.site_id = s.site_id
        WHERE m.month IS NULL OR s.site_id IS NULL
    """).fetchone()[0]
    expected = len(MONTHS) * len(SITES)
    observed = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    actual_sites = cursor.execute("SELECT site_id, label FROM dim_site").fetchall()
    actual_months = cursor.execute("SELECT month, calendar_year FROM dim_month").fetchall()
    dimensions_pass = (sorted(actual_sites) == sorted(SITES.items())
                       and sorted(actual_months) == [(m, int(m[:4])) for m in MONTHS])
    published = cursor.execute(
        "SELECT contract_version, published_at, through_month FROM publication WHERE domain = ?",
        (domain["id"],),
    ).fetchall()
    hours = None
    if len(published) == 1:
        version, published_at, through = published[0]
        try:
            timestamp = datetime.fromisoformat(published_at)
            if timestamp.tzinfo and timestamp.utcoffset() == timezone.utc.utcoffset(None) and timestamp <= AS_OF:
                hours = round((AS_OF - timestamp).total_seconds() / 3600, 2)
        except (ValueError, TypeError):
            pass
    else:
        version, published_at, through = None, None, None
    checks = {
        "unique_grain": duplicate == 0,
        "valid_dimensions": orphans == 0 and dimensions_pass,
        "full_coverage": observed == expected,
        "metric_invariants": invalid == 0,
        "publication_contract": version == CONTRACT["version"] and through == THROUGH_MONTH and hours is not None,
    }
    valid = all(checks.values())
    status = ("blocked" if not valid else
              "late" if hours > domain["freshness_hours"] else "current")
    return {"id": domain["id"], "status": status, "checks": checks, "rows": observed,
            "expected_rows": expected, "published_at": published_at, "through_month": through,
            "age_hours": hours, "sla_hours": domain["freshness_hours"]}


def query_metric(cursor, domain, metric, start, end, site):
    numerator = metric["numerator"]
    denominator = metric["denominator"]
    expressions = f"SUM({numerator}), " + (f"SUM({denominator})" if denominator else "NULL")
    table = domain["table"]
    scope = "" if site is None else " AND f.site_id = ?"
    params = (start, end) if site is None else (start, end, site)
    base = f"FROM {table} AS f WHERE f.month BETWEEN ? AND ?{scope}"
    period = cursor.execute(f"SELECT {expressions} {base}", params).fetchone()
    trend = cursor.execute(f"SELECT f.month, {expressions} {base} GROUP BY f.month ORDER BY f.month", params).fetchall()
    breakdown = cursor.execute(f"""
        SELECT f.site_id, {expressions} {base} GROUP BY f.site_id ORDER BY f.site_id
    """, params).fetchall()
    return period, trend, breakdown


def value(metric, numerator, denominator):
    if numerator is None or (metric["denominator"] and not denominator):
        return None
    result = Decimal(numerator) * Decimal(str(metric["scale"]))
    if metric["denominator"]:
        result /= Decimal(denominator)
    return float(result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def rounded(number):
    return float(number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def dashboard_metric(cursor, domain, metric, start, end, site):
    period, trend, breakdown = query_metric(cursor, domain, metric, start, end, site)
    current = value(metric, *period)
    previous_start = f"{int(start[:4]) - 1}{start[4:]}"
    previous_end = f"{int(end[:4]) - 1}{end[4:]}"
    previous = None
    if previous_start in MONTHS and previous_end in MONTHS:
        previous_period, _, _ = query_metric(cursor, domain, metric, previous_start, previous_end, site)
        previous = value(metric, *previous_period)
    delta = None
    if current is not None and previous not in (None, 0):
        difference = Decimal(str(current)) - Decimal(str(previous))
        delta = rounded(difference if metric["unit"] == "%" else difference * 100 / Decimal(str(previous)))
    months = int(end[5:]) - int(start[5:]) + 1
    goal = metric["goal"] if metric["goal_basis"] == "period" else (metric["goal"] * months if site is None else None)
    return {
        "id": metric["id"], "value": current, "previous": previous, "delta": delta,
        "goal": goal, "trend_goal": metric["goal"] if goal is not None else None,
        "trend": [{"month": month, "value": value(metric, n, d)} for month, n, d in trend],
        "sites": [{"id": site_id, "value": value(metric, n, d)} for site_id, n, d in breakdown],
    }
