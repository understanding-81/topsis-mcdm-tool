from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"

OUTPUT_DIR.mkdir(exist_ok=True)


@app.route("/")
def health():
    return jsonify({"status": "TOPSIS backend running"})


def parse_weights(raw_value):
    values = [item.strip() for item in raw_value.split(",")]
    if not values or any(not item for item in values):
        return None
    try:
        weights = [float(item) for item in values]
    except ValueError:
        return None
    total = sum(weights)
    if not np.isfinite(weights).all() or not np.isfinite(total):
        return None
    if any(weight < 0 for weight in weights):
        return None
    if total <= 0:
        return None
    return weights


def parse_impacts(raw_value):
    impacts = [item.strip() for item in raw_value.split(",")]
    if not impacts or any(not item for item in impacts):
        return None
    if any(impact not in {"+", "-"} for impact in impacts):
        return None
    return impacts


def run_topsis(df, weights, impacts):
    data = df.iloc[:, 1:].values.astype(float)
    weights = np.array(weights)

    norm = np.sqrt((data**2).sum(axis=0))
    normalized = np.divide(data, norm, out=np.zeros_like(data), where=norm != 0)
    weighted = normalized * weights

    ideal_best, ideal_worst = [], []

    for i, impact in enumerate(impacts):
        if impact == "+":
            ideal_best.append(weighted[:, i].max())
            ideal_worst.append(weighted[:, i].min())
        else:
            ideal_best.append(weighted[:, i].min())
            ideal_worst.append(weighted[:, i].max())

    d_best = np.sqrt(((weighted - ideal_best) ** 2).sum(axis=1))
    d_worst = np.sqrt(((weighted - ideal_worst) ** 2).sum(axis=1))

    distance = d_best + d_worst
    scores = np.divide(
        d_worst,
        distance,
        out=np.full_like(d_worst, 0.5),
        where=distance != 0,
    )
    result = df.copy()
    result["Topsis Score"] = scores
    result["Rank"] = (
        result["Topsis Score"].rank(ascending=False, method="min").astype(int)
    )

    return result


@app.route("/api/topsis", methods=["POST"])
def topsis_api():
    file = request.files.get("file")
    weights_raw = request.form.get("weights", "")
    impacts_raw = request.form.get("impacts", "")

    if not file:
        return jsonify({"error": "CSV file required"}), 400

    if not weights_raw or not impacts_raw:
        return jsonify({"error": "Weights and impacts are required"}), 400

    weights = parse_weights(weights_raw)
    if weights is None:
        return jsonify(
            {
                "error": "Weights must be non-negative comma-separated numbers with a positive total"
            }
        ), 400

    impacts = parse_impacts(impacts_raw)
    if impacts is None:
        return jsonify({"error": "Impacts must be comma-separated + or - values"}), 400

    try:
        df = pd.read_csv(file)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeError):
        return jsonify({"error": "Uploaded file is not a valid CSV"}), 400

    if df.shape[1] < 3:
        return jsonify(
            {"error": "CSV must contain an identifier and at least two criteria"}
        ), 400

    if df.empty:
        return jsonify({"error": "CSV must contain at least one alternative"}), 400

    criteria_count = df.shape[1] - 1

    if len(weights) != criteria_count:
        return jsonify({"error": "Weights count mismatch"}), 400

    if len(impacts) != criteria_count:
        return jsonify({"error": "Impacts count mismatch"}), 400

    try:
        criteria = df.iloc[:, 1:].apply(pd.to_numeric, errors="raise")
    except (TypeError, ValueError):
        return jsonify({"error": "Criteria values must be numeric"}), 400

    if not np.isfinite(criteria.to_numpy()).all():
        return jsonify({"error": "Criteria values must be finite"}), 400

    validated_df = df.copy()
    validated_df.iloc[:, 1:] = criteria
    result_df = run_topsis(validated_df, weights, impacts)

    output_file = f"topsis_result_{uuid4().hex}.csv"
    output_path = OUTPUT_DIR / output_file
    result_df.to_csv(output_path, index=False)

    return jsonify(
        {
            "table": result_df.to_dict(orient="records"),
            "download": f"/api/download/{output_file}",
        }
    )


@app.route("/api/download/<filename>")
def download_file(filename):
    safe_name = secure_filename(filename)
    if not safe_name:
        return jsonify({"error": "Result file not found"}), 404
    output_path = OUTPUT_DIR / safe_name
    if not output_path.is_file():
        return jsonify({"error": "Result file not found"}), 404
    return send_file(output_path, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
