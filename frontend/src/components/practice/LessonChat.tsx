import { GraduationCap, Send } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { practiceApi } from "../../api/practiceApi";
import { useAgentChoice } from "../../hooks/useAgentChoice";
import type { AgentChoice, LessonChatMessage } from "../../types/practice.types";
import { ErrorAlert } from "../common/ErrorAlert";
import { Markdown } from "../common/Markdown";

const SUGGESTED_DOUBTS = [
  "Explain it more simply",
  "Give me another example",
  "Explain it with a real-life analogy",
  "Why does this matter in interviews?",
  "What should I remember from this?",
];

interface LessonChatProps {
  itemId: number;
  agent: AgentChoice;
  agentLabel: string;
  isReady: boolean;
}

/** "Ask the teacher": a chat about this lesson only. Doubts and answers are saved with the lesson. */
export function LessonChat({ itemId, agent, agentLabel, isReady }: LessonChatProps) {
  const { isChecking } = useAgentChoice();
  const [messages, setMessages] = useState<LessonChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const threadRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    practiceApi
      .getLessonChat(itemId)
      .then(setMessages)
      .catch(() => undefined);
  }, [itemId]);

  // Keep the newest message in view.
  useEffect(() => {
    const thread = threadRef.current;
    if (thread) thread.scrollTop = thread.scrollHeight;
  }, [messages, pendingQuestion]);

  async function ask(question: string) {
    const text = question.trim();
    if (!text || pendingQuestion !== null) return;
    setPendingQuestion(text);
    setDraft("");
    setError(null);
    try {
      const saved = await practiceApi.askTeacher(itemId, agent, text);
      setMessages((current) => [...current, ...saved]);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setDraft(text); // give the question back so it isn't lost
    } finally {
      setPendingQuestion(null);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void ask(draft);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void ask(draft);
    }
  }

  const isBusy = pendingQuestion !== null;

  return (
    <aside className="card lesson-chat" aria-label="Ask the teacher">
      <div className="lesson-chat__header">
        <span className="lesson-chat__avatar" aria-hidden="true">
          <GraduationCap size={18} />
        </span>
        <div>
          <h2 className="card__title">Ask the teacher</h2>
          <p className="muted lesson-chat__subtitle">Any doubt about this lesson — no question is too basic.</p>
        </div>
      </div>

      <div className="lesson-chat__thread" ref={threadRef}>
        {messages.length === 0 && !isBusy && (
          <div className="lesson-chat__empty">
            <p className="muted">Stuck on something? Try one of these, or type your own question.</p>
            <div className="lesson-chat__suggestions">
              {SUGGESTED_DOUBTS.map((doubt) => (
                <button
                  key={doubt}
                  type="button"
                  className="lesson-chat__chip"
                  onClick={() => void ask(doubt)}
                  disabled={!isReady}
                >
                  {doubt}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div key={message.id} className={`lesson-chat__message lesson-chat__message--${message.role}`}>
            {message.role === "assistant" ? <Markdown text={message.content} /> : <p>{message.content}</p>}
          </div>
        ))}

        {pendingQuestion !== null && (
          <>
            <div className="lesson-chat__message lesson-chat__message--user">
              <p>{pendingQuestion}</p>
            </div>
            <div className="lesson-chat__message lesson-chat__message--assistant lesson-chat__typing" role="status">
              <span className="lesson-chat__dots" aria-hidden="true">
                <span />
                <span />
                <span />
              </span>
              {agentLabel} is thinking…
            </div>
          </>
        )}
      </div>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      <form className="lesson-chat__composer" onSubmit={handleSubmit}>
        <textarea
          className="input lesson-chat__input"
          rows={2}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            isReady
              ? "Ask a doubt… (Enter to send, Shift+Enter for a new line)"
              : isChecking
                ? "Checking your AI connection…"
                : "Connect a model to ask questions"
          }
          disabled={isBusy || !isReady}
          maxLength={2000}
          aria-label="Your question"
        />
        <button
          type="submit"
          className="button button--primary lesson-chat__send"
          disabled={isBusy || !isReady || !draft.trim()}
          aria-label="Send question"
        >
          <Send size={16} />
        </button>
      </form>
    </aside>
  );
}
