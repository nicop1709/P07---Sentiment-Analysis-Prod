from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def test_predict_positive():
    r = client.post("/predict", json={"text": "I love this product, amazing!"})
    assert r.status_code == 200
    body = r.json()
    assert body["sentiment"] in ("positive", "negative")
    # Avec ton fallback, "love" -> score >= 0.5, donc "positive"
    assert body["sentiment"] == "positive"
    assert 0.0 <= body["score"] <= 1.0
    assert "latency_ms" in body

def test_predict_negative():
    r = client.post("/predict", json={"text": "I hate this, awful!"})
    assert r.status_code == 200
    assert r.json()["sentiment"] == "negative"
