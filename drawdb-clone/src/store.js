import { create } from 'zustand';
import { COLORS } from './constants';

const LS_KEY = 'drawdb-clone-react-v1';

/* ---------------- persistence ---------------- */
let saveTimer = null;
function persist(s) {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    try {
      localStorage.setItem(
        LS_KEY,
        JSON.stringify({
          title: s.title,
          seq: s.seq,
          tables: s.tables,
          relationships: s.relationships,
        }),
      );
    } catch (e) { /* storage full or unavailable — skip */ }
  }, 250);
}
function load() {
  try {
    const doc = JSON.parse(localStorage.getItem(LS_KEY));
    if (doc && Array.isArray(doc.tables) && Array.isArray(doc.relationships)) return doc;
  } catch (e) { /* corrupt — fall through to seed */ }
  return null;
}

function makeEmpty() {
  return { title: 'Untitled Diagram', seq: 1, tables: [], relationships: [] };
}

const snap = (s) => ({
  title: s.title, seq: s.seq, tables: s.tables, relationships: s.relationships,
});

/* ---------------- diagram store ---------------- */
export const useDiagram = create((set, get) => ({
  ...(load() || makeEmpty()),
  past: [],
  future: [],
  _lastKey: null,
  _lastAt: 0,

  /**
   * All mutations funnel through here.
   * key === null      → silent (no history entry, e.g. mid-drag moves)
   * key === undefined → always record a history entry
   * key === string    → record, but coalesce repeats within 800ms (typing)
   */
  _apply(fn, key) {
    const s = get();
    const now = Date.now();
    let past = s.past;
    if (key !== null && !(typeof key === 'string' && key === s._lastKey && now - s._lastAt < 800)) {
      past = [...s.past.slice(-79), snap(s)];
    }
    const patch = fn(s) || {};
    set({
      ...patch,
      past,
      future: key === null ? s.future : [],
      _lastKey: typeof key === 'string' ? key : null,
      _lastAt: now,
    });
    persist(get());
  },

  undo() {
    const s = get();
    if (!s.past.length) return;
    const prev = s.past[s.past.length - 1];
    set({ ...prev, past: s.past.slice(0, -1), future: [...s.future, snap(s)], _lastKey: null });
    persist(get());
  },
  redo() {
    const s = get();
    if (!s.future.length) return;
    const next = s.future[s.future.length - 1];
    set({ ...next, past: [...s.past, snap(s)], future: s.future.slice(0, -1), _lastKey: null });
    persist(get());
  },

  setTitle(v) {
    get()._apply(() => ({ title: v }), 'title');
  },

  addTable(pos) {
    let created;
    get()._apply((s) => {
      let seq = s.seq;
      created = {
        id: seq++,
        name: `table_${s.tables.length + 1}`,
        x: Math.round(pos.x), y: Math.round(pos.y),
        color: COLORS[s.tables.length % COLORS.length],
        fields: [{
          id: seq++, name: 'id', type: 'INT',
          pk: true, notNull: true, unique: false, increment: true, def: '',
        }],
      };
      return { seq, tables: [...s.tables, created] };
    });
    return created;
  },
  updateTable(id, patch, key) {
    get()._apply(
      (s) => ({ tables: s.tables.map((t) => (t.id === id ? { ...t, ...patch } : t)) }),
      key,
    );
  },
  moveTable(id, pos) {
    get()._apply(
      (s) => ({
        tables: s.tables.map((t) =>
          t.id === id ? { ...t, x: Math.round(pos.x), y: Math.round(pos.y) } : t),
      }),
      null,
    );
  },
  beginMove() {
    // one history entry per drag, taken before the first silent move
    get()._apply(() => ({}), undefined);
  },
  deleteTable(id) {
    get()._apply((s) => ({
      tables: s.tables.filter((t) => t.id !== id),
      relationships: s.relationships.filter((r) => r.startTable !== id && r.endTable !== id),
    }));
  },
  deleteMany(nodeIds, edgeIds) {
    if (!nodeIds.length && !edgeIds.length) return;
    get()._apply((s) => {
      const tids = new Set(nodeIds);
      const eids = new Set(edgeIds);
      return {
        tables: s.tables.filter((t) => !tids.has(t.id)),
        relationships: s.relationships.filter(
          (r) => !eids.has(r.id) && !tids.has(r.startTable) && !tids.has(r.endTable)),
      };
    });
  },

  addField(tid) {
    get()._apply((s) => {
      let seq = s.seq;
      return {
        seq: seq + 1,
        tables: s.tables.map((t) =>
          t.id === tid
            ? {
                ...t,
                fields: [...t.fields, {
                  id: seq, name: `field_${t.fields.length + 1}`, type: 'VARCHAR',
                  pk: false, notNull: false, unique: false, increment: false, def: '',
                }],
              }
            : t),
      };
    });
  },
  updateField(tid, fid, patch, key) {
    get()._apply(
      (s) => ({
        tables: s.tables.map((t) =>
          t.id === tid
            ? {
                ...t,
                fields: t.fields.map((f) => {
                  if (f.id !== fid) return f;
                  const next = { ...f, ...patch };
                  if (patch.pk === true) next.notNull = true;
                  return next;
                }),
              }
            : t),
      }),
      key,
    );
  },
  deleteField(tid, fid) {
    get()._apply((s) => ({
      tables: s.tables.map((t) =>
        t.id === tid ? { ...t, fields: t.fields.filter((f) => f.id !== fid) } : t),
      relationships: s.relationships.filter((r) => r.startField !== fid && r.endField !== fid),
    }));
  },

  addRelationship(partial) {
    const s = get();
    // a relationship between the same two fields already exists in either
    // drawing direction — a reversed drag is the same line, not a new one
    const dup = s.relationships.some(
      (r) =>
        (r.startField === partial.startField && r.endField === partial.endField) ||
        (r.startField === partial.endField && r.endField === partial.startField),
    );
    if (dup) return null;
    let created;
    get()._apply((st) => {
      created = {
        id: st.seq, cardinality: 'many_to_one', ...partial,
      };
      return { seq: st.seq + 1, relationships: [...st.relationships, created] };
    });
    return created;
  },
  updateRelationship(id, patch) {
    get()._apply((s) => ({
      relationships: s.relationships.map((r) => (r.id === id ? { ...r, ...patch } : r)),
    }));
  },
  swapRelationship(id) {
    get()._apply((s) => ({
      relationships: s.relationships.map((r) => {
        if (r.id !== id) return r;
        let card = r.cardinality;
        if (card === 'one_to_many') card = 'many_to_one';
        else if (card === 'many_to_one') card = 'one_to_many';
        return {
          ...r,
          startTable: r.endTable, startField: r.endField,
          endTable: r.startTable, endField: r.startField,
          cardinality: card,
        };
      }),
    }));
  },
  deleteRelationship(id) {
    get()._apply((s) => ({
      relationships: s.relationships.filter((r) => r.id !== id),
    }));
  },

  importDoc(doc) {
    get()._apply(() => {
      let maxId = 1;
      for (const t of doc.tables) {
        maxId = Math.max(maxId, t.id + 1);
        for (const f of t.fields || []) maxId = Math.max(maxId, f.id + 1);
      }
      for (const r of doc.relationships) maxId = Math.max(maxId, r.id + 1);
      return {
        title: doc.title || 'Imported Diagram',
        seq: Math.max(doc.seq || 1, maxId),
        tables: doc.tables,
        relationships: doc.relationships,
      };
    });
  },
  clearAll() {
    get()._apply(() => ({ tables: [], relationships: [] }));
  },
}));

/* ---------------- ui store ---------------- */
export const useUi = create((set) => ({
  tab: 'tables',
  expandedId: null,
  sqlOpen: false,
  theme: document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light',
  set,
  toggleTheme() {
    set((s) => {
      const theme = s.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = theme;
      try { localStorage.setItem('er-theme', theme); } catch (e) {}
      return { theme };
    });
  },
}));
