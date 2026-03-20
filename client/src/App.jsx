import React from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import { Provider } from 'react-redux';
import AppRoutes from './Components/Routes/routes';
import { store } from './Components/store/store';

// IMPORTANT: NavBar and Footer are intentionally removed from here.
// Each role's pages (Merchant, Admin, Clerk) render their own
// NavBar and Footer inside their layouts to properly account
// for the fixed sidebar offset. Rendering them here causes
// double headers and a broken footer that ignores the sidebar.

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