import { BookCheck, Download, Flame, Gauge, Settings, Target, Timer } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { notebookApi, progressApi } from "../api/studyApi";
import { CountUp } from "../components/common/CountUp";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { SkeletonResults } from "../components/common/Skeleton";
import { PageHeader } from "../components/layout/PageHeader";
import { ActivityCalendar } from "../components/progress/ActivityCalendar";
import { MasteryHeatmap } from "../components/progress/MasteryHeatmap";
import { useProfile } from "../context/ProfileContext";
import type { Progress } from "../types/plan.types";

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

export function ProgressPage() {
  const { profile } = useProfile();
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!profile) return;
    progressApi
      .get()
      .then(setProgress)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [profile]);

  if (profile === null) {
    return (
      <div className="page">
        <PageHeader eyebrow="Review" title="Progress" />
        <div className="card">
          <EmptyState
            icon={Settings}
            title="Pick your career track first"
            description="Progress is tracked against your track's syllabus."
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

  const weeklyReportUrl = notebookApi.exportUrl({ date_from: isoDaysAgo(6) }, "full");

  return (
    <div className="page">
      <PageHeader
        eyebrow={progress ? `Review · ${progress.track_name}` : "Review"}
        title="Progress"
        description="How far you've come, what's strong, what's weak, and how ready you are."
        actions={
          <a className="button button--ghost" href={weeklyReportUrl} download>
            <Download size={16} /> Weekly report (PDF)
          </a>
        }
      />
      {error && <ErrorAlert message={error} />}
      {!progress ? (
        <SkeletonResults label="Loading progress" />
      ) : (
        <>
          <section className="card readiness" aria-label="Interview readiness">
            <div className="readiness__hero">
              <span className="page-header__eyebrow">
                <Gauge size={14} aria-hidden="true" /> Interview readiness
              </span>
              <span className="readiness__value">
                <CountUp value={progress.readiness.score} format={(v) => (v < 10 ? v.toFixed(1) : String(Math.round(v)))} />
                <span className="readiness__unit">%</span>
              </span>
              <span className="readiness__label">{progress.readiness.label}</span>
            </div>
            <div className="readiness__breakdown">
              <span className="readiness__meter" aria-hidden="true">
                <span style={{ width: `${progress.readiness.score}%` }} />
              </span>
              <dl>
                <div>
                  <dt>Syllabus covered</dt>
                  <dd>{Math.round(progress.readiness.coverage_percent)}%</dd>
                </div>
                <div>
                  <dt>Average mastery</dt>
                  <dd>{progress.readiness.mastery_percent === null ? "—" : `${Math.round(progress.readiness.mastery_percent)}%`}</dd>
                </div>
                <div>
                  <dt>Mock interviews</dt>
                  <dd>{progress.readiness.mock_average === null ? "—" : `${Math.round(progress.readiness.mock_average)}%`}</dd>
                </div>
                <div>
                  <dt>Interview in</dt>
                  <dd>{progress.days_until_interview === null ? "no date" : `${progress.days_until_interview} days`}</dd>
                </div>
              </dl>
              <p className="muted readiness__note">
                Readiness counts a subtopic fully only when every concept is taught and you score well on it.
              </p>
            </div>
          </section>

          <div className="stat-grid">
            <div className="card today-stat">
              <Flame size={20} aria-hidden="true" />
              <span className="today-stat__value">{progress.streak_days}</span>
              <span className="muted">day streak · best {progress.longest_streak}</span>
            </div>
            <div className="card today-stat">
              <Timer size={20} aria-hidden="true" />
              <span className="today-stat__value">{progress.minutes_this_week}</span>
              <span className="muted">minutes this week · {progress.minutes_total} total</span>
            </div>
            <div className="card today-stat">
              <BookCheck size={20} aria-hidden="true" />
              <span className="today-stat__value">{progress.items_learnt}</span>
              <span className="muted">learnt of {progress.items_seen} items</span>
            </div>
            <div className="card today-stat">
              <Target size={20} aria-hidden="true" />
              <span className="today-stat__value">
                {progress.average_recent_score === null ? "—" : `${Math.round(progress.average_recent_score)}%`}
              </span>
              <span className="muted">average recent score</span>
            </div>
          </div>

          <MasteryHeatmap topics={progress.topics} />
          <ActivityCalendar days={progress.activity} />
        </>
      )}
    </div>
  );
}
