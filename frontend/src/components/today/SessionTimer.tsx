import { Pause, Play, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";

interface SessionTimerProps {
  planDate: string;
  plannedMinutes: number;
}

interface TimerState {
  elapsedMs: number;
  runningSince: number | null;
}

const storageKey = (planDate: string) => `prep-pilot:timer:${planDate}`;

function load(planDate: string): TimerState {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey(planDate)) ?? "null") as TimerState | null;
    if (saved && typeof saved.elapsedMs === "number") return saved;
  } catch {
    // storage blocked or corrupt: start fresh
  }
  return { elapsedMs: 0, runningSince: null };
}

function save(planDate: string, state: TimerState): void {
  try {
    localStorage.setItem(storageKey(planDate), JSON.stringify(state));
  } catch {
    // the timer still works, it just won't survive a reload
  }
}

const pad = (n: number) => String(n).padStart(2, "0");

/** A study timer for today's session; it keeps running across page changes and reloads. */
export function SessionTimer({ planDate, plannedMinutes }: SessionTimerProps) {
  const [state, setState] = useState<TimerState>(() => load(planDate));
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (state.runningSince === null) return;
    const tick = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(tick);
  }, [state.runningSince]);

  function update(next: TimerState) {
    setState(next);
    save(planDate, next);
    setNow(Date.now());
  }

  const elapsedMs = state.elapsedMs + (state.runningSince !== null ? now - state.runningSince : 0);
  const totalSeconds = Math.floor(elapsedMs / 1000);
  const percent = Math.min(100, (elapsedMs / (plannedMinutes * 60_000)) * 100);
  const isRunning = state.runningSince !== null;

  return (
    <div className="session-timer" aria-label="Session timer">
      <div className="session-timer__clock" role="timer" aria-live="off">
        {pad(Math.floor(totalSeconds / 3600))}:{pad(Math.floor((totalSeconds % 3600) / 60))}:{pad(totalSeconds % 60)}
      </div>
      <span className="muted session-timer__goal">of {plannedMinutes} min planned</span>
      <span className="session-timer__bar" aria-hidden="true">
        <span style={{ width: `${percent}%` }} />
      </span>
      <div className="button-row">
        {isRunning ? (
          <button type="button" className="button button--ghost button--small" onClick={() => update({ elapsedMs, runningSince: null })}>
            <Pause size={14} /> Pause
          </button>
        ) : (
          <button type="button" className="button button--primary button--small" onClick={() => update({ elapsedMs: state.elapsedMs, runningSince: Date.now() })}>
            <Play size={14} /> {state.elapsedMs ? "Resume" : "Start session"}
          </button>
        )}
        {elapsedMs > 0 && (
          <button
            type="button"
            className="icon-button icon-button--subtle"
            onClick={() => update({ elapsedMs: 0, runningSince: null })}
            aria-label="Reset timer"
            title="Reset timer"
          >
            <RotateCcw size={14} />
          </button>
        )}
      </div>
    </div>
  );
}
