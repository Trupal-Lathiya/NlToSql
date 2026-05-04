import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { signup } from "../services/apiClient";
import "../auth.css";

export default function SignupPage({ onLogin }) {
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) =>
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!form.username.trim() || !form.email.trim() || !form.password.trim()) {
      setError("Please fill in all fields.");
      return;
    }
    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (form.password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    setLoading(true);
    const res = await signup(form.username.trim(), form.email.trim(), form.password);
    setLoading(false);

    if (res.status === "success") {
      onLogin(res.user);
      navigate("/");
    } else {
      setError(res.message || "Signup failed. Please try again.");
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

        <h2 className="auth-title">Create an account</h2>
        <p className="auth-subtitle">Start querying your database in plain English</p>

        {error && <div className="auth-error">⚠️ {error}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="auth-field">
            <label className="auth-label">Username</label>
            <input
              className="auth-input"
              type="text"
              name="username"
              placeholder="Choose a username"
              value={form.username}
              onChange={handleChange}
              disabled={loading}
              autoComplete="username"
            />
          </div>

          <div className="auth-field">
            <label className="auth-label">Email</label>
            <input
              className="auth-input"
              type="email"
              name="email"
              placeholder="Enter your email"
              value={form.email}
              onChange={handleChange}
              disabled={loading}
              autoComplete="email"
            />
          </div>

          <div className="auth-field">
            <label className="auth-label">Password</label>
            <input
              className="auth-input"
              type="password"
              name="password"
              placeholder="Choose a password (min 6 chars)"
              value={form.password}
              onChange={handleChange}
              disabled={loading}
              autoComplete="new-password"
            />
          </div>

          <div className="auth-field">
            <label className="auth-label">Confirm Password</label>
            <input
              className="auth-input"
              type="password"
              name="confirmPassword"
              placeholder="Repeat your password"
              value={form.confirmPassword}
              onChange={handleChange}
              disabled={loading}
              autoComplete="new-password"
            />
          </div>

          <button className="auth-btn" type="submit" disabled={loading}>
            {loading ? (
              <span className="auth-loading">
                <span className="auth-spinner" /> Creating account…
              </span>
            ) : (
              "Create Account"
            )}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account?{" "}
          <Link to="/login" className="auth-link">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}