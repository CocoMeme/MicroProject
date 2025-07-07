import React from 'react'
import StatCard from './StatCard'
import SystemStatus from './SystemStatus'
import RecentParcels from './RecentParcels'
import '../css/Dashboard.css'

const Dashboard = ({ dashboardData, systemStatus, recentParcels, lastUpdate, onRefresh }) => {
  if (!dashboardData) return (
    <div className="loading-state">
      <div className="loading-spinner"></div>
      <p>Loading dashboard data...</p>
    </div>
  )

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString()
  }

  const formatLastUpdate = (date) => {
    if (!date) return 'Never'
    return date.toLocaleTimeString()
  }

  return (
    <div className="dashboard">
      <div className="dashboard-info">
        <div className="system-status-indicator">
          <span className={`status-dot ${dashboardData.system_status === 'operational' ? 'green' : 'red'}`}></span>
          <span className="status-text">{dashboardData.system_status.toUpperCase()}</span>
        </div>
        <div className="update-info">
          <div className="last-update">
            Data updated: {formatLastUpdate(lastUpdate)}
          </div>
          {onRefresh && (
            <button className="refresh-btn" onClick={onRefresh} title="Refresh data">
              🔄
            </button>
          )}
        </div>
      </div>

      <div className="dashboard-grid">
        {/* Main Stats */}
        <div className="stats-section">
          <StatCard 
            title="Total Parcels" 
            value={dashboardData.total_parcels} 
            icon="📦"
            color="blue"
          />
          <StatCard 
            title="Processed Today" 
            value={dashboardData.processed_today} 
            icon="✅"
            color="green"
          />
          <StatCard 
            title="Pending" 
            value={dashboardData.pending_parcels} 
            icon="⏳"
            color="orange"
          />
          <StatCard 
            title="Rate (per hour)" 
            value={dashboardData.sorting_rate} 
            icon="⚡"
            color="purple"
          />
        </div>

        {/* System Status */}
        <div className="system-section">
          <SystemStatus 
            systemStatus={systemStatus}
            conveyorSpeed={dashboardData.conveyor_speed}
          />
        </div>

        {/* Recent Parcels */}
        <div className="parcels-section">
          <RecentParcels parcels={recentParcels} />
        </div>
      </div>
    </div>
  )
}

export default Dashboard
