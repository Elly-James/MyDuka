import React from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import { AuthProvider } from './Components/context/AuthContext';
import AppRoutes from './Components/Routes/routes';
import NavBar from './Components/NavBar/NavBar';
import Footer from './Components/Footer/Footer';
import './App.css';

const App = () => {
  return (
    <Router>
      <AuthProvider>
        <div className="app-container">
          <NavBar />
          <div className="content-wrapper">
            <AppRoutes />
          </div>
          <Footer />
        </div>
      </AuthProvider>
    </Router>
  );
};

export default App;