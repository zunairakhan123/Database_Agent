import { useEffect, useState } from 'react';
import { useWorkspace } from '../context/WorkspaceContext';
import { Server, Plus, Clock, Trash2, ArrowRight } from 'lucide-react';

interface WorkspaceMeta {
  id: string;
  name: string;
  lastAccessed: number;
}

export default function Dashboard() {
  const { loadWorkspace, createNewWorkspace } = useWorkspace();
  const [history, setHistory] = useState<WorkspaceMeta[]>([]);

  useEffect(() => {
    const saved = JSON.parse(localStorage.getItem('agentic_workspace_history') || '[]');
    setHistory(saved.sort((a: WorkspaceMeta, b: WorkspaceMeta) => b.lastAccessed - a.lastAccessed));
  }, []);

  const deleteWorkspace = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const updated = history.filter(w => w.id !== id);
    localStorage.setItem('agentic_workspace_history', JSON.stringify(updated));
    setHistory(updated);
    // Future implementation: trigger DELETE /api/v1/workspace/:id
  };

  return (
    <div className="w-screen h-screen bg-slate-100 flex items-center justify-center p-6 font-sans">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl overflow-hidden border border-gray-200 p-8 flex flex-col h-[80vh]">
        <div className="flex justify-between items-center mb-8 shrink-0">
          <div>
            <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
              <Server className="text-blue-600" /> Enterprise BI Workspaces
            </h1>
            <p className="text-slate-500 text-sm mt-1">Select an existing analytical session or start a new one.</p>
          </div>
          <button 
            onClick={createNewWorkspace}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 px-5 rounded-lg transition-all flex items-center gap-2 shadow-sm"
          >
            <Plus size={18} /> New Workspace
          </button>
        </div>

        <div className="flex-1 overflow-y-auto pr-2 grid grid-cols-1 md:grid-cols-2 gap-4 auto-rows-max">
          {history.length === 0 ? (
            <div className="col-span-full h-48 flex flex-col items-center justify-center border-2 border-dashed border-gray-300 rounded-xl text-gray-400">
              <Clock size={32} className="mb-3 opacity-50" />
              <p>No previous workspaces found.</p>
            </div>
          ) : (
            history.map(ws => (
              <div 
                key={ws.id} 
                onClick={() => loadWorkspace(ws.id)}
                className="group bg-slate-50 border border-slate-200 hover:border-blue-400 hover:shadow-md p-5 rounded-xl cursor-pointer transition-all flex flex-col justify-between h-36"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-bold text-slate-700 text-lg">{ws.name}</h3>
                    <p className="text-xs text-slate-400 font-mono mt-1">{ws.id}</p>
                  </div>
                  <button 
                    onClick={(e) => deleteWorkspace(ws.id, e)}
                    className="text-slate-300 hover:text-red-500 transition-colors p-1"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
                <div className="flex justify-between items-center mt-4">
                  <span className="text-xs text-slate-500 font-medium">
                    Last active: {new Date(ws.lastAccessed).toLocaleDateString()}
                  </span>
                  <ArrowRight size={18} className="text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity transform group-hover:translate-x-1" />
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}