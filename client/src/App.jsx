import React from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import { Provider } from 'react-redux';
import AppRoutes from './Components/Routes/routes';
import { store } from './Components/store/store';

// NavBar and Footer are rendered inside each page component (Dashboard, etc.)
// to ensure they only appear on authenticated pages and maintain proper
// sidebar + navbar layout. Do NOT render them globally here.

const App = () => {
  return (
    <Provider store={store}>
      <Router>
        <AppRoutes />
      </Router>
    </Provider>
  );
};

export default App;