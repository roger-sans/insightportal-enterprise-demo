from contextlib import closing
from pathlib import Path
import sqlite3

from .warehouse import DOMAINS

ACTORS = {
    "analyst": "Business Analyst",
    "product-owner": "Product Owner",
    "governance": "Data Governance",
    "release-manager": "Release Lead",
    **{f"{key}-steward": domain["owner"] for key, domain in DOMAINS.items()},
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS request (
    id INTEGER PRIMARY KEY,
    domain TEXT NOT NULL, title TEXT NOT NULL, rationale TEXT NOT NULL,
    requester TEXT NOT NULL, kind TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'submitted',
    impact INTEGER NOT NULL CHECK(impact BETWEEN 1 AND 5),
    urgency INTEGER NOT NULL CHECK(urgency BETWEEN 1 AND 5),
    effort INTEGER NOT NULL CHECK(effort BETWEEN 1 AND 5),
    version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS decision (
    id INTEGER PRIMARY KEY, request_id INTEGER NOT NULL REFERENCES request(id),
    actor TEXT NOT NULL, action TEXT NOT NULL, note TEXT NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE TABLE IF NOT EXISTS feedback (
    domain TEXT NOT NULL, actor TEXT NOT NULL, rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    PRIMARY KEY (domain, actor)
);
"""

SEED = (
    ("finance", "Reconcile bookings with recognised revenue",
     "Finance and Sales need a bridge showing when signed work becomes recognised revenue.",
     "analyst", "data-contract", "triaged", 5, 5, 3, 2),
    ("operations", "Explain missed service commitments",
     "Dispatch needs a standard split by fulfilment reason for the operations review.",
     "analyst", "enhancement", "accepted", 5, 4, 2, 3),
    ("people", "Validate regional cohort coverage",
     "People leadership needs evidence of safe aggregation before deeper segmentation.",
     "analyst", "quality", "submitted", 4, 5, 3, 1),
    ("commercial", "Track first-use of the sales product",
     "Sales Operations wants to verify that regional team leads can find the KPI definitions.",
     "analyst", "enhancement", "released", 3, 3, 1, 4),
)


class Conflict(Exception):
    pass


class InvalidDecision(Exception):
    pass


class MissingRequest(Exception):
    pass


class Workflow:
    def __init__(self, path: Path):
        self.path = path

    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as conn, conn:
            conn.executescript(SCHEMA)
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT COUNT(*) FROM request").fetchone()[0]:
                return
            for seed in SEED:
                cursor = conn.execute("""
                    INSERT INTO request(domain, title, rationale, requester, kind, state, impact, urgency, effort, version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, seed)
                domain, _, _, requester, _, _, _, _, _, version = seed
                evidence = [
                    (requester, "submit", "Captured for the monthly product review.", "2026-09-22T09:00:00Z"),
                    ("product-owner", "triage", "Ranked against the current outcome and available delivery capacity.", "2026-09-23T09:00:00Z"),
                    (f"{domain}-steward", "accept", "Domain criteria and acceptance evidence agreed.", "2026-09-24T09:00:00Z"),
                    ("release-manager", "release", "Acceptance reviewed in a simulated stakeholder walkthrough.", "2026-09-30T09:00:00Z"),
                ]
                conn.executemany("""
                    INSERT INTO decision(request_id, actor, action, note, recorded_at) VALUES (?, ?, ?, ?, ?)
                """, [(cursor.lastrowid, *entry) for entry in evidence[:version]])

    def list(self):
        with closing(self.connect()) as conn:
            conn.execute("BEGIN")
            rows = conn.execute("""
                SELECT *, impact * 3 + urgency * 2 - effort AS score
                FROM request ORDER BY score DESC, id ASC
            """).fetchall()
            audit = conn.execute("SELECT * FROM decision ORDER BY id").fetchall()
        decisions = {}
        for event in audit:
            decisions.setdefault(event["request_id"], []).append(dict(event))
        return [{**dict(row), "history": decisions.get(row["id"], [])} for row in rows]

    def submit(self, request):
        with closing(self.connect()) as conn, conn:
            cursor = conn.execute("""
                INSERT INTO request(domain, title, rationale, requester, kind, impact, urgency, effort)
                VALUES (:domain, :title, :rationale, :requester, :kind, :impact, :urgency, :effort)
            """, request)
            key = cursor.lastrowid
            conn.execute("INSERT INTO decision (request_id, actor, action, note) VALUES (?, ?, 'submit', ?)",
                         (key, request["requester"], request["rationale"]))
        return key

    def decide(self, key, version, actor, action, note):
        with closing(self.connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM request WHERE id = ?", (key,)).fetchone()
            if row is None:
                raise MissingRequest
            if row["version"] != version:
                raise Conflict("This request changed. Reload it before deciding.")
            steward = f"{row['domain']}-steward"
            reviewer_for_domain = "governance" if row["requester"] == steward else steward
            transitions = {
                ("submitted", "triage"): ("triaged", "product-owner"),
                ("triaged", "accept"): ("accepted", reviewer_for_domain),
                ("triaged", "decline"): ("declined", reviewer_for_domain),
                ("accepted", "release"): ("released", "release-manager"),
            }
            transition = transitions.get((row["state"], action))
            if not transition:
                raise InvalidDecision("This action is unavailable for the current state.")
            state, reviewer = transition
            if actor != reviewer or actor == row["requester"]:
                raise InvalidDecision("Select the assigned independent simulated reviewer.")
            conn.execute("UPDATE request SET state = ?, version = version + 1 WHERE id = ?", (state, key))
            conn.execute("INSERT INTO decision (request_id, actor, action, note) VALUES (?, ?, ?, ?)",
                         (key, actor, action, note))

    def feedback(self, domain, actor, rating):
        with closing(self.connect()) as conn, conn:
            conn.execute("""
                INSERT INTO feedback (domain, actor, rating) VALUES (?, ?, ?)
                ON CONFLICT(domain, actor) DO UPDATE SET rating = excluded.rating
            """, (domain, actor, rating))

    def adoption(self):
        with closing(self.connect()) as conn:
            feedback = {row["domain"]: {"count": row["responses"], "average": row["average"]}
                        for row in conn.execute("""
                            SELECT domain, COUNT(*) AS responses, ROUND(AVG(rating), 2) AS average
                            FROM feedback GROUP BY domain
                        """)}
        # Cohorts are synthetic and can overlap. Only within-domain totals are meaningful.
        return [
            {"id": key, "eligible": eligible, "active": active, "returning": returning, "weeks": weeks,
             "survey_count": responses, "survey_average": satisfaction,
             "local_feedback": feedback.get(key, {"count": 0, "average": None})}
            for key, eligible, active, returning, weeks, responses, satisfaction in (
                ("finance", 42, 34, 27, [22, 25, 31, 34], 13, 4.5),
                ("commercial", 92, 64, 48, [41, 48, 53, 64], 24, 4.2),
                ("operations", 125, 79, 53, [55, 63, 72, 79], 27, 3.8),
                ("people", 30, 18, 13, [12, 11, 15, 18], 9, 4.1),
            )
        ]
