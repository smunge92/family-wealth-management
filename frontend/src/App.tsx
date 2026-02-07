import React, { useEffect, useState, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';
import { useMsal, useIsAuthenticated } from '@azure/msal-react';
import { loginRequest } from './services/auth';
import { initializeApi } from './services/api';
import Accounts from './components/Accounts/Accounts';
import Transactions from './components/Transactions/Transactions';
import FinancialInsights from './components/Insights/FinancialInsights';
import DashboardComponent from './components/Dashboard/Dashboard';
import About from './components/About/About';
import { FamilyMemberFilter } from './components/common/FamilyMemberFilter';
import './App.css';

const App: React.FC = () => {
  const { instance } = useMsal();
  const isAuthenticated = useIsAuthenticated();

  // Initialize API with MSAL instance for authenticated requests
  useEffect(() => {
    if (isAuthenticated) {
      initializeApi(instance);
    }
  }, [instance, isAuthenticated]);

  const [loginError, setLoginError] = useState<string | null>(null);

  const handleLogin = () => {
    setLoginError(null);
    instance.loginPopup(loginRequest).catch((error) => {
      // Sanitize error - never expose Client IDs, tenant IDs, or internal details
      const errorMsg = error?.errorMessage || error?.message || '';
      if (errorMsg.includes('AADSTS50020') || errorMsg.includes('does not exist in')) {
        setLoginError('Access denied. Your account is not authorized for this application.');
      } else if (errorMsg.includes('AADSTS65004') || errorMsg.includes('consent')) {
        setLoginError('Access denied. Please contact the app administrator.');
      } else if (errorMsg.includes('user_cancelled') || errorMsg.includes('cancelled')) {
        // User closed the popup - no error to show
        setLoginError(null);
      } else if (errorMsg.includes('AADSTS')) {
        setLoginError('Sign-in failed. Please try again or contact the app administrator.');
      } else {
        setLoginError(null);
      }
      // Log sanitized info for debugging (no secrets)
      console.error('Login failed:', error?.errorCode || 'unknown');
    });
  };

  const handleLogout = () => {
    instance.logoutPopup().catch((error) => {
      console.error('Logout failed:', error);
    });
  };

  if (!isAuthenticated) {
    return (
      <div className="App">
        <div className="login-container">
          <div className="card">
            <h1>Family Wealth Management</h1>
            <p>Secure financial tracking and planning for your family</p>
            {loginError && (
              <div className="login-error">{loginError}</div>
            )}
            <button className="button button-primary" onClick={handleLogin}>
              Sign in with Microsoft
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <Router>
      <AppContent handleLogout={handleLogout} />
    </Router>
  );
};

const AppContent: React.FC<{ handleLogout: () => void }> = ({ handleLogout }) => {
  const location = useLocation();
  const { accounts } = useMsal();
  const user = accounts[0];
  const [showUserMenu, setShowUserMenu] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  // Get user initials for avatar
  const getInitials = () => {
    if (!user?.name) return 'U';
    const names = user.name.split(' ');
    if (names.length >= 2) {
      return `${names[0][0]}${names[names.length - 1][0]}`.toUpperCase();
    }
    return names[0][0].toUpperCase();
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>Family Wealth Management</h1>
        <nav className="app-nav">
          <Link to="/about" className={isActive('/about') ? 'active' : ''}>About</Link>
          <Link to="/" className={isActive('/') ? 'active' : ''}>Dashboard</Link>
          <Link to="/accounts" className={isActive('/accounts') ? 'active' : ''}>Accounts</Link>
          <Link to="/transactions" className={isActive('/transactions') ? 'active' : ''}>Transactions</Link>
          <Link to="/planning" className={isActive('/planning') ? 'active' : ''}>Planning</Link>
        </nav>
        <div className="header-actions">
          <FamilyMemberFilter />
          <div className="user-profile-container" ref={userMenuRef}>
            <button
              className="user-profile-btn"
              onClick={() => setShowUserMenu(!showUserMenu)}
            >
              <div className="user-avatar">{getInitials()}</div>
              <svg
                className={`user-chevron ${showUserMenu ? 'open' : ''}`}
                viewBox="0 0 24 24"
                width="16"
                height="16"
                fill="currentColor"
              >
                <path d="M7 10l5 5 5-5z"/>
              </svg>
            </button>
            {showUserMenu && (
              <div className="user-menu">
                <div className="user-menu-header">
                  <div className="user-menu-avatar">{getInitials()}</div>
                  <div className="user-menu-info">
                    <span className="user-menu-name">{user?.name || 'User'}</span>
                    <span className="user-menu-email">{user?.username || ''}</span>
                  </div>
                </div>
                <div className="user-menu-divider"></div>
                <button className="user-menu-item sign-out" onClick={handleLogout}>
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                    <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z"/>
                  </svg>
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="app-main">
        <Routes>
          <Route path="/" element={<DashboardComponent />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/planning" element={<FinancialInsights />} />
          <Route path="/about" element={<About />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  );
};

export default App;
