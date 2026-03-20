import React, { useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import './footer.css';

const Footer = () => {
  const { user, loading } = useContext(AuthContext);

  // Wait until loading is complete
  if (loading) return null;
  // Don't show Footer on public pages (e.g., login)
  if (!user) return null;

  const year = new Date().getFullYear();

  return (
    <footer className="footer">
      <div className="footer-container">
        <p className="footer-copy">© {year} MyDuka. All rights reserved.</p>
        <nav className="footer-links">
          <a href="/terms"                    className="footer-link">Terms of Service</a>
          <a href="/privacy"                  className="footer-link">Privacy Policy</a>
          <a href="mailto:support@myduka.com" className="footer-link">Contact Us</a>
        </nav>
      </div>
    </footer>
  );
};

export default Footer;