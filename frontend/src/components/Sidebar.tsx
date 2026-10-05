import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api/client';
import { Database, CheckSquare, Square, RefreshCw, Plus, Edit3, X } from 'lucide-react';
import { useWorkspace } from '../context/WorkspaceContext';

interface EditableMetadata {
  urn: string;
  tableName: string;
  businessName: string;
  description: string;
  columns: { name: string; businessName: string }[];
}

export default function Sidebar() {
  const { setSyncedTables, navigateToAddSource } = useWorkspace(); 
  
  const [tables, setTables] = useState<any[]>([]);
  const [selectedTables, setSelectedTables] = useState<Set<string>>(new Set());
  const [isSyncing, setIsSyncing] = useState(false);
  const [metrics, setMetrics] = useState<string[]>([]);
  const [isFetching, setIsFetching] = useState(false);
  const [metadataDraft, setMetadataDraft] = useState<EditableMetadata | null>(null);
  const [isLoadingMetadata, setIsLoadingMetadata] = useState(false);
  const [isReindexing, setIsReindexing] = useState(false);
  const [metadataError, setMetadataError] = useState('');
  const [feedback, setFeedback] = useState('');

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
    setFeedback('');
    try {
      const res = await apiClient.post('/metadata/sync', {
        selected_tables: Array.from(selectedTables)
      });
      setMetrics(res.data.drafted_metrics || []);
      setSyncedTables(Array.from(selectedTables)); 
      setFeedback('Semantic metadata synced successfully.');
    } catch (error) {
      console.error("Sync failed:", error);
      setFeedback('Sync failed. Check the backend logs and try again.');
    } finally {
      setIsSyncing(false);
    }
  };

  const openMetadataEditor = async () => {
    const tableName = Array.from(selectedTables)[0];
    if (!tableName) return;

    setIsLoadingMetadata(true);
    setMetadataError('');
    setFeedback('');
    try {
      const res = await apiClient.get('/metadata/entities', { params: { table_name: tableName } });
      const entity = res.data.entities?.[0];
      if (!entity) {
        throw new Error('Sync this table to the Semantic Layer before editing its metadata.');
      }

      setMetadataDraft({
        urn: entity.urn,
        tableName,
        businessName: entity.business.business_name || '',
        description: entity.business.user_description
          || entity.business.deterministic_description
          || entity.business.llm_generated_description
          || '',
        columns: entity.physical.columns.map((column: { name: string; business_name?: string | null }) => ({
          name: column.name,
          businessName: column.business_name || ''
        }))
      });
    } catch (error: any) {
      setMetadataError(error.response?.data?.detail || error.message || 'Unable to load metadata.');
      setMetadataDraft(null);
    } finally {
      setIsLoadingMetadata(false);
    }
  };

  const handleReindex = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!metadataDraft) return;

    setIsReindexing(true);
    setMetadataError('');
    try {
      await apiClient.post('/metadata/reindex', {
        urn: metadataDraft.urn,
        business_name: metadataDraft.businessName.trim() || null,
        description: metadataDraft.description.trim() || null,
        columns: metadataDraft.columns.map(column => ({
          name: column.name,
          business_name: column.businessName.trim() || null
        }))
      });
      setMetadataDraft(null);
      setFeedback(`Metadata saved and ${metadataDraft.tableName} re-indexed.`);
    } catch (error: any) {
      setMetadataError(error.response?.data?.detail || 'Re-index failed. Please try again.');
    } finally {
      setIsReindexing(false);
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
        {selectedTables.size === 1 && (
          <button
            onClick={openMetadataEditor}
            disabled={isLoadingMetadata || isSyncing}
            className="w-full mb-2 border border-slate-300 bg-white hover:bg-slate-100 disabled:opacity-50 text-slate-700 py-2 rounded-md font-medium text-sm transition-all flex justify-center items-center gap-2"
          >
            {isLoadingMetadata ? <RefreshCw size={16} className="animate-spin" /> : <Edit3 size={16} />}
            Edit Metadata / Re-index
          </button>
        )}
        <button 
          onClick={handleSync}
          disabled={selectedTables.size === 0 || isSyncing}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white py-2 rounded-md font-medium text-sm transition-all flex justify-center items-center gap-2"
        >
          {isSyncing ? <RefreshCw size={16} className="animate-spin" /> : null}
          {isSyncing ? 'Drafting Semantics...' : 'Sync Semantic Layer'}
        </button>
        {feedback && <p className="mt-2 text-xs text-slate-600" role="status">{feedback}</p>}
        {!metadataDraft && metadataError && <p className="mt-2 text-xs text-red-600" role="alert">{metadataError}</p>}
      </div>
      
      {metrics.length > 0 && (
        <div className="p-4 bg-green-50 border-t border-green-100 max-h-48 overflow-y-auto">
          <p className="text-xs font-bold text-green-800 mb-2">AI Drafted KPIs:</p>
          <ul className="text-xs text-green-700 space-y-1 list-disc pl-4">
            {metrics.map((m, idx) => <li key={idx}>{m}</li>)}
          </ul>
        </div>
      )}

      {metadataDraft && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 flex items-center justify-center p-4">
          <form
            onSubmit={handleReindex}
            className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col"
          >
            <div className="flex items-center justify-between border-b border-slate-200 p-5">
              <div>
                <h3 className="font-bold text-slate-800">Edit semantic metadata</h3>
                <p className="text-xs text-slate-500 mt-1">{metadataDraft.tableName}</p>
              </div>
              <button type="button" onClick={() => setMetadataDraft(null)} aria-label="Close metadata editor">
                <X size={20} className="text-slate-500 hover:text-slate-800" />
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-4">
              <label className="block">
                <span className="block text-sm font-medium text-slate-700 mb-1">Business table name</span>
                <input
                  value={metadataDraft.businessName}
                  onChange={event => setMetadataDraft({ ...metadataDraft, businessName: event.target.value })}
                  maxLength={200}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                />
              </label>
              <label className="block">
                <span className="block text-sm font-medium text-slate-700 mb-1">Table description</span>
                <textarea
                  value={metadataDraft.description}
                  onChange={event => setMetadataDraft({ ...metadataDraft, description: event.target.value })}
                  maxLength={2000}
                  rows={3}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                />
              </label>

              <div>
                <p className="text-sm font-medium text-slate-700 mb-2">Column business names</p>
                <div className="space-y-2">
                  {metadataDraft.columns.map((column, index) => (
                    <label key={column.name} className="grid grid-cols-2 gap-3 items-center">
                      <span className="text-xs font-mono text-slate-500 truncate" title={column.name}>{column.name}</span>
                      <input
                        value={column.businessName}
                        onChange={event => {
                          const columns = metadataDraft.columns.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, businessName: event.target.value } : item
                          );
                          setMetadataDraft({ ...metadataDraft, columns });
                        }}
                        maxLength={200}
                        aria-label={`Business name for ${column.name}`}
                        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                      />
                    </label>
                  ))}
                </div>
              </div>

              {metadataError && <p className="text-sm text-red-600" role="alert">{metadataError}</p>}
            </div>

            <div className="flex justify-end gap-2 border-t border-slate-200 p-4">
              <button
                type="button"
                onClick={() => setMetadataDraft(null)}
                className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isReindexing}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
              >
                {isReindexing && <RefreshCw size={15} className="animate-spin" />}
                {isReindexing ? 'Re-indexing...' : 'Save & Re-index'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}