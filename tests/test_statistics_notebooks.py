"""Execute notebook code against controlled API responses, without external requests."""

import base64
import hashlib
import io
import json
import threading
import unittest
from collections import Counter
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter


ROOT = Path(__file__).resolve().parents[1]
WHATS_NEW = "statistics-whats_new.ipynb"
INSPECTIONS = "inspections-invalid_multiple_facets_values.ipynb"
PROVIDER_ID = "A" * 32


def response(payload=None, status=200):
    result = requests.Response()
    result.status_code = status
    result.url = "https://example.test/api"
    result._content = json.dumps(payload).encode() if payload is not None else b"Proxy Error"
    return result


def execute_notebook(name):
    notebook = json.loads((ROOT / name).read_text(encoding="utf-8"))
    namespace = {}
    with patch("IPython.display.display") as display, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        try:
            for index, cell in enumerate(notebook["cells"]):
                if cell["cell_type"] == "code":
                    code = compile("".join(cell["source"]), f"{name}:cell{index}", "exec")
                    exec(code, namespace)
        finally:
            if "session" in namespace:
                namespace["session"].close()
    return namespace, [call.args[0] for call in display.call_args_list]


def supplier_id(value):
    digest = hashlib.sha1(f"www_fiz-karlsruhe_de{value}".encode()).digest()
    return base64.b32encode(digest).decode("ascii")


class WhatsNewTests(unittest.TestCase):
    def run_report(self, suppliers=("100",), missing=(), empty=False):
        calls = Counter()

        def get(session, url, **kwargs):
            self.assertIsNotNone(kwargs.get("timeout"), "API calls must have a timeout")
            if "/items/" in url:
                item_id = url.split("/items/", 1)[1].split("/", 1)[0]
                calls[item_id] += 1
                if item_id in {supplier_id(value) for value in missing}:
                    return response(status=404)
                name = "Provider <Archive>" if item_id == PROVIDER_ID else next(
                    f"Supplier {value}" for value in suppliers if supplier_id(value) == item_id
                )
                return response({"cortex-institution": {"name": name, "sector": "sec_01"}})

            params = dict(kwargs["params"])
            if "facet.pivot" in params:
                calls["pivot"] += 1
                pivots = [] if empty else [{
                    "value": "dataset-1",
                    "pivot": [{"value": PROVIDER_ID, "count": 7}],
                }]
                return response({"facet_counts": {"facet_pivot": {"dataset_id,dataprovider_id": pivots}}})

            calls["metadata"] += 1
            return response({"facet_counts": {"facet_fields": {
                "md_format": ["LIDO", 7],
                "dataset_label": ["Test dataset", 7],
                "type_fct": ["mediatype_002", 7],
                "supplier_id": [part for value in suppliers for part in (value, 7)],
            }}})

        with patch.object(requests.Session, "get", autospec=True, side_effect=get):
            namespace, displayed = execute_notebook(WHATS_NEW)
        return namespace["df"], displayed, calls

    def test_empty_period_is_a_successful_report(self):
        frame, displayed, calls = self.run_report(empty=True)
        self.assertTrue(frame.empty)
        self.assertIn("supplier_name", frame.columns)
        self.assertIn("dataset_id", frame.columns)
        self.assertTrue(any("Keine Treffer" in getattr(value, "data", "") for value in displayed))
        self.assertTrue(any("Letzte Aktualisierung" in getattr(value, "data", "") for value in displayed))
        self.assertEqual(calls, {"pivot": 1})

    def test_scalar_values_keep_counts_labels_and_links(self):
        frame, _, calls = self.run_report()
        self.assertEqual(len(frame), 1)
        row = frame.iloc[0]
        self.assertEqual(row["count"], 7)
        self.assertEqual(row["type_fct"], "Bild (7)")
        self.assertEqual(row["provider_sector"], "Archiv")
        self.assertIn(f'/organization/{PROVIDER_ID}"', row["provider_name"])
        self.assertIn("Provider &lt;Archive&gt;", row["provider_name"])
        self.assertIn(f'/organization/{supplier_id("100")}"', row["supplier_name"])
        self.assertIn("Supplier 100</a>", row["supplier_name"])
        self.assertIn("dataset_id%3Adataset-1", row["dataset_id"])
        self.assertEqual(calls[PROVIDER_ID], 1, "Repeated name/sector lookups should use the cache")
        self.assertEqual(calls[supplier_id("100")], 1)

    def test_multiple_suppliers_keep_their_own_labels_when_one_is_missing(self):
        frame, _, calls = self.run_report(suppliers=("100", "200", "300"), missing=("100",))
        links = frame.iloc[0]["supplier_name"]
        self.assertNotIn(supplier_id("100"), links)
        self.assertIn(f'/organization/{supplier_id("200")}" target="_blank">Supplier 200</a>', links)
        self.assertIn(f'/organization/{supplier_id("300")}" target="_blank">Supplier 300</a>', links)
        self.assertEqual(links.count("<a "), 2)
        self.assertTrue(all(calls[supplier_id(value)] == 1 for value in ("100", "200", "300")))

    def test_absent_supplier_is_rendered_without_a_link(self):
        frame, _, _ = self.run_report(suppliers=())
        self.assertEqual(frame.iloc[0]["supplier_name"], "")

    def test_http_failure_is_not_reported_as_an_empty_period(self):
        with patch.object(requests.Session, "get", return_value=response(status=503)):
            with self.assertRaises(requests.HTTPError):
                execute_notebook(WHATS_NEW)


@contextmanager
def local_api(statuses):
    """Route notebook HTTPS requests through their real adapter to a local HTTP API."""
    calls = Counter()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            endpoint = "organization" if "/organization/" in self.path else "facets"
            calls[endpoint] += 1
            sequence = statuses.get(endpoint, [200])
            status = sequence[min(calls[endpoint] - 1, len(sequence) - 1)]
            payload = {"response": {"docs": []}} if endpoint == "organization" else {
                "facets": {"providers": {"buckets": []}}
            }
            body = json.dumps(payload).encode() if status == 200 else b"<h1>Proxy Error</h1>"
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    worker.start()
    real_send = HTTPAdapter.send

    def send(adapter, request, **kwargs):
        original = urlsplit(request.url)
        request.url = f"http://127.0.0.1:{server.server_port}{original.path}?{original.query}"
        kwargs["proxies"] = {}
        return real_send(adapter, request, **kwargs)

    try:
        with patch.object(HTTPAdapter, "send", send), patch("urllib3.util.retry.time.sleep"):
            yield calls
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


class RetryTests(unittest.TestCase):
    def test_temporary_server_errors_recover_and_finish_the_notebook(self):
        with local_api({"organization": [500, 502, 200], "facets": [503, 200]}) as calls:
            namespace, _ = execute_notebook(INSPECTIONS)
        self.assertTrue(namespace["df_org"].empty)
        self.assertEqual(calls["organization"], 3)
        self.assertEqual(calls["facets"], 3)  # retry first facet, then execute second facet

    def test_persistent_proxy_error_is_bounded_and_preserves_http_status(self):
        with local_api({"facets": [502]}) as calls:
            with self.assertRaises(requests.HTTPError) as failure:
                execute_notebook(INSPECTIONS)
        self.assertEqual(failure.exception.response.status_code, 502)
        self.assertEqual(calls["facets"], 4)

    def test_persistent_organization_failure_stops_after_four_attempts(self):
        with local_api({"organization": [500]}) as calls:
            with self.assertRaises(requests.HTTPError) as failure:
                execute_notebook(INSPECTIONS)
        self.assertEqual(failure.exception.response.status_code, 500)
        self.assertEqual(calls, {"organization": 4})

    def test_client_errors_are_not_retried(self):
        with local_api({"organization": [404]}) as calls:
            with self.assertRaises(requests.HTTPError):
                execute_notebook(INSPECTIONS)
        self.assertEqual(calls, {"organization": 1})


if __name__ == "__main__":
    unittest.main()
