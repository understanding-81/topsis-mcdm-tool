import { useState, useRef } from "react";
import api from "../services/api";
import ResultTable from "./ResultTable";

export default function TopsisForm() {
  const formRef = useRef();

  const [weightsValue, setWeightsValue] = useState("");
  const [impactsValue, setImpactsValue] = useState("");
  const [expectedCount, setExpectedCount] = useState(null);
  const [downloadUrl, setDownloadUrl] = useState("");

  const [sendMail, setSendMail] = useState(false);
  const [result, setResult] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const countCriteria = (value) =>
    value ? value.split(",").filter(Boolean).length : 0;

  const countsMatch =
    expectedCount !== null &&
    countCriteria(weightsValue) === expectedCount &&
    countCriteria(impactsValue) === expectedCount;

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const headers = event.target.result
        .trim()
        .split("\n")[0]
        .split(",");
      setExpectedCount(headers.length - 1);
      setWeightsValue("");
      setImpactsValue("");
    };
    reader.readAsText(file);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setResult([]);
    setDownloadUrl("");

    if (!countsMatch) {
      setError(`Exactly ${expectedCount} weights and impacts are required`);
      return;
    }

    setLoading(true);
    const formData = new FormData(e.target);

    try {
      const res = await api.post("/topsis", formData);
      setResult(res.data.table);
      setDownloadUrl(res.data.download);
    } catch (err) {
      setError(err.response?.data?.error || "Server error");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    formRef.current.reset();
    setWeightsValue("");
    setImpactsValue("");
    setExpectedCount(null);
    setSendMail(false);
    setResult([]);
    setError("");
    setDownloadUrl("");
  };

  return (
    <div className="min-vh-100 d-flex justify-content-center align-items-center bg-light px-3">
      <div
        className="bg-white shadow-lg rounded-4 p-4 p-md-5"
        style={{ maxWidth: "700px", width: "100%" }}
      >
        {/* ---------- HEADER ---------- */}
        <div className="text-center mb-4">
          <h2 className="fw-bold text-primary">TOPSIS</h2>
          <p className="text-dark mb-0">
            Technique for Order Preference by Similarity to Ideal Solution
          </p>
        </div>

        {/* ---------- FORM ---------- */}
        <form ref={formRef} onSubmit={handleSubmit}>
          {/* CSV Upload */}
          <div className="mb-4">
            <label className="fw-semibold text-dark mb-1 d-block">
              Upload CSV File
            </label>
            <input
              type="file"
              name="file"
              className="form-control"
              required
              onChange={handleFileChange}
            />
          </div>

          {expectedCount !== null && (
            <div className="alert alert-info py-2 text-dark">
              Detected <strong>{expectedCount}</strong> criteria
            </div>
          )}

          {/* Weights */}
          <div className="mb-4">
            <label className="fw-semibold text-dark mb-1 d-block">
              Weights
            </label>
            <input
              type="text"
              name="weights"
              className="form-control"
              placeholder="1,1,1,1"
              value={weightsValue}
              onChange={(e) => setWeightsValue(e.target.value)}
              required
            />
            <small className="text-dark">
              {countCriteria(weightsValue)} / {expectedCount ?? "?"} criteria
            </small>
          </div>

          {/* Impacts */}
          <div className="mb-4">
            <label className="fw-semibold text-dark mb-1 d-block">
              Impacts
            </label>
            <input
              type="text"
              name="impacts"
              className="form-control"
              placeholder="+,+,+,-"
              value={impactsValue}
              onChange={(e) => setImpactsValue(e.target.value)}
              required
            />
            <small className="text-dark">
              {countCriteria(impactsValue)} / {expectedCount ?? "?"} criteria
            </small>
          </div>

          {/* Email Option */}
          <div className="form-check mb-3">
            <input
              type="checkbox"
              className="form-check-input"
              id="sendMail"
              name="send_mail"
              onChange={(e) => setSendMail(e.target.checked)}
            />
            <label className="form-check-label text-dark" htmlFor="sendMail">
              Send result to email
            </label>
          </div>

          {sendMail && (
            <div className="mb-4">
              <input
                type="email"
                name="email"
                className="form-control"
                placeholder="Enter email address"
                required
              />
            </div>
          )}

          {error && (
            <div className="alert alert-danger text-center">{error}</div>
          )}

          {/* Buttons */}
          <div className="d-grid gap-3 mt-4">
            <button
              type="submit"
              className="btn btn-primary btn-lg"
              disabled={!countsMatch || loading}
            >
              {loading ? "Processing..." : "Calculate TOPSIS"}
            </button>

            <button
              type="button"
              className="btn btn-outline-secondary"
              onClick={handleReset}
            >
              Reset Form
            </button>
          </div>

          <div className="text-center mt-4">
            <a href="/sample_input.csv" download className="text-primary">
              Download Sample CSV
            </a>
          </div>
        </form>

        {/* ---------- RESULT ---------- */}
        {result.length > 0 && (
          <>
            <hr className="my-5" />
            <h4 className="text-center mb-3">Result</h4>
            <ResultTable data={result} />
            <div className="text-center mt-4">
              <a href={downloadUrl} className="btn btn-success">
                Download Output CSV
              </a>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
