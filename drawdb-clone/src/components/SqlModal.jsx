import { useMemo, useState } from 'react';
import { X } from 'lucide-react';
import { useDiagram, useUi } from '../store';
import { generateSql } from '../sql';

const slugify = (s) =>
  (s || 'diagram').trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '') || 'diagram';

export default function SqlModal() {
  const tables = useDiagram((s) => s.tables);
  const relationships = useDiagram((s) => s.relationships);
  const title = useDiagram((s) => s.title);
  const ui = useUi.getState;
  const [dialect, setDialect] = useState('mysql');
  const [copied, setCopied] = useState(false);

  const sql = useMemo(
    () => generateSql(tables, relationships, dialect),
    [tables, relationships, dialect],
  );

  const close = () => ui().set({ sqlOpen: false });

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (e) { /* clipboard unavailable */ }
  };

  const download = () => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([sql], { type: 'text/plain' }));
    a.download = slugify(title) + '.sql';
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  };

  return (
    <div className="modal" role="dialog" aria-modal="true" onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div className="modal-box">
        <div className="modal-head">
          <span className="modal-title">Export SQL</span>
          <select value={dialect} onChange={(e) => setDialect(e.target.value)} aria-label="SQL dialect">
            <option value="mysql">MySQL</option>
            <option value="postgres">PostgreSQL</option>
            <option value="sqlite">SQLite</option>
          </select>
          <button className="icon-btn" title="Close" onClick={close}><X size={15} /></button>
        </div>
        <div className="modal-body">
          <textarea className="sql-out" readOnly spellCheck={false} value={sql} />
        </div>
        <div className="modal-foot">
          <button className="btn line" onClick={copy}>{copied ? 'Copied ✓' : 'Copy'}</button>
          <button className="btn primary" onClick={download}>Download .sql</button>
        </div>
      </div>
    </div>
  );
}
