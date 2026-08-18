import { useEffect, useState } from 'react';
import type { PywebviewAgentState, PywebviewMode, PywebviewSystemStatus } from '../types/pywebview';

export interface TranscriptLine {
  role: 'you' | 'agent';
  text: string;
}

export interface PywebviewBridgeState {
  /** True only when this page is loaded inside the voice agent's pywebview window, not a normal browser tab. */
  isEmbedded: boolean;
  agentState: PywebviewAgentState;
  transcript: TranscriptLine[];
  systemStatus: PywebviewSystemStatus;
  lastQuery: { toolName: string; preview: string } | null;
  /** Switch input mode -- 'voice' (mic/wake-word) or 'text' (mic off, typed only). No-op outside pywebview. */
  setMode: (mode: PywebviewMode) => void;
}

const MAX_TRANSCRIPT_LINES = 12;

/**
 * Receives live updates from the voice agent's Python process when this app
 * is running inside its pywebview window (see voice-agent/ui/window.py,
 * which calls these exact function names via `evaluate_js` -- unchanged
 * from what it called on the old orb.html). In a normal browser tab none of
 * these ever fire, so `isEmbedded` stays false and every consumer should
 * fall back to its default (non-reactive) look.
 */
export function usePywebviewBridge(): PywebviewBridgeState {
  const [isEmbedded, setIsEmbedded] = useState(false);
  const [agentState, setAgentStateValue] = useState<PywebviewAgentState>('idle');
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [systemStatus, setSystemStatusValue] = useState<PywebviewSystemStatus>({});
  const [lastQuery, setLastQueryValue] = useState<PywebviewBridgeState['lastQuery']>(null);

  useEffect(() => {
    // pywebview injects `window.pywebview` ASYNCHRONOUSLY, after the page's
    // own load -- checking it once here is a race React usually loses (this
    // effect fires close to immediately on mount, well before pywebview's
    // bridge script finishes running), which was leaving isEmbedded stuck
    // at false forever even inside the real voice-agent window. Check
    // immediately for the case it already won that race, but also listen
    // for pywebview's own 'pywebviewready' event (fired once the API is
    // actually available) to catch it whichever order they land in.
    if (typeof window.pywebview !== 'undefined') {
      setIsEmbedded(true);
    }
    const onReady = () => setIsEmbedded(true);
    window.addEventListener('pywebviewready', onReady);

    window.setAgentState = (state) => setAgentStateValue(state);
    window.appendTranscriptLine = (role, text) =>
      setTranscript((prev) => [...prev.slice(-(MAX_TRANSCRIPT_LINES - 1)), { role, text }]);
    window.setSystemStatus = (status) => setSystemStatusValue((prev) => ({ ...prev, ...status }));
    window.setLastQuery = (toolName, preview) => setLastQueryValue({ toolName, preview });
    window.toggleGraph = () => {
      /* No architecture-diagram overlay in the web dashboard (yet) -- reserved for parity with orb.html. */
    };

    return () => {
      window.removeEventListener('pywebviewready', onReady);
      delete window.setAgentState;
      delete window.appendTranscriptLine;
      delete window.setSystemStatus;
      delete window.setLastQuery;
      delete window.toggleGraph;
    };
  }, []);

  const setMode = (mode: PywebviewMode) => {
    window.pywebview?.api.set_mode(mode);
  };

  return { isEmbedded, agentState, transcript, systemStatus, lastQuery, setMode };
}
