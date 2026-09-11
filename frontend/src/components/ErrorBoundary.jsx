import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught a render exception:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 my-8 rounded-2xl bg-rose-950/20 border border-rose-500/30 text-center space-y-4 max-w-lg mx-auto">
          <div className="p-3 bg-rose-500/10 text-rose-400 rounded-xl inline-block">
            <AlertTriangle className="h-8 w-8 mx-auto" />
          </div>
          <h2 className="text-lg font-bold text-white">Something went wrong</h2>
          <p className="text-xs text-rose-300/80">
            {this.state.error?.message || 'A display error occurred while rendering this section.'}
          </p>
          <div className="pt-2">
            <button
              onClick={this.handleReset}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition cursor-pointer"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
