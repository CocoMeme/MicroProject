import React from 'react'
import '../css/RecentParcels.css'

const RecentParcels = ({ parcels }) => {
  if (!parcels || parcels.length === 0) return <div>Loading recent parcels...</div>

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString()
  }

  const getSizeColor = (size) => {
    switch(size.toLowerCase()) {
      case 'small': return 'green'
      case 'medium': return 'orange'
      case 'large': return 'red'
      default: return 'gray'
    }
  }

  return (
    <div className="recent-parcels-panel">
      <h2>Recent Parcels</h2>
      <div className="parcels-table">
        <div className="table-header">
          <div className="col-id">ID</div>
          <div className="col-weight">Weight</div>
          <div className="col-size">Size</div>
          <div className="col-destination">Destination</div>
          <div className="col-time">Time</div>
        </div>
        <div className="table-body">
          {parcels.map((parcel) => (
            <div key={parcel.id} className="table-row">
              <div className="col-id">{parcel.id}</div>
              <div className="col-weight">{parcel.weight}kg</div>
              <div className="col-size">
                <span className={`size-badge ${getSizeColor(parcel.size)}`}>
                  {parcel.size}
                </span>
              </div>
              <div className="col-destination">{parcel.destination}</div>
              <div className="col-time">{formatTime(parcel.timestamp)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default RecentParcels
