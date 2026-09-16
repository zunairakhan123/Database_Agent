import axios from 'axios';

export const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/v1',
});

// Dynamically inject the workspace ID and active thread ID into every request
apiClient.interceptors.request.use((config) => {
  const workspaceId = localStorage.getItem('agentic_workspace_id') || 'default_workspace';
  const activeThreadId = localStorage.getItem('agentic_active_thread_id') || workspaceId;
  
  config.headers['X-Workspace-ID'] = workspaceId;
  config.headers['X-Thread-ID'] = activeThreadId;
  
  return config;
});