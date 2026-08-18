import { createContext, useContext } from 'react';
import type { ReactNode } from 'react';
import { usePywebviewBridge } from '../hooks/usePywebviewBridge';
import type { PywebviewBridgeState } from '../hooks/usePywebviewBridge';

const VoiceAgentBridgeContext = createContext<PywebviewBridgeState | null>(null);

/**
 * Registers the `window.setAgentState` / `appendTranscriptLine` / etc.
 * bridge functions Python calls into (see voice-agent/ui/window.py) at the
 * app root, so they exist the instant React mounts -- regardless of which
 * route is showing. Registering them inside DashboardHome instead (as
 * originally built) left them undefined on the login/guest page, and
 * Python's very first `set_state("idle")` call raced React's own mount
 * timing even once logged in; window.py now also guards for a missing
 * function, but not registering until a user is authenticated was the
 * larger bug -- the voice agent's window shows this dashboard from the
 * moment it opens, before any login has happened.
 */
export function VoiceAgentBridgeProvider({ children }: { children: ReactNode }) {
  const bridge = usePywebviewBridge();
  return <VoiceAgentBridgeContext.Provider value={bridge}>{children}</VoiceAgentBridgeContext.Provider>;
}

export function useVoiceAgentBridge(): PywebviewBridgeState {
  const context = useContext(VoiceAgentBridgeContext);
  if (!context) {
    throw new Error('useVoiceAgentBridge must be used within a VoiceAgentBridgeProvider');
  }
  return context;
}
