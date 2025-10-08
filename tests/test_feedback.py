from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def test_feedback_info():
    r = client.post("/feedback", json={
        "text": "Great flight",
        "predicted": "positive",
        "score": 0.9,
        "is_valid": True
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True

def test_feedback_warning():
    r = client.post("/feedback", json={
        "text": "Delayed flight",
        "predicted": "positive",
        "score": 0.8,
        "is_valid": False
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True
