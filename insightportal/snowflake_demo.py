"""Load a fresh Snowflake demo schema and compare it with the local semantics."""
import argparse

from .warehouse import DOMAINS, dashboard_metric, populate, quality, snowflake_connection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--load", action="store_true", help="create and load tables in an empty dedicated schema")
    args = parser.parse_args()

    import sqlite3

    with snowflake_connection() as remote:
        if args.load:
            with remote.cursor() as cursor:
                if cursor.execute("SHOW OBJECTS IN SCHEMA").fetchall():
                    parser.error("use an empty dedicated Snowflake schema")
            populate(remote)
        local = sqlite3.connect(":memory:")
        try:
            populate(local)
            for domain in DOMAINS.values():
                with remote.cursor() as rf:
                    lf = local.cursor()
                    if quality(rf, domain) != quality(lf, domain):
                        raise SystemExit(f"Quality parity differs for {domain['id']}")
                    for metric in domain["metrics"]:
                        for start, end, site in (
                            ("2026-01", "2026-09", None),
                            ("2026-03", "2026-06", "metro"),
                            ("2025-01", "2025-12", "harbor"),
                        ):
                            if dashboard_metric(rf, domain, metric, start, end, site) != dashboard_metric(
                                lf, domain, metric, start, end, site
                            ):
                                raise SystemExit(f"Semantic parity differs for {metric['id']}")
        finally:
            local.close()
    print("Snowflake parity passed for all four products and eight metrics.")


if __name__ == "__main__":
    main()
