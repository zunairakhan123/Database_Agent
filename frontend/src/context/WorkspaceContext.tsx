import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';

interface ChatThread {
  id: string;
  title: string;
  messages: any[];
}

interface WorkspaceMeta {
  id: string;
  name: string;
  lastAccessed: number;
}

interface WorkspaceContextType {
  workspaceId: string;
  isConnected: boolean;
  syncedTables: string[];
  threads: ChatThread[];
  activeThreadId: string;
  messages: any[];
  setActiveThreadId: (id: string) => void;
  createNewThread: () => void;
  deleteThread: (id: string) => void;
  setMessages: React.Dispatch<React.SetStateAction<any[]>>;
  setSyncedTables: (tables: string[]) => void;
  connectWorkspace: () => void;
  disconnectWorkspace: () => void;
  navigateToAddSource: () => void;
  loadWorkspace: (id: string) => void;
  createNewWorkspace: () => void;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [workspaceId, setWorkspaceId] = useState<string>('');
  const [isConnected, setIsConnected] = useState(false);
  const [syncedTables, setSyncedTables] = useState<string[]>([]);
  
  const [threads, setThreads] = useState<ChatThread[]>([{ id: 'default_thread', title: 'Main Session', messages: [] }]);
  const [activeThreadId, setActiveThreadId] = useState<string>('default_thread');
  
  const navigate = useNavigate();

  const saveToHistory = useCallback((id: string) => {
    if (!id) return;
    const history: WorkspaceMeta[] = JSON.parse(localStorage.getItem('agentic_workspace_history') || '[]');
    const existingIndex = history.findIndex(w => w.id === id);
    
    if (existingIndex >= 0) {
      history[existingIndex].lastAccessed = Date.now();
    } else {
      history.push({ id, name: `Workspace ${id.slice(-4)}`, lastAccessed: Date.now() });
    }
    localStorage.setItem('agentic_workspace_history', JSON.stringify(history));
  }, []);

  // HYDRATION: Restore state ONLY. Do not force route redirects here.
  useEffect(() => {
    const currentId = localStorage.getItem('agentic_workspace_id');
    if (currentId) {
      setWorkspaceId(currentId);
      saveToHistory(currentId);

      const hydrateSession = async (wsId: string) => {
        try {
          const res = await apiClient.get('/catalog/tables', { headers: { 'X-Workspace-ID': wsId } });
          if (res.data && res.data.tables && res.data.tables.length > 0) {
            setIsConnected(true);
            // DELETED the forced redirect. We let the user stay on whatever page they are on.
          }
        } catch (error) {
          console.debug("Hydration check failed.");
        }
      };
      hydrateSession(currentId);
    } else {
      // Only redirect if they genuinely have no active session at all
      if (window.location.pathname !== '/') {
        navigate('/');
      }
    }
  }, [navigate, saveToHistory]);

  useEffect(() => {
    localStorage.setItem('agentic_active_thread_id', activeThreadId);
  }, [activeThreadId]);

  const messages = threads.find(t => t.id === activeThreadId)?.messages || [];

  const setMessages: React.Dispatch<React.SetStateAction<any[]>> = (updater) => {
    setThreads(prevThreads => 
      prevThreads.map(thread => {
        if (thread.id === activeThreadId) {
          const newMsgs = typeof updater === 'function' ? updater(thread.messages) : updater;
          let title = thread.title;
          if (thread.title === 'Main Session' && newMsgs.length > 0 && newMsgs[0].content) {
            title = newMsgs[0].content.slice(0, 25) + '...';
          }
          return { ...thread, messages: newMsgs, title };
        }
        return thread;
      })
    );
  };

  const createNewThread = () => {
    const newId = `thread_${Math.random().toString(36).substring(2, 10)}`;
    setThreads(prev => [{ id: newId, title: 'New Analysis', messages: [] }, ...prev]);
    setActiveThreadId(newId);
  };

  const deleteThread = (id: string) => {
    if (threads.length <= 1) return; 
    const remaining = threads.filter(t => t.id !== id);
    setThreads(remaining);
    if (activeThreadId === id) setActiveThreadId(remaining[0].id);
  };

  const loadWorkspace = (id: string) => {
    setWorkspaceId(id);
    localStorage.setItem('agentic_workspace_id', id);
    saveToHistory(id);
    setIsConnected(true);
    navigate('/model/sources');
  };

  const createNewWorkspace = () => {
    const newId = `ws_${Math.random().toString(36).substring(2, 15)}`;
    setWorkspaceId(newId);
    localStorage.setItem('agentic_workspace_id', newId);
    saveToHistory(newId);
    setSyncedTables([]);
    setThreads([{ id: 'default_thread', title: 'Main Session', messages: [] }]);
    navigate('/connect');
  };

  const connectWorkspace = () => {
    setIsConnected(true);
    navigate('/model/sources');
  };

  const navigateToAddSource = () => {
    navigate('/connect');
  };

  const disconnectWorkspace = () => {
    setIsConnected(false);
    setSyncedTables([]);
    setThreads([{ id: 'default_thread', title: 'Main Session', messages: [] }]);
    setActiveThreadId('default_thread');
    localStorage.removeItem('agentic_workspace_id'); 
    setWorkspaceId('');
    navigate('/'); 
  };

  return (
    <WorkspaceContext.Provider value={{
      workspaceId, isConnected, syncedTables, threads, activeThreadId, messages,
      setActiveThreadId, createNewThread, deleteThread, setMessages, setSyncedTables, 
      connectWorkspace, disconnectWorkspace, navigateToAddSource, loadWorkspace, createNewWorkspace
    }}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) throw new Error('useWorkspace must be used within a WorkspaceProvider');
  return context;
}