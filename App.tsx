import { useState } from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import RiskDetail from './pages/RiskDetail';
import AlertDetail from './pages/AlertDetail';
import AuditLog from './pages/AuditLog';
import './index.css';

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <BrowserRouter>
      <div className="app-layout">
        {/* Mobile overlay */}
        <div 
          className={`sidebar-overlay ${sidebarOpen ? 'visible' : ''}`} 
          onClick={() => setSidebarOpen(false)} 
        />

        {/* Sidebar */}
        <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
          <div className="sidebar-brand">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <h1>CCIS</h1>
                <p>Contract Compliance Intelligence</p>
              </div>
              <button className="sidebar-close-btn" onClick={() => setSidebarOpen(false)} aria-label="Close menu">
                ✕
              </button>
            </div>
          </div>
          <nav className="sidebar-nav">
            <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} end onClick={() => setSidebarOpen(false)}>
              <span className="nav-icon">📁</span>
              <span className="nav-label">Documents</span>
            </NavLink>
            <NavLink to="/dashboard" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span className="nav-icon">📊</span>
              <span className="nav-label">Dashboard</span>
            </NavLink>
            <NavLink to="/alerts" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span className="nav-icon">🔔</span>
              <span className="nav-label">Alerts</span>
            </NavLink>
            <NavLink to="/audit" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <span className="nav-icon">📝</span>
              <span className="nav-label">Audit Trails</span>
            </NavLink>
          </nav>
          <div className="sidebar-footer">
            <div className="sidebar-footer-badge">
              <span style={{ fontSize: '0.65rem', color: 'var(--accent-cyan)', fontWeight: 700 }}>AI-POWERED</span>
            </div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', marginTop: 4 }}>v1.0 · Claude Engine</div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="main-content">
          {/* Top bar with hamburger */}
          <div className="topbar">
            <button className="hamburger-btn" onClick={() => setSidebarOpen(true)} aria-label="Open menu">
              <span className="hamburger-line" />
              <span className="hamburger-line" />
              <span className="hamburger-line" />
            </button>
            <div className="topbar-title">CCIS</div>
          </div>
          <Routes>
            <Route path="/" element={<Upload />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/risks/:riskId" element={<RiskDetail />} />
            <Route path="/alerts" element={<AlertDetail />} />
            <Route path="/alerts/:alertId" element={<AlertDetail />} />
            <Route path="/audit" element={<AuditLog />} />
            <Route path="/audit/:docId" element={<AuditLog />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
