import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { WorkspaceProvider } from './context/WorkspaceContext';
import MainLayout from './layouts/MainLayout';
import ConnectionScreen from './components/ConnectionScreen';
import Dashboard from './components/Dashboard';
import Sidebar from './components/Sidebar'; 
import DatabaseERD from './components/DatabaseERD/DatabaseERD';
import AgentChat from './components/AgentChat';

function App() {
  return (
    <BrowserRouter>
      <WorkspaceProvider>
        <Routes>
          {/* ROOT DIRECTS STRICTLY TO DASHBOARD */}
          <Route path="/" element={<Dashboard />} />
          <Route path="/dashboard" element={<Navigate to="/" replace />} />
          
          <Route path="/connect" element={<ConnectionScreen />} />
          
          <Route element={<MainLayout />}>
            <Route path="/model/sources" element={<Sidebar />} />
            <Route path="/model/erd" element={<DatabaseERD />} />
            <Route path="/explore" element={<AgentChat />} />
          </Route>
          
          {/* Fallback routing MUST point to root, not /connect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </WorkspaceProvider>
    </BrowserRouter>
  );
}

export default App;