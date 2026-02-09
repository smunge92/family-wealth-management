import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { PublicClientApplication, EventType } from '@azure/msal-browser';
import { MsalProvider } from '@azure/msal-react';
import { msalConfig } from './services/auth';
import { ToastProvider, ToastContainer } from './components/common/Toast';
import { FamilyMemberProvider } from './context/FamilyMemberContext';
import { CategoriesProvider } from './context/CategoriesContext';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { initializeLogger } from './services/logger';

// Initialize centralized logger and Application Insights
initializeLogger();

// Initialize MSAL instance
const msalInstance = new PublicClientApplication(msalConfig);

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

// MSAL requires async initialization before use
msalInstance.initialize().then(() => {
  // Handle redirect promise (for redirect flow)
  msalInstance.handleRedirectPromise().then((response) => {
    if (response) {
      console.log('Login successful');
    }
  }).catch((error) => {
    console.error('Redirect error:', error?.errorCode || 'unknown');
  });

  // Set active account if available
  const accounts = msalInstance.getAllAccounts();
  if (accounts.length > 0) {
    msalInstance.setActiveAccount(accounts[0]);
  }

  // Listen for login events
  msalInstance.addEventCallback((event) => {
    if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
      const payload = event.payload as { account: any };
      msalInstance.setActiveAccount(payload.account);
    }
  });

  root.render(
    <React.StrictMode>
      <ErrorBoundary>
        <MsalProvider instance={msalInstance}>
          <ToastProvider>
            <FamilyMemberProvider>
              <CategoriesProvider>
                <App />
                <ToastContainer />
              </CategoriesProvider>
            </FamilyMemberProvider>
          </ToastProvider>
        </MsalProvider>
      </ErrorBoundary>
    </React.StrictMode>
  );
});
