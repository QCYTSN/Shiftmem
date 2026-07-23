import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class AppErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ShiftMem demo render failure", error, info);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <main className="runtime-error">
        <AlertTriangle aria-hidden="true" />
        <h1>The current evidence view could not be rendered.</h1>
        <p>Reload the page to return to the verified default cell.</p>
        <code>{this.state.error.message}</code>
        <button type="button" onClick={() => window.location.reload()}>Reload evidence lab</button>
      </main>
    );
  }
}
