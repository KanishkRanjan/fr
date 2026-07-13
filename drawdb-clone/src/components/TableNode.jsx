import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { KeyRound } from 'lucide-react';

function TableNode({ data, selected }) {
  const t = data.table;
  return (
    <div className={`tnode${selected ? ' sel' : ''}`}>
      <div className="tnode-strip" style={{ background: t.color }} />
      <div className="tnode-name" title={t.name}>{t.name}</div>
      {t.fields.map((f) => (
        <div className="tnode-row" key={f.id}>
          <Handle
            type="source"
            position={Position.Left}
            id={`${f.id}-l`}
            className="tnode-conn"
          />
          <span className="tnode-fname" title={f.name}>
            {f.pk && <KeyRound size={10} className="tnode-key" />}
            {f.name}
          </span>
          <span className="tnode-ftype">{f.type.toLowerCase()}</span>
          <Handle
            type="source"
            position={Position.Right}
            id={`${f.id}-r`}
            className="tnode-conn"
          />
        </div>
      ))}
      {t.fields.length === 0 && <div className="tnode-empty">no fields</div>}
    </div>
  );
}

export default memo(TableNode);
