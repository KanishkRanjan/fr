import { memo } from 'react';
import { BaseEdge, EdgeLabelRenderer, useInternalNode } from '@xyflow/react';
import { NODE_W, HEAD_H, ROW_H } from '../constants';
import { CARDINALITIES } from '../constants';

/**
 * "Floating" relationship edge: instead of using the handle the connection was
 * drawn from, anchors are recomputed from current node positions so the edge
 * always leaves each table on the side facing the other table — like drawDB.
 */
function RelationshipEdge({ id, source, target, data, selected }) {
  const sourceNode = useInternalNode(source);
  const targetNode = useInternalNode(target);
  if (!sourceNode || !targetNode || !data?.rel) return null;

  const rel = data.rel;
  const st = sourceNode.data.table;
  const tt = targetNode.data.table;

  const sPos = sourceNode.internals.positionAbsolute;
  const tPos = targetNode.internals.positionAbsolute;
  const sW = sourceNode.measured?.width ?? NODE_W;
  const tW = targetNode.measured?.width ?? NODE_W;

  const si = Math.max(0, st.fields.findIndex((f) => f.id === rel.startField));
  const ti = Math.max(0, tt.fields.findIndex((f) => f.id === rel.endField));
  const sy = sPos.y + HEAD_H + si * ROW_H + ROW_H / 2;
  const ty = tPos.y + HEAD_H + ti * ROW_H + ROW_H / 2;

  const sRight = sPos.x + sW / 2 <= tPos.x + tW / 2;
  const sx = sPos.x + (sRight ? sW : 0);
  const tx = tPos.x + (sRight ? 0 : tW);
  const sd = sRight ? 1 : -1;

  const bend = Math.max(50, Math.min(150, Math.abs(tx - sx) * 0.55));
  const path = `M ${sx} ${sy} C ${sx + bend * sd} ${sy}, ${tx - bend * sd} ${ty}, ${tx} ${ty}`;

  const [ms, mt] = (CARDINALITIES[rel.cardinality] || CARDINALITIES.one_to_many).marks;

  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        interactionWidth={14}
        className={`rel-edge${selected ? ' sel' : ''}`}
      />
      <EdgeLabelRenderer>
        <div
          className={`rel-card${selected ? ' sel' : ''}`}
          style={{ transform: `translate(-50%, -50%) translate(${sx + 16 * sd}px, ${sy - 10}px)` }}
        >
          {ms}
        </div>
        <div
          className={`rel-card${selected ? ' sel' : ''}`}
          style={{ transform: `translate(-50%, -50%) translate(${tx - 16 * sd}px, ${ty - 10}px)` }}
        >
          {mt}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

export default memo(RelationshipEdge);
