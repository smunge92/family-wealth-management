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

// Scopes for API access (your backend)
export const apiRequest: PopupRequest = {
  scopes: [`api://${process.env.REACT_APP_AZURE_CLIENT_ID}/access_as_user`],
};

// Get access token for API calls
export const getAccessToken = async (instance: any): Promise<string | null> => {
  const account = instance.getAllAccounts()[0];

  if (!account) {
    // No account - return null, let request proceed without auth
    return null;
  }

  try {
    // First, try to get an API-scoped access token
    const response = await instance.acquireTokenSilent({
      ...apiRequest,
      account,
    });
    return response.accessToken;
  } catch (error) {
    console.warn('API token acquisition failed, trying ID token fallback:', error);

    // Fallback: Try to get the ID token (always available after login)
    // The ID token contains user info that the backend needs
    try {
      const idTokenResponse = await instance.acquireTokenSilent({
        ...loginRequest,
        account,
      });
      // Use the ID token as fallback - backend can still extract user info from it
      if (idTokenResponse.idToken) {
        console.log('Using ID token as fallback');
        return idTokenResponse.idToken;
      }
    } catch (idTokenError) {
      console.warn('ID token fallback also failed:', idTokenError);
    }

    return null;
  }
};
