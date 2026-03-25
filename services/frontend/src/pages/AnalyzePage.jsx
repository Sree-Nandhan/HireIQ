import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import { useSimulatedProgress, AGENT_STEPS } from "../hooks/useSSE";

export default function AnalyzePage() {
  const navigate = useNavigate();
  const [jobTitle, setJobTitle] = useState("");
  const [company, setCompany] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [resumeFile, setResumeFile] = useState(null);
  const [resumeText, setResumeText] = useState("");
  const [step, setStep] = useState("form"); // form | streaming
  const [applicationId, setApplicationId] = useState(null);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [error, setError] = useState("");
  const [companyData, setCompanyData] = useState(null);
  const [revealedText, setRevealedText] = useState("");
  const [revealedChips, setRevealedChips] = useState([]);
  const [revealedCulture, setRevealedCulture] = useState("");
  const [revealedWhy, setRevealedWhy] = useState("");

  const { currentStep, progress } = useSimulatedProgress(
    step === "streaming",
    analysisComplete
  );

  // Full reveal sequence — all word-by-word / line-by-line
  const revealRef = useRef({ timer: null });

  useEffect(() => {
    if (!companyData?.what_they_do) return;

    setRevealedText("");
    setRevealedChips([]);
    setRevealedCulture("");
    setRevealedWhy("");

    // Helper: reveal words of a string one by one, call onDone when finished
    const revealWords = (text, setter, delay, onDone) => {
      const words = text.split(" ");
      let i = 0;
      const tick = () => {
        i += 1;
        setter(words.slice(0, i).join(" "));
        if (i < words.length) {
          revealRef.current.timer = setTimeout(tick, delay);
        } else {
          onDone();
        }
      };
      revealRef.current.timer = setTimeout(tick, delay);
    };

    // Helper: reveal list items one by one, call onDone when finished
    const revealItems = (items, setter, delay, onDone) => {
      if (!items.length) { onDone(); return; }
      items.forEach((item, ci) => {
        setTimeout(() => setter((prev) => [...prev, item]), ci * delay);
      });
      setTimeout(onDone, items.length * delay + 400);
    };

    // Chain: what_they_do → projects → culture_notes → why_apply
    revealWords(companyData.what_they_do, setRevealedText, 120, () => {
      revealItems(companyData.recent_projects || [], setRevealedChips, 500, () => {
        const culture = companyData.culture_notes || "";
        const why = companyData.why_apply || "";
        if (culture) {
          revealWords(culture, setRevealedCulture, 120, () => {
            if (why) revealWords(why, setRevealedWhy, 120, () => {});
          });
        } else if (why) {
          revealWords(why, setRevealedWhy, 120, () => {});
        }
      });
    });

    return () => clearTimeout(revealRef.current.timer);
  }, [companyData]);

  // When progress hits 100%, wait briefly then navigate to results
  useEffect(() => {
    if (analysisComplete && currentStep === AGENT_STEPS.length && applicationId) {
      const t = setTimeout(() => navigate(`/results/${applicationId}`), 700);
      return () => clearTimeout(t);
    }
  }, [analysisComplete, currentStep, applicationId, navigate]);

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setResumeFile(file);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await api.post("/resume/extract", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResumeText(res.data.text);
    } catch {
      setError("Could not extract text from PDF. Please paste your resume manually.");
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (!resumeText.trim()) {
      setError("Please upload your resume PDF.");
      return;
    }
    try {
      const appRes = await api.post("/applications", {
        job_title: jobTitle,
        company,
        job_description: jobDescription,
        resume_text: resumeText,
      });
      const appId = appRes.data.id;
      setApplicationId(appId);
      setStep("streaming");

      // Fire company preview and full analysis in parallel
      api.post("/company-preview", { company, job_description: jobDescription })
        .then((r) => setCompanyData(r.data))
        .catch(() => {});

      await api.post("/analyze", { application_id: appId });
      setAnalysisComplete(true);
    } catch (err) {
      setError(err.response?.data?.detail || "Analysis failed. Please try again.");
      setStep("form");
    }
  };

  if (step === "streaming") {
    const pct = Math.round(progress * 100);
    const isFinishing = pct === 100;

    return (
      <div className="stream-page">
        <div className="stream-card">
          <h2 className={isFinishing ? "stream-title done" : "stream-title"}>
            {isFinishing ? "Analysis complete!" : "Analyzing your application..."}
          </h2>

          <div className="progress-wrap">
            <div className="progress-bar-track">
              <div
                className={`progress-bar-fill${isFinishing ? " finishing" : ""}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className={`progress-pct${isFinishing ? " done" : ""}`}>{pct}%</span>
          </div>

          <ul className="step-list">
            {AGENT_STEPS.map((s, i) => {
              const isDone = i < currentStep;
              const isActive = i === currentStep && !isFinishing;
              return (
                <li key={s.key} className={isDone ? "done" : isActive ? "active" : ""}>
                  <span className="step-icon">{s.icon}</span>
                  <span className="step-label">{s.label}</span>
                  <span className="step-status">
                    {isDone ? "✓" : isActive ? <span className="pulse-dot" /> : ""}
                  </span>
                </li>
              );
            })}
          </ul>

          {/* Company research card — appears as data streams in */}
          {companyData ? (
            <div className="company-preview-card">
              <p className="company-preview-label">While you wait — here's what we found about</p>
              <h3 className="company-preview-name">{companyData.company_name || company}</h3>

              {revealedText && (
                <p className="company-preview-about">
                  {revealedText}
                  {revealedChips.length === 0 && !revealedCulture && <span className="cursor-blink">|</span>}
                </p>
              )}

              {revealedChips.length > 0 && (
                <div className="company-preview-projects">
                  <p className="company-preview-projects-label">What they're working on:</p>
                  <ul className="company-preview-projects-list">
                    {revealedChips.map((p) => (
                      <li key={p}>{p}</li>
                    ))}
                  </ul>
                </div>
              )}

              {revealedCulture && (
                <div className="company-preview-extra">
                  <p className="company-preview-projects-label">Culture &amp; Values</p>
                  <p className="company-preview-extra-text">
                    {revealedCulture}
                    {!revealedWhy && <span className="cursor-blink">|</span>}
                  </p>
                </div>
              )}

              {revealedWhy && (
                <div className="company-preview-extra">
                  <p className="company-preview-projects-label">Why Apply</p>
                  <p className="company-preview-extra-text">
                    {revealedWhy}<span className="cursor-blink">|</span>
                  </p>
                </div>
              )}
            </div>
          ) : (
            <p className="company-preview-loading">Researching {company}...</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="analyze-page">
      <div className="analyze-header">
        <div>
          <h2>New Application Analysis</h2>
          <p className="analyze-sub">Paste the job details and your resume — our AI agents will do the rest.</p>
        </div>
      </div>

      <form onSubmit={submit} className="analyze-form">
        {/* Row: Job Title + Company */}
        <div className="analyze-section">
          <div className="row-2">
            <div className="form-field">
              <label>Job Title <span className="req">*</span></label>
              <input
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                required
                placeholder="Senior Software Engineer"
              />
            </div>
            <div className="form-field">
              <label>Company <span className="req">*</span></label>
              <input
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                required
                placeholder="Acme Corp"
              />
            </div>
          </div>
        </div>

        {/* Two-column: JD left, Resume right */}
        <div className="analyze-cols">
          <div className="form-field" style={{ display: "flex", flexDirection: "column" }}>
            <label>Job Description <span className="req">*</span></label>
            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              required
              placeholder="Paste the full job description here..."
              style={{ flex: 1, resize: "none" }}
            />
          </div>

          <div className="form-field resume-col">
            <label>Resume <span className="req">*</span></label>

            {/* Upload zone */}
            <label className={`upload-zone${resumeFile ? " upload-zone--done" : ""}`}>
              <input
                type="file"
                accept="application/pdf"
                onChange={handleFileChange}
                style={{ display: "none" }}
              />
              {resumeFile ? (
                <>
                  <span className="upload-icon">✓</span>
                  <span className="upload-filename">{resumeFile.name}</span>
                  <span className="upload-hint">{resumeText.length} chars extracted</span>
                </>
              ) : (
                <>
                  <span className="upload-icon">📄</span>
                  <span className="upload-prompt">Click to upload PDF</span>
                  <span className="upload-hint">Supported format: PDF</span>
                </>
              )}
            </label>
          </div>
        </div>

        {error && <p className="error">{error}</p>}

        <button type="submit" className="btn-primary analyze-submit">
          Analyze Application →
        </button>
      </form>
    </div>
  );
}
