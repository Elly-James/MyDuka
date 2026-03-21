import React, { useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import './footer.css';

const Footer = () => {
  const { user, loading } = useContext(AuthContext);

  if (loading) return null;
  if (!user)   return null;

  const year = new Date().getFullYear();

  const roleLabel = {
    MERCHANT: 'Merchant Portal',
    ADMIN:    'Admin Portal',
    CLERK:    'Clerk Portal',
  }[user?.role] || 'Portal';

  return (
    <footer className="footer">

      {/* Gold accent line at the very top */}
      <div className="footer-accent-bar" />

      <div className="footer-container">

        {/* ── Left: Brand + role ── */}
        <div className="footer-brand">
          <span className="footer-logo">MyDuka</span>
          <span className="footer-role-badge">{roleLabel}</span>
        </div>

        {/* ── Center: Copyright ── */}
        <p className="footer-copy">
          © {year} MyDuka. All rights reserved.
        </p>

        {/* ── Right: Links ── */}
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