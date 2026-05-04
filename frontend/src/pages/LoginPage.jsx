import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { login } from "../services/apiClient";
import "../auth.css";

export default function LoginPage({ onLogin }) {
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) =>
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!form.username.trim() || !form.password.trim()) {
      setError("Please fill in all fields.");
      return;
    }
    setLoading(true);
    const res = await login(form.username.trim(), form.password);
    setLoading(false);
    if (res.status === "success") {
      onLogin(res.user);
      navigate("/");
    } else {
      setError(res.message || "Invalid credentials.");
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        {/* Brand */}
        <div className="auth-brand">
          <span className="auth-brand-icon">🗄️</span>
          <div>
            <div className="auth-brand-name">NL2SQL</div>
            <div className="auth-brand-sub">Natural Language → SQL</div>
          </div>
        </div>

        <h2 className="auth-title">Welcome back</h2>
        <p className="auth-subtitle">Sign in to your account to continue</p>

        {error && <div className="auth-error">⚠️ {error}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="auth-field">
            <label className="auth-label">Email</label>
                <input
                className="auth-input"
                type="email"
                name="username"
                placeholder="Enter your email (e.g. john@company.com)"
              value={form.username}
              onChange={handleChange}
              disabled={loading}
              autoComplete="username"
            />
          </div>

          <div className="auth-field">
            <label className="auth-label">Password</label>
            <input
              className="auth-input"
              type="password"
              name="password"
              placeholder="Enter your password"
              value={form.password}
              onChange={handleChange}
              disabled={loading}
              autoComplete="current-password"
            />
          </div>

          <button className="auth-btn" type="submit" disabled={loading}>
            {loading ? (
              <span className="auth-loading">
                <span className="auth-spinner" /> Signing in…
              </span>
            ) : (
              "Sign In"
            )}
          </button>
        </form>

        <p className="auth-switch">
          Don't have an account?{" "}
          <Link to="/signup" className="auth-link">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}