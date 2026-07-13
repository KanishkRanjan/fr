import { useEffect, useState } from 'react';
import { GraduationCap, Pencil, Plus, RefreshCw, Trash2, FileText, ArrowRight } from 'lucide-react';
import { usePortal } from '../portal/store';
import { deleteQuestion, getQuestion, listQuestions } from '../portal/api';
import { useDiagram } from '../store';

function RolePicker() {
  const setRole = usePortal((s) => s.setRole);
  return (
    <div className="role-pick">
      <h1>ER Diagram Practice Portal</h1>
      <p className="role-sub">Choose how you want to use the portal.</p>
      <div className="role-cards">
        <button className="role-card" onClick={() => setRole('teacher')}>
          <Pencil size={26} />
          <span className="role-name">Teacher</span>
          <span className="role-desc">
            Write a problem statement, draw the reference ER diagram, and publish
            it as a question for students.
          </span>
        </button>
        <button className="role-card" onClick={() => setRole('student')}>
          <GraduationCap size={26} />
          <span className="role-name">Student</span>
          <span className="role-desc">
            Pick a question, model it as an ER diagram in the editor, and submit —
            the validator grades it against the teacher&rsquo;s reference.
          </span>
        </button>
      </div>
    </div>
  );
}

export default function PortalHome() {
  const role = usePortal((s) => s.role);
  const portal = usePortal.getState;
  const [questions, setQuestions] = useState(null);   // null = loading
  const [error, setError] = useState(null);

  const refresh = async () => {
    setError(null);
    try {
      setQuestions(await listQuestions());
    } catch (e) {
      setQuestions([]);
      setError(e.message);
    }
  };
  useEffect(() => { if (role) refresh(); }, [role]);

  if (!role) return <div className="portal-page"><RolePicker /></div>;

  const openAuthor = () => {
    useDiagram.getState().clearAll();
    portal().set({ view: 'editor', mode: 'author', question: null, result: null });
  };

  const openQuestion = async (q) => {
    try {
      if (role === 'teacher') {
        const full = await getQuestion(q.id, true);
        useDiagram.getState().importDoc(full.reference);
        portal().set({ view: 'editor', mode: 'review', question: full, result: null });
      } else {
        const full = await getQuestion(q.id);
        portal().set({ view: 'editor', mode: 'solve', question: full, result: null });
      }
    } catch (e) {
      setError(e.message);
    }
  };

  const removeQuestion = async (e, q) => {
    e.stopPropagation();
    if (!confirm(`Delete question "${q.title}"?`)) return;
    try {
      await deleteQuestion(q.id);
      refresh();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="portal-page">
      <div className="portal-head">
        <h1>{role === 'teacher' ? 'Your Questions' : 'Available Questions'}</h1>
        <div className="portal-head-actions">
          {role === 'teacher' && (
            <button className="btn primary" onClick={openAuthor}>
              <Plus size={14} /> New question
            </button>
          )}
          <button className="btn line" onClick={refresh} title="Refresh list">
            <RefreshCw size={14} />
          </button>
          <button
            className="btn line"
            onClick={() => portal().set({ view: 'editor', mode: null, question: null })}
            title="Open the diagram editor without a question"
          >
            Open editor
          </button>
          <button className="btn" onClick={() => portal().setRole(null)}>
            Switch role
          </button>
        </div>
      </div>

      {error && <div className="portal-error">{error}</div>}

      {questions === null ? (
        <div className="portal-empty">Loading…</div>
      ) : questions.length === 0 ? (
        <div className="portal-empty">
          {role === 'teacher'
            ? 'No questions yet. Click "New question", draw the reference solution, and publish it.'
            : 'No questions available yet — ask your teacher to publish one.'}
        </div>
      ) : (
        <div className="qlist">
          {questions.map((q) => (
            <div key={q.id} className="qcard" onClick={() => openQuestion(q)}
                 role="button" tabIndex={0}
                 onKeyDown={(e) => { if (e.key === 'Enter') openQuestion(q); }}>
              <FileText size={16} className="qcard-icon" />
              <div className="qcard-main">
                <span className="qcard-title">{q.title}</span>
                <span className="qcard-meta">
                  #{q.id} · {new Date(q.created_at * 1000).toLocaleDateString()}
                </span>
              </div>
              {role === 'teacher' && (
                <button className="icon-btn danger" title="Delete question"
                        onClick={(e) => removeQuestion(e, q)}>
                  <Trash2 size={14} />
                </button>
              )}
              <ArrowRight size={15} className="qcard-go" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
