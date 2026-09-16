import React, { useState, useEffect, useMemo, useRef } from 'react';
import { apiClient } from '../api/client';
import { Send, Terminal, Database, BarChart2, MessageSquare, Loader2, Sparkles, Settings2, User, Plus, Trash2, MessageCircle } from 'lucide-react';
import { 
  BarChart, Bar, LineChart, Line, AreaChart, Area, ComposedChart, ScatterChart, Scatter,
  PieChart, Pie, Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend 
} from 'recharts';
import { useWorkspace } from '../context/WorkspaceContext';

const COLORS = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

const formatSQL = (sql?: string) => {
  if (!sql) return "";
  return sql
    .replace(/\b(SELECT|FROM|WHERE|GROUP BY|ORDER BY|LEFT JOIN|RIGHT JOIN|INNER JOIN|HAVING|LIMIT)\b/gi, "\n$1")
    .replace(/,\s+/g, ",\n  ") 
    .trim();
};

const MessageCard = ({ msg }: { msg: any }) => {
  if (msg.role === 'user') {
    return (
      <div className="flex gap-4 items-start w-full max-w-4xl mx-auto my-4">
        <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center shrink-0">
          <User size={16} className="text-slate-600" />
        </div>
        <div className="bg-slate-800 text-white p-4 rounded-2xl rounded-tl-none text-sm shadow-md font-medium">
          {msg.content}
        </div>
      </div>
    );
  }

  const response = msg.data;
  const [activeTab, setActiveTab] = useState<'table' | 'sql' | 'chart'>('chart');
  const [chartType, setChartType] = useState<'bar' | 'line' | 'area' | 'composed' | 'scatter' | 'pie' | 'radar'>('bar');
  const [xAxisKey, setXAxisKey] = useState<string>('');
  const [yAxisKeys, setYAxisKeys] = useState<string[]>([]);

  const rawResults = response?.results || [];
  const keys = useMemo(() => rawResults.length > 0 ? Object.keys(rawResults[0]) : [], [rawResults]);
  const canChart = rawResults.length > 0 && keys.length >= 2;

  // 1. DATA SANITIZATION: Strip currencies/commas so Recharts can mathematically plot the Y-Axis
  const parsedResults = useMemo(() => {
    return rawResults.map((row: any) => {
      const sanitizedRow = { ...row };
      keys.forEach(k => {
        const val = sanitizedRow[k];
        if (typeof val === 'string') {
          const cleaned = val.replace(/[$, ]/g, '');
          if (cleaned !== '' && !isNaN(Number(cleaned))) {
            sanitizedRow[k] = Number(cleaned);
          }
        }
      });
      return sanitizedRow;
    });
  }, [rawResults, keys]);

  useEffect(() => {
    if (parsedResults.length > 0) {
      const sample = parsedResults[0];
      const numericCols: string[] = [];
      const categoricalCols: string[] = [];

      keys.forEach(key => {
        const val = sample[key];
        if (typeof val === 'number' || (val !== null && val !== '' && !isNaN(Number(val)))) {
          numericCols.push(key);
        } else {
          categoricalCols.push(key);
        }
      });

      setXAxisKey(categoricalCols.length > 0 ? categoricalCols[0] : keys[0]);
      setYAxisKeys(numericCols.length > 0 ? numericCols : [keys[1] || keys[0]]);
      
      if (numericCols.length === 0) {
        setChartType('table' as any);
        setActiveTab('table');
      } else if (categoricalCols.length === 0 && numericCols.length >= 2) {
        setChartType('scatter');
      } else {
        setChartType('bar');
      }
    } else {
      setActiveTab('sql'); 
    }
  }, [keys, parsedResults]);

  const availableCharts = useMemo(() => {
    return [
      { id: 'bar', name: 'Bar Chart', valid: true },
      { id: 'line', name: 'Line Chart', valid: true },
      { id: 'area', name: 'Area Chart', valid: true },
      { id: 'composed', name: 'Dual-Axis (Bar + Line)', valid: yAxisKeys.length >= 2 },
      { id: 'scatter', name: 'Scatter Plot', valid: yAxisKeys.length >= 2 },
      { id: 'pie', name: 'Pie Chart', valid: parsedResults.length <= 20 && yAxisKeys.length >= 1 },
      { id: 'radar', name: 'Radar Chart', valid: parsedResults.length <= 12 && yAxisKeys.length >= 1 }
    ].filter(c => c.valid);
  }, [parsedResults.length, yAxisKeys]);

  const renderChart = () => {
    if (!xAxisKey || yAxisKeys.length === 0) return null;

    const xAxisProps = {
      dataKey: xAxisKey,
      tick: { fontSize: 11, fill: '#64748b' },
      axisLine: false,
      tickLine: false,
      angle: -45,
      textAnchor: 'end' as const,
      height: 70 
    };

    switch (chartType) {
      case 'line':
        return (
          <LineChart data={parsedResults} margin={{ bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis {...xAxisProps} />
            <YAxis tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
            <Legend wrapperStyle={{ paddingTop: '10px' }} />
            {yAxisKeys.map((y, i) => <Line key={y} type="monotone" dataKey={y} stroke={COLORS[i % COLORS.length]} strokeWidth={3} dot={{ r: 4 }} />)}
          </LineChart>
        );
      case 'area':
        return (
          <AreaChart data={parsedResults} margin={{ bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis {...xAxisProps} />
            <YAxis tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
            <Legend wrapperStyle={{ paddingTop: '10px' }} />
            {yAxisKeys.map((y, i) => <Area key={y} type="monotone" dataKey={y} stroke={COLORS[i % COLORS.length]} fill={COLORS[i % COLORS.length]} fillOpacity={0.3} strokeWidth={2} />)}
          </AreaChart>
        );
      case 'composed':
        return (
          <ComposedChart data={parsedResults} margin={{ bottom: 20, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis {...xAxisProps} />
            
            {/* 2. DUAL AXIS SCALING: Left Axis for Bar, Right Axis for Line */}
            <YAxis yAxisId="left" orientation="left" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
            {yAxisKeys.length > 1 && (
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
            )}
            
            <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
            <Legend wrapperStyle={{ paddingTop: '10px' }} />
            
            {/* Map data keys to their respective independent axes */}
            <Bar yAxisId="left" dataKey={yAxisKeys[0]} fill={COLORS[0]} radius={[4, 4, 0, 0]} maxBarSize={50} />
            {yAxisKeys[1] && <Line yAxisId="right" type="monotone" dataKey={yAxisKeys[1]} stroke={COLORS[2]} strokeWidth={3} />}
          </ComposedChart>
        );
      case 'scatter':
        return (
          <ScatterChart margin={{ bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey={yAxisKeys[0]} type="number" name={yAxisKeys[0]} tick={{ fontSize: 11, fill: '#64748b' }} />
            <YAxis dataKey={yAxisKeys[1] || yAxisKeys[0]} type="number" name={yAxisKeys[1] || yAxisKeys[0]} tick={{ fontSize: 11, fill: '#64748b' }} />
            <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ borderRadius: '8px' }} />
            <Legend wrapperStyle={{ paddingTop: '10px' }} />
            <Scatter name="Data Distribution" data={parsedResults} fill={COLORS[0]} />
          </ScatterChart>
        );
      case 'pie':
        return (
          <PieChart margin={{ bottom: 20 }}>
            <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
            <Legend layout="horizontal" verticalAlign="bottom" align="center" />
            <Pie data={parsedResults} dataKey={yAxisKeys[0]} nameKey={xAxisKey} cx="50%" cy="50%" outerRadius={110} label>
              {parsedResults.map((_: any, index: number) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
            </Pie>
          </PieChart>
        );
      case 'radar':
        return (
          <RadarChart cx="50%" cy="50%" outerRadius={100} data={parsedResults} margin={{ bottom: 20 }}>
            <PolarGrid stroke="#e2e8f0" />
            <PolarAngleAxis dataKey={xAxisKey} tick={{ fontSize: 11, fill: '#64748b' }} />
            <PolarRadiusAxis angle={30} domain={['auto', 'auto']} />
            <Tooltip contentStyle={{ borderRadius: '8px' }} />
            <Legend wrapperStyle={{ paddingTop: '10px' }} />
            {yAxisKeys.map((y, i) => (
              <Radar key={y} name={y} dataKey={y} stroke={COLORS[i % COLORS.length]} fill={COLORS[i % COLORS.length]} fillOpacity={0.4} />
            ))}
          </RadarChart>
        );
      case 'bar':
      default:
        return (
          <BarChart data={parsedResults} margin={{ bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis {...xAxisProps} />
            <YAxis tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
            <Tooltip cursor={{ fill: '#f1f5f9' }} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
            <Legend wrapperStyle={{ paddingTop: '10px' }} />
            {yAxisKeys.map((y, i) => <Bar key={y} dataKey={y} fill={COLORS[i % COLORS.length]} radius={[4, 4, 0, 0]} maxBarSize={50} />)}
          </BarChart>
        );
    }
  };

  return (
    <div className="flex gap-4 items-start w-full max-w-6xl mx-auto my-6">
      <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0 border border-blue-200">
        <Sparkles size={16} className="text-blue-600" />
      </div>
      
      <div className="flex-1 flex flex-col gap-3 min-w-0">
        {response.conversational_reply && (
          <div className="text-sm text-slate-700 bg-white p-4 rounded-xl border border-slate-200 shadow-sm leading-relaxed">
            {response.conversational_reply}
          </div>
        )}

        {response.error && (
          <div className="p-4 text-red-600 bg-red-50 text-sm font-medium border-l-4 border-red-500 rounded-r-xl">
            {response.error}
          </div>
        )}

        {!response.error && response.generated_sql && (
          <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden flex flex-col w-full">
            <div className="flex border-b border-gray-100 bg-slate-50 text-sm font-semibold text-gray-600">
              <button 
                onClick={() => setActiveTab('chart')} disabled={!canChart}
                className={`flex-1 py-3 flex justify-center items-center gap-2 border-b-2 transition-colors ${!canChart ? 'opacity-40 cursor-not-allowed' : ''} ${activeTab === 'chart' ? 'border-blue-600 text-blue-700 bg-white' : 'border-transparent hover:bg-gray-100'}`}
              >
                <BarChart2 size={16} /> Visual Exploration
              </button>
              <button 
                onClick={() => setActiveTab('table')}
                className={`flex-1 py-3 flex justify-center items-center gap-2 border-b-2 transition-colors ${activeTab === 'table' ? 'border-blue-600 text-blue-700 bg-white' : 'border-transparent hover:bg-gray-100'}`}
              >
                <Database size={16} /> Data Grid
              </button>
              <button 
                onClick={() => setActiveTab('sql')}
                className={`flex-1 py-3 flex justify-center items-center gap-2 border-b-2 transition-colors ${activeTab === 'sql' ? 'border-blue-600 text-blue-700 bg-white' : 'border-transparent hover:bg-gray-100'}`}
              >
                <Terminal size={16} /> Execution Plan
              </button>
            </div>

            <div className="p-4 h-[450px] flex flex-col bg-white">
              {activeTab === 'chart' && canChart && (
                <div className="flex flex-col h-full gap-4">
                  <div className="flex flex-wrap gap-4 items-center bg-slate-50 p-2.5 rounded border border-slate-200 shrink-0">
                    <Settings2 size={16} className="text-slate-500" />
                    <select value={chartType} onChange={(e: any) => setChartType(e.target.value)} className="text-xs bg-white border border-slate-300 rounded px-2 py-1 text-slate-700 outline-none">
                      {availableCharts.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </select>
                    <div className="w-px h-4 bg-slate-300 mx-1"></div>
                    <select value={xAxisKey} onChange={(e) => setXAxisKey(e.target.value)} className="text-xs bg-white border border-slate-300 rounded px-2 py-1 text-slate-700 outline-none">
                      {keys.map(k => <option key={k} value={k}>X: {k}</option>)}
                    </select>
                  </div>
                  <div className="flex-1 w-full min-h-0">
                    <ResponsiveContainer width="100%" height="100%">
                      {renderChart() as React.ReactElement}
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {activeTab === 'table' && (
                <div className="h-full overflow-auto border border-gray-200 rounded shadow-inner">
                  <table className="w-full text-left text-sm border-collapse">
                    <thead className="bg-slate-50 sticky top-0 z-10 shadow-sm">
                      <tr>{keys.map((col) => <th key={col} className="p-3 font-semibold text-slate-600 whitespace-nowrap">{col}</th>)}</tr>
                    </thead>
                    <tbody>
                      {rawResults.map((row: any, i: number) => (
                        <tr key={i} className="border-b border-gray-100 last:border-0 hover:bg-blue-50/50">
                          {Object.values(row).map((val: any, j: number) => <td key={j} className="p-3 text-slate-700">{String(val)}</td>)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {activeTab === 'sql' && (
                <div className="h-full bg-[#0f172a] rounded p-4 overflow-auto">
                  <pre className="text-emerald-400 text-sm font-mono leading-relaxed">
                    {formatSQL(response.generated_sql)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default function AgentChat() {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  
  const { threads, activeThreadId, setActiveThreadId, createNewThread, deleteThread, messages, setMessages } = useWorkspace();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || loading) return;

    const userText = question;
    setQuestion('');
    
    const newHistory = [...messages, { role: 'user', content: userText }];
    setMessages(newHistory);
    setLoading(true);

    try {
      const apiHistory = messages.map(m => ({ role: m.role, content: m.content }));
      
      const res = await apiClient.post('/query', { 
        question: userText,
        chat_history: apiHistory 
      });

      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: res.data.conversational_reply || "Here is your data:", 
        data: res.data 
      }]);

    } catch (error) {
      console.error("Query failed:", error);
      setMessages(prev => [...prev, { role: 'assistant', content: "Query failed.", data: { error: "Network or Server Error." } }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full h-full bg-white flex overflow-hidden">
      {/* Multi-Chat Sessions Sidebar Drawer */}
      <div className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col shrink-0">
        <div className="p-4 border-b border-slate-800 flex justify-between items-center">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Chat Sessions</span>
          <button 
            onClick={createNewThread}
            className="p-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-md transition-all shadow-sm"
            title="New Chat Session"
          >
            <Plus size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          {threads.map(thread => (
            <div 
              key={thread.id}
              onClick={() => setActiveThreadId(thread.id)}
              className={`group flex items-center justify-between p-2.5 rounded-lg text-xs cursor-pointer transition-all ${activeThreadId === thread.id ? 'bg-blue-600 text-white font-medium shadow' : 'text-slate-300 hover:bg-slate-800'}`}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <MessageCircle size={14} className="shrink-0 opacity-75" />
                <span className="truncate">{thread.title}</span>
              </div>
              {threads.length > 1 && (
                <button 
                  onClick={(e) => { e.stopPropagation(); deleteThread(thread.id); }}
                  className="opacity-0 group-hover:opacity-100 hover:text-red-300 text-slate-400 p-1 transition-opacity"
                >
                  <Trash2 size={13} />
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Main Conversation Window */}
      <div className="flex-1 flex flex-col h-full bg-white min-w-0">
        <div className="p-4 border-b border-gray-100 bg-slate-50 flex items-center gap-2 shrink-0">
          <MessageSquare size={18} className="text-blue-600" />
          <h2 className="font-semibold text-slate-800 text-sm">Enterprise Analytics Chat</h2>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 bg-slate-50/50 scroll-smooth">
          {messages.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <Sparkles size={48} className="text-blue-200 mb-4" />
              <p className="text-sm font-medium text-slate-600">Ask a question to begin analysis</p>
            </div>
          )}

          {messages.map((msg, idx) => (
            <MessageCard key={idx} msg={msg} />
          ))}

          {loading && (
            <div className="flex gap-4 items-center w-full max-w-6xl mx-auto my-6 text-blue-600">
              <Loader2 size={24} className="animate-spin" />
              <span className="text-sm font-semibold tracking-wide">Synthesizing SQL & Executing...</span>
            </div>
          )}
        </div>

        <form onSubmit={handleQuery} className="p-6 border-t border-gray-200 bg-white shrink-0 shadow-[0_-4px_6px_-1px_rgb(0,0,0,0.05)]">
          <div className="max-w-4xl mx-auto flex gap-3">
            <input 
              type="text" value={question} onChange={(e) => setQuestion(e.target.value)}
              placeholder="Explore your data semantics..." disabled={loading}
              className="flex-1 border-2 border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 text-slate-700 font-medium disabled:opacity-50"
            />
            <button 
              type="submit" disabled={loading || !question.trim()}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white px-6 rounded-xl transition-all flex items-center justify-center font-semibold gap-2"
            >
              <Send size={18} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}