import React, { Component, ErrorInfo, ReactNode } from 'react';
import { logger } from '../../../services/logger';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * React Error Boundary to catch rendering errors and prevent white-screen crashes.
 * Logs errors to Application Insights and shows a user-friendly fallback UI.
 */
class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    logger.error('React Error Boundary caught an error', error, {
      componentStack: errorInfo.componentStack || '',
    });
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  handleRefresh = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div style={styles.container}>
          <div style={styles.card}>
            <div style={styles.icon}>
              <svg viewBox="0 0 24 24" width="64" height="64" fill="#800020">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
              </svg>
            </div>
            <h1 style={styles.title}>Something went wrong</h1>
            <p style={styles.message}>
              An unexpected error occurred. Please try again or refresh the page.
            </p>
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <pre style={styles.errorDetail}>{this.state.error.message}</pre>
            )}
            <div style={styles.actions}>
              <button style={styles.retryButton} onClick={this.handleRetry}>
                Try Again
              </button>
              <button style={styles.refreshButton} onClick={this.handleRefresh}>
                Refresh Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    backgroundColor: '#f9fafb',
    padding: '20px',
  },
  card: {
    textAlign: 'center' as const,
    padding: '48px',
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    boxShadow: '0 4px 24px rgba(0, 0, 0, 0.1)',
    maxWidth: '480px',
    width: '100%',
  },
  icon: {
    marginBottom: '24px',
  },
  title: {
    fontSize: '24px',
    fontWeight: 600,
    color: '#1f2937',
    margin: '0 0 12px 0',
  },
  message: {
    fontSize: '16px',
    color: '#6b7280',
    margin: '0 0 24px 0',
    lineHeight: 1.5,
  },
  errorDetail: {
    fontSize: '12px',
    color: '#ef4444',
    backgroundColor: '#fef2f2',
    padding: '12px',
    borderRadius: '8px',
    textAlign: 'left' as const,
    overflow: 'auto',
    marginBottom: '24px',
    maxHeight: '100px',
  },
  actions: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'center',
  },
  retryButton: {
    padding: '10px 24px',
    backgroundColor: '#800020',
    color: '#ffffff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
  },
  refreshButton: {
    padding: '10px 24px',
    backgroundColor: '#ffffff',
    color: '#374151',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
  },
};

export default ErrorBoundary;
