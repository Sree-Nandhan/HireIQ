import { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../api/client";
import { useSimulatedProgress, AGENT_STEPS } from "../hooks/useSSE";

const LOG = "[ResultsPage]";
const TABS = ["Gap Analysis", "Tailored Bullets", "Cover Letter", "Interview Q&A", "ATS Score"];

function CopyButton({ text, label = "Copy" }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <button className={`btn-copy${copied ? " btn-copy--done" : ""}`} onClick={copy}>
      {copied ? "✓ Copied" : label}
    </button>
  );
}

export default function ResultsPage() {
  const { id } = useParams();
  const [app, setApp]           = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [tab, setTab]           = useState(0);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState("");
  const [reanalyzing, setReanalyzing]   = useState(false);
  const [reanalyzeDone, setReanalyzeDone] = useState(false);
  const { currentStep, progress } = useSimulatedProgress(reanalyzing, reanalyzeDone);
  const [reanalyzeModal, setReanalyzeModal] = useState(false);
  const [newResumeFile, setNewResumeFile]   = useState(null);
  const [newResumeText, setNewResumeText]   = useState("");
  const [chatOpen, setChatOpen]       = useState(false);
  const [chatExpanded, setChatExpanded] = useState(false);
  const [messages, setMessages]       = useState([]);
  const [question, setQuestion]       = useState("");
  const [coachLoading, setCoachLoading] = useState(false);
  const chatBottomRef = useRef(null);

  useEffect(() => {
    const load = async () => {
      console.log(`${LOG} Loading application id=${id}`);
      try {
        const res = await api.get(`/applications/${id}`);
        setApp(res.data);
        if (res.data.analyses?.length > 0) {
          const latest = res.data.analyses[res.data.analyses.length - 1];
          setAnalysis(latest);
          console.log(`${LOG} Loaded analysis id=${latest.id}, ats_score=${latest.ats_score}, match=${latest.match_percentage}%`);
        } else {
          console.warn(`${LOG} No analyses found for application id=${id}`);
        }
      } catch (err) {
        const msg = err.response?.data?.detail || "Could not load results.";
        console.error(`${LOG} Failed to load application id=${id}:`, msg, err);
        setError(msg);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  if (loading) return <div className="center-msg">Loading results...</div>;
  if (error)   return <div className="center-msg error">{error}</div>;
  if (!analysis) return <div className="center-msg">No analysis found for this application.</div>;

  const gap     = analysis.gap_analysis || {};
  const bullets = analysis.tailored_bullets || [];
  const qa      = analysis.interview_qa || [];
  const ats     = analysis.ats_details || {};
  const atsScore = analysis.ats_score ?? ats.score ?? null;

  const handleNewResumePDF = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    console.log(`${LOG} New resume PDF selected: ${file.name}`);
    setNewResumeFile(file);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await api.post("/resume/extract", form, { headers: { "Content-Type": "multipart/form-data" } });
      console.log(`${LOG} New resume extracted: ${res.data.text?.length ?? 0} chars`);
      setNewResumeText(res.data.text);
    } catch (err) {
      console.error(`${LOG} Failed to extract new resume PDF:`, err.response?.data?.detail || err.message, err);
      setNewResumeText("");
    }
  };

  const reanalyze = async () => {
    if (reanalyzing) return;
    console.log(`${LOG} Starting re-analysis for app id=${id}${newResumeText ? " with updated resume" : ""}`);
    setReanalyzing(true);
    setReanalyzeModal(false);
    try {
      if (newResumeText.trim()) {
        console.log(`${LOG} Updating resume text for app id=${id}`);
        await api.patch(`/applications/${id}/resume`, { resume_text: newResumeText });
      }
      await api.post("/analyze", { application_id: Number(id) });
      console.log(`${LOG} Re-analysis pipeline completed`);
      setReanalyzeDone(true);
      await new Promise((r) => setTimeout(r, 800));
      const res = await api.get(`/applications/${id}`);
      setApp(res.data);
      if (res.data.analyses?.length > 0) {
        const latest = res.data.analyses[res.data.analyses.length - 1];
        setAnalysis(latest);
        console.log(`${LOG} Re-analysis saved: ats_score=${latest.ats_score}, match=${latest.match_percentage}%`);
      }
    } catch (err) {
      const msg = err.response?.data?.detail || "Re-analysis failed.";
      console.error(`${LOG} Re-analysis failed for app id=${id}:`, msg, err);
    } finally {
      setReanalyzing(false);
      setReanalyzeDone(false);
      setNewResumeFile(null);
      setNewResumeText("");
    }
  };

  const askCoach = async (e) => {
    e.preventDefault();
    if (!question.trim() || coachLoading) return;
    const q = question.trim();
    console.log(`${LOG} Sending coach question for app id=${id}:`, q);
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setQuestion("");
    setCoachLoading(true);
    try {
      const res = await api.post("/coach", { application_id: Number(id), question: q });
      console.log(`${LOG} Coach answer received (${res.data.answer?.length ?? 0} chars)`);
      setMessages((prev) => [...prev, { role: "coach", text: res.data.answer }]);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      console.error(`${LOG} Coach request failed:`, msg, err);
      setMessages((prev) => [...prev, { role: "coach", text: "Sorry, I couldn't answer that right now. Try again." }]);
    } finally {
      setCoachLoading(false);
      setTimeout(() => chatBottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  };

  return (
    <div className="results-page">
      <div className="results-header">
        <div>
          <h2>{app.job_title}</h2>
          <p className="subtitle">{app.company}</p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <button className="btn-secondary" onClick={() => setReanalyzeModal(true)} disabled={reanalyzing}>
            {reanalyzing ? "Re-analyzing..." : "↺ Re-analyze"}
          </button>
          <Link to="/tracker" className="btn-secondary">Back to Tracker</Link>
        </div>
      </div>

      <div className="tab-row">
        {TABS.map((t, i) => (
          <button
            key={t}
            className={tab === i ? "tab active" : "tab"}
            onClick={() => {
              console.log(`${LOG} Switching to tab: ${t}`);
              setTab(i);
            }}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {tab === 0 && (
          <div className="gap-panel">
            <div className="score-badge">
              {gap.match_percentage ?? "--"}% Match
            </div>
            {gap.summary && <p className="gap-summary">{gap.summary}</p>}
            <div className="row-2">
              <div>
                <h4>Matching Skills</h4>
                <ul>
                  {(gap.matching_skills || []).map((s) => (
                    <li key={s} className="skill-match">{s}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h4>Missing Skills</h4>
                <ul>
                  {(gap.missing_skills || []).map((s) => (
                    <li key={s} className="skill-miss">{s}</li>
                  ))}
                </ul>
                {(gap.partial_matches || []).length > 0 && (
                  <>
                    <h4 style={{ marginTop: "1rem" }}>Partial Matches</h4>
                    <ul>
                      {gap.partial_matches.map((s) => (
                        <li key={s} className="skill-partial">{s}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            </div>
          </div>
        )}

        {tab === 1 && (
          <div className="bullets-list">
            <div className="tab-toolbar">
              <CopyButton
                text={bullets.filter(b => b.tailored?.trim()).map(b => b.tailored).join("\n\n")}
                label="Copy All Bullets"
              />
            </div>
            {bullets.filter(b => b.tailored?.trim()).length === 0 && (
              <p className="muted">No tailored bullets — the resume may not have enough experience bullets to rewrite.</p>
            )}
            {bullets.filter(b => b.tailored?.trim()).map((b, i) => (
              <div key={i} className="bullet-card">
                <p className="bullet-original"><span className="label">Original</span>{b.original}</p>
                <div className="bullet-tailored-row">
                  <p className="bullet-tailored"><span className="label">Tailored</span>{b.tailored}</p>
                  <CopyButton text={b.tailored} />
                </div>
                <p className="bullet-reasoning"><span className="label">Why</span>{b.reasoning}</p>
              </div>
            ))}
          </div>
        )}

        {tab === 2 && (
          <div className="cover-letter-wrap">
            <div className="tab-toolbar">
              <CopyButton text={analysis.cover_letter} label="Copy Cover Letter" />
            </div>
            <pre className="cover-letter">{analysis.cover_letter}</pre>
          </div>
        )}

        {tab === 3 && (
          <div className="qa-list">
            <div className="tab-toolbar">
              <CopyButton
                text={qa.map((item, i) => `Q${i+1}: ${item.question}\nA: ${item.model_answer}`).join("\n\n")}
                label="Copy All Q&A"
              />
            </div>
            {qa.length === 0 && <p className="muted">No interview questions generated.</p>}
            {qa.map((item, i) => (
              <div key={i} className="qa-item">
                <p className="question">
                  Q{i + 1}: {item.question}
                  {item.type && <span className="qa-type">{item.type}</span>}
                </p>
                <div className="qa-answer-row">
                  <p className="answer">A: {item.model_answer}</p>
                  <CopyButton text={item.model_answer} />
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === 4 && (
          <div className="ats-panel">
            <div className="score-badge">{atsScore ?? "--"} / 100</div>
            {ats.overall_assessment && <p className="ats-assessment">{ats.overall_assessment}</p>}
            <div className="row-2">
              {(ats.keyword_matches || []).length > 0 && (
                <div>
                  <h4>Keyword Matches</h4>
                  <ul>
                    {ats.keyword_matches.map((k) => (
                      <li key={k} className="skill-match">{k}</li>
                    ))}
                  </ul>
                </div>
              )}
              {(ats.keyword_misses || []).length > 0 && (
                <div>
                  <h4>Missing Keywords</h4>
                  <ul>
                    {ats.keyword_misses.map((k) => (
                      <li key={k} className="skill-miss">{k}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            {(ats.formatting_suggestions || []).length > 0 && (
              <div className="formatting-tips">
                <h4>Formatting Tips</h4>
                <ul>
                  {ats.formatting_suggestions.map((tip, i) => (
                    <li key={i}>{tip}</li>
                  ))}
                </ul>
              </div>
            )}
            {analysis.input_tokens != null && (
              <p className="token-info">
                Tokens used — Input: {analysis.input_tokens} | Output: {analysis.output_tokens}
              </p>
            )}
          </div>
        )}
      </div>

      {/* ── Re-analyze progress overlay ── */}
      {reanalyzing && (
        <div className="reanalyze-overlay">
          <div className="stream-card" style={{ maxWidth: "520px", width: "100%" }}>
            <h2 className={reanalyzeDone ? "stream-title done" : "stream-title"}>
              {reanalyzeDone ? "Analysis complete!" : "Re-analyzing your application..."}
            </h2>
            <div className="progress-wrap">
              <div className="progress-bar-track">
                <div
                  className={`progress-bar-fill${reanalyzeDone ? " finishing" : ""}`}
                  style={{ width: `${Math.round(progress * 100)}%` }}
                />
              </div>
              <span className={`progress-pct${reanalyzeDone ? " done" : ""}`}>
                {Math.round(progress * 100)}%
              </span>
            </div>
            <ul className="step-list">
              {AGENT_STEPS.map((s, i) => {
                const isDone   = i < currentStep;
                const isActive = i === currentStep && !reanalyzeDone;
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
          </div>
        </div>
      )}

      {/* ── Re-analyze modal ── */}
      {reanalyzeModal && (
        <div className="modal-overlay" onClick={() => setReanalyzeModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3>Re-analyze Application</h3>
            <p className="modal-sub">Optionally upload an updated resume, or re-run with the existing one.</p>

            <label className={`upload-zone${newResumeFile ? " upload-zone--done" : ""}`} style={{ marginTop: "1rem" }}>
              <input type="file" accept="application/pdf" onChange={handleNewResumePDF} style={{ display: "none" }} />
              {newResumeFile ? (
                <>
                  <span className="upload-icon">✓</span>
                  <span className="upload-filename">{newResumeFile.name}</span>
                  <span className="upload-hint">{newResumeText.length} chars extracted</span>
                </>
              ) : (
                <>
                  <span className="upload-icon">📄</span>
                  <span className="upload-prompt">Upload new resume (optional)</span>
                  <span className="upload-hint">Leave blank to re-run with existing resume</span>
                </>
              )}
            </label>

            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setReanalyzeModal(false)}>Cancel</button>
              <button className="btn-primary" onClick={reanalyze}>
                {newResumeFile ? "Update Resume & Re-analyze" : "Re-analyze"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Career Coach floating chat ── */}
      {!chatOpen && (
        <button className="coach-fab" onClick={() => setChatOpen(true)} title="Career Coach">
          🎤 <span className="coach-fab-label">Career Coach</span>
        </button>
      )}

      {chatOpen && (
        <div className={`coach-panel${chatExpanded ? " coach-panel--expanded" : ""}`}>
          <div className="coach-panel-header">
            <div>
              <span>🎤 Career Coach</span>
              <span className="coach-panel-sub">Ask anything about this application</span>
            </div>
            <div style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
              <button
                className="coach-expand-btn"
                onClick={() => setChatExpanded((e) => !e)}
                title={chatExpanded ? "Collapse" : "Expand"}
              >
                {chatExpanded ? "⊡" : "⊞"}
              </button>
              <button
                className="coach-expand-btn"
                onClick={() => { setChatOpen(false); setChatExpanded(false); }}
                title="Close"
              >
                ✕
              </button>
            </div>
          </div>

          <div className="coach-messages">
            {messages.length === 0 && (
              <div className="coach-empty">
                <p>Ask me anything about your application — interview tips, how to address skill gaps, cover letter advice, salary negotiation, or anything else.</p>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`coach-msg coach-msg--${m.role}`}>
                {m.text}
              </div>
            ))}
            {coachLoading && (
              <div className="coach-msg coach-msg--coach coach-typing">
                <span /><span /><span />
              </div>
            )}
            <div ref={chatBottomRef} />
          </div>

          <form className="coach-input-row" onSubmit={askCoach}>
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. How do I address the missing skills?"
              disabled={coachLoading}
            />
            <button type="submit" className="coach-send" disabled={coachLoading || !question.trim()}>
              ↑
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
