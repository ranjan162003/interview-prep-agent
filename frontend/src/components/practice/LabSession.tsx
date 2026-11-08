import { ArrowRight, CheckCircle2, Lightbulb, Send, XCircle } from "lucide-react";
import { useState, type FormEvent } from "react";

import { taskApi } from "../../api/studyApi";
import type { AgentChoice } from "../../types/practice.types";
import type { LabResult, SecurityLab } from "../../types/task.types";
import { ErrorAlert } from "../common/ErrorAlert";
import { LoadingSpinner } from "../common/LoadingSpinner";
import { Markdown, renderInline } from "../common/Markdown";
import { DifficultyPill } from "./DifficultyPill";
import { ScoreRing } from "./ScoreRing";

const ARTIFACT_LABELS: Record<string, string> = {
  log: "Log excerpt",
  code: "Code",
  http: "HTTP traffic",
  email: "Email",
  config: "Configuration",
  packet: "Packet capture",
  alert: "Alert",
};

interface LabSessionProps {
  lab: SecurityLab;
  agent: AgentChoice;
  agentLabel: string;
  onFinished: () => void;
  onNextLab: () => void;
}

/** A hands-on security lab: read the scenario, analyse the evidence, answer each task, get graded. */
export function LabSession({ lab, agent, agentLabel, onFinished, onNextLab }: LabSessionProps) {
  const [answers, setAnswers] = useState<string[]>(() => lab.tasks.map(() => ""));
  const [result, setResult] = useState<LabResult | null>(null);
  const [isGrading, setIsGrading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setIsGrading(true);
    setError(null);
    try {
      setResult(await taskApi.submitLab(lab.item_id, agent, answers));
      onFinished();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsGrading(false);
    }
  }

  return (
    <div className="lab">
      <article className="card lesson" aria-label="Lab scenario">
        <div className="quiz__meta">
          <span className="page-header__eyebrow">
            {lab.subtopic.topic_name} · {lab.subtopic.subtopic_name}
          </span>
          <DifficultyPill difficulty={lab.subtopic.difficulty} />
        </div>
        <h2 className="lesson__title">{lab.title}</h2>
        <Markdown text={lab.scenario_markdown} className="lesson__body" />
        <div className="lab__artifact">
          <span className="lab__artifact-label">{ARTIFACT_LABELS[lab.artifact_type] ?? "Evidence"}</span>
          <pre>
            <code>{lab.artifact}</code>
          </pre>
        </div>
      </article>

      {result ? (
        <>
          <LabResultCard result={result} />
          <div className="button-row">
            <button type="button" className="button button--primary" onClick={onNextLab}>
              Next lab <ArrowRight size={16} />
            </button>
          </div>
        </>
      ) : (
        <form className="card explain" onSubmit={handleSubmit}>
          <span className="page-header__eyebrow">Your analysis</span>
          {lab.tasks.map((task, i) => (
            <label key={i} className="field">
              <span className="field__label">
                Task {i + 1}: {renderInline(task.question)}
              </span>
              <textarea
                className="input explain__answer"
                rows={3}
                value={answers[i]}
                onChange={(event) => setAnswers((current) => current.map((a, j) => (j === i ? event.target.value : a)))}
                disabled={isGrading}
                placeholder="Your answer, with the evidence that supports it…"
              />
            </label>
          ))}
          {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}
          {isGrading ? (
            <LoadingSpinner label={`${agentLabel} is grading your analysis…`} />
          ) : (
            <div className="button-row">
              <button type="submit" className="button button--primary" disabled={answers.every((a) => !a.trim())}>
                <Send size={16} /> Submit for grading
              </button>
            </div>
          )}
        </form>
      )}
    </div>
  );
}

function LabResultCard({ result }: { result: LabResult }) {
  return (
    <section className="card grade" aria-label="Lab result">
      <div className="grade__header">
        <ScoreRing score={result.score} />
        <div>
          <p className="grade__status">
            {result.status === "weak" ? "Needs work — this comes back for review soon." : "Well analysed — saved to your notebook."}
          </p>
          <p className="muted">{renderInline(result.overall_feedback)}</p>
        </div>
      </div>

      <ol className="lab__results">
        {result.tasks.map((task, i) => (
          <li key={i}>
            <div className="grade__criterion-head">
              <span className="grade__criterion-name">
                Task {i + 1}: {renderInline(task.question)}
              </span>
              <span className="muted">{task.score}/5</span>
            </div>
            <span className="grade__bar" aria-hidden="true">
              <span style={{ width: `${(task.score / 5) * 100}%` }} />
            </span>
            <p className="grade__criterion-comment">{renderInline(task.comment)}</p>
            <p className="lab__answer">
              <strong>You:</strong> {task.your_answer || <em>no answer</em>}
            </p>
            <p className="lab__answer">
              <CheckCircle2 size={14} aria-hidden="true" /> <strong>Expected:</strong> {renderInline(task.expected_answer)}
            </p>
            {task.missed.length > 0 && (
              <ul className="key-points">
                {task.missed.map((m) => (
                  <li key={m} className="key-points__item--missed">
                    <XCircle size={16} aria-hidden="true" />
                    <span>{renderInline(m)}</span>
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ol>

      <details className="grade__details" open>
        <summary>
          <Lightbulb size={16} aria-hidden="true" /> How an expert solves it
        </summary>
        <Markdown text={result.walkthrough_markdown} />
        <ul className="key-points">
          {result.key_points.map((point) => (
            <li key={point}>
              <Lightbulb size={16} aria-hidden="true" />
              <span>{renderInline(point)}</span>
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}
