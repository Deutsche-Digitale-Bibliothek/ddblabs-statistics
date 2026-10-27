"""Regression tests for the newspaper map without external API requests."""

from io import BytesIO
import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock, Mock, patch

import folium
import pandas as pd
import requests
from urllib3.response import HTTPResponse


NOTEBOOK = Path(__file__).resolve().parents[1] / "statistics-dzp-title_map.ipynb"
MARKER_COLUMNS = ["id", "title", "all_locations", "location_for_coord", "lon", "lat"]


class NewspaperMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        cls.code = ["".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"]

    def setUp(self):
        self.namespace = {}
        exec(compile(self.code[0], str(NOTEBOOK), "exec"), self.namespace)
        self.namespace["display"] = Mock()
        self.namespace["tqdm"] = MagicMock()

    def run_map_cell(self, docs, entityfacts):
        response = Mock()
        response.json.return_value = {
            "response": {"numFound": len(docs), "docs": docs},
            "nextCursorMark": "*",
        }
        with (
            patch.object(requests.Session, "get", return_value=response) as solr_get,
            patch.object(requests, "get", side_effect=entityfacts) as entityfacts_get,
            patch.object(folium, "GeoJson", return_value=folium.FeatureGroup()),
        ):
            exec(compile(self.code[1], str(NOTEBOOK), "exec"), self.namespace)
        solr_get.assert_called_once()
        response.raise_for_status.assert_called_once()
        self.assertIn("leaflet", self.namespace["m"].get_root().render())
        return entityfacts_get

    def test_empty_solr_result_still_renders_map(self):
        entityfacts_get = self.run_map_cell([], AssertionError("Unexpected EntityFacts request"))
        entityfacts_get.assert_not_called()
        self.assertTrue(self.namespace["newspapers_with_issues"].empty)
        self.assertEqual(self.namespace["marker_df"].columns.tolist(), MARKER_COLUMNS)
        self.assertEqual(self.namespace["marker_count"], 0)

    def test_all_entityfacts_requests_fail_still_renders_map(self):
        docs = [{
            "id": "newspaper-1", "title": "Example newspaper",
            "locationUri": ["https://d-nb.info/gnd/first", "https://d-nb.info/gnd/second"],
            "location": ["First", "Second"],
        }]
        entityfacts_get = self.run_map_cell(docs, requests.ConnectionError("Unavailable"))
        self.assertEqual(entityfacts_get.call_count, 2)
        self.assertTrue(self.namespace["marker_df"].empty)
        self.assertEqual(self.namespace["marker_count"], 0)
        self.assertTrue(self.namespace["display"].call_args_list[0].args[0].data.endswith("0 in 0 Markern"))

    def test_failed_first_entityfacts_request_keeps_second_location(self):
        docs = [{
            "id": "newspaper-1", "title": "Example newspaper",
            "locationUri": ["https://d-nb.info/gnd/first", "https://d-nb.info/gnd/second"],
            "location": ["First", "Second"],
        }]

        def entityfacts(url, **kwargs):
            if url.endswith("/first"):
                raise requests.ConnectionError("Unavailable")
            response = Mock()
            response.json.return_value = {"location": {"geometry": {"coordinates": [13, 52]}}}
            return response

        self.run_map_cell(docs, entityfacts)
        marker = self.namespace["marker_df"].iloc[0]
        self.assertEqual(marker["location_for_coord"], "Second")
        self.assertEqual((marker["lon"], marker["lat"]), (13, 52))
        self.assertEqual(self.namespace["marker_count"], 1)

    def test_invalid_coordinates_do_not_shift_location_names(self):
        for first_coords in [None, float("nan"), [], ["invalid", 51], [12, float("nan")]]:
            with self.subTest(first_coords=first_coords):
                data = pd.DataFrame([{
                    "id": "newspaper-1", "title": "Example newspaper",
                    "location": ["First", "Second"],
                    "locationCoords": [first_coords, ["13", "52"]],
                }])
                markers = self.namespace["build_marker_dataframe"](data)
                self.assertEqual(len(markers), 1)
                self.assertEqual(markers.iloc[0]["location_for_coord"], "Second")
                self.assertEqual((markers.iloc[0]["lon"], markers.iloc[0]["lat"]), (13, 52))

    def test_no_valid_coordinates_preserves_marker_columns(self):
        for coords in [None, float("nan"), [None, None], ["invalid", "invalid"]]:
            with self.subTest(coords=coords):
                data = pd.DataFrame([{
                    "id": "newspaper-1", "title": "Example newspaper",
                    "location": ["First", "Second"], "locationCoords": coords,
                }])
                markers = self.namespace["build_marker_dataframe"](data)
                self.assertTrue(markers.empty)
                self.assertEqual(markers.columns.tolist(), MARKER_COLUMNS)

    def test_solr_retries_transient_get_failures(self):
        session = requests.Session()
        session.trust_env = False
        body = json.dumps({"response": {"numFound": 0, "docs": []}, "nextCursorMark": "*"}).encode()
        responses = [
            HTTPResponse(status=502, body=BytesIO(b"Bad Gateway"), preload_content=False),
            HTTPResponse(status=200, body=BytesIO(body), preload_content=False),
        ]
        with (
            patch.object(requests, "Session", return_value=session),
            patch("urllib3.connectionpool.HTTPConnectionPool._make_request", side_effect=responses) as request,
            patch("urllib3.util.retry.Retry.sleep"),
        ):
            result = self.namespace["solr_to_dataframe"]("https://example.test/select")
        self.assertTrue(result.empty)
        self.assertEqual(request.call_count, 2)


if __name__ == "__main__":
    unittest.main()
