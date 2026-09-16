import { useState } from 'react';
import { Database, FileText, TableProperties, Link, Loader2, Server, CheckSquare, Plus, ArrowRight } from 'lucide-react';
import { apiClient } from '../api/client';
import { useWorkspace } from '../context/WorkspaceContext';

declare global {
  interface Window {
    google: any;
    gapi: any;
  }
}

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const GOOGLE_API_KEY="AIzaSyDyn0e-PSPZ2x_wFVgkUDR4BjB--gs6AZo";

if (!GOOGLE_CLIENT_ID || !GOOGLE_API_KEY) {
  console.warn("Google Cloud credentials are missing from the environment.");
}

export default function ConnectionScreen() {
  const { connectWorkspace } = useWorkspace();
  const [activeTab, setActiveTab] = useState<'database' | 'csv' | 'excel' | 'sheets'>('database');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [stagedSources, setStagedSources] = useState<{name: string, type: string}[]>([]);

  const [dbType, setDbType] = useState('postgres');
  const [connName, setConnName] = useState('');
  const [connUrl, setConnUrl] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  
  const [sheetId, setSheetId] = useState('');
  const [spreadsheetName, setSpreadsheetName] = useState('');
  const [accessToken, setAccessToken] = useState('');

  const handleGoogleSheetsAuth = () => {
    const tokenClient = window.google.accounts.oauth2.initTokenClient({
      client_id: GOOGLE_CLIENT_ID,
      scope: 'https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/spreadsheets.readonly',
      callback: (response: any) => {
        if (response.error !== undefined) {
          setError('Google authentication failed.');
          return;
        }
        setAccessToken(response.access_token);
        openGooglePicker(response.access_token);
      },
    });
    tokenClient.requestAccessToken({ prompt: 'consent' });
  };

  const openGooglePicker = (token: string) => {
    window.gapi.load('picker', () => {
      const picker = new window.google.picker.PickerBuilder()
        .addView(window.google.picker.ViewId.SPREADSHEETS)
        .setOAuthToken(token)
        .setDeveloperKey(GOOGLE_API_KEY)
        .setCallback((data: any) => {
          if (data.action === window.google.picker.Action.PICKED) {
            const document = data.docs[0];
            setSheetId(document.id);
            setSpreadsheetName(document.name);
          }
        })
        .build();
      picker.setVisible(true);
    });
  };

  const handleAttachSource = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (activeTab === 'database') {
        const formData = new FormData();
        formData.append('db_type', dbType);
        formData.append('connection_name', connName);
        formData.append('connection_url', connUrl);
        await apiClient.post('/connect/database', formData);
        
        setStagedSources(prev => [...prev, { name: connName, type: 'Database' }]);
        setConnName('');
        setConnUrl('');
      } 
      else if (activeTab === 'csv' || activeTab === 'excel') {
        if (files.length === 0) throw new Error(`Please select at least one file.`);
        for (const file of files) {
          const formData = new FormData();
          const safeTableName = file.name.replace(/\.[^/.]+$/, "").replace(/[^a-zA-Z0-9_]/g, "_").toLowerCase();
          formData.append('table_name', safeTableName);
          formData.append('file', file);
          await apiClient.post('/connect/file', formData);
          
          setStagedSources(prev => [...prev, { name: safeTableName, type: activeTab.toUpperCase() }]);
        }
        setFiles([]);
      } 
      else if (activeTab === 'sheets') {
        if (!sheetId || !accessToken) throw new Error("Please authenticate and select a Google Sheet first.");
        
        const formData = new FormData();
        formData.append('spreadsheet_id', sheetId);
        formData.append('spreadsheet_name', spreadsheetName);
        formData.append('access_token', accessToken);
        
        await apiClient.post('/connect/google_sheets', formData);
        
        setStagedSources(prev => [...prev, { name: spreadsheetName, type: 'Google Sheets' }]);
        setSheetId('');
        setSpreadsheetName('');
      }
      
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || 'Connection failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-screen h-screen bg-slate-100 flex items-center justify-center p-6 font-sans">
      {/* Strict fixed height (h-[550px]) to match Dashboard and prevent stretching */}
      <div className="bg-white rounded-xl shadow-xl w-full max-w-5xl h-[550px] flex overflow-hidden border border-gray-200">
        
        {/* LEFT PANEL: STAGING CART */}
        <div className="w-1/3 bg-slate-50 border-r border-gray-200 p-8 flex flex-col h-full">
          <div className="flex items-center gap-3 mb-6 shrink-0">
            <div className="bg-blue-500 w-10 h-10 rounded-lg flex items-center justify-center shadow-md shrink-0">
              <Server className="text-white" size={20} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-800">Active Workspace</h2>
              <p className="text-xs text-slate-500">Staged federated sources</p>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto space-y-3 pr-2">
            {stagedSources.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-400 text-sm border-2 border-dashed border-slate-200 rounded-lg p-4 text-center">
                Workspace is empty. Attach databases or files to begin.
              </div>
            ) : (
              stagedSources.map((source, idx) => (
                <div key={idx} className="bg-white p-3 rounded-md border border-slate-200 shadow-sm flex flex-col">
                  <span className="text-xs font-bold text-blue-600 uppercase tracking-wider mb-1">{source.type}</span>
                  <span className="text-sm font-semibold text-slate-700 truncate">{source.name}</span>
                </div>
              ))
            )}
          </div>

          <button 
            onClick={connectWorkspace}
            disabled={stagedSources.length === 0}
            className="w-full mt-6 shrink-0 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-300 text-white font-semibold py-3 px-4 rounded-md transition-all flex justify-center items-center gap-2 shadow-md"
          >
            Proceed to Canvas <ArrowRight size={18} />
          </button>
        </div>

        {/* RIGHT PANEL: CONNECTION FORMS */}
        <div className="w-2/3 flex flex-col h-full bg-white p-8">
          <h1 className="text-2xl font-bold text-slate-800 mb-6 shrink-0">Add Data Source</h1>
          
          <div className="flex border-b border-gray-200 overflow-x-auto shrink-0 mb-6">
            <button onClick={() => setActiveTab('database')} className={`flex-1 py-3 flex justify-center items-center gap-2 font-medium transition-colors border-b-2 ${activeTab === 'database' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
              <Database size={16} /> Relational DB
            </button>
            <button onClick={() => setActiveTab('csv')} className={`flex-1 py-3 flex justify-center items-center gap-2 font-medium transition-colors border-b-2 ${activeTab === 'csv' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
              <FileText size={16} /> CSV Files
            </button>
            <button onClick={() => setActiveTab('excel')} className={`flex-1 py-3 flex justify-center items-center gap-2 font-medium transition-colors border-b-2 ${activeTab === 'excel' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
              <TableProperties size={16} /> Excel Files
            </button>
            <button onClick={() => setActiveTab('sheets')} className={`flex-1 py-3 flex justify-center items-center gap-2 font-medium transition-colors border-b-2 ${activeTab === 'sheets' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
              <Link size={16} /> Google Sheets
            </button>
          </div>

          <div className="flex-1 overflow-y-auto pr-2">
            {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md shrink-0">{error}</div>}

            {/* Removed justify-between and flex-1 so elements stack tightly */}
            <form onSubmit={handleAttachSource} className="flex flex-col gap-6">
              
              {activeTab === 'database' && (
                <div className="space-y-4">
                  <div className="flex gap-4">
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Database Type</label>
                      <select 
                        value={dbType} onChange={e => setDbType(e.target.value)}
                        className="w-full border border-gray-300 rounded-md p-2.5 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none bg-slate-50"
                      >
                        <option value="postgres">PostgreSQL</option>
                        <option value="mysql">MySQL</option>
                      </select>
                    </div>
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Connection Alias</label>
                      <input 
                        type="text" required value={connName} onChange={e => setConnName(e.target.value)}
                        placeholder="e.g. prod_db"
                        className="w-full border border-gray-300 rounded-md p-2.5 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none bg-slate-50"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Connection URL</label>
                    <input 
                      type="password" required value={connUrl} onChange={e => setConnUrl(e.target.value)}
                      placeholder={dbType === 'mysql' ? 'mysql://user:password@host:port/dbname' : 'postgresql://user:password@host:port/dbname'}
                      className="w-full border border-gray-300 rounded-md p-2.5 text-sm focus:ring-blue-500 focus:border-blue-500 outline-none bg-slate-50"
                    />
                  </div>
                </div>
              )}

              {(activeTab === 'csv' || activeTab === 'excel') && (
                <div className="space-y-4">
                  <div className="bg-blue-50 p-4 rounded-md border border-blue-100 text-sm text-blue-800 leading-relaxed">
                    You can select multiple files at once. Each file becomes its own queryable table in the unified workspace.
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Upload {activeTab.toUpperCase()} File(s)</label>
                    <input 
                      type="file" multiple accept={activeTab === 'csv' ? '.csv' : '.xlsx'} 
                      onChange={e => {
                        const newFiles = Array.from(e.target.files || []);
                        setFiles(prev => {
                          const existingNames = new Set(prev.map(f => f.name));
                          const uniqueNewFiles = newFiles.filter(f => !existingNames.has(f.name));
                          return [...prev, ...uniqueNewFiles];
                        });
                        e.target.value = '';
                      }}
                      className="w-full border border-gray-300 rounded-md p-2 text-sm file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-100 file:text-blue-700 hover:file:bg-blue-200 cursor-pointer"
                    />
                  </div>
                  {files.length > 0 && (
                    <div className="bg-slate-50 p-3 rounded-md border border-slate-200 max-h-40 overflow-y-auto">
                      <div className="flex justify-between items-center mb-2">
                        <p className="text-xs font-semibold text-slate-600">Pending Uploads ({files.length}):</p>
                        <button type="button" onClick={() => setFiles([])} className="text-xs font-bold text-red-500 hover:text-red-700">Clear All</button>
                      </div>
                      <ul className="space-y-2">
                        {files.map((f, i) => (
                          <li key={i} className="flex justify-between items-center bg-white p-2 px-3 rounded border border-slate-200 text-sm shadow-sm">
                            <span className="font-mono text-slate-700">{f.name.replace(/\.[^/.]+$/, "").replace(/[^a-zA-Z0-9_]/g, "_").toLowerCase()}</span>
                            <button type="button" onClick={() => setFiles(files.filter((_, idx) => idx !== i))} className="text-slate-400 hover:text-red-500 font-bold px-2 text-lg">×</button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'sheets' && (
                <div className="space-y-4">
                  <div className="bg-blue-50 p-4 rounded-md border border-blue-100 text-sm text-blue-800 leading-relaxed">
                    Securely authenticate to select a Google Spreadsheet. Every tab in the workbook will be ingested as an independent relational table.
                  </div>
                  {!sheetId ? (
                    <button
                      type="button"
                      onClick={handleGoogleSheetsAuth}
                      className="w-full bg-white border border-gray-300 text-gray-700 font-semibold py-3 px-4 rounded-md shadow-sm hover:bg-gray-50 flex justify-center items-center gap-3"
                    >
                      <svg className="w-6 h-6" viewBox="0 0 24 24">
                        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                      </svg>
                      Authenticate & Pick Sheet
                    </button>
                  ) : (
                    <div className="bg-green-50 border border-green-200 text-green-800 p-4 rounded-md flex justify-between items-center shadow-sm">
                      <div className="flex flex-col">
                        <span className="font-semibold flex items-center gap-2">
                          <CheckSquare size={18} className="text-green-600" /> Workbook Selected
                        </span>
                        <span className="text-sm text-green-700 mt-1 font-mono">{spreadsheetName}</span>
                      </div>
                      <button type="button" onClick={() => {setSheetId(''); setSpreadsheetName('');}} className="text-green-600 hover:text-green-900 text-xs font-bold uppercase px-3 py-2 bg-green-100 hover:bg-green-200 rounded transition-colors">
                        Change
                      </button>
                    </div>
                  )}
                </div>
              )}

              <button 
                type="submit" disabled={loading || (activeTab === 'csv' && files.length === 0) || (activeTab === 'excel' && files.length === 0) || (activeTab === 'sheets' && !sheetId)}
                className="w-full shrink-0 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:text-slate-500 text-white font-semibold py-3.5 px-4 rounded-md transition-all flex justify-center items-center gap-2 shadow-sm"
              >
                {loading ? <Loader2 className="animate-spin" size={20} /> : <Plus size={20} />}
                {loading ? 'Attaching Source...' : 'Attach to Workspace'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}