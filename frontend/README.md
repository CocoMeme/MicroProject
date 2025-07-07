# Frontend for Parcel Sorting Machine

This is the React frontend for the Parcel Sorting Machine project using Raspberry Pi 5 and ESP32.

## Setup

### Prerequisites
- Node.js 16 or higher
- npm (comes with Node.js)

### Installation

1. Install dependencies:
```bash
npm install
```

### Running the Application

1. Start the development server:
```bash
npm run dev
```

The development server will start on `http://localhost:5173`

2. Build for production:
```bash
npm run build
```

3. Preview the production build:
```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/     # React components
│   ├── pages/         # Page components
│   ├── hooks/         # Custom React hooks
│   ├── utils/         # Utility functions
│   ├── App.jsx        # Main App component
│   └── main.jsx       # Entry point
├── public/            # Static assets
├── package.json       # Dependencies and scripts
├── vite.config.js     # Vite configuration
├── .gitignore        # Git ignore file
└── README.md         # This file
```

## Development

- The frontend is built with React and Vite for fast development
- Hot Module Replacement (HMR) is enabled for instant updates
- ESLint is configured for code quality
- The app will communicate with the Flask backend API
- Real-time updates from ESP32 sensors will be displayed

## Technologies Used

- **React** - UI library
- **Vite** - Build tool and development server
- **JavaScript** - Programming language
- **CSS3** - Styling

## API Integration

*To be documented as API endpoints are implemented*+ Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.
