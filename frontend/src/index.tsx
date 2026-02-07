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
      console.log('Login successful:', response.account?.username);
    }
  }).catch((error) => {
    console.error('Redirect error:', error);
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
    </React.StrictMode>
  );
});
