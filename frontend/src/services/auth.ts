import { Configuration, PopupRequest } from '@azure/msal-browser';

// MSAL configuration
export const msalConfig: Configuration = {
  auth: {
    clientId: process.env.REACT_APP_AZURE_CLIENT_ID || '',
    authority: process.env.REACT_APP_AZURE_AUTHORITY || '',
    redirectUri: process.env.REACT_APP_AZURE_REDIRECT_URI || window.location.origin,
  },
  cache: {
    cacheLocation: 'sessionStorage',
    storeAuthStateInCookie: false,
  },
};

// Scopes for login (Microsoft Graph)
export const loginRequest: PopupRequest = {
  scopes: ['User.Read', 'openid', 'profile'],
};

// Get auth token for API calls
export const getAccessToken = async (instance: any): Promise<string | null> => {
  const account = instance.getAllAccounts()[0];

  if (!account) {
    return null;
  }

  try {
    // Use ID token for authentication - contains user info (oid, email, name)
    // that the backend needs for user identification and access control
    const response = await instance.acquireTokenSilent({
      ...loginRequest,
      account,
    });
    return response.idToken;
  } catch (error) {
    console.warn('Token acquisition failed:', error);
    return null;
  }
};
