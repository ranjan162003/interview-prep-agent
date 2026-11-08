import { CheckCircle2, Lightbulb, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { planApi } from "../../api/studyApi";
import type { DailyRecap } from "../../types/plan.types";
import { ErrorAlert } from "../common/ErrorAlert";
import { SkeletonList } from "../common/Skeleton";
import { renderInline } from "../common/Markdown";

const KIND_LABELS: Record<string, string> = {
  concept: "Lesson",
  quiz_question: "Quiz",
  coding_problem: "Coding",
  security_lab: "Lab",
  mock_question: "Mock",
};

interface RecapPanelProps {
  isDone: boolean;
  onMarkDone: () => void;
}

/** End of the day: what was learnt, what's weak, and what comes next. */
export function RecapPanel({ isDone, onMarkDone }: RecapPanelProps) {
  const [recap, setRecap] = useState<DailyRecap | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    planApi
      .getRecap()
      .then(setRecap)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  if (error) return <ErrorAlert message={error} />;
  if (!recap) return <SkeletonList rows={3} label="Loading recap" />;

  return (
    <section className="card recap" aria-label="Today's recap">
      <span className="page-header__eyebrow">Recap</span>
      <h2 className="card__title">
        {recap.items.length
          ? `You worked on ${recap.items.length} item${recap.items.length > 1 ? "s" : ""} today`
          : "Nothing answered yet today"}
        {recap.minutes_done ? ` · ${recap.minutes_done} min of plan done` : ""}
      </h2>

      {recap.items.length > 0 && (
        <ul className="recap__items">
          {recap.items.map((item) => (
            <li key={item.item_id}>
              <div className="recap__item-head">
                {item.status === "weak" ? (
                  <XCircle size={16} className="text-critical" aria-label="Needs review" />
                ) : (
                  <CheckCircle2 size={16} className="text-good" aria-label="Learnt" />
                )}
                <span className="pill">{KIND_LABELS[item.kind] ?? item.kind}</span>
                <span className="recap__item-title">{renderInline(item.title)}</span>
                {item.score !== null && <span className="muted">{Math.round(item.score)}%</span>}
              </div>
              {item.key_points.slice(0, 3).map((point) => (
                <p key={point} className="recap__point">
                  <Lightbulb size={13} aria-hidden="true" /> {renderInline(point)}
                </p>
              ))}
            </li>
          ))}
        </ul>
      )}

      <div className="recap__next">
        {recap.weak_subtopics.length > 0 && (
          <p>
            <strong>Weak spots:</strong> {recap.weak_subtopics.join(", ")} — they come back for review automatically.
          </p>
        )}
        {recap.reviews_due_tomorrow > 0 && (
          <p>
            <strong>Tomorrow:</strong> {recap.reviews_due_tomorrow} subtopic{recap.reviews_due_tomorrow > 1 ? "s" : ""} due for review.
          </p>
        )}
        {recap.next_up && (
          <p>
            <strong>Up next in your syllabus:</strong> {recap.next_up}
          </p>
        )}
      </div>

      <div className="button-row">
        {!isDone && (
          <button type="button" className="button button--primary" onClick={onMarkDone}>
            <CheckCircle2 size={16} /> Finish today's session
          </button>
        )}
        <Link to="/notebook" className="button button--ghost">
          Open notebook
        </Link>
      </div>
    </section>
  );
}
