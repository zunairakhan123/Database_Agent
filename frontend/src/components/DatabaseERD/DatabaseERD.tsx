import { useEffect, useMemo, useCallback, useState } from 'react';
import { 
  ReactFlow, Background, Controls, MiniMap,
  useNodesState, useEdgesState, addEdge,
  getBezierPath, type EdgeProps, MarkerType,
  type OnConnect, type Node, type Edge
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { apiClient } from '../../api/client';
import TableNode from './TableNode';
import { useWorkspace } from '../../context/WorkspaceContext';
import { Settings, Save, Trash2, X } from 'lucide-react';

// --- CUSTOM INTERACTIVE EDGE ---
// Elevates the canvas from a static picture to an interactive semantic builder.
const EditableEdge = ({
  id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data, style, markerEnd,
}: EdgeProps) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition,
  });

  // Safely cast data to 'any' to bypass strict TypeScript checks for our custom properties
  const edgeData = data as any;

  return (
    <>
      <path id={id} style={style} className="react-flow__edge-path" d={edgePath} markerEnd={markerEnd} />
      <foreignObject
        width={40} height={40} x={labelX - 20} y={labelY - 20}
        className="pointer-events-auto flex items-center justify-center overflow-visible"
      >
        <button
          className="w-8 h-8 bg-white border-2 border-slate-300 rounded-full flex items-center justify-center cursor-pointer shadow-sm hover:bg-blue-50 hover:border-blue-500 hover:text-blue-600 text-slate-600 transition-all text-[10px] font-bold"
          onClick={(event) => {
            event.stopPropagation();
            // Now TypeScript knows edgeData is safe to access
            if (edgeData?.onEdit) {
              edgeData.onEdit(id, edgeData);
            }
          }}
        >
          {edgeData?.cardinality || '1:N'}
        </button>
      </foreignObject>
    </>
  );
};

export default function DatabaseERD() {
  const { syncedTables } = useWorkspace(); 
  const selectedTables = syncedTables;     
  
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  
  const [activeEdge, setActiveEdge] = useState<any | null>(null);

  const edgeTypes = useMemo(() => ({ editable: EditableEdge }), []);
  const nodeTypes = useMemo(() => ({ table: TableNode }), []);

  useEffect(() => {
    const fetchERD = async () => {
      if (selectedTables.length === 0) {
        setNodes([]);
        setEdges([]);
        return;
      }

      try {
        const queryParam = `?selected_tables=${selectedTables.join(',')}`;
        const response = await apiClient.get(`/catalog/erd${queryParam}`);
        
        const layoutedNodes = response.data.nodes.map((node: any, index: number) => ({
          ...node,
          type: 'table', 
          position: {
            x: (index % 3) * 350 + 50,
            y: Math.floor(index / 3) * 250 + 50
          }
        }));

        const hydratedEdges = response.data.edges.map((edge: any) => ({
          ...edge,
          markerEnd: { type: MarkerType.ArrowClosed, color: '#3b82f6' },
          data: {
            ...edge.data,
            onEdit: (id: string, data: any) => setActiveEdge({ edgeId: id, ...data })
          }
        }));

        setNodes(layoutedNodes);
        setEdges(hydratedEdges);
      } catch (error) {
        console.error("Failed to fetch ERD:", error);
      }
    };

    fetchERD();
  }, [selectedTables, setNodes, setEdges]);
  
  const onConnect: OnConnect = useCallback(
    async (params) => {
      const defaultRule = {
        source_urn: params.source,
        target_urn: params.target,
        condition: `${params.source}.id = ${params.target}.${params.source}_id`,
        join_type: 'LEFT',
        cardinality: '1:N'
      };

      const newEdge: Edge = {
        ...params,
        id: `edge-${params.source}-${params.target}`,
        type: 'editable',
        animated: true,
        style: { stroke: '#3b82f6', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#3b82f6' },
        data: { 
          ...defaultRule, 
          source_table: params.source,
          target_table: params.target,
          onEdit: (id: string, data: any) => setActiveEdge({ edgeId: id, ...data }) 
        }
      };

      setEdges((eds) => addEdge(newEdge, eds));

      try {
        await apiClient.post('/catalog/join-rule', defaultRule);
      } catch (err) {
        console.error("❌ Failed to save Join Rule to backend:", err);
      }
    },
    [setEdges]
  );

  const saveEdgeDetails = async () => {
    if (!activeEdge) return;
    try {
      const rule = {
        source_urn: activeEdge.source_table,
        target_urn: activeEdge.target_table,
        condition: activeEdge.condition,
        join_type: activeEdge.join_type,
        cardinality: activeEdge.cardinality
      };
      await apiClient.post('/catalog/join-rule', rule);
      
      setEdges(eds => eds.map(e => e.id === activeEdge.edgeId ? { ...e, data: { ...e.data, ...activeEdge } } : e));
      setActiveEdge(null);
    } catch (err) {
      console.error("Failed to save updated rule", err);
    }
  };

  const deleteEdge = async () => {
    if (!activeEdge) return;
    try {
      await apiClient.delete(`/catalog/join-rule/${activeEdge.source_table}/${activeEdge.target_table}`);
      setEdges(eds => eds.filter(e => e.id !== activeEdge.edgeId));
      setActiveEdge(null);
    } catch (err) {
      console.error("Failed to delete rule", err);
    }
  };

  return (
    <div className="w-full h-full flex bg-slate-50 overflow-hidden">
      
      {/* CANVAS */}
      <div className="flex-1 h-full relative">
        <ReactFlow 
          edgeTypes={edgeTypes} 
          edges={edges} 
          fitView 
          nodeTypes={nodeTypes} 
          nodes={nodes} 
          onConnect={onConnect} 
          onEdgesChange={onEdgesChange} 
          onNodesChange={onNodesChange}
        >
          <Background gap={16} />
          <Controls />
          <MiniMap nodeStrokeWidth={3} pannable zoomable />
        </ReactFlow>
      </div>

      {/* SEMANTIC RELATIONSHIP EDITOR DRAWER */}
      {activeEdge && (
        <div className="w-80 h-full bg-white border-l border-slate-200 shadow-2xl flex flex-col shrink-0 z-10">
          <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
            <h3 className="font-bold text-slate-700 flex items-center gap-2">
              <Settings size={16} /> Relationship Editor
            </h3>
            <button onClick={() => setActiveEdge(null)} className="text-slate-400 hover:text-slate-700"><X size={18} /></button>
          </div>
          
          <div className="p-4 flex-1 overflow-y-auto flex flex-col gap-5 text-sm">
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">Source Table</label>
              <input type="text" disabled value={activeEdge.source_table} className="w-full bg-slate-100 border border-slate-200 rounded px-3 py-2 text-slate-600 cursor-not-allowed" />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">Target Table</label>
              <input type="text" disabled value={activeEdge.target_table} className="w-full bg-slate-100 border border-slate-200 rounded px-3 py-2 text-slate-600 cursor-not-allowed" />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">Join Condition (SQL)</label>
              <input type="text" value={activeEdge.condition} onChange={e => setActiveEdge({...activeEdge, condition: e.target.value})} className="w-full bg-white border border-blue-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded px-3 py-2 text-slate-700 outline-none font-mono text-xs" />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">Join Type</label>
              <select value={activeEdge.join_type} onChange={e => setActiveEdge({...activeEdge, join_type: e.target.value})} className="w-full bg-white border border-slate-300 rounded px-3 py-2 text-slate-700 outline-none">
                <option value="LEFT">LEFT JOIN (Preserve Source)</option>
                <option value="INNER">INNER JOIN (Strict Match)</option>
                <option value="FULL">FULL OUTER JOIN</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">Cardinality</label>
              <select value={activeEdge.cardinality} onChange={e => setActiveEdge({...activeEdge, cardinality: e.target.value})} className="w-full bg-white border border-slate-300 rounded px-3 py-2 text-slate-700 outline-none">
                <option value="1:1">One-to-One (1:1)</option>
                <option value="1:N">One-to-Many (1:N)</option>
                <option value="N:M">Many-to-Many (N:M)</option>
              </select>
            </div>
          </div>

          <div className="p-4 border-t border-slate-100 bg-slate-50 flex gap-2">
            <button onClick={deleteEdge} className="flex-1 py-2 bg-white border border-red-200 text-red-600 hover:bg-red-50 rounded shadow-sm font-semibold flex items-center justify-center gap-2 transition-colors">
              <Trash2 size={16} /> Delete
            </button>
            <button onClick={saveEdgeDetails} className="flex-1 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded shadow-sm font-semibold flex items-center justify-center gap-2 transition-colors">
              <Save size={16} /> Save Rule
            </button>
          </div>
        </div>
      )}
    </div>
  );
}