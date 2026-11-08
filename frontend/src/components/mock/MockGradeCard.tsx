import { CheckCircle2, XCircle } from "lucide-react";

import type { MockQuestionGrade } from "../../types/task.types";
import { Markdown, renderInline } from "../common/Markdown";
import { ScoreRing } from "../practice/ScoreRing";

/** Feedback for one interview question: score, criteria, what was covered or missed, a stronger answer. */
export function MockGradeCard({ grade, open = false }: { grade: MockQuestionGrade; open?: boolean }) {
  return (
    <details className="card mock-grade" open={open}>
      <summary className="mock-grade__summary">
        <ScoreRing score={grade.score} size="small" />
        <span className="mock-grade__question">
          <span className="page-header__eyebrow">
            Question {grade.question_index + 1} · {grade.subtopic_name}
          </span>
          <span>{renderInline(grade.question)}</span>
        </span>
      </summary>

      <p className="muted">{renderInline(grade.overall_feedback)}</p>
      <ul className="grade__criteria">
        {grade.criteria.map((criterion) => (
          <li key={criterion.name}>
            <div className="grade__criterion-head">
              <span className="grade__criterion-name">{criterion.name}</span>
              <span className="muted">{criterion.score}/5</span>
            </div>
            <span className="grade__bar" aria-hidden="true">
              <span style={{ width: `${(criterion.score / 5) * 100}%` }} />
            </span>
            <p className="grade__criterion-comment">{renderInline(criterion.comment)}</p>
          </li>
        ))}
      </ul>
      <div className="grade__points">
        {grade.covered_points.length > 0 && (
          <ul className="key-points">
            {grade.covered_points.map((point) => (
              <li key={point}>
                <CheckCircle2 size={16} aria-hidden="true" />
                <span>{renderInline(point)}</span>
              </li>
            ))}
          </ul>
        )}
        {grade.missed_points.length > 0 && (
          <ul className="key-points">
            {grade.missed_points.map((point) => (
              <li key={point} className="key-points__item--missed">
                <XCircle size={16} aria-hidden="true" />
                <span>{renderInline(point)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="grade__details">
        <p className="card__title">A stronger answer</p>
        <Markdown text={grade.improved_answer} />
      </div>
    </details>
  );
}
