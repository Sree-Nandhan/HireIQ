import { BrowserRouter, Routes, Route, Navigate, Link } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import AuthPage from "./pages/AuthPage";
import AnalyzePage from "./pages/AnalyzePage";
import ResultsPage from "./pages/ResultsPage";
import TrackerPage from "./pages/TrackerPage";
import "./index.css";

function Nav() {
  const { token, user, logout } = useAuth();
  if (!token) return null;
  const displayName = user?.first_name || user?.email?.split("@")[0] || "?";
  const initials = displayName.slice(0, 2).toUpperCase();
  return (
    <nav className="navbar">
      <Link to="/tracker" className="brand">HireIQ</Link>
      <div className="nav-links">
        <Link to="/tracker">Tracker</Link>
        <Link to="/analyze">New Analysis</Link>
        <button onClick={logout} className="btn-ghost">Sign Out</button>
        <div className="nav-avatar" title={displayName}>{initials}</div>
      </div>
    </nav>
  );
}

function ProtectedRoute({ children }) {
  const { token } = useAuth();
  return token ? children : <Navigate to="/auth" replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Nav />
        <main className="main-content">
          <Routes>
            <Route path="/auth" element={<AuthPage />} />
            <Route path="/tracker" element={<ProtectedRoute><TrackerPage /></ProtectedRoute>} />
            <Route path="/analyze" element={<ProtectedRoute><AnalyzePage /></ProtectedRoute>} />
            <Route path="/results/:id" element={<ProtectedRoute><ResultsPage /></ProtectedRoute>} />
            <Route path="*" element={<Navigate to="/tracker" replace />} />
          </Routes>
        </main>
      </BrowserRouter>
    </AuthProvider>
  );
}
