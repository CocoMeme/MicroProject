import React from 'react'
import '../css/MainLayout.css'

const MainLayout = ({ children, title, subtitle }) => {
  return (
    <div className="main-layout">
      <div className="main-header">
        <div className="header-content">
          <h1 className="main-title">{title}</h1>
          {subtitle && <p className="main-subtitle">{subtitle}</p>}
        </div>
        <div className="header-actions">
          <div className="current-time">
            {new Date().toLocaleTimeString()}
          </div>
        </div>
      </div>
      
      <div className="main-content">
        {children}
      </div>
    </div>
  )
}

export default MainLayout
