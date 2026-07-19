import React from 'react';
import PropTypes from 'prop-types';

/**
 * Error Boundary Component
 * 
 * Catches React errors and displays a graceful fallback UI.
 * Prevents entire app from crashing when a component errors.
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0,
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    const errorCount = this.state.errorCount + 1;
    
    this.setState(prevState => ({
      error,
      errorInfo,
      errorCount: prevState.errorCount + 1,
    }));

    // Log to backend error tracking service
    console.error('Error caught by ErrorBoundary:', error);
    console.error('Error info:', errorInfo);

    // Optional: Send to error tracking service (Sentry, LogRocket, etc.)
    if (window.errorTracker) {
      window.errorTracker.captureException(error, {
        contexts: { react: errorInfo },
        tags: { boundary: 'ErrorBoundary' },
      });
    }

    // If too many errors, force page reload
    if (errorCount > 5) {
      console.error('Too many errors. Reloading page.');
      setTimeout(() => window.location.reload(), 3000);
    }
  }

  resetError = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary-container">
          <div className="error-boundary-content">
            <div className="error-icon">⚠️</div>
            <h2>Something went wrong</h2>
            <p className="error-message">
              We encountered an unexpected error. Please try refreshing the page or contact support if the problem persists.
            </p>
            
            {process.env.NODE_ENV === 'development' && (
              <details className="error-details">
                <summary>Error Details (Development Only)</summary>
                <pre>
                  {this.state.error && this.state.error.toString()}
                  {'\n\n'}
                  {this.state.errorInfo && this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}

            <div className="error-boundary-actions">
              <button 
                onClick={this.resetError}
                className="btn-reset"
              >
                Try Again
              </button>
              <button 
                onClick={() => window.location.href = '/'}
                className="btn-home"
              >
                Go Home
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

ErrorBoundary.propTypes = {
  children: PropTypes.node,
};

export default ErrorBoundary;
