import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api/client';
import { Database, CheckSquare, Square, RefreshCw, Plus } from 'lucide-react';
import { useWorkspace } from '../context/WorkspaceContext';

export default function Sidebar() {
  const { setSyncedTables, navigateToAddSource } = useWorkspace(); 
  
  const [tables, setTables] = useState<any[]>([]);
  const [selectedTables, setSelectedTables] = useState<Set<string>>(new Set());
  const [isSyncing, setIsSyncing] = useState(false);
  const [metrics, setMetrics] = useState<string[]>([]);
  const [isFetching, setIsFetching] = useState(false);

  const fetchTables = useCallback(async () => {
    setIsFetching(true);
    try {
      const res = await apiClient.get('/catalog/tables');
      setTables(res.data.tables || []);
    } catch (err) {
      console.error("Failed to fetch sidebar tables", err);
    } finally {
      setIsFetching(false);
    }
  }, []);

  useEffect(() => {
    fetchTables();
  }, [fetchTables]);

  const toggleTable = (fqn: string) => {
    const newSet = new Set(selectedTables);
    if (newSet.has(fqn)) newSet.delete(fqn);
    else newSet.add(fqn);
    setSelectedTables(newSet);
  };

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      const res = await apiClient.post('/metadata/sync', {
        selected_tables: Array.from(selectedTables)
      });
      setMetrics(res.data.drafted_metrics || []);
      setSyncedTables(Array.from(selectedTables)); 
    } catch (error) {
      console.error("Sync failed:", error);
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <div className="w-full h-full bg-white flex flex-col shadow-sm">
      <div className="p-4 border-b border-gray-100 bg-slate-50 flex justify-between items-center">
        <div>
          <h2 className="font-semibold flex items-center gap-2 text-slate-800">
            <Database size={18} className="text-blue-600"/> Data Sources
          </h2>
          <p className="text-xs text-slate-500 mt-1">Select tables for Semantic Layer</p>
        </div>
        <div className="flex gap-2">
          {/* NEW: Add Data Source Button */}
          <button 
            onClick={navigateToAddSource} 
            className="p-1.5 text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-md transition-colors"
            title="Add New Data Source"
          >
            <Plus size={16} />
          </button>
          <button 
            onClick={fetchTables} 
            disabled={isFetching}
            className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
            title="Refresh Tables"
          >
            <RefreshCw size={16} className={isFetching ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {tables.length === 0 && !isFetching && (
          <div className="flex flex-col items-center mt-6">
            <p className="text-sm text-gray-500 mb-3">No tables found.</p>
            <button 
              onClick={navigateToAddSource}
              className="text-xs bg-white border border-gray-300 text-gray-700 py-1.5 px-3 rounded hover:bg-gray-50 flex items-center gap-2"
            >
              <Plus size={14} /> Attach Data Source
            </button>
          </div>
        )}
        
        {tables.map((t) => (
          <div 
            key={t.fqn} 
            onClick={() => toggleTable(t.fqn)}
            className="flex items-center gap-3 p-2 rounded-md hover:bg-slate-50 cursor-pointer transition-colors border border-transparent hover:border-gray-200"
          >
            {selectedTables.has(t.fqn) ? 
              <CheckSquare size={18} className="text-blue-600 shrink-0" /> : 
              <Square size={18} className="text-gray-300 shrink-0" />
            }
            <div className="min-w-0 overflow-hidden">
              <p className="text-sm font-medium text-gray-700 truncate">{t.name}</p>
              <p className="text-xs text-gray-400 font-mono truncate">{t.schema}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="p-4 border-t border-gray-100 bg-slate-50">
        <button 
          onClick={handleSync}
          disabled={selectedTables.size === 0 || isSyncing}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white py-2 rounded-md font-medium text-sm transition-all flex justify-center items-center gap-2"
        >
          {isSyncing ? <RefreshCw size={16} className="animate-spin" /> : null}
          {isSyncing ? 'Drafting Semantics...' : 'Sync Semantic Layer'}
        </button>
      </div>
      
      {metrics.length > 0 && (
        <div className="p-4 bg-green-50 border-t border-green-100 max-h-48 overflow-y-auto">
          <p className="text-xs font-bold text-green-800 mb-2">AI Drafted KPIs:</p>
          <ul className="text-xs text-green-700 space-y-1 list-disc pl-4">
            {metrics.map((m, idx) => <li key={idx}>{m}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}