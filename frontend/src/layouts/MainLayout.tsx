import { Outlet, NavLink, Navigate } from 'react-router-dom';
import { useWorkspace } from '../context/WorkspaceContext';
import { Database, Network, MessageSquare, LogOut } from 'lucide-react';

export default function MainLayout() {
  const { workspaceId, isConnected, disconnectWorkspace } = useWorkspace();

  // Protect the routes: If not connected, kick them back to the connection screen
  if (!isConnected) {
    return <Navigate to="/connect" replace />;
  }

  return (
    <div className="w-screen h-screen flex flex-col bg-slate-50 overflow-hidden font-sans">
      {/* Top Header */}
      <header className="h-14 bg-slate-900 flex items-center justify-between px-6 shadow-md z-20 shrink-0">
        <h1 className="text-lg font-bold text-white tracking-wide">
          Agentic BI <span className="text-blue-400">Platform</span>
        </h1>
        <div className="flex items-center gap-4">
          <span className="text-xs text-green-400 bg-green-400/10 px-2 py-1 rounded-full font-mono border border-green-500/20">
            ● Session Active
          </span>
          <span className="text-xs text-slate-400 font-mono hidden md:inline-block">
            {workspaceId}
          </span>
        </div>
      </header>

      {/* Main Body with Nav Rail */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Nav Rail */}
        <nav className="w-16 bg-slate-800 flex flex-col items-center py-4 gap-4 shadow-lg z-10 shrink-0">
          <NavLink to="/model/sources" title="Data Sources" className={({ isActive }) => `p-3 rounded-xl transition-all ${isActive ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400 hover:text-white hover:bg-slate-700'}`}>
            <Database size={20} />
          </NavLink>
          <NavLink to="/model/erd" title="Semantic Topology" className={({ isActive }) => `p-3 rounded-xl transition-all ${isActive ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400 hover:text-white hover:bg-slate-700'}`}>
            <Network size={20} />
          </NavLink>
          <NavLink to="/explore" title="Agent Chat" className={({ isActive }) => `p-3 rounded-xl transition-all ${isActive ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400 hover:text-white hover:bg-slate-700'}`}>
            <MessageSquare size={20} />
          </NavLink>
          
          <div className="mt-auto">
            <button onClick={disconnectWorkspace} title="Disconnect" className="p-3 rounded-xl text-slate-400 hover:text-red-400 hover:bg-slate-700 transition-all">
              <LogOut size={20} />
            </button>
          </div>
        </nav>

        {/* Dynamic Page Content */}
        <main className="flex-1 relative overflow-hidden bg-white">
          <Outlet />
        </main>
      </div>
    </div>
  );
}