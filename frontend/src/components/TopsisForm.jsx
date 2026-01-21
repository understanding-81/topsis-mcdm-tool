import { useState, useRef } from "react";
import api from "../services/api";
import { sendResultEmail } from "../services/email";
import ResultTable from "./ResultTable";

export default function TopsisForm() {
  const formRef = useRef();

  const [weights, setWeights] = useState("");
  const [impacts, setImpacts] = useState("");
  const [result, setResult] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const [sendEmail, setSendEmail] = useState(false);
  const [email, setEmail] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setResult([]);
    setLoading(true);

    const formData = new FormData(e.target);

    try {
      const res = await api.post("/api/topsis", formData);
      setResult(res.data.table);

      // 📧 Send email using EmailJS
      if (sendEmail && email) {
        const downloadLink =
          window.location.origin + res.data.download;

        await sendResultEmail(email, downloadLink);
      }
    } catch (err) {
      setError(err.response?.data?.error || "Server error");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    formRef.current.reset();
    setWeights("");
    setImpacts("");
    setResult([]);
    setError("");
    setSendEmail(false);
    setEmail("");
  };

  return (
    <div className="card p-4 shadow">
      <form ref={formRef} onSubmit={handleSubmit}>
        {/* Upload CSV */}
        <div className="mb-3">
          <label className="form-label">Upload CSV File</label>
          <input
            type="file"
            name="file"
            className="form-control"
            accept=".csv"
            required
          />
        </div>

        {/* Weights */}
        <div className="mb-3">
          <label className="form-label">
            Weights (comma separated)
          </label>
          <input
            type="text"
            name="weights"
            className="form-control"
            placeholder="1,1,1,1"
            value={weights}
            onChange={(e) => setWeights(e.target.value)}
            required
          />
        </div>

        {/* Impacts */}
        <div className="mb-3">
          <label className="form-label">
            Impacts (comma separated)
          </label>
          <input
            type="text"
            name="impacts"
            className="form-control"
            placeholder="+,-,+,-"
            value={impacts}
            onChange={(e) => setImpacts(e.target.value)}
            required
          />
        </div>

        {/* Email checkbox */}
        <div className="form-check mb-3">
          <input
            type="checkbox"
            className="form-check-input"
            checked={sendEmail}
            onChange={(e) => setSendEmail(e.target.checked)}
          />
          <label className="form-check-label">
            Send result to email
          </label>
        </div>

        {/* Email input */}
        {sendEmail && (
          <div className="mb-3">
            <input
              type="email"
              className="form-control"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="alert alert-danger">{error}</div>
        )}

        {/* Buttons */}
        <div className="d-grid gap-2">
          <button
            className="btn btn-primary"
            disabled={loading}
          >
            {loading ? "Processing..." : "Calculate TOPSIS"}
          </button>

          <button
            type="button"
            className="btn btn-outline-secondary"
            onClick={handleReset}
          >
            Reset
          </button>
        </div>
      </form>

      {/* Result */}
      {result.length > 0 && (
        <>
          <hr />
          <h5 className="text-center">Result</h5>
          <ResultTable data={result} />
        </>
      )}
    </div>
  );
}
