import { Mic, Play, Settings } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { mockApi, planApi } from "../api/studyApi";
import { trackApi } from "../api/trackApi";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { SkeletonResults } from "../components/common/Skeleton";
import { ActiveModelSelector } from "../components/connectors/ActiveModelSelector";
import { PageHeader } from "../components/layout/PageHeader";
import { InterviewRoom } from "../components/mock/InterviewRoom";
import { useProfile } from "../context/ProfileContext";
import { useToast } from "../context/ToastContext";
import { useAgentChoice } from "../hooks/useAgentChoice";
import type { MockKind } from "../types/plan.types";
import type { MockSession, MockSessionSummary } from "../types/task.types";
import type { Track } from "../types/track.types";

const KINDS: { value: MockKind; label: string; hint: string }[] = [
  { value: "technical", label: "Technical", hint: "Concepts, trade-offs, “how would you…”" },
  { value: "behavioural", label: "Behavioural", hint: "STAR stories: teamwork, conflict, impact" },
  { value: "mixed", label: "Mixed", hint: "Like a real first round" },
];
const KIND_SET = new Set<MockKind>(["technical", "behavioural", "mixed"]);

export function MockInterviewPage() {
  const { profile } = useProfile();
  const { agent, isReady, label: agentLabel } = useAgentChoice();
  const toast = useToast();
  const [searchParams] = useSearchParams();
  const blockId = searchParams.get("block");

  const [kind, setKind] = useState<MockKind>(() => {
    const requested = searchParams.get("kind") as MockKind | null;
    return requested && KIND_SET.has(requested) ? requested : "mixed";
  });
  const [count, setCount] = useState(() => Number(searchParams.get("count")) || 3);
  const [subtopicId, setSubtopicId] = useState(searchParams.get("subtopic") ?? "");
  const [track, setTrack] = useState<Track | null>(null);
  const [history, setHistory] = useState<MockSessionSummary[]>([]);
  const [session, setSession] = useState<MockSession | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const autoStarted = useRef(false);

  const loadHistory = useCallback(() => {
    mockApi.list().then(setHistory).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!profile) return;
    trackApi.getTrack(profile.track_id).then(setTrack).catch(() => undefined);
    loadHistory();
  }, [profile, loadHistory]);

  const start = useCallback(async () => {
    setIsStarting(true);
    setError(null);
    try {
      setSession(await mockApi.start(agent, kind, count, kind === "behavioural" ? null : subtopicId || null));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsStarting(false);
    }
  }, [agent, kind, count, subtopicId]);

  // Arriving from Today's plan: start straight away (once).
  useEffect(() => {
    if (blockId && profile && isReady && !session && !autoStarted.current) {
      autoStarted.current = true;
      void start();
    }
  }, [blockId, profile, isReady, session, start]);

  function handleFinished() {
    loadHistory();
    if (blockId) {
      planApi
        .completeBlock(blockId)
        .then(() => toast({ message: "Mock interview block done." }))
        .catch(() => undefined);
    }
  }

  async function openPast(id: number) {
    try {
      setSession(await mockApi.get(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  if (profile === undefined) {
    return (
      <div className="page">
        <PageHeader eyebrow="Prepare" title="Mock interview" />
        <SkeletonResults label="Loading" />
      </div>
    );
  }
  if (profile === null) {
    return (
      <div className="page">
        <PageHeader eyebrow="Prepare" title="Mock interview" />
        <div className="card">
          <EmptyState
            icon={Settings}
            title="Pick your career track first"
            description="The interviewer asks questions from your track's syllabus."
            actions={
              <Link to="/settings" className="button button--primary">
                Set up my prep
              </Link>
            }
          />
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow={`Prepare · ${profile.track_name}`}
        title="Mock interview"
        description="A realistic interview: the interviewer asks follow-ups like “why?” and “what if…?”, then scores each answer and shows a stronger one."
      />

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {session ? (
        <InterviewRoom
          key={session.id}
          session={session}
          agent={agent}
          agentLabel={agentLabel}
          onUpdate={setSession}
          onFinished={handleFinished}
          onNewInterview={() => setSession(null)}
        />
      ) : (
        <>
          <section className="card practice-setup" aria-label="Interview setup">
            <div className="segmented segmented--three" role="radiogroup" aria-label="Interview type">
              {KINDS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  role="radio"
                  aria-checked={kind === option.value}
                  className={`segmented__option${kind === option.value ? " segmented__option--selected" : ""}`}
                  onClick={() => setKind(option.value)}
                >
                  <span className="segmented__label">{option.label}</span>
                  <span className="segmented__hint">{option.hint}</span>
                </button>
              ))}
            </div>

            <div className="practice-setup__row">
              <div className="mock-setup__fields">
                <label className="field">
                  <span className="field__label">Questions</span>
                  <select className="input" value={count} onChange={(event) => setCount(Number(event.target.value))}>
                    {[1, 2, 3, 4, 5].map((n) => (
                      <option key={n} value={n}>
                        {n} question{n > 1 ? "s" : ""} (~{n * 8} min)
                      </option>
                    ))}
                  </select>
                </label>
                {kind !== "behavioural" && track && (
                  <label className="field">
                    <span className="field__label">Focus</span>
                    <select className="input" value={subtopicId} onChange={(event) => setSubtopicId(event.target.value)}>
                      <option value="">What I've studied so far</option>
                      {track.topics.map((topic) => (
                        <optgroup key={topic.id} label={topic.name}>
                          {topic.subtopics.map((s) => (
                            <option key={s.id} value={s.id}>
                              {s.name}
                            </option>
                          ))}
                        </optgroup>
                      ))}
                    </select>
                  </label>
                )}
              </div>
              <ActiveModelSelector />
            </div>

            <div className="button-row">
              <button
                type="button"
                className="button button--primary button--large"
                onClick={() => void start()}
                disabled={isStarting || !isReady}
              >
                <Play size={16} /> Start interview
              </button>
            </div>
          </section>

          {isStarting && (
            <div className="card practice-loading">
              <LoadingSpinner label={`${agentLabel} is preparing your interview…`} />
            </div>
          )}

          {history.length > 0 && (
            <section className="card" aria-label="Past interviews">
              <h2 className="card__title">Past interviews</h2>
              <ul className="mock-history">
                {history.map((item) => (
                  <li key={item.id}>
                    <button type="button" className="mock-history__item" onClick={() => void openPast(item.id)}>
                      <Mic size={16} aria-hidden="true" />
                      <span className="mock-history__text">
                        <span className="mock-history__question">{item.first_question}</span>
                        <span className="muted">
                          {new Date(item.created_at).toLocaleDateString()} · {item.kind} · {item.question_count} question
                          {item.question_count > 1 ? "s" : ""}
                          {item.status === "in_progress" ? " · in progress" : ""}
                        </span>
                      </span>
                      {item.overall_score !== null && <span className="mock-history__score">{Math.round(item.overall_score)}</span>}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}
