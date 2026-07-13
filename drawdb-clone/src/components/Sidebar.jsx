import { useState } from 'react';
import { X, MoreHorizontal, ArrowLeftRight } from 'lucide-react';
import { useDiagram, useUi } from '../store';
import { TYPES, COLORS, CARDINALITIES } from '../constants';

function FieldRow({ table, field }) {
  const [more, setMore] = useState(false);
  const store = useDiagram.getState;
  const up = (patch, key) => store().updateField(table.id, field.id, patch, key);

  return (
    <div className="frow-wrap">
      <div className="frow">
        <input
          className="f-name"
          value={field.name}
          spellCheck={false}
          aria-label="Field name"
          onChange={(e) => up({ name: e.target.value }, `fname-${field.id}`)}
        />
        <select
          value={field.type}
          aria-label="Field type"
          onChange={(e) => up({ type: e.target.value })}
        >
          {TYPES.map((tp) => <option key={tp}>{tp}</option>)}
        </select>
        <button
          className={`tag${field.pk ? ' on' : ''}`}
          title="Primary key"
          onClick={() => up({ pk: !field.pk })}
        >PK</button>
        <button
          className={`tag${field.notNull ? ' on' : ''}`}
          title="Not null"
          onClick={() => up({ notNull: !field.notNull })}
        >NN</button>
        <button className="icon-btn" title="More options" onClick={() => setMore(!more)}>
          <MoreHorizontal size={13} />
        </button>
        <button
          className="icon-btn danger"
          title="Delete field"
          onClick={() => store().deleteField(table.id, field.id)}
        >
          <X size={13} />
        </button>
      </div>
      {more && (
        <div className="fmore">
          <label>
            <input
              type="checkbox"
              checked={field.unique}
              onChange={(e) => up({ unique: e.target.checked })}
            /> Unique
          </label>
          <label>
            <input
              type="checkbox"
              checked={field.increment}
              onChange={(e) => up({ increment: e.target.checked })}
            /> Auto-increment
          </label>
          <label>
            Default{' '}
            <input
              type="text"
              value={field.def}
              spellCheck={false}
              onChange={(e) => up({ def: e.target.value }, `fdef-${field.id}`)}
            />
          </label>
        </div>
      )}
    </div>
  );
}

function TableCard({ table }) {
  const expandedId = useUi((s) => s.expandedId);
  const open = expandedId === table.id;
  const store = useDiagram.getState;
  const ui = useUi.getState;

  return (
    <div className={`tcard${open ? ' open' : ''}`}>
      <div
        className="tcard-head"
        onClick={() => ui().set({ expandedId: open ? null : table.id })}
      >
        <span className="tcard-dot" style={{ background: table.color }} />
        <span className="tcard-title">{table.name}</span>
        <span className="tcard-count">{table.fields.length}</span>
        <button
          className="icon-btn danger"
          title="Delete table"
          onClick={(e) => { e.stopPropagation(); store().deleteTable(table.id); }}
        >
          <X size={13} />
        </button>
      </div>
      {open && (
        <div className="tcard-body">
          <label className="fld">
            Name
            <input
              value={table.name}
              spellCheck={false}
              onChange={(e) => store().updateTable(table.id, { name: e.target.value }, `tname-${table.id}`)}
            />
          </label>
          <div className="swatches">
            {COLORS.map((c) => (
              <button
                key={c}
                className={`swatch${c === table.color ? ' on' : ''}`}
                style={{ background: c }}
                title={c}
                onClick={() => store().updateTable(table.id, { color: c })}
              />
            ))}
          </div>
          <div className="frows">
            {table.fields.map((f) => <FieldRow key={f.id} table={table} field={f} />)}
          </div>
          <button className="btn ghost" onClick={() => store().addField(table.id)}>
            + Add field
          </button>
        </div>
      )}
    </div>
  );
}

function RelationshipCard({ rel }) {
  const tables = useDiagram((s) => s.tables);
  const store = useDiagram.getState;
  const ts = tables.find((t) => t.id === rel.startTable);
  const te = tables.find((t) => t.id === rel.endTable);
  if (!ts || !te) return null;
  const fs = ts.fields.find((f) => f.id === rel.startField);
  const fe = te.fields.find((f) => f.id === rel.endField);

  return (
    <div className="rcard">
      <div className="rcard-head">
        <span className="rcard-path">
          {ts.name}.{fs?.name ?? '?'} → {te.name}.{fe?.name ?? '?'}
        </span>
        <button className="icon-btn" title="Swap direction" onClick={() => store().swapRelationship(rel.id)}>
          <ArrowLeftRight size={13} />
        </button>
        <button className="icon-btn danger" title="Delete relationship" onClick={() => store().deleteRelationship(rel.id)}>
          <X size={13} />
        </button>
      </div>
      <div className="rcard-grid">
        <label className="fld">
          Cardinality
          <select
            value={rel.cardinality}
            onChange={(e) => store().updateRelationship(rel.id, { cardinality: e.target.value })}
          >
            {Object.entries(CARDINALITIES).map(([k, v]) => (
              <option key={k} value={k}>{v.label}</option>
            ))}
          </select>
        </label>
      </div>
    </div>
  );
}

export default function Sidebar() {
  const tables = useDiagram((s) => s.tables);
  const relationships = useDiagram((s) => s.relationships);
  const tab = useUi((s) => s.tab);
  const ui = useUi.getState;
  const [q, setQ] = useState('');

  const shown = q.trim()
    ? tables.filter((t) => t.name.toLowerCase().includes(q.trim().toLowerCase()))
    : tables;

  return (
    <aside className="sidebar">
      <div className="tabs" role="tablist">
        <button
          className={`tab${tab === 'tables' ? ' on' : ''}`}
          role="tab"
          onClick={() => ui().set({ tab: 'tables' })}
        >Tables</button>
        <button
          className={`tab${tab === 'rels' ? ' on' : ''}`}
          role="tab"
          onClick={() => ui().set({ tab: 'rels' })}
        >Relationships</button>
      </div>
      <div className="panel">
        {tab === 'tables' ? (
          <>
            <input
              className="search"
              type="search"
              placeholder="Search tables…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            {shown.length
              ? shown.map((t) => <TableCard key={t.id} table={t} />)
              : (
                <div className="panel-note">
                  {tables.length
                    ? 'No tables match your search.'
                    : <>No tables yet. Click <b>+ Table</b> in the toolbar to create one.</>}
                </div>
              )}
          </>
        ) : (
          relationships.length
            ? relationships.map((r) => <RelationshipCard key={r.id} rel={r} />)
            : (
              <div className="panel-note">
                No relationships yet.<br />
                On the canvas, drag from the dot at a field's edge onto a field
                of another table to create a foreign key.
              </div>
            )
        )}
      </div>
    </aside>
  );
}
