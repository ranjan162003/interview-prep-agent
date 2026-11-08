import { CheckCircle2, Lightbulb, Quote, XCircle } from "lucide-react";

import type { ExplainResult } from "../../types/practice.types";
import { Markdown, renderInline } from "../common/Markdown";
import { ScoreRing } from "./ScoreRing";

const MAX_CRITERION_SCORE = 5;

/** The grader's verdict: score, per-criterion bars, what was covered/missed, quoted evidence, model answer. */
export function GradeCard({ result }: { result: ExplainResult }) {
  return (
    <section className="card grade" aria-label="Your grade">
      <div className="grade__header">
        <ScoreRing score={result.score} />
        <div>
          <p className="grade__status">
            {result.status === "weak" ? "Needs work — this comes back for review soon." : "Learnt — saved to your notebook."}
          </p>
          <p className="muted">{renderInline(result.overall_feedback)}</p>
        </div>
      </div>

      <ul className="grade__criteria">
        {result.criteria.map((criterion) => (
          <li key={criterion.name}>
            <div className="grade__criterion-head">
              <span className="grade__criterion-name">{criterion.name}</span>
              <span className="muted">
                {criterion.score}/{MAX_CRITERION_SCORE}
              </span>
            </div>
            <span className="grade__bar" aria-hidden="true">
              <span style={{ width: `${(criterion.score / MAX_CRITERION_SCORE) * 100}%` }} />
            </span>
            <p className="grade__criterion-comment">{renderInline(criterion.comment)}</p>
          </li>
        ))}
      </ul>

      <div className="grade__points">
        {result.covered_points.length > 0 && (
          <div>
            <h3 className="card__title">You covered</h3>
            <ul className="key-points">
              {result.covered_points.map((point) => (
                <li key={point}>
                  <CheckCircle2 size={16} aria-hidden="true" />
                  <span>{renderInline(point)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {result.missed_points.length > 0 && (
          <div>
            <h3 className="card__title">You missed</h3>
            <ul className="key-points">
              {result.missed_points.map((point) => (
                <li key={point} className="key-points__item--missed">
                  <XCircle size={16} aria-hidden="true" />
                  <span>{renderInline(point)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {result.evidence.length > 0 && (
        <div>
          <h3 className="card__title">From your answer</h3>
          <ul className="grade__evidence">
            {result.evidence.map((item, i) => (
              <li key={i}>
                <blockquote>
                  <Quote size={14} aria-hidden="true" /> {item.quote}
                </blockquote>
                <p>{renderInline(item.comment)}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      <details className="grade__details" open>
        <summary>A stronger version of your answer</summary>
        <Markdown text={result.improved_answer} />
      </details>

      <details className="grade__details">
        <summary>
          <Lightbulb size={16} aria-hidden="true" /> Revision note and model answer
        </summary>
        <ul className="key-points">
          {result.key_points.map((point) => (
            <li key={point}>
              <Lightbulb size={16} aria-hidden="true" />
              <span>{renderInline(point)}</span>
            </li>
          ))}
        </ul>
        <Markdown text={result.reference_answer} />
      </details>
    </section>
  );
}
