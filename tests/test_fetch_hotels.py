"""Offline tests for the AppSync client seam in src/frontend/search_hotels.py.

Run from the repository root:
    python -m unittest discover -s tests
"""
import os
import sys
import unittest
from unittest import mock

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "frontend"))

import search_hotels  # noqa: E402
from search_hotels import AppSyncError, fetch_hotels  # noqa: E402


def fake_response(status=200, json_body=None, json_error=None):
    resp = mock.Mock()
    resp.status_code = status
    resp.ok = 200 <= status < 400
    if json_error is not None:
        resp.json.side_effect = json_error
    else:
        resp.json.return_value = json_body
    return resp


class FetchHotelsTest(unittest.TestCase):
    def call(self, response=None, side_effect=None):
        with mock.patch.object(search_hotels.requests, "post") as post:
            if side_effect is not None:
                post.side_effect = side_effect
            else:
                post.return_value = response
            result = fetch_hotels("https://example/graphql", "key", "Les Loges", 100)
        return post, result

    def test_sends_query_variables_api_key_and_timeout(self):
        body = {"data": {"listHotelsNearAirport": {"hotels": [{"id": 1}], "airport": {"name": "Les Loges"}}}}
        post, result = self.call(fake_response(json_body=body))

        self.assertEqual(result, {"hotels": [{"id": 1}], "airport": {"name": "Les Loges"}})
        _, kwargs = post.call_args
        self.assertEqual(kwargs["headers"], {"x-api-key": "key"})
        self.assertEqual(kwargs["json"]["variables"], {"airportName": "Les Loges", "withinKm": 100})
        self.assertIn("listHotelsNearAirport(airportName: $airportName, withinKm: $withinKm)", kwargs["json"]["query"])
        self.assertEqual(kwargs["timeout"], search_hotels.REQUEST_TIMEOUT_SECONDS)

    def test_null_result_and_null_hotels_normalise_to_empty(self):
        _, result = self.call(fake_response(json_body={"data": {"listHotelsNearAirport": None}}))
        self.assertEqual(result, {"hotels": [], "airport": None})

        _, result = self.call(fake_response(json_body={"data": {"listHotelsNearAirport": {"hotels": None, "airport": None}}}))
        self.assertEqual(result, {"hotels": [], "airport": None})

    def test_graphql_errors_raise_with_messages(self):
        body = {"data": None, "errors": [{"errorType": "UnauthorizedException", "message": "You are not authorized"}]}
        with self.assertRaisesRegex(AppSyncError, "You are not authorized"):
            self.call(fake_response(status=401, json_body=body))

    def test_non_json_body_raises_readable_error(self):
        with self.assertRaisesRegex(AppSyncError, "non-JSON response \\(HTTP 404\\)"):
            self.call(fake_response(status=404, json_error=ValueError("Expecting value")))

    def test_http_error_without_graphql_errors_raises(self):
        with self.assertRaisesRegex(AppSyncError, "HTTP 502"):
            self.call(fake_response(status=502, json_body={"message": "Bad gateway"}))

    def test_network_failure_raises(self):
        with self.assertRaisesRegex(AppSyncError, "Could not reach"):
            self.call(side_effect=requests.ConnectionError("boom"))
        with self.assertRaisesRegex(AppSyncError, "Could not reach"):
            self.call(side_effect=requests.Timeout("slow"))


if __name__ == "__main__":
    unittest.main()
