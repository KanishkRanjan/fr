import { useState } from 'react';
import { ArrowLeft, CheckCircle2, Send, UploadCloud, XCircle } from 'lucide-react';
import { usePortal } from '../portal/store';
import { createQuestion, submitAnswer } from '../portal/api';
import { useDiagram } from '../store';

function currentDiagramDoc() {
  const s = useDiagram.getState();
  return { title: s.title, seq: s.seq, tables: s.tables, relationships: s.relationships };
}

function NamesPanel({ names }) {
  if (!names) return null;
  const tone = names.score >= 80 ? 'good' : names.score >= 50 ? 'warn' : 'bad';
  return (
    <div className="names-report">
      <div className="names-head">
        <span>Table naming</span>
        <span className={`names-score ${tone}`}>{names.score}/100</span>
      </div>
      {names.matched.length > 0 && (
        <ul className="names-list">
          {names.matched.map((m, i) => (
            <li key={i}>
              <span className={`names-tag ${m.type}`}>{m.type}</span>
              <span className="names-pair">{m.student} → {m.teacher}</span>
            </li>
          ))}
        </ul>
      )}
      {names.missing.length > 0 && (
        <div className="names-line bad">Missing: {names.missing.join(', ')}</div>
      )}
      {names.extra.length > 0 && (
        <div className="names-line warn">Extra: {names.extra.join(', ')}</div>
      )}
    </div>
  );
}

function ResultPanel({ result }) {
  if (!result) return null;
  return (
    <>
      <div className={`verdict ${result.is_valid ? 'pass' : 'fail'}`}>
        <div className="verdict-head">
          {result.is_valid ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
          <span>{result.is_valid ? 'Correct — diagram matches the reference model' : 'Not a match yet'}</span>
        </div>
        <div className="verdict-meta">
          engine: {result.algorithm_used}
          {result.stats?.engine_ran && result.stats.engine_ms != null && ` · ${result.stats.engine_ms} ms`}
        </div>
        {!result.is_valid && (
          <ul className="verdict-list">
            {result.mismatches.map((m, i) => (
              <li key={i}><b>{m.code}</b> — {m.message}</li>
            ))}
          </ul>
        )}
      </div>
      <NamesPanel names={result.names} />
    </>
  );
}

function AuthorPanel() {
  const portal = usePortal.getState;
  const [title, setTitle] = useState('');
  const [prompt, setPrompt] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const publish = async () => {
    setError(null);
    setBusy(true);
    try {
      await createQuestion(title, prompt, currentDiagramDoc());
      portal().backToPortal();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <h2 className="drawer-title">New question</h2>
      <label className="fld">Title
        <input value={title} onChange={(e) => setTitle(e.target.value)}
               placeholder="e.g. Library lending system" spellCheck={false} />
      </label>
      <label className="fld" style={{ flex: 1, minHeight: 0 }}>Problem statement
        <textarea className="drawer-textarea" value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Describe the scenario and requirements the students must model…" />
      </label>
      <div className="drawer-note">
        The diagram currently on the canvas is saved as the <b>reference solution</b>.
        Draw it before publishing.
      </div>
      {error && <div className="portal-error">{error}</div>}
      <button className="btn primary" disabled={busy} onClick={publish}>
        <UploadCloud size={14} /> {busy ? 'Publishing…' : 'Publish question'}
      </button>
    </>
  );
}

function ReviewPanel({ question }) {
  return (
    <>
      <h2 className="drawer-title">{question.title}</h2>
      <div className="drawer-prompt">{question.prompt}</div>
      <div className="drawer-note">
        The <b>reference solution</b> is loaded on the canvas. Students never see it.
      </div>
    </>
  );
}

function SolvePanel({ question }) {
  const result = usePortal((s) => s.result);
  const portal = usePortal.getState;
  const [algorithm, setAlgorithm] = useState('bliss');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const submit = async () => {
    setError(null);
    setBusy(true);
    try {
      const r = await submitAnswer(question.id, currentDiagramDoc(), algorithm);
      portal().set({ result: r });
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <h2 className="drawer-title">{question.title}</h2>
      <div className="drawer-prompt">{question.prompt}</div>
      <div className="drawer-actions">
        <label className="fld" style={{ flex: 1 }}>Validator
          <select value={algorithm} onChange={(e) => setAlgorithm(e.target.value)}>
            <option value="bliss">Bliss</option>
          </select>
        </label>
        <button className="btn primary" disabled={busy} onClick={submit}
                style={{ alignSelf: 'flex-end' }}>
          <Send size={14} /> {busy ? 'Checking…' : 'Submit'}
        </button>
      </div>
      {error && <div className="portal-error">{error}</div>}
      <ResultPanel result={result} />
    </>
  );
}

export default function PortalDrawer() {
  const mode = usePortal((s) => s.mode);
  const question = usePortal((s) => s.question);
  const portal = usePortal.getState;
  if (!mode) return null;

  return (
    <aside className="drawer">
      <button className="btn drawer-back" onClick={() => portal().backToPortal()}>
        <ArrowLeft size={14} /> Back to portal
      </button>
      {mode === 'author' && <AuthorPanel />}
      {mode === 'review' && question && <ReviewPanel question={question} />}
      {mode === 'solve' && question && <SolvePanel question={question} />}
    </aside>
  );
}
