import React from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import { Provider } from 'react-redux';
import AppRoutes from './Components/Routes/routes';
import NavBar from './Components/NavBar/NavBar';
import Footer from './Components/Footer/Footer';
import { store } from './Components/store/store';

const App = () => {
  return (
    <Provider store={store}>
      <Router>
        <div className="app-container">
          <NavBar />
          <div className="content-wrapper">
            <AppRoutes />
          </div>
          <Footer />
        </div>
      </Router>
    </Provider>
  );
};

export default App;