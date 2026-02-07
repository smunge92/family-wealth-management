import axios from 'axios';
import { IPublicClientApplication } from '@azure/msal-browser';
import { getAccessToken } from './auth';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:7071/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Store for MSAL instance
let msalInstance: IPublicClientApplication | null = null;

// Initialize API with MSAL instance
export const initializeApi = (instance: IPublicClientApplication) => {
  msalInstance = instance;
};

// Request interceptor to add auth token
api.interceptors.request.use(
  async (config) => {
    if (msalInstance) {
      try {
        const token = await getAccessToken(msalInstance);
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        // If token is null, proceed without auth header
        // Backend with REQUIRE_AUTH=false will accept the request
      } catch (error) {
        console.error('Failed to acquire token for API request:', error);
        // Continue without token - the server will return 401 if auth is required
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.error('Authentication error - please log in again');
      // Could trigger re-authentication here
    }
    return Promise.reject(error);
  }
);

export default api;
