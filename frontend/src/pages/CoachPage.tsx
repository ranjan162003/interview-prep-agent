import { MessageSquarePlus, MessagesSquare, Search, Send, Settings, Trash2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { coachApi } from "../api/studyApi";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { Markdown } from "../components/common/Markdown";
import { SkeletonResults } from "../components/common/Skeleton";
import { PageHeader } from "../components/layout/PageHeader";
import { useProfile } from "../context/ProfileContext";
import { useAgentChoice } from "../hooks/useAgentChoice";
import type { CoachConversationSummary, CoachMessage } from "../types/task.types";

const SUGGESTIONS = [
  "How ready am I for my interview?",
  "What are my weakest topics right now?",
  "Explain dynamic programming like I'm new to it",
  "Why did I get my last quiz question wrong?",
  "Give me 5 more questions like my last quiz",
  "Make me a plan for the next 7 days",
];

export function CoachPage() {
  const { profile } = useProfile();
  const { agent, isReady, isChecking, label: agentLabel } = useAgentChoice();
  const [searchParams, setSearchParams] = useSearchParams();
  const conversationId = Number(searchParams.get("c")) || null;

  const [conversations, setConversations] = useState<CoachConversationSummary[]>([]);
  const [messages, setMessages] = useState<CoachMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const threadRef = useRef<HTMLDivElement>(null);

  const loadConversations = useCallback(() => {
    coachApi.list().then(setConversations).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (profile) loadConversations();
  }, [profile, loadConversations]);

  useEffect(() => {
    if (!conversationId) {
      setMessages([]);
      return;
    }
    coachApi
      .get(conversationId)
      .then((c) => setMessages(c.messages))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [conversationId]);

  useEffect(() => {
    const thread = threadRef.current;
    if (thread) thread.scrollTop = thread.scrollHeight;
  }, [messages, pending]);

  function openConversation(id: number | null) {
    const params = new URLSearchParams(searchParams);
    if (id) params.set("c", String(id));
    else params.delete("c");
    setSearchParams(params, { replace: true });
  }

  async function send(text: string) {
    const message = text.trim();
    if (!message || pending !== null) return;
    setPending(message);
    setDraft("");
    setError(null);
    try {
      const reply = await coachApi.send(agent, message, conversationId);
      setMessages((current) => [...current, ...reply.messages]);
      if (reply.conversation.id !== conversationId) openConversation(reply.conversation.id);
      loadConversations();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setDraft(message);
    } finally {
      setPending(null);
    }
  }

  async function remove(id: number) {
    try {
      await coachApi.remove(id);
      if (id === conversationId) openConversation(null);
      loadConversations();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void send(draft);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send(draft);
    }
  }

  if (profile === undefined) {
    return (
      <div className="page">
        <PageHeader eyebrow="Review" title="Coach" />
        <SkeletonResults label="Loading" />
      </div>
    );
  }
  if (profile === null) {
    return (
      <div className="page">
        <PageHeader eyebrow="Review" title="Coach" />
        <div className="card">
          <EmptyState
            icon={Settings}
            title="Pick your career track first"
            description="The coach uses your track, scores and notebook to answer."
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
        eyebrow={`Review · ${profile.track_name}`}
        title="Coach"
        description="Ask anything about your prep. The coach can look at your scores, weak topics, syllabus and past answers."
      />

      <div className="coach">
        <aside className="card coach__list" aria-label="Conversations">
          <button type="button" className="button button--secondary button--block" onClick={() => openConversation(null)}>
            <MessageSquarePlus size={16} /> New chat
          </button>
          {conversations.length === 0 ? (
            <p className="muted coach__empty-list">Your chats will appear here.</p>
          ) : (
            <ul>
              {conversations.map((c) => (
                <li key={c.id} className={c.id === conversationId ? "coach__conversation--active" : undefined}>
                  <button type="button" className="coach__conversation" onClick={() => openConversation(c.id)}>
                    <MessagesSquare size={14} aria-hidden="true" />
                    <span>{c.title}</span>
                  </button>
                  <button
                    type="button"
                    className="icon-button icon-button--subtle"
                    onClick={() => void remove(c.id)}
                    aria-label={`Delete “${c.title}”`}
                    title="Delete chat"
                  >
                    <Trash2 size={14} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>

        <section className="card coach__chat" aria-label="Chat with your coach">
          <div className="coach__thread" ref={threadRef}>
            {messages.length === 0 && pending === null && (
              <div className="coach__welcome">
                <MessagesSquare size={28} aria-hidden="true" />
                <h2 className="card__title">What would you like help with?</h2>
                <div className="lesson-chat__suggestions">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} type="button" className="lesson-chat__chip" onClick={() => void send(s)} disabled={!isReady}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m) => (
              <div key={m.id} className={`lesson-chat__message lesson-chat__message--${m.role}`}>
                {m.role === "assistant" ? (
                  <>
                    {m.tools_used.length > 0 && (
                      <span className="coach__tools">
                        <Search size={12} aria-hidden="true" /> {m.tools_used.join(" · ")}
                      </span>
                    )}
                    <Markdown text={m.content} />
                  </>
                ) : (
                  <p>{m.content}</p>
                )}
              </div>
            ))}
            {pending !== null && (
              <>
                <div className="lesson-chat__message lesson-chat__message--user">
                  <p>{pending}</p>
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
                  ? "Ask your coach… (Enter to send, Shift+Enter for a new line)"
                  : isChecking
                    ? "Checking your AI connection…"
                    : "Connect a model to chat"
              }
              disabled={pending !== null || !isReady}
              maxLength={4000}
              aria-label="Your message"
            />
            <button type="submit" className="button button--primary lesson-chat__send" disabled={pending !== null || !isReady || !draft.trim()} aria-label="Send">
              <Send size={16} />
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
