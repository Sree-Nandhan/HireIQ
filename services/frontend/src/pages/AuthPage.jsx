import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const FEATURES = [
  { icon: "📊", title: "Gap Analysis",     desc: "See exactly where your skills stand against the job." },
  { icon: "✏️",  title: "Tailored Bullets", desc: "AI rewrites your resume bullets to match the JD."    },
  { icon: "✉️",  title: "Cover Letter",     desc: "Personalized cover letter generated in seconds."     },
  { icon: "⚡", title: "ATS Scoring",      desc: "Know your chances before you hit apply."              },
];

export default function AuthPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode]           = useState("login");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName]   = useState("");
  const [email, setEmail]         = useState("");
  const [password, setPassword]   = useState("");
  const [error, setError]         = useState("");
  const [loading, setLoading]     = useState(false);
  const [welcome, setWelcome]     = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setWelcome("");
    setLoading(true);
    try {
      if (mode === "login") {
        await login(email, password);
        navigate("/tracker");
      } else {
        await register(email, password, firstName, lastName);
        const name = firstName || email.split("@")[0];
        setWelcome(`Welcome to HireIQ, ${name}! Your account is ready.`);
        setTimeout(() => navigate("/tracker"), 1800);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Authentication failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-layout">
      {/* ── Left panel ── */}
      <div className="auth-brand">
        <div className="auth-brand-inner">
          <div className="auth-logo">HireIQ</div>
          <p className="auth-tagline">Your AI-powered career intelligence system.</p>

          <ul className="auth-features">
            {FEATURES.map((f) => (
              <li key={f.title}>
                <span className="feat-icon">{f.icon}</span>
                <div>
                  <strong>{f.title}</strong>
                  <p>{f.desc}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* ── Right panel ── */}
      <div className="auth-form-panel">
        <div className="auth-card">
          <h2>{mode === "login" ? "Welcome back" : "Create account"}</h2>
          <p className="auth-sub">
            {mode === "login"
              ? "Sign in to continue to HireIQ"
              : "Start analyzing your applications today"}
          </p>

          <form onSubmit={submit} className="auth-form">
            {mode === "register" && (
              <div className="auth-row">
                <div className="auth-field">
                  <label>First Name</label>
                  <input
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    required
                    placeholder="Jane"
                    autoComplete="given-name"
                  />
                </div>
                <div className="auth-field">
                  <label>Last Name</label>
                  <input
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    required
                    placeholder="Smith"
                    autoComplete="family-name"
                  />
                </div>
              </div>
            )}
            <div className="auth-field">
              <label>Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="you@example.com"
                autoComplete="email"
              />
            </div>
            <div className="auth-field">
              <label>Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
              />
            </div>

            {error   && <p className="auth-error">{error}</p>}
            {welcome && <p className="auth-welcome">{welcome}</p>}

            <button type="submit" className="auth-submit" disabled={loading}>
              {loading
                ? "Please wait…"
                : mode === "login" ? "Sign In" : "Create Account"}
            </button>
          </form>

          <p className="auth-switch">
            {mode === "login" ? "Don't have an account? " : "Already have an account? "}
            <button
              className="auth-switch-btn"
              onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}
            >
              {mode === "login" ? "Register" : "Sign In"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
