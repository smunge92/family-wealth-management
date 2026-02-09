/**
 * Centralized logging service with Application Insights integration.
 * Provides structured logging and global error capture for the frontend.
 */

import { ApplicationInsights } from '@microsoft/applicationinsights-web';

let appInsights: ApplicationInsights | null = null;

/**
 * Initialize Application Insights if connection string is available.
 * Call once at app startup (index.tsx).
 */
export function initializeLogger(): void {
  const connectionString = process.env.REACT_APP_APPINSIGHTS_CONNECTION_STRING;

  if (connectionString) {
    try {
      appInsights = new ApplicationInsights({
        config: {
          connectionString,
          enableAutoRouteTracking: true,
          disableFetchTracking: false,
          enableCorsCorrelation: true,
          enableRequestHeaderTracking: true,
          enableResponseHeaderTracking: true,
        },
      });
      appInsights.loadAppInsights();
      appInsights.trackPageView();
      logger.info('Application Insights initialized');
    } catch (err) {
      console.error('Failed to initialize Application Insights:', err);
    }
  }

  // Set up global error handlers
  window.addEventListener('unhandledrejection', (event) => {
    logger.error('Unhandled promise rejection', {
      reason: event.reason?.message || String(event.reason),
    });
  });
}

/**
 * Get the Application Insights instance (if initialized).
 */
export function getAppInsights(): ApplicationInsights | null {
  return appInsights;
}

/**
 * Centralized logger that sends to both console (dev) and Application Insights (prod).
 */
export const logger = {
  info(message: string, properties?: Record<string, string>): void {
    if (process.env.NODE_ENV === 'development') {
      console.info(`[INFO] ${message}`, properties || '');
    }
    appInsights?.trackTrace({ message, severityLevel: 1 }, properties);
  },

  warn(message: string, properties?: Record<string, string>): void {
    if (process.env.NODE_ENV === 'development') {
      console.warn(`[WARN] ${message}`, properties || '');
    }
    appInsights?.trackTrace({ message, severityLevel: 2 }, properties);
  },

  error(message: string, error?: unknown, properties?: Record<string, string>): void {
    if (process.env.NODE_ENV === 'development') {
      console.error(`[ERROR] ${message}`, error || '', properties || '');
    }
    if (error instanceof Error) {
      appInsights?.trackException({ exception: error, properties: { ...properties, message } });
    } else {
      appInsights?.trackTrace({ message, severityLevel: 3 }, properties);
    }
  },

  trackEvent(name: string, properties?: Record<string, string>): void {
    if (process.env.NODE_ENV === 'development') {
      console.info(`[EVENT] ${name}`, properties || '');
    }
    appInsights?.trackEvent({ name }, properties);
  },
};

export default logger;
