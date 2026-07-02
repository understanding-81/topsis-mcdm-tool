from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import numpy as np
from pathlib import Path
from uuid import uuid4
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

@app.route("/")
def health():
    return jsonify({"status": "TOPSIS backend running"})

def run_topsis(df, weights, impacts):
    data = df.iloc[:, 1:].values.astype(float)
    weights = np.array(weights)

    norm = np.sqrt((data ** 2).sum(axis=0))
    normalized = data / norm
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

    df["Topsis Score"] = d_worst / (d_best + d_worst)
    df["Rank"] = df["Topsis Score"].rank(ascending=False).astype(int)

    return df

@app.route("/api/topsis", methods=["POST"])
def topsis_api():
    file = request.files.get("file")
    weights_raw = request.form.get("weights", "")
    impacts_raw = request.form.get("impacts", "")

    if not file:
        return jsonify({"error": "CSV file required"}), 400

    if not weights_raw or not impacts_raw:
        return jsonify({"error": "Weights and impacts are required"}), 400

    try:
        weights = [
            float(item.strip())
            for item in weights_raw.split(",")
            if item.strip()
        ]
    except ValueError:
        return jsonify({"error": "Weights must be comma-separated numbers"}), 400

    impacts = [
        item.strip()
        for item in impacts_raw.split(",")
        if item.strip()
    ]

    df = pd.read_csv(file)
    criteria_count = df.shape[1] - 1

    if len(weights) != criteria_count:
        return jsonify({"error": "Weights count mismatch"}), 400

    if len(impacts) != criteria_count:
        return jsonify({"error": "Impacts count mismatch"}), 400

    if any(impact not in {"+", "-"} for impact in impacts):
        return jsonify({"error": "Impacts must be + or -"}), 400

    result_df = run_topsis(df, weights, impacts)

    output_file = f"topsis_result_{uuid4().hex}.csv"
    output_path = OUTPUT_DIR / output_file
    result_df.to_csv(output_path, index=False)

    return jsonify({
        "table": result_df.to_dict(orient="records"),
        "download": f"/api/download/{output_file}"
    })

@app.route("/api/download/<filename>")
def download_file(filename):
    safe_name = secure_filename(filename)
    output_path = OUTPUT_DIR / safe_name
    if not output_path.exists():
        return jsonify({"error": "Result file not found"}), 404
    return send_file(output_path, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
