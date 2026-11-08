import { Mic, Send, Square, UserRound } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { mockApi } from "../../api/studyApi";
import type { AgentChoice } from "../../types/practice.types";
import type { MockSession } from "../../types/task.types";
import { ErrorAlert } from "../common/ErrorAlert";
import { renderInline } from "../common/Markdown";
import { ScoreRing } from "../practice/ScoreRing";
import { MockGradeCard } from "./MockGradeCard";

interface InterviewRoomProps {
  session: MockSession;
  agent: AgentChoice;
  agentLabel: string;
  onUpdate: (session: MockSession) => void;
  onFinished: (session: MockSession) => void;
  onNewInterview: () => void;
}

/** The interview itself: questions and follow-ups as a conversation, then the scorecard. */
export function InterviewRoom({ session, agent, agentLabel, onUpdate, onFinished, onNewInterview }: InterviewRoomProps) {
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const threadRef = useRef<HTMLDivElement>(null);
  const isFinished = session.status === "finished";

  useEffect(() => {
    const thread = threadRef.current;
    if (thread) thread.scrollTop = thread.scrollHeight;
  }, [session.turns.length, pending]);

  async function send(text: string) {
    if (!text.trim() || pending !== null) return;
    setPending(text.trim());
    setDraft("");
    setError(null);
    try {
      const updated = await mockApi.answer(session.id, agent, text.trim());
      onUpdate(updated);
      if (updated.status === "finished") onFinished(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setDraft(text);
    } finally {
      setPending(null);
    }
  }

  async function endEarly() {
    setPending("");
    try {
      const updated = await mockApi.end(session.id, agent);
      onUpdate(updated);
      onFinished(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setPending(null);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void send(draft);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void send(draft);
    }
  }

  return (
    <div className="interview">
      <section className="card interview__room" aria-label="Interview">
        <div className="card__title-row">
          <h2 className="card__title">
            {isFinished ? "Interview complete" : `Question ${session.current_index + 1} of ${session.question_count}`}
          </h2>
          {!isFinished && (
            <button type="button" className="button button--ghost button--small" onClick={() => void endEarly()} disabled={pending !== null}>
              <Square size={14} /> End interview
            </button>
          )}
        </div>

        <div className="interview__thread" ref={threadRef}>
          {session.turns.map((turn, i) => (
            <div key={i} className={`interview__turn interview__turn--${turn.role}`}>
              <span className="interview__avatar" aria-hidden="true">
                {turn.role === "interviewer" ? <Mic size={15} /> : <UserRound size={15} />}
              </span>
              <div className="interview__bubble">
                <span className="interview__speaker">{turn.role === "interviewer" ? "Interviewer" : "You"}</span>
                <p>{turn.role === "interviewer" ? renderInline(turn.content) : turn.content}</p>
              </div>
            </div>
          ))}
          {pending !== null && pending !== "" && (
            <>
              <div className="interview__turn interview__turn--candidate">
                <span className="interview__avatar" aria-hidden="true">
                  <UserRound size={15} />
                </span>
                <div className="interview__bubble">
                  <span className="interview__speaker">You</span>
                  <p>{pending}</p>
                </div>
              </div>
              <div className="interview__turn interview__turn--interviewer lesson-chat__typing" role="status">
                <span className="lesson-chat__dots" aria-hidden="true">
                  <span />
                  <span />
                  <span />
                </span>
                The interviewer ({agentLabel}) is listening…
              </div>
            </>
          )}
          {pending === "" && <p className="muted" role="status">Wrapping up and grading…</p>}
        </div>

        {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

        {!isFinished && (
          <form className="interview__composer" onSubmit={handleSubmit}>
            <textarea
              className="input explain__answer"
              rows={4}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Answer as you would out loud in the interview… (Ctrl+Enter to send)"
              disabled={pending !== null}
              aria-label="Your answer"
            />
            <button type="submit" className="button button--primary" disabled={pending !== null || !draft.trim()}>
              <Send size={16} /> Answer
            </button>
          </form>
        )}
      </section>

      {isFinished ? (
        <section className="card interview__summary" aria-label="Interview result">
          <div className="grade__header">
            {session.overall_score !== null ? <ScoreRing score={session.overall_score} /> : null}
            <div>
              <p className="grade__status">
                {session.overall_score === null
                  ? "No answers were graded."
                  : session.overall_score >= 70
                    ? "Strong interview — keep this up."
                    : "Good practice — the feedback below shows what to work on."}
              </p>
              <p className="muted">Every question and your answers are saved to the notebook.</p>
            </div>
          </div>
          {session.grades.map((grade, i) => (
            <MockGradeCard key={grade.item_id} grade={grade} open={i === 0} />
          ))}
          <div className="button-row">
            <button type="button" className="button button--primary" onClick={onNewInterview}>
              <Mic size={16} /> New interview
            </button>
          </div>
        </section>
      ) : (
        session.grades.length > 0 && (
          <section className="interview__feedback" aria-label="Feedback so far">
            <span className="page-header__eyebrow">Feedback so far</span>
            {session.grades.map((grade) => (
              <MockGradeCard key={grade.item_id} grade={grade} />
            ))}
          </section>
        )
      )}
    </div>
  );
}
