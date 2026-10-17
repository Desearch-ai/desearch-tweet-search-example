"""Offline tests for the HTTP layer: a fake client stands in for the Desearch API."""
import importlib.util, pathlib, threading, urllib.error, urllib.request
from http.server import ThreadingHTTPServer

import pytest

import app

POST = {"id": "42", "text": "gm @someone", "created_at": "Sat Oct 17 08:00:00 +0000 2026", "lang": "en",
        "like_count": 3, "reply_count": 0, "retweet_count": 1, "user": {"username": "someone"}, "media": []}


class FakeClient:
    def __init__(self, status=200, body=None):
        self.calls, self.status, self.body = [], status, [POST] if body is None else body

    def search(self, params, tag="search"):
        self.calls.append(params)
        return self.status, self.body, {"latency_s": 0.1}


@pytest.fixture
def serve():
    servers = []

    def start(client):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler(client))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        servers.append(srv)
        return f"http://127.0.0.1:{srv.server_address[1]}"
    yield start
    for s in servers:
        s.shutdown()


def get(url):
    try:
        r = urllib.request.urlopen(url, timeout=5)
        return r.status, dict(r.headers), r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode()


def test_bad_form_is_400_and_makes_no_call(serve):
    c = FakeClient()
    base = serve(c)
    for q in ("/search?q=", "/search?q=x&start_date=2026-10-10&end_date=2026-10-01", "/search?q=x&count=500"):
        assert get(base + q)[0] == 400
    assert c.calls == []


def test_search_page_and_csv(serve):
    c = FakeClient()
    base = serve(c)
    st, _, page = get(base + "/search?q=desearch&any=bittensor,subnet&count=5")
    assert st == 200 and "1 of 5 requested posts returned" in page and "someone" not in page
    assert c.calls[0]["query"] == "desearch (bittensor OR subnet)" and "exclude_domains" not in c.calls[0]
    st, hd, csv_text = get(base + "/search.csv?q=desearch&count=5")
    assert st == 200 and hd["Content-Type"].startswith("text/csv") and "https://x.com/i/status/42" in csv_text


def test_api_error_is_502(serve):
    assert get(serve(FakeClient(status=503, body={"detail": "x"})) + "/search?q=x")[0] == 502


def test_home_and_404(serve):
    base = serve(FakeClient())
    assert get(base + "/")[0] == 200 and get(base + "/nope")[0] == 404


def test_key_from_env_or_file(tmp_path, monkeypatch):
    f = tmp_path / "k"
    f.write_text("FILEKEY\n")
    monkeypatch.delenv("DESEARCH_API_KEY", raising=False)
    monkeypatch.setenv("DESEARCH_API_KEY_FILE", str(f))
    assert app.api_key() == "FILEKEY"
    monkeypatch.setenv("DESEARCH_API_KEY", "ENVKEY")
    assert app.api_key() == "ENVKEY"
    monkeypatch.delenv("DESEARCH_API_KEY")
    monkeypatch.delenv("DESEARCH_API_KEY_FILE")
    with pytest.raises(SystemExit):
        app.api_key()


def test_filter_check_tool_sends_no_exclude_domains():
    p = pathlib.Path(__file__).resolve().parent.parent / "tools" / "filter_check.py"
    spec = importlib.util.spec_from_file_location("filter_check", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.CHECKS and all("exclude_domains" not in extra for _, extra in mod.CHECKS)
