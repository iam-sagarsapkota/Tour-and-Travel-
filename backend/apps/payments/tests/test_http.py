"""The real HTTP helper, exercised against a throwaway local server."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from apps.payments.gateways import GatewayError, http_json


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep test output quiet
        pass

    def _reply(self, status, body):
        payload = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self._reply(200, {"path": self.path})

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        if self.path == "/lookup":
            # Khalti answers "User canceled" with HTTP 400 and a JSON body.
            self._reply(400, {"status": "User canceled", "echo": body})
        elif self.path == "/broken":
            self._reply(502, b"<html>Bad gateway</html>")
        else:
            self._reply(200, {"auth": self.headers["Authorization"], "echo": body})


@pytest.fixture(scope="module")
def server():
    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def test_get_with_query(server):
    status, data = http_json("GET", f"{server}/status", params={"a": "1", "b": "x y"})
    assert status == 200
    assert data == {"path": "/status?a=1&b=x+y"}


def test_post_json_with_headers(server):
    status, data = http_json(
        "POST", f"{server}/initiate", body={"amount": 1000}, headers={"Authorization": "Key k"}
    )
    assert (status, data) == (200, {"auth": "Key k", "echo": {"amount": 1000}})


def test_error_status_still_returns_json(server):
    status, data = http_json("POST", f"{server}/lookup", body={"pidx": "P"})
    assert status == 400
    assert data["status"] == "User canceled"


def test_non_json_error_raises(server):
    with pytest.raises(GatewayError):
        http_json("POST", f"{server}/broken", body={})


def test_unreachable_host_raises(settings):
    settings.PAYMENT_HTTP_TIMEOUT = 2
    with pytest.raises(GatewayError):
        http_json("GET", "http://127.0.0.1:9/nothing-listens-here")
