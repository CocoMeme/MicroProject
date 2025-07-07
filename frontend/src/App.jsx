import { useState } from 'react'
import Sidebar from './layouts/Sidebar'
import MainLayout from './layouts/MainLayout'
import Dashboard from './components/Dashboard'
import useApiData from './hooks/useApiData'
import './css/App.css'

function App() {
  const [activeSection, setActiveSection] = useState('dashboard')
  
  // API base URL - adjust this for your backend
  const API_BASE = 'http://localhost:5000/api'
  
  // Use custom hook for data management
  const {
    dashboardData,
    systemStatus,
    recentParcels,
    loading,
    error,
    lastUpdate,
    refreshData
  } = useApiData(API_BASE)

  const renderContent = () => {
    if (loading) {
      return (
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading Dashboard...</p>
        </div>
      )
    }

    switch (activeSection) {
      case 'dashboard':
        return (
          <Dashboard 
            dashboardData={dashboardData}
            systemStatus={systemStatus}
            recentParcels={recentParcels}
            lastUpdate={lastUpdate}
            onRefresh={refreshData}
          />
        )
      case 'parcels':
        return (
          <div className="content-placeholder">
            <h2>Parcels Management</h2>
            <p>Parcel tracking and management features coming soon...</p>
          </div>
        )
      case 'system':
        return (
          <div className="content-placeholder">
            <h2>System Control</h2>
            <p>System configuration and control panel coming soon...</p>
          </div>
        )
      case 'analytics':
        return (
          <div className="content-placeholder">
            <h2>Analytics</h2>
            <p>Performance analytics and reports coming soon...</p>
          </div>
        )
      case 'settings':
        return (
          <div className="content-placeholder">
            <h2>Settings</h2>
            <p>Application settings and preferences coming soon...</p>
          </div>
        )
      default:
        return (
          <Dashboard 
            dashboardData={dashboardData}
            systemStatus={systemStatus}
            recentParcels={recentParcels}
          />
        )
    }
  }

  const getPageTitle = () => {
    switch (activeSection) {
      case 'dashboard': return 'Dashboard'
      case 'parcels': return 'Parcel Management'
      case 'system': return 'System Control'
      case 'analytics': return 'Analytics'
      case 'settings': return 'Settings'
      default: return 'Dashboard'
    }
  }

  const getPageSubtitle = () => {
    switch (activeSection) {
      case 'dashboard': return 'Real-time monitoring and overview'
      case 'parcels': return 'Track and manage parcels'
      case 'system': return 'Configure system settings'
      case 'analytics': return 'Performance insights and reports'
      case 'settings': return 'Application preferences'
      default: return 'Real-time monitoring and overview'
    }
  }

  return (
    <div className="App">
      <Sidebar 
        activeSection={activeSection} 
        setActiveSection={setActiveSection} 
      />
      <MainLayout 
        title={getPageTitle()} 
        subtitle={getPageSubtitle()}
      >
        {renderContent()}
      </MainLayout>
    </div>
  )
}

export default App
