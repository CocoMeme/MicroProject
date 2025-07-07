import React, { useState } from 'react'
import '../css/Sidebar.css'

const Sidebar = ({ activeSection, setActiveSection }) => {
  const [isCollapsed, setIsCollapsed] = useState(false)

  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'parcels', label: 'Parcels', icon: '📦' },
    { id: 'system', label: 'System', icon: '⚙️' },
    { id: 'analytics', label: 'Analytics', icon: '📈' },
    { id: 'settings', label: 'Settings', icon: '🔧' }
  ]

  const toggleSidebar = () => {
    setIsCollapsed(!isCollapsed)
  }

  return (
    <div className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="logo">
          <span className="logo-icon">🏭</span>
          {!isCollapsed && <span className="logo-text">Parcel Sorter</span>}
        </div>
        <button className="toggle-btn" onClick={toggleSidebar}>
          {isCollapsed ? '▶' : '◀'}
        </button>
      </div>
      
      <nav className="sidebar-nav">
        {menuItems.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${activeSection === item.id ? 'active' : ''}`}
            onClick={() => setActiveSection(item.id)}
            title={isCollapsed ? item.label : ''}
          >
            <span className="nav-icon">{item.icon}</span>
            {!isCollapsed && <span className="nav-label">{item.label}</span>}
          </button>
        ))}
      </nav>
      
      <div className="sidebar-footer">
        <div className="status-indicator">
          <span className="status-dot green"></span>
          {!isCollapsed && <span className="status-text">System Online</span>}
        </div>
      </div>
    </div>
  )
}

export default Sidebar
