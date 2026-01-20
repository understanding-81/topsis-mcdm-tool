from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import numpy as np
import os
import re
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# ===================== LOAD ENV =====================
load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"

# ===================== APP INIT =====================
app = Flask(__name__)
CORS(app)

# Vercel allows writing only to /tmp
UPLOAD_DIR = "/tmp/uploads"
OUTPUT_DIR = "/tmp/outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ===================== HEALTH CHECK =====================
@app.route("/api/")
def health():
    return {"status": "TOPSIS backend running"}

# ===================== TOPSIS LOGIC =====================
def run_topsis(df, weights, impacts):
    data = df.iloc[:, 1:].values.astype(float)
    weights = np.array(weights)

    # Normalize decision matrix
    norm_matrix = data / np.sqrt((data ** 2).sum(axis=0))

    # Apply weights
    weighted_matrix = norm_matrix * weights

    ideal_best = []
    ideal_worst = []

    for i, impact in enumerate(impacts):
        if impact == "+":
            ideal_best.append(weighted_matrix[:, i].max())
            ideal_worst.append(weighted_matrix[:, i].min())
        else:
            ideal_best.append(weighted_matrix[:, i].min())
            ideal_worst.append(weighted_matrix[:, i].max())

    dist_best = np.sqrt(((weighted_matrix - ideal_best) ** 2).sum(axis=1))
    dist_worst = np.sqrt(((weighted_matrix - ideal_worst) ** 2).sum(axis=1))

    df["Topsis Score"] = dist_worst / (dist_best + dist_worst)
    df["Rank"] = df["Topsis Score"].rank(ascending=False).astype(int)

    return df

# ===================== EMAIL =====================
def send_email(receiver_email, file_path):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise Exception("Gmail credentials not configured")

    msg = EmailMessage()
    msg["From"] = GMAIL_USER
    msg["To"] = receiver_email
    msg["Subject"] = "TOPSIS Result"
    msg.set_content("Attached is the TOPSIS result generated from your input file.")

    with open(file_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="text",
            subtype="csv",
            filename="topsis_result.csv"
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)

# ===================== API =====================
@app.route("/api/topsis", methods=["POST"])
def topsis_api():
    file = request.files.get("file")
    weights = request.form.get("weights")
    impacts = request.form.get("impacts")
    email = request.form.get("email")

    send_mail = str(request.form.get("send_mail")).lower() in ["true", "on", "1"]

    if not file:
        return jsonify({"error": "CSV file is required"}), 400

    if send_mail:
        if not email or not re.match(EMAIL_REGEX, email):
            return jsonify({"error": "Invalid email address"}), 400

    try:
        weights = list(map(float, weights.split(",")))
        impacts = impacts.split(",")
    except Exception:
        return jsonify({"error": "Invalid weights or impacts format"}), 400

    if not all(i in ["+", "-"] for i in impacts):
        return jsonify({"error": "Impacts must be '+' or '-'"}), 400

    input_path = os.path.join(UPLOAD_DIR, secure_filename(file.filename))
    file.save(input_path)

    df = pd.read_csv(input_path)

    if len(weights) != df.shape[1] - 1:
        return jsonify({"error": "Weights and criteria count mismatch"}), 400

    result_df = run_topsis(df, weights, impacts)

    output_filename = f"topsis_result_{os.getpid()}.csv"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    result_df.to_csv(output_path, index=False)

    email_sent = False
    email_error = None

    if send_mail:
        try:
            send_email(email, output_path)
            email_sent = True
        except Exception:
            email_error = "Email sending failed"

    return jsonify({
        "table": result_df.to_dict(orient="records"),
        "download": f"/api/download/{output_filename}",
        "emailSent": email_sent,
        "emailError": email_error
    })

# ===================== DOWNLOAD =====================
@app.route("/api/download/<filename>")
def download(filename):
    return send_file(
        os.path.join(OUTPUT_DIR, filename),
        as_attachment=True
    )
