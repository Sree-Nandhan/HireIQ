import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const LOG = "[AuthPage]";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

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

  // Field-level validation errors
  const [fieldErrors, setFieldErrors] = useState({});
  // Track which fields have been touched (blurred)
  const [touched, setTouched] = useState({});

  const validateFields = () => {
    const errs = {};
    if (mode === "register") {
      if (!firstName.trim()) errs.firstName = "First name is required.";
      if (!lastName.trim())  errs.lastName  = "Last name is required.";
    }
    if (!email.trim()) {
      errs.email = "Email is required.";
    } else if (!EMAIL_RE.test(email.trim())) {
      errs.email = "Enter a valid email address.";
    }
    if (!password) {
      errs.password = "Password is required.";
    } else if (password.length < 8) {
      errs.password = "Password must be at least 8 characters.";
    }
    return errs;
  };

  const handleBlur = (field) => {
    setTouched((prev) => ({ ...prev, [field]: true }));
    const errs = validateFields();
    setFieldErrors(errs);
  };

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setWelcome("");

    // Mark all fields as touched so errors are visible
    setTouched(
      mode === "register"
        ? { firstName: true, lastName: true, email: true, password: true }
        : { email: true, password: true }
    );

    const errs = validateFields();
    if (Object.keys(errs).length > 0) {
      setFieldErrors(errs);
      console.warn(`${LOG} Submit blocked — validation errors:`, errs);
      return;
    }

    setLoading(true);
    console.log(`${LOG} Submitting ${mode} for:`, email);
    try {
      if (mode === "login") {
        await login(email, password);
        console.log(`${LOG} Login complete — navigating to /tracker`);
        navigate("/tracker");
      } else {
        await register(email, password, firstName, lastName);
        const name = firstName || email.split("@")[0];
        setWelcome(`Welcome to HireIQ, ${name}! Your account is ready.`);
        console.log(`${LOG} Registration complete — navigating in 1.8s`);
        setTimeout(() => navigate("/tracker"), 1800);
      }
    } catch (err) {
      const msg = err.response?.data?.detail || "Authentication failed. Please try again.";
      console.error(`${LOG} ${mode} failed:`, msg, err);
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    const next = mode === "login" ? "register" : "login";
    console.log(`${LOG} Switching mode to: ${next}`);
    setMode(next);
    setError("");
    setWelcome("");
    setFieldErrors({});
    setTouched({});
  };

  const fe = (field) =>
    touched[field] && fieldErrors[field] ? fieldErrors[field] : null;

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

          <form onSubmit={submit} className="auth-form" noValidate>
            {mode === "register" && (
              <div className="auth-row">
                <div className="auth-field">
                  <label>First Name</label>
                  <input
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    onBlur={() => handleBlur("firstName")}
                    placeholder="Jane"
                    autoComplete="given-name"
                    className={fe("firstName") ? "input--invalid" : ""}
                  />
                  {fe("firstName") && <span className="field-error">{fe("firstName")}</span>}
                </div>
                <div className="auth-field">
                  <label>Last Name</label>
                  <input
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    onBlur={() => handleBlur("lastName")}
                    placeholder="Smith"
                    autoComplete="family-name"
                    className={fe("lastName") ? "input--invalid" : ""}
                  />
                  {fe("lastName") && <span className="field-error">{fe("lastName")}</span>}
                </div>
              </div>
            )}

            <div className="auth-field">
              <label>Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onBlur={() => handleBlur("email")}
                placeholder="you@example.com"
                autoComplete="email"
                className={fe("email") ? "input--invalid" : ""}
              />
              {fe("email") && <span className="field-error">{fe("email")}</span>}
            </div>

            <div className="auth-field">
              <label>Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onBlur={() => handleBlur("password")}
                placeholder="••••••••"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                className={fe("password") ? "input--invalid" : ""}
              />
              {fe("password") && <span className="field-error">{fe("password")}</span>}
              {mode === "register" && !fe("password") && password && password.length < 8 && (
                <span className="field-hint">
                  {8 - password.length} more character{8 - password.length !== 1 ? "s" : ""} needed
                </span>
              )}
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
            <button className="auth-switch-btn" onClick={switchMode}>
              {mode === "login" ? "Register" : "Sign In"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
