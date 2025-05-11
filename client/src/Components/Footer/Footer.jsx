import React, { useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import './footer.css';

const Footer = () => {
  const { user, loading } = useContext(AuthContext);

  if (loading) return null; // Wait until loading is complete
  if (!user) return null; // Don't show Footer on public pages (e.g., login)

  return (
    <footer className="footer">
      <div className="footer-container">
        <p>© 2025 MyDuka. All rights reserved.</p>
        <div className="footer-links">
          <a href="/terms" className="footer-link">Terms of Service</a>
          <a href="/privacy" className="footer-link">Privacy Policy</a>
          <a href="mailto:support@myduka.com" className="footer-link">Contact Us</a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;