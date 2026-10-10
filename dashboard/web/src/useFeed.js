// Engineered by uncoalesced
// Live event feed from dashboard/server.py. Event shapes: docs/CONTRACTS.md.
import { useEffect, useReducer, useState } from "react";

export const initial = {
  call: null,          // { lang, scenario, simulated }
  state: null,         // PANIC | STALLING | BAITING | EXTRACTING | WRAPUP
  messages: [],        // { speaker: "scammer" | "persona", text, ts, state? , cut? }
  intel: [],           // Intel events, first sighting only
  metrics: null,
  report: null,
};

export function reduce(s, ev) {
  switch (ev.type) {
    case "call_start":
      return { ...initial, call: { lang: ev.lang, scenario: ev.scenario, simulated: ev.simulated }, state: ev.state };
    case "transcript":
      if (!ev.final) return s;
      return { ...s, messages: [...s.messages, { speaker: ev.speaker, text: ev.text, ts: ev.ts }] };
    case "speak": {
      const last = s.messages.findLast((m) => m.speaker === "scammer");
      return { ...s, state: ev.state,
               messages: [...s.messages, { speaker: "persona", text: ev.text, state: ev.state, ts: last?.ts, endCall: ev.end_call }] };
    }
    case "intel":
      if (s.intel.some((i) => i.kind === ev.kind && i.value === ev.value)) return s;
      return { ...s, intel: [...s.intel, ev] };
    case "barge_in": {
      const i = s.messages.findLastIndex((m) => m.speaker === "persona");
      if (i < 0) return s;
      const messages = s.messages.slice();
      messages[i] = { ...messages[i], cut: true };
      return { ...s, messages };
    }
    case "metrics":
      return { ...s, metrics: ev };
    case "report":
      return { ...s, report: ev.report, state: ev.report?.call?.final_state ?? s.state };
    default:
      return s;
  }
}

const wsUrl = () => new URLSearchParams(location.search).get("ws") || "ws://127.0.0.1:8765";

export function useFeed() {
  const [state, dispatch] = useReducer(reduce, initial);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let ws, timer, delay = 500, stopped = false;
    const open = () => {
      ws = new WebSocket(wsUrl());
      ws.onopen = () => { setConnected(true); delay = 500; };
      ws.onmessage = (m) => { try { dispatch(JSON.parse(m.data)); } catch { /* ignore malformed */ } };
      ws.onclose = () => {
        setConnected(false);
        if (!stopped) timer = setTimeout(open, (delay = Math.min(delay * 2, 5000)));
      };
    };
    open();
    return () => { stopped = true; clearTimeout(timer); ws?.close(); };
  }, []);

  return { ...state, connected };
}
