import { useState } from "react";

import type { SubtopicMastery, TopicMastery } from "../../types/plan.types";
import { useCellTooltip } from "./useCellTooltip";

/** Mastery → one of five steps of a single-hue ramp (validated; see --seq-* tokens). */
export function masteryStep(mastery: number | null): number | null {
  if (mastery === null) return null;
  return Math.min(5, Math.floor(mastery / 20) + 1);
}

const STATUS_TEXT: Record<SubtopicMastery["status"], string> = {
  not_started: "Not started",
  in_progress: "In progress",
  covered: "All concepts covered",
  weak: "Needs review",
};

function formatDate(iso: string | null): string {
  return iso ? new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { day: "numeric", month: "short" }) : "—";
}

/** Topic mastery heat-map: one row per topic, one cell per subtopic, darker = stronger. */
export function MasteryHeatmap({ topics }: { topics: TopicMastery[] }) {
  const { containerRef, cellProps, tooltip } = useCellTooltip();
  const [asTable, setAsTable] = useState(false);

  return (
    <section className="card" aria-label="Topic mastery">
      <div className="card__title-row">
        <h2 className="card__title">Topic mastery</h2>
        <button type="button" className="link-button" onClick={() => setAsTable((v) => !v)}>
          {asTable ? "Show heat-map" : "Show as table"}
        </button>
      </div>

      {asTable ? (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Subtopic</th>
                <th scope="col">Mastery</th>
                <th scope="col">Concepts covered</th>
                <th scope="col">Status</th>
                <th scope="col">Next review</th>
              </tr>
            </thead>
            <tbody>
              {topics.flatMap((topic) =>
                topic.subtopics.map((s) => (
                  <tr key={s.subtopic_id}>
                    <th scope="row">
                      <span className="muted">{topic.name} · </span>
                      {s.name}
                    </th>
                    <td>{s.mastery === null ? "—" : `${Math.round(s.mastery)}%`}</td>
                    <td>{Math.round(s.coverage * 100)}%</td>
                    <td>{STATUS_TEXT[s.status]}</td>
                    <td>{formatDate(s.next_review_on)}</td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="heatmap" ref={containerRef}>
          {topics.map((topic) => (
            <div key={topic.topic_id} className="heatmap__row">
              <span className="heatmap__label" title={topic.name}>
                {topic.name}
                <span className="heatmap__label-value">{topic.mastery === null ? "—" : `${Math.round(topic.mastery)}%`}</span>
              </span>
              <div className="heatmap__cells">
                {topic.subtopics.map((s) => {
                  const step = masteryStep(s.mastery);
                  return (
                    <span
                      key={s.subtopic_id}
                      className={`heatmap__cell${step === null ? " heatmap__cell--empty" : ""}${s.status === "weak" ? " heatmap__cell--weak" : ""}`}
                      style={step === null ? undefined : { background: `var(--seq-${step})` }}
                      aria-label={`${s.name}: ${s.mastery === null ? "not answered yet" : `${Math.round(s.mastery)}% mastery`}, ${STATUS_TEXT[s.status].toLowerCase()}`}
                      {...cellProps([
                        s.name,
                        s.mastery === null ? "Not answered yet" : `Mastery ${Math.round(s.mastery)}%`,
                        `Concepts covered ${Math.round(s.coverage * 100)}%`,
                        STATUS_TEXT[s.status] + (s.next_review_on ? ` · review ${formatDate(s.next_review_on)}` : ""),
                      ])}
                    >
                      {s.status === "weak" ? "!" : ""}
                    </span>
                  );
                })}
              </div>
            </div>
          ))}
          {tooltip}
        </div>
      )}

      <div className="heatmap-legend" aria-label="Legend">
        <span className="heatmap-legend__item">
          <span className="heatmap__cell heatmap__cell--empty heatmap-legend__swatch" /> Not started
        </span>
        <span className="heatmap-legend__ramp">
          <span className="muted">0%</span>
          {[1, 2, 3, 4, 5].map((step) => (
            <span key={step} className="heatmap-legend__swatch" style={{ background: `var(--seq-${step})` }} />
          ))}
          <span className="muted">100% mastery</span>
        </span>
        <span className="heatmap-legend__item">
          <span className="heatmap__cell heatmap__cell--weak heatmap-legend__swatch">!</span> Needs review
        </span>
      </div>
    </section>
  );
}
