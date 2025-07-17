// Configuration file for API endpoints
const config = {
  // Backend API Configuration
  BACKEND_URL: process.env.REACT_APP_BACKEND_URL || 'http://192.168.100.61:5000',
  API_BASE_URL: process.env.REACT_APP_API_BASE_URL || 'http://192.168.100.61:5000/api',
  
  // Raspberry Pi Configuration
  RASPBERRY_PI_URL: process.env.REACT_APP_RASPBERRY_PI_URL || 'http://192.168.100.63:5001',
  
  // Individual host and port configurations for advanced usage
  BACKEND_HOST: process.env.REACT_APP_BACKEND_HOST || '192.168.100.61',
  BACKEND_PORT: process.env.REACT_APP_BACKEND_PORT || '5000',
  RASPBERRY_PI_HOST: process.env.REACT_APP_RASPBERRY_PI_HOST || '192.168.100.63',
  RASPBERRY_PI_PORT: process.env.REACT_APP_RASPBERRY_PI_PORT || '5001',
};

export default config;
