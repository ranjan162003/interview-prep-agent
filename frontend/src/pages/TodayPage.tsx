import { ArrowRight, CalendarClock, Flame, RefreshCw, Settings, Timer } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { planApi, progressApi } from "../api/studyApi";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { SkeletonResults } from "../components/common/Skeleton";
import { PageHeader } from "../components/layout/PageHeader";
import { BlockCard } from "../components/today/BlockCard";
import { RecapPanel } from "../components/today/RecapPanel";
import { SessionTimer } from "../components/today/SessionTimer";
import { useProfile } from "../context/ProfileContext";
import type { DailyPlan, Progress } from "../types/plan.types";

function countdownText(days: number | null): string {
  if (days === null) return "No interview date set — practising at your own pace.";
  if (days === 0) return "Your interview is today. Good luck!";
  if (days === 1) return "Your interview is tomorrow — a light review today.";
  return `${days} days until your interview.`;
}

export function TodayPage() {
  const { profile } = useProfile();
  const [plan, setPlan] = useState<DailyPlan | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [showRecap, setShowRecap] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isRebuilding, setIsRebuilding] = useState(false);

  const load = useCallback(() => {
    planApi
      .getToday()
      .then(setPlan)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
    progressApi.get().then(setProgress).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (profile) load();
  }, [profile, load]);

  async function rebuild() {
    setIsRebuilding(true);
    try {
      setPlan(await planApi.regenerate());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsRebuilding(false);
    }
  }

  async function finishRecap(blockId: string) {
    try {
      setPlan(await planApi.completeBlock(blockId));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  if (profile === undefined) {
    return (
      <div className="page">
        <PageHeader eyebrow="Prepare" title="Today" />
        <SkeletonResults label="Loading" />
      </div>
    );
  }

  if (profile === null) {
    return (
      <div className="page">
        <PageHeader eyebrow="Prepare" title="Welcome to PrepPilot" />
        <div className="card">
          <EmptyState
            icon={Settings}
            title="Let's set up your prep"
            description="Pick the role you're preparing for and your interview date. Every day you'll get a 1–2 hour plan that targets your weak spots."
            actions={
              <Link to="/settings" className="button button--primary">
                Get started <ArrowRight size={16} />
              </Link>
            }
          />
        </div>
      </div>
    );
  }

  const nextIndex = plan?.blocks.findIndex((b) => !b.done) ?? -1;
  const recapBlock = plan?.blocks.find((b) => b.kind === "recap");
  const allDone = plan !== null && nextIndex === -1;
  const nothingDone = plan !== null && plan.blocks.every((b) => !b.done);

  return (
    <div className="page">
      <PageHeader
        eyebrow={`Prepare · ${profile.track_name}`}
        title="Today"
        description={countdownText(profile.days_until_interview)}
        actions={
          nothingDone && (
            <button type="button" className="button button--ghost" onClick={() => void rebuild()} disabled={isRebuilding}>
              <RefreshCw size={16} className={isRebuilding ? "spin" : undefined} /> Rebuild plan
            </button>
          )
        }
      />

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      <div className="today-stats">
        <div className="card today-stat">
          <CalendarClock size={20} aria-hidden="true" />
          <span className="today-stat__value">{profile.days_until_interview ?? "—"}</span>
          <span className="muted">days to go</span>
        </div>
        <div className="card today-stat">
          <Timer size={20} aria-hidden="true" />
          <span className="today-stat__value">
            {plan?.minutes_done ?? 0}
            <span className="muted">/{plan?.daily_minutes ?? profile.daily_minutes}</span>
          </span>
          <span className="muted">minutes done today</span>
        </div>
        <div className="card today-stat">
          <Flame size={20} aria-hidden="true" />
          <span className="today-stat__value">{progress?.streak_days ?? "—"}</span>
          <span className="muted">day streak</span>
        </div>
      </div>

      {!plan ? (
        <SkeletonResults label="Building today's plan" />
      ) : (
        <div className="today-layout">
          <section className="card" aria-label="Today's plan">
            <div className="card__title-row">
              <h2 className="card__title">{allDone ? "All done for today 🎉" : "Today's plan"}</h2>
              <span className="muted">{plan.blocks.filter((b) => b.done).length}/{plan.blocks.length} blocks</span>
            </div>
            <ol className="plan-blocks">
              {plan.blocks.map((block, index) => (
                <BlockCard
                  key={block.id}
                  block={block}
                  index={index}
                  isNext={index === nextIndex}
                  onOpenRecap={() => setShowRecap(true)}
                />
              ))}
            </ol>
          </section>

          <aside className="today-side">
            <section className="card">
              <SessionTimer planDate={plan.plan_date} plannedMinutes={plan.daily_minutes} />
            </section>
            {progress && progress.reviews_due > 0 && (
              <section className="card today-reviews">
                <span className="page-header__eyebrow">Spaced repetition</span>
                <p>
                  <strong>{progress.reviews_due}</strong> subtopic{progress.reviews_due > 1 ? "s are" : " is"} due for review. The
                  most overdue one is in today's warm-up quiz.
                </p>
              </section>
            )}
          </aside>
        </div>
      )}

      {plan && (showRecap || recapBlock?.done) && recapBlock && (
        <RecapPanel isDone={recapBlock.done} onMarkDone={() => void finishRecap(recapBlock.id)} />
      )}
    </div>
  );
}
