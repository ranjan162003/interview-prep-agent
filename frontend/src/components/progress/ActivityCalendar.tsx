import type { ActivityDay } from "../../types/plan.types";
import { useCellTooltip } from "./useCellTooltip";

const WEEKDAY_LABELS = ["Mon", "", "Wed", "", "Fri", "", "Sun"];

/** Answers given that day → ramp step (0 = no activity). */
function activityStep(day: ActivityDay): number {
  const answers = day.answers;
  if (answers === 0 && day.minutes === 0) return 0;
  if (answers <= 2) return 1;
  if (answers <= 5) return 2;
  if (answers <= 10) return 3;
  if (answers <= 20) return 4;
  return 5;
}

/** The last 12 weeks as a GitHub-style calendar: columns are weeks, rows are weekdays. */
export function ActivityCalendar({ days }: { days: ActivityDay[] }) {
  const { containerRef, cellProps, tooltip } = useCellTooltip();
  // Pad the start so the first column begins on a Monday.
  const firstWeekday = (new Date(`${days[0].day}T00:00:00`).getDay() + 6) % 7;
  const cells: (ActivityDay | null)[] = [...Array<null>(firstWeekday).fill(null), ...days];
  const activeDays = days.filter((d) => d.answers || d.minutes).length;

  return (
    <section className="card" aria-label="Study activity">
      <div className="card__title-row">
        <h2 className="card__title">Last 12 weeks</h2>
        <span className="muted">
          {activeDays} active day{activeDays === 1 ? "" : "s"}
        </span>
      </div>
      <div className="calendar" ref={containerRef}>
        <div className="calendar__weekdays" aria-hidden="true">
          {WEEKDAY_LABELS.map((label, i) => (
            <span key={i}>{label}</span>
          ))}
        </div>
        <div className="calendar__grid">
          {cells.map((day, i) =>
            day === null ? (
              <span key={`pad-${i}`} className="calendar__cell calendar__cell--pad" aria-hidden="true" />
            ) : (
              <span
                key={day.day}
                className={`calendar__cell${activityStep(day) === 0 ? " calendar__cell--zero" : ""}`}
                style={activityStep(day) ? { background: `var(--seq-${activityStep(day)})` } : undefined}
                aria-label={`${day.day}: ${day.answers} answers, ${day.minutes} minutes`}
                {...cellProps([
                  new Date(`${day.day}T00:00:00`).toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" }),
                  `${day.answers} answer${day.answers === 1 ? "" : "s"}`,
                  `${day.minutes} min of plan done`,
                ])}
              />
            ),
          )}
        </div>
        {tooltip}
      </div>
      <div className="heatmap-legend">
        <span className="heatmap-legend__ramp">
          <span className="muted">Less</span>
          <span className="calendar__cell calendar__cell--zero heatmap-legend__swatch" />
          {[1, 2, 3, 4, 5].map((step) => (
            <span key={step} className="heatmap-legend__swatch" style={{ background: `var(--seq-${step})` }} />
          ))}
          <span className="muted">More answers</span>
        </span>
      </div>
    </section>
  );
}
