function sqlType(f, dialect) {
  let tp = f.type;
  if (dialect === 'postgres') {
    if (f.increment && (tp === 'INT' || tp === 'SMALLINT')) return 'SERIAL';
    if (f.increment && tp === 'BIGINT') return 'BIGSERIAL';
    if (tp === 'DATETIME') tp = 'TIMESTAMP';
    if (tp === 'BLOB') tp = 'BYTEA';
    if (tp === 'DOUBLE') tp = 'DOUBLE PRECISION';
  }
  if (dialect === 'sqlite') {
    if (['UUID', 'JSON', 'DATETIME', 'TIMESTAMP', 'DATE', 'TIME'].includes(tp)) tp = 'TEXT';
    if (['INT', 'BIGINT', 'SMALLINT'].includes(tp)) tp = 'INTEGER';
  }
  if (dialect === 'mysql' && tp === 'UUID') tp = 'CHAR(36)';
  if (tp === 'VARCHAR') tp = 'VARCHAR(255)';
  if (tp === 'DECIMAL') tp = 'DECIMAL(10,2)';
  return tp;
}

function sqlDefault(v) {
  if (/^-?\d+(\.\d+)?$/.test(v)) return v;
  if (/^(NULL|TRUE|FALSE|CURRENT_TIMESTAMP|CURRENT_DATE|CURRENT_TIME|NOW\(\))$/i.test(v)) return v;
  return `'${v.replace(/'/g, "''")}'`;
}

export function generateSql(tables, relationships, dialect) {
  const q = dialect === 'mysql' ? (s) => '`' + s + '`' : (s) => '"' + s + '"';
  const byId = (id) => tables.find((t) => t.id === id);
  const out = [];

  const fks = [];
  for (const r of relationships) {
    let ts = byId(r.startTable), te = byId(r.endTable);
    if (!ts || !te) continue;
    let fs = ts.fields.find((f) => f.id === r.startField);
    let fe = te.fields.find((f) => f.id === r.endField);
    if (!fs || !fe) continue;
    // The FOREIGN KEY column lives on the "many" side. one_to_many is the same
    // relationship drawn parent-first, so flip it before emitting SQL —
    // otherwise we'd put the FK on the parent's primary key.
    if (r.cardinality === 'one_to_many') {
      [ts, te] = [te, ts];
      [fs, fe] = [fe, fs];
    }
    const clause = `FOREIGN KEY (${q(fs.name)}) REFERENCES ${q(te.name)} (${q(fe.name)})`;
    fks.push({ tableId: ts.id, tableName: ts.name, clause });
  }

  for (const t of tables) {
    const lines = [];
    for (const f of t.fields) {
      let l = '  ' + q(f.name) + ' ' + sqlType(f, dialect);
      if (f.notNull && !(dialect === 'postgres' && f.increment)) l += ' NOT NULL';
      if (f.unique && !f.pk) l += ' UNIQUE';
      // sqlite INTEGER PRIMARY KEY autoincrements implicitly; postgres uses SERIAL
      if (f.increment && dialect === 'mysql') l += ' AUTO_INCREMENT';
      if (f.def) l += ' DEFAULT ' + sqlDefault(f.def);
      lines.push(l);
    }
    const pks = t.fields.filter((f) => f.pk);
    if (pks.length) lines.push('  PRIMARY KEY (' + pks.map((f) => q(f.name)).join(', ') + ')');
    // sqlite has no ALTER TABLE ... ADD FOREIGN KEY — constraints must be inline
    if (dialect === 'sqlite') {
      for (const fk of fks) if (fk.tableId === t.id) lines.push('  ' + fk.clause);
    }
    out.push(`CREATE TABLE ${q(t.name)} (\n${lines.join(',\n')}\n);`);
  }

  if (dialect !== 'sqlite') {
    for (const fk of fks) {
      out.push(`ALTER TABLE ${q(fk.tableName)} ADD ${fk.clause};`);
    }
  }

  return out.join('\n\n') || '-- The diagram is empty.';
}
