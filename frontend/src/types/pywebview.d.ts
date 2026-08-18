// When this app is loaded inside the voice agent's pywebview window
// (instead of a normal browser tab), Python calls these global functions
// directly via `window.evaluate_js(...)` -- see voice-agent/ui/window.py.
// They mirror exactly what voice-agent/ui/orb.html used to define itself;
// keeping the same names/shapes means window.py needed zero changes.
export interface PywebviewSystemStatus {
  revit_mcp?: string;
  building_code?: string;
  wake_word?: string;
  /** Set when a conversation attempt failed (e.g. OpenAI quota exhausted); cleared (set to null) once the next attempt starts. */
  error?: string | null;
  /** Current input mode -- 'voice' (mic/wake-word, spoken replies) or 'text' (mic off entirely, typed replies). */
  mode?: PywebviewMode;
}

export type PywebviewAgentState = 'idle' | 'listening' | 'thinking' | 'speaking';
export type PywebviewMode = 'voice' | 'text';

declare global {
  interface Window {
    pywebview?: {
      api: {
        submit_text: (text: string) => void;
        set_mode: (mode: PywebviewMode) => void;
      };
    };
    setAgentState?: (state: PywebviewAgentState) => void;
    appendTranscriptLine?: (role: 'you' | 'agent', text: string) => void;
    setSystemStatus?: (status: PywebviewSystemStatus) => void;
    setLastQuery?: (toolName: string, preview: string) => void;
    toggleGraph?: () => void;
  }
}
