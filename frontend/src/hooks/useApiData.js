import { useState, useEffect, useCallback, useRef } from 'react'

const useApiData = (apiBase) => {
  const [dashboardData, setDashboardData] = useState(null)
  const [systemStatus, setSystemStatus] = useState(null)
  const [recentParcels, setRecentParcels] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)
  
  // Use refs to track if component is still mounted
  const isMountedRef = useRef(true)
  
  // Fetch functions with better error handling
  const fetchDashboardData = useCallback(async () => {
    try {
      const response = await fetch(`${apiBase}/dashboard`)
      if (!response.ok) {
        throw new Error(`Dashboard API error: ${response.status}`)
      }
      const data = await response.json()
      if (isMountedRef.current) {
        setDashboardData(data)
        setError(null)
      }
    } catch (err) {
      console.error('Error fetching dashboard data:', err)
      if (isMountedRef.current) {
        setError(prev => ({ ...prev, dashboard: err.message }))
      }
    }
  }, [apiBase])

  const fetchSystemStatus = useCallback(async () => {
    try {
      const response = await fetch(`${apiBase}/system-status`)
      if (!response.ok) {
        throw new Error(`System status API error: ${response.status}`)
      }
      const data = await response.json()
      if (isMountedRef.current) {
        setSystemStatus(data)
        setError(null)
      }
    } catch (err) {
      console.error('Error fetching system status:', err)
      if (isMountedRef.current) {
        setError(prev => ({ ...prev, system: err.message }))
      }
    }
  }, [apiBase])

  const fetchRecentParcels = useCallback(async () => {
    try {
      const response = await fetch(`${apiBase}/recent-parcels`)
      if (!response.ok) {
        throw new Error(`Recent parcels API error: ${response.status}`)
      }
      const data = await response.json()
      if (isMountedRef.current) {
        setRecentParcels(data)
        setError(null)
      }
    } catch (err) {
      console.error('Error fetching recent parcels:', err)
      if (isMountedRef.current) {
        setError(prev => ({ ...prev, parcels: err.message }))
      }
    }
  }, [apiBase])

  // Fetch all data
  const fetchAllData = useCallback(async (isInitialLoad = false) => {
    if (isInitialLoad) {
      setLoading(true)
    }
    
    try {
      await Promise.all([
        fetchDashboardData(),
        fetchSystemStatus(),
        fetchRecentParcels()
      ])
      
      if (isMountedRef.current) {
        setLastUpdate(new Date())
      }
    } catch (err) {
      console.error('Error in fetchAllData:', err)
    } finally {
      if (isMountedRef.current && isInitialLoad) {
        setLoading(false)
      }
    }
  }, [fetchDashboardData, fetchSystemStatus, fetchRecentParcels])

  // Manual refresh function
  const refreshData = useCallback(() => {
    fetchAllData(false)
  }, [fetchAllData])

  useEffect(() => {
    // Initial data fetch
    fetchAllData(true)
    
    // Set up auto-refresh every 5 seconds
    const interval = setInterval(() => {
      fetchAllData(false)
    }, 5000)
    
    // Cleanup function
    return () => {
      clearInterval(interval)
      isMountedRef.current = false
    }
  }, [fetchAllData])

  return {
    dashboardData,
    systemStatus,
    recentParcels,
    loading,
    error,
    lastUpdate,
    refreshData
  }
}

export default useApiData
