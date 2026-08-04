import { Component } from "react";

export default class PageErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error("Page render error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-4">
          <h2 className="h5 text-danger">This page could not be displayed</h2>
          <p className="text-muted mb-3">
            Try refreshing the browser. If the problem continues, check the
            browser console (F12) for details.
          </p>
          <button
            type="button"
            className="btn btn-outline-primary btn-sm"
            onClick={() => window.location.reload()}
          >
            Reload page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
