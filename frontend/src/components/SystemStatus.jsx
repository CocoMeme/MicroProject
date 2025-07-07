import React from 'react'
import '../css/SystemStatus.css'

const SystemStatus = ({ systemStatus, conveyorSpeed }) => {
  if (!systemStatus) return <div>Loading system status...</div>

  const getStatusColor = (status) => {
    if (status === 'running' || status === 'operational' || status === 'active' || status === 'connected' || status === 'healthy') {
      return 'green'
    }
    return 'red'
  }

  return (
    <div className="system-status-panel">
      <h2>System Status</h2>
      <div className="system-grid">
        <div className="system-item">
          <span className="system-label">Conveyor Belt</span>
          <span className={`system-value ${getStatusColor(systemStatus.conveyor_belt)}`}>
            {systemStatus.conveyor_belt}
          </span>
        </div>
        <div className="system-item">
          <span className="system-label">Sorting Arms</span>
          <span className={`system-value ${getStatusColor(systemStatus.sorting_arms)}`}>
            {systemStatus.sorting_arms}
          </span>
        </div>
        <div className="system-item">
          <span className="system-label">Sensors</span>
          <span className={`system-value ${getStatusColor(systemStatus.sensors)}`}>
            {systemStatus.sensors}
          </span>
        </div>
        <div className="system-item">
          <span className="system-label">ESP32</span>
          <span className={`system-value ${getStatusColor(systemStatus.esp32_connection)}`}>
            {systemStatus.esp32_connection}
          </span>
        </div>
        <div className="system-item">
          <span className="system-label">Raspberry Pi</span>
          <span className={`system-value ${getStatusColor(systemStatus.raspberry_pi)}`}>
            {systemStatus.raspberry_pi}
          </span>
        </div>
        <div className="system-item">
          <span className="system-label">Conveyor Speed</span>
          <span className="system-value">{conveyorSpeed} m/s</span>
        </div>
      </div>
      
      <div className="environmental-data">
        <div className="env-item">
          <span className="env-label">Temperature</span>
          <span className="env-value">{systemStatus.temperature}°C</span>
        </div>
        <div className="env-item">
          <span className="env-label">Humidity</span>
          <span className="env-value">{systemStatus.humidity}%</span>
        </div>
        <div className="env-item">
          <span className="env-label">Uptime</span>
          <span className="env-value">{systemStatus.uptime}</span>
        </div>
      </div>
    </div>
  )
}

export default SystemStatus
