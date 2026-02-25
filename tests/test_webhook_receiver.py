import hashlib
import hmac
import json

from fastapi.testclient import TestClient
from webhook_receiver.app import app
from shared.services.config import settings


client = TestClient(app)


def make_signature(body: bytes) -> str:
      sig = hmac.new(settings.app_secret.encode(), body, hashlib.sha256).hexdigest()
      return f"sha256={sig}"


def test_health():
      resp = client.get("/health")
      assert resp.status_code == 200
      assert resp.json() == {"status": "ok"}
      print("Health OK")


def test_verify():
      resp = client.get("/webhook", params={
          "hub.verify_token": settings.verify_token,
          "hub.challenge": "test_challenge_123",
      })
      assert resp.status_code == 200
      assert resp.text == "test_challenge_123"
      print("Verify OK")


def test_bad_signature():
      resp = client.post("/webhook", content=b'{}', headers={
          "x-hub-signature-256": "sha256=wrong",
      })
      assert resp.status_code == 401
      print("Bad signature rejected OK")


if __name__ == "__main__":
      test_health()
      test_verify()
      test_bad_signature()
      print("All webhook tests OK")