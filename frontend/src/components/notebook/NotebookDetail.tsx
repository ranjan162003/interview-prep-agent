import { CheckCircle2, Lightbulb, MessagesSquare, XCircle } from "lucide-react";

import type { NotebookItemDetail } from "../../types/task.types";
import { Markdown, renderInline } from "../common/Markdown";
import { KIND_LABELS } from "./notebookLabels";

type Grade = Record<string, unknown>;

const text = (value: unknown) => (typeof value === "string" ? value : "");
const list = (value: unknown) => (Array.isArray(value) ? value.map(String) : []);

function Points({ items, missed = false }: { items: string[]; missed?: boolean }) {
  if (!items.length) return null;
  return (
    <ul className="key-points">
      {items.map((item) => (
        <li key={item} className={missed ? "key-points__item--missed" : undefined}>
          {missed ? <XCircle size={16} aria-hidden="true" /> : <Lightbulb size={16} aria-hidden="true" />}
          <span>{renderInline(item)}</span>
        </li>
      ))}
    </ul>
  );
}

function Code({ code }: { code: string }) {
  return (
    <pre className="markdown__code">
      <code>{code}</code>
    </pre>
  );
}

/** Everything saved about one item, laid out for revision. */
export function NotebookDetail({ item }: { item: NotebookItemDetail }) {
  const content = item.content;
  const last = item.history[item.history.length - 1];
  const grade: Grade = (last?.grade as Grade) ?? {};

  return (
    <article className="card notebook-detail" aria-label={item.title}>
      <div className="quiz__meta">
        <span className="pill">{KIND_LABELS[item.kind] ?? item.kind}</span>
        {item.is_review && <span className="review-pill">Review</span>}
        <span className="page-header__eyebrow">
          {item.topic_name} · {item.subtopic_name}
        </span>
      </div>
      <h2 className="lesson__title">{renderInline(item.title)}</h2>
      <p className="muted notebook-detail__meta">
        {new Date(item.created_at).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" })}
        {item.history.length > 0 && ` · ${item.history.length} attempt${item.history.length > 1 ? "s" : ""}`}
        {item.best_score !== null && ` · best ${Math.round(item.best_score)}%`}
        {item.status === "weak" && " · needs review"}
      </p>

      {item.key_points.length > 0 && (
        <section className="notebook-detail__notes">
          <h3 className="card__title">Revision note</h3>
          <Points items={item.key_points} />
        </section>
      )}

      {item.kind === "concept" && (
        <>
          <details className="grade__details">
            <summary>The lesson</summary>
            <Markdown text={text(content.lesson_markdown)} className="lesson__body" />
          </details>
          <h3 className="card__title">Explain-back: {renderInline(text(content.explain_prompt))}</h3>
          {item.history.map((attempt, i) => (
            <div key={i} className="notebook-detail__attempt">
              <span className="muted">
                Attempt {i + 1} · {Math.round(attempt.score)}%
              </span>
              <Markdown text={attempt.answer_text} />
              <Points items={list((attempt.grade as Grade | null)?.missed_points)} missed />
            </div>
          ))}
          {item.reference_answer && (
            <details className="grade__details" open={!item.history.length}>
              <summary>Model answer</summary>
              <Markdown text={item.reference_answer} />
            </details>
          )}
          {item.chat.length > 0 && (
            <section className="notebook-detail__chat">
              <h3 className="card__title">
                <MessagesSquare size={16} aria-hidden="true" /> Your questions to the teacher
              </h3>
              {item.chat.map((m) => (
                <div key={m.id} className={`lesson-chat__message lesson-chat__message--${m.role}`}>
                  {m.role === "assistant" ? <Markdown text={m.content} /> : <p>{m.content}</p>}
                </div>
              ))}
            </section>
          )}
        </>
      )}

      {item.kind === "quiz_question" && (
        <>
          <ol className="notebook-detail__options">
            {list(content.options).map((option, i) => {
              const correct = i === content.correct_index;
              const chosen = last?.selected_index === i;
              return (
                <li key={i} className={correct ? "is-correct" : chosen ? "is-wrong" : undefined}>
                  <span className="quiz-option__letter">{String.fromCharCode(65 + i)}</span>
                  <span>{renderInline(option)}</span>
                  {correct && <CheckCircle2 size={16} aria-label="Correct answer" />}
                  {chosen && !correct && <XCircle size={16} aria-label="Your answer" />}
                </li>
              );
            })}
          </ol>
          <p>{renderInline(text(content.explanation))}</p>
        </>
      )}

      {item.kind === "coding_problem" && (
        <>
          <details className="grade__details">
            <summary>Problem</summary>
            <Markdown text={text(content.statement_markdown)} className="lesson__body" />
          </details>
          {last && (
            <>
              <h3 className="card__title">
                Your final code · {String(grade.passed ?? "?")}/{String(grade.total ?? "?")} tests
              </h3>
              <Code code={last.answer_text} />
              <p>{renderInline(text((grade.review as Grade | undefined)?.complexity_comment))}</p>
              <Points items={list((grade.review as Grade | undefined)?.edge_cases_missed)} missed />
            </>
          )}
          {item.reference_answer && (
            <details className="grade__details">
              <summary>
                Reference solution · {text(content.time_complexity)} time, {text(content.space_complexity)} space
              </summary>
              <Code code={item.reference_answer} />
            </details>
          )}
        </>
      )}

      {item.kind === "security_lab" && (
        <>
          <Markdown text={text(content.scenario_markdown)} className="lesson__body" />
          <div className="lab__artifact">
            <span className="lab__artifact-label">Evidence</span>
            <pre>
              <code>{text(content.artifact)}</code>
            </pre>
          </div>
          {(content.tasks as { question: string; expected_answer: string }[] | undefined)?.map((task, i) => {
            const answers = last ? last.answer_text.split("\n\n") : [];
            return (
              <div key={i} className="notebook-detail__attempt">
                <strong>
                  Task {i + 1}: {renderInline(task.question)}
                </strong>
                {answers[i] && (
                  <p>
                    <em>You:</em> {answers[i]}
                  </p>
                )}
                <p>
                  <em>Expected:</em> {renderInline(task.expected_answer)}
                </p>
              </div>
            );
          })}
          {item.reference_answer && (
            <details className="grade__details">
              <summary>Walkthrough</summary>
              <Markdown text={item.reference_answer} />
            </details>
          )}
        </>
      )}

      {item.kind === "mock_question" && (
        <>
          {last && (
            <>
              <h3 className="card__title">Your interview · {Math.round(last.score)}%</h3>
              <Markdown text={last.answer_text} />
              <Points items={list(grade.missed_points)} missed />
              {text(grade.improved_answer) && (
                <details className="grade__details" open>
                  <summary>A stronger answer</summary>
                  <Markdown text={text(grade.improved_answer)} />
                </details>
              )}
            </>
          )}
          {item.reference_answer && (
            <details className="grade__details">
              <summary>Model answer</summary>
              <Markdown text={item.reference_answer} />
            </details>
          )}
        </>
      )}
    </article>
  );
}
