import pytest
from fastapi.testclient import TestClient
from main import app
client = TestClient(app)
def test_health():
    r = client.get('/api/health')
    assert r.status_code == 200
