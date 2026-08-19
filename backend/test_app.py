import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as app_module


class TopsisApiTest(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        self.output_directory = tempfile.TemporaryDirectory()
        self.output_patch = patch.object(
            app_module,
            "OUTPUT_DIR",
            Path(self.output_directory.name),
        )
        self.output_patch.start()

    def tearDown(self):
        self.output_patch.stop()
        self.output_directory.cleanup()

    def post_csv(self, csv_content, weights="1,1", impacts="+,-"):
        return self.client.post(
            "/api/topsis",
            data={
                "file": (io.BytesIO(csv_content), "input.csv"),
                "weights": weights,
                "impacts": impacts,
            },
            content_type="multipart/form-data",
        )

    def test_missing_fields_return_bad_request(self):
        response = self.client.post("/api/topsis", data={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "CSV file required"})

        response = self.post_csv(b"name,cost,quality\na,1,2\n", weights="")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(), {"error": "Weights and impacts are required"}
        )

    def test_malformed_weights_return_bad_request(self):
        csv_content = b"name,cost,quality\na,1,2\n"
        for weights in (
            "1,,2",
            "one,2",
            "nan,2",
            "1e308,1e308",
            "-1,2",
            "0,0",
        ):
            with self.subTest(weights=weights):
                response = self.post_csv(csv_content, weights=weights)
                self.assertEqual(response.status_code, 400)
                self.assertIn("Weights", response.get_json()["error"])

    def test_malformed_impacts_return_bad_request(self):
        csv_content = b"name,cost,quality\na,1,2\n"
        for impacts in ("+,,", "+,gain"):
            with self.subTest(impacts=impacts):
                response = self.post_csv(csv_content, impacts=impacts)
                self.assertEqual(response.status_code, 400)
                self.assertIn("Impacts", response.get_json()["error"])

    def test_field_count_mismatches_return_bad_request(self):
        csv_content = b"name,cost,quality\na,1,2\n"
        response = self.post_csv(csv_content, weights="1")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "Weights count mismatch"})

        response = self.post_csv(csv_content, impacts="+")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "Impacts count mismatch"})

    def test_invalid_csv_uploads_return_bad_request(self):
        cases = (
            (b"", "Uploaded file is not a valid CSV"),
            (b"\xff\xfe\x00", "Uploaded file is not a valid CSV"),
            (
                b"name,cost\na,1\n",
                "CSV must contain an identifier and at least two criteria",
            ),
            (b"name,cost,quality\n", "CSV must contain at least one alternative"),
            (b"name,cost,quality\na,one,2\n", "Criteria values must be numeric"),
            (b"name,cost,quality\na,NaN,2\n", "Criteria values must be finite"),
        )
        for csv_content, error in cases:
            with self.subTest(error=error):
                response = self.post_csv(csv_content)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json(), {"error": error})

    def test_valid_csv_returns_ranked_table_and_download(self):
        response = self.post_csv(
            b"name,cost,quality\na,10,8\nb,5,6\n",
            weights="1,2",
            impacts="-,+",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload["table"]), 2)
        self.assertEqual(sorted(row["Rank"] for row in payload["table"]), [1, 2])
        self.assertRegex(
            payload["download"], r"^/api/download/topsis_result_[0-9a-f]{32}\.csv$"
        )

        download = self.client.get(payload["download"])
        self.assertEqual(download.status_code, 200)
        self.assertIn(b"Topsis Score,Rank", download.data)
        download.close()

    def test_zero_criteria_produce_stable_ties(self):
        response = self.post_csv(
            b"name,cost,quality\na,0,0\nb,0,0\n",
            weights="1,1",
            impacts="-,+",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [
                (row["Topsis Score"], row["Rank"])
                for row in response.get_json()["table"]
            ],
            [(0.5, 1), (0.5, 1)],
        )

    def test_download_rejects_invalid_and_missing_names(self):
        for url in ("/api/download/..", "/api/download/missing.csv"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(
                    response.get_json(), {"error": "Result file not found"}
                )


if __name__ == "__main__":
    unittest.main()
