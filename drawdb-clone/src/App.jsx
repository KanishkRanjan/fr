import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ConnectionMode,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useDiagram, useUi } from './store';
import { usePortal } from './portal/store';
import TableNode from './components/TableNode';
import RelationshipEdge from './components/RelationshipEdge';
import Toolbar from './components/Toolbar';
import Sidebar from './components/Sidebar';
import SqlModal from './components/SqlModal';
import PortalHome from './components/PortalHome';
import PortalDrawer from './components/PortalDrawer';

const nodeTypes = { table: TableNode };
const edgeTypes = { rel: RelationshipEdge };

function Canvas() {
  const tables = useDiagram((s) => s.tables);
  const relationships = useDiagram((s) => s.relationships);
  const theme = useUi((s) => s.theme);
  const store = useDiagram.getState;
  const ui = useUi.getState;

  const [selNodes, setSelNodes] = useState(() => new Set());
  const [selEdges, setSelEdges] = useState(() => new Set());

  const nodes = useMemo(
    () => tables.map((t) => ({
      id: String(t.id),
      type: 'table',
      position: { x: t.x, y: t.y },
      data: { table: t },
      selected: selNodes.has(String(t.id)),
    })),
    [tables, selNodes],
  );
  const edges = useMemo(
    () => relationships.map((r) => ({
      id: String(r.id),
      source: String(r.startTable),
      target: String(r.endTable),
      type: 'rel',
      data: { rel: r },
      selected: selEdges.has(String(r.id)),
    })),
    [relationships, selEdges],
  );

  const onNodesChange = useCallback((changes) => {
    let sel = null;
    for (const c of changes) {
      if (c.type === 'position' && c.position) {
        store().moveTable(+c.id, c.position);
      } else if (c.type === 'select') {
        sel = sel || new Set(selNodes);
        c.selected ? sel.add(c.id) : sel.delete(c.id);
      }
    }
    if (sel) setSelNodes(sel);
  }, [selNodes]);

  const onEdgesChange = useCallback((changes) => {
    let sel = null;
    for (const c of changes) {
      if (c.type === 'select') {
        sel = sel || new Set(selEdges);
        c.selected ? sel.add(c.id) : sel.delete(c.id);
      }
    }
    if (sel) setSelEdges(sel);
  }, [selEdges]);

  const onConnect = useCallback((conn) => {
    const startField = parseInt(conn.sourceHandle, 10);
    const endField = parseInt(conn.targetHandle, 10);
    if (Number.isNaN(startField) || Number.isNaN(endField)) return;
    if (conn.source === conn.target && startField === endField) return;
    const rel = store().addRelationship({
      startTable: +conn.source,
      startField,
      endTable: +conn.target,
      endField,
    });
    if (rel) ui().set({ tab: 'rels' });
  }, []);

  const onDelete = useCallback(({ nodes: dn, edges: de }) => {
    store().deleteMany(dn.map((n) => +n.id), de.map((e) => +e.id));
  }, []);

  return (
    <div className="canvas-wrap">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeDragStart={() => store().beginMove()}
        onNodeClick={(e, node) => ui().set({ tab: 'tables', expandedId: +node.id })}
        onEdgeClick={() => ui().set({ tab: 'rels' })}
        onDelete={onDelete}
        connectionMode={ConnectionMode.Loose}
        connectionRadius={24}
        deleteKeyCode={['Backspace', 'Delete']}
        colorMode={theme}
        minZoom={0.15}
        maxZoom={4}
        fitView
        fitViewOptions={{ padding: 0.3, maxZoom: 1.25 }}
        proOptions={{ hideAttribution: false }}
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1.4} />
        <Controls position="bottom-right" />
        <MiniMap
          position="bottom-left"
          pannable
          zoomable
          nodeColor={(n) => n.data.table.color}
        />
      </ReactFlow>
      {tables.length === 0 && (
        <div className="empty-hint">
          <div>
            Your diagram is empty.<br />
            Click <kbd>+ Table</kbd> to add a table, drag tables to arrange them,<br />
            and drag from a field's edge dot onto another field to draw a relationship.
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const sqlOpen = useUi((s) => s.sqlOpen);
  const portalView = usePortal((s) => s.view);

  useEffect(() => {
    const onKey = (e) => {
      const tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
      const mod = e.metaKey || e.ctrlKey;
      if (mod && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        e.shiftKey ? useDiagram.getState().redo() : useDiagram.getState().undo();
      } else if (mod && e.key.toLowerCase() === 'y') {
        e.preventDefault();
        useDiagram.getState().redo();
      } else if (e.key === 'Escape' && useUi.getState().sqlOpen) {
        useUi.getState().set({ sqlOpen: false });
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <ReactFlowProvider>
      {portalView === 'home' ? (
        <PortalHome />
      ) : (
        <div className="app">
          <Toolbar />
          <div className="main">
            <Sidebar />
            <Canvas />
            <PortalDrawer />
          </div>
          {sqlOpen && <SqlModal />}
        </div>
      )}
    </ReactFlowProvider>
  );
}
