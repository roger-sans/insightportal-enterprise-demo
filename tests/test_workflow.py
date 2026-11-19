from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from insightportal.main import create_app

REQUEST = {
    "domain": "finance", "title": "Add a quarter-close reconciliation",
    "rationale": "Verify opening bookings against their close-month classifications.",
    "requester": "analyst", "kind": "data-contract", "impact": 5, "urgency": 4, "effort": 3,
}


def decide(client, key, action, actor, version):
    return client.post(f"/api/v1/requests/{key}/decisions", json={
        "action": action, "actor": actor, "version": version,
        "note": "Business evidence was reviewed and criteria were recorded.",
    })


def test_routes_are_in_openapi(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        paths = client.get("/openapi.json").json()["paths"]
        assert {"get", "post"} == set(paths["/api/v1/requests"])
        assert "/api/v1/dashboard" in paths
        assert "/api/v1/adoption/feedback" in paths


def test_full_workflow_persists_and_is_audited(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        response = client.post("/api/v1/requests", json=REQUEST)
        assert response.status_code == 201
        row = response.json()
        key = row["id"]
        assert row["score"] == 20
        assert decide(client, key, "release", "release-manager", 1).status_code == 422
        assert decide(client, key, "triage", "product-owner", 1).json()["state"] == "triaged"
        assert decide(client, key, "accept", "commercial-steward", 2).status_code == 422
        assert decide(client, key, "accept", "finance-steward", 2).json()["state"] == "accepted"
        assert decide(client, key, "release", "release-manager", 3).json()["state"] == "released"
    with TestClient(create_app(tmp_path)) as client:
        entries = client.get("/api/v1/requests").json()
        row = next(item for item in entries if item["id"] == key)
        assert row["version"] == 4
        assert [e["action"] for e in row["history"]] == ["submit", "triage", "accept", "release"]
        assert len(entries) == 5
        assert [item["score"] for item in entries] == sorted((item["score"] for item in entries), reverse=True)


def test_secondary_reviewer_can_decline_a_steward_request(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        key = client.post("/api/v1/requests", json={**REQUEST, "requester": "finance-steward"}).json()["id"]
        assert decide(client, key, "triage", "product-owner", 1).status_code == 200
        assert decide(client, key, "accept", "finance-steward", 2).status_code == 422
        assert decide(client, key, "decline", "governance", 2).json()["state"] == "declined"
        assert decide(client, key, "release", "release-manager", 3).status_code == 422


def test_simultaneous_decisions_have_one_winner(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        key = client.post("/api/v1/requests", json=REQUEST).json()["id"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: decide(client, key, "triage", "product-owner", 1).status_code, range(2)))
        assert sorted(outcomes) == [200, 409]
        row = next(item for item in client.get("/api/v1/requests").json() if item["id"] == key)
        assert row["version"] == 2
        assert len(row["history"]) == 2


def test_mutations_validate_payload_and_origin(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.post("/api/v1/requests", json={**REQUEST, "impact": 6}).status_code == 422
        assert client.post("/api/v1/requests", json={**REQUEST, "domain": "other"}).status_code == 422
        assert client.post("/api/v1/requests", json={**REQUEST, "requester": "people-steward"}).status_code == 422
        assert client.post("/api/v1/requests", data=REQUEST).status_code == 415
        assert client.post("/api/v1/requests", json=REQUEST, headers={"Origin": "https://elsewhere.test"}).status_code == 403
        assert client.post("/api/v1/requests", json=REQUEST, headers={"Origin": "http://testserver"}).status_code == 201


def test_feedback_is_persistent_and_within_demo_domains(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        query = {"domain": "people", "actor": "analyst", "rating": 5}
        result = client.post("/api/v1/adoption/feedback", json=query).json()
        assert result["local_feedback"] == {"count": 1, "average": 5.0}
        assert result["survey_count"] == 9
        assert client.post("/api/v1/adoption/feedback", json={**query, "actor": "finance-steward"}).status_code == 422
        assert client.post("/api/v1/adoption/feedback", json={**query, "rating": 8}).status_code == 422
        client.post("/api/v1/adoption/feedback", json={**query, "rating": 3})
    with TestClient(create_app(tmp_path)) as client:
        row = next(item for item in client.get("/api/v1/adoption").json() if item["id"] == "people")
        assert row["local_feedback"] == {"count": 1, "average": 3.0}
