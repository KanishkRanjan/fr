import { useRef } from 'react';
import { useReactFlow } from '@xyflow/react';
import {
  Plus, Undo2, Redo2, Database, Download, Upload, Trash2, Moon, Sun, Home,
} from 'lucide-react';
import { useDiagram, useUi } from '../store';
import { usePortal } from '../portal/store';
import { NODE_W } from '../constants';

const slugify = (s) =>
  (s || 'diagram').trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '') || 'diagram';

function downloadFile(name, text, mime) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type: mime }));
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}

export default function Toolbar() {
  const title = useDiagram((s) => s.title);
  const canUndo = useDiagram((s) => s.past.length > 0);
  const canRedo = useDiagram((s) => s.future.length > 0);
  const theme = useUi((s) => s.theme);
  const fileRef = useRef(null);
  const { screenToFlowPosition } = useReactFlow();

  const store = useDiagram.getState;
  const ui = useUi.getState;

  const addTable = () => {
    const pane = document.querySelector('.react-flow');
    const r = pane.getBoundingClientRect();
    const n = useDiagram.getState().tables.length;
    const pos = screenToFlowPosition({
      x: r.left + r.width / 2 + (n % 5) * 24,
      y: r.top + r.height / 2 - 80 + (n % 5) * 24,
    });
    const t = store().addTable({ x: pos.x - NODE_W / 2, y: pos.y });
    ui().set({ tab: 'tables', expandedId: t.id });
  };

  const saveJson = () => {
    const s = store();
    downloadFile(
      slugify(s.title) + '.json',
      JSON.stringify(
        { title: s.title, seq: s.seq, tables: s.tables, relationships: s.relationships },
        null, 2,
      ),
      'application/json',
    );
  };

  const loadJson = (e) => {
    const file = e.target.files[0];
    e.target.value = '';
    if (!file) return;
    const rd = new FileReader();
    rd.onload = () => {
      try {
        const doc = JSON.parse(rd.result);
        if (!doc || !Array.isArray(doc.tables) || !Array.isArray(doc.relationships)) {
          throw new Error('not a diagram file');
        }
        store().importDoc(doc);
        ui().set({ expandedId: null });
      } catch (err) {
        alert('Could not read that file — expected a diagram JSON export.');
      }
    };
    rd.readAsText(file);
  };

  const clearAll = () => {
    const s = store();
    if (!s.tables.length && !s.relationships.length) return;
    if (confirm('Clear the whole diagram? You can undo with Ctrl+Z.')) {
      s.clearAll();
      ui().set({ expandedId: null });
    }
  };

  return (
    <header className="topbar">
      <button className="btn icon" title="Back to portal"
              onClick={() => usePortal.getState().backToPortal()}>
        <Home size={15} />
      </button>
      <span className="logo" title="ER Diagram Editor">
        <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
          <rect x="1.5" y="2.5" width="11" height="8" rx="2" stroke="var(--accent)" strokeWidth="1.8" />
          <rect x="9.5" y="11.5" width="11" height="8" rx="2" fill="var(--accent)" />
          <path d="M7 10.5v3a2 2 0 0 0 2 2h.5" stroke="var(--accent)" strokeWidth="1.8" fill="none" />
        </svg>
      </span>
      <input
        className="title-in"
        value={title}
        spellCheck={false}
        aria-label="Diagram title"
        onChange={(e) => store().setTitle(e.target.value)}
      />
      <span className="tb-sep" />
      <button className="btn primary" onClick={addTable}>
        <Plus size={14} /> Table
      </button>
      <span className="tb-sep" />
      <button className="btn" disabled={!canUndo} onClick={() => store().undo()} title="Undo (Ctrl+Z)">
        <Undo2 size={14} /> Undo
      </button>
      <button className="btn" disabled={!canRedo} onClick={() => store().redo()} title="Redo (Ctrl+Shift+Z)">
        <Redo2 size={14} /> Redo
      </button>
      <span className="tb-spacer" />
      <button className="btn" onClick={() => ui().set({ sqlOpen: true })} title="Export SQL DDL">
        <Database size={14} /> Export SQL
      </button>
      <button className="btn" onClick={saveJson} title="Save diagram as JSON">
        <Download size={14} /> Save
      </button>
      <button className="btn" onClick={() => fileRef.current?.click()} title="Load diagram from JSON">
        <Upload size={14} /> Load
      </button>
      <span className="tb-sep" />
      <button className="btn icon" onClick={clearAll} title="Clear diagram">
        <Trash2 size={14} />
      </button>
      <button className="btn icon" onClick={() => ui().toggleTheme()} title="Toggle light/dark theme">
        {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
      </button>
      <input ref={fileRef} type="file" accept=".json,application/json" hidden onChange={loadJson} />
    </header>
  );
}
