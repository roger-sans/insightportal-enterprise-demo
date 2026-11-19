# Snowflake consumption and parity

The FastAPI reader can target Snowflake using the official Python connector. It uses the same parameterised SQL, KPI registry and response shapes as the local mode. The supplied setup is limited to reproducible **synthetic** analytics. Snowflake was unavailable during validation of this release. We parsed the Snowflake DDL and exercised the SQLite reference and the remote-mode failure path locally. Account-side privileges, cloud execution and parity still need verification.

## Isolated setup

1. Create a dedicated, empty schema and choose a small auto-suspending warehouse in a Snowflake test database.
2. Install `python -m pip install -r requirements-snowflake.txt` in the local environment.
3. Export `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`, `SNOWFLAKE_SCHEMA` and `SNOWFLAKE_ROLE` for a test principal authorised to create tables in that schema. Supply secrets through your environment.
4. Run `python -m insightportal.snowflake_demo --load`. This creates seven tables from [DDL](../warehouse/schema.sql), populates the deterministic fixture and compares quality, KPI totals, trend, breakdown, goals and prior-year values for three filter scopes across all eight metrics. The loader refuses to run when the schema already contains objects. Snowflake DDL commits independently, so a failed partial load needs a fresh empty test schema.
5. Give a dedicated reader role schema, database and warehouse usage and table SELECT using the [grant example](../warehouse/snowflake/roles.sql). Set the same connection variables to that reader and run `python -m insightportal.snowflake_demo` again to verify least-privilege parity.
6. With the frontend built, run `WAREHOUSE_MODE=snowflake python -m uvicorn insightportal.main:app --host 127.0.0.1 --port 8000` and confirm **Snowflake** under Data health. Requests and feedback continue to use local SQLite.

The demo assumes a stable serving schema throughout a query. Schedule a refresh into a new versioned schema and verify it before switching a live reader in future work. Use a read-only role and replace interactive credentials with managed authentication before any managed pilot.

Snowflake standard-table primary and foreign keys act as metadata. The runtime gate independently checks duplicates, orphan values, coverage and metric constraints so the reader can withhold invalid analytics. SQLite enforces keys and local foreign-key checks. The synthetic DDL uses the same string keys and integer measures on both engines.

[Snowflake Python connector API](https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-api) · [Snowflake constraints](https://docs.snowflake.com/en/sql-reference/constraints-overview)
