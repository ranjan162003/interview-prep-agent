import { ArrowRight, Check, Save } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { trackApi } from "../api/trackApi";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { Skeleton } from "../components/common/Skeleton";
import { PageHeader } from "../components/layout/PageHeader";
import { SyllabusPreview } from "../components/settings/SyllabusPreview";
import { useProfile } from "../context/ProfileContext";
import { useToast } from "../context/ToastContext";
import type { DailyMinutes, TrackSummary } from "../types/track.types";

const SESSION_OPTIONS: { value: DailyMinutes; label: string; hint: string }[] = [
  { value: 60, label: "1 hour a day", hint: "Quiz, one concept, one problem or lab, one mock question" },
  { value: 120, label: "2 hours a day", hint: "Longer problems, two concepts, a fuller mock interview" },
];

function todayIso(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

export function SettingsPage() {
  const { profile, saveProfile } = useProfile();
  const toast = useToast();
  const [tracks, setTracks] = useState<TrackSummary[] | null>(null);
  const [trackId, setTrackId] = useState("");
  const [hasDate, setHasDate] = useState(true);
  const [interviewDate, setInterviewDate] = useState("");
  const [dailyMinutes, setDailyMinutes] = useState<DailyMinutes>(60);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    trackApi
      .listTracks()
      .then(setTracks)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  // Start the form from the saved profile once it arrives.
  useEffect(() => {
    if (!profile) return;
    setTrackId(profile.track_id);
    setHasDate(profile.interview_date !== null);
    setInterviewDate(profile.interview_date ?? "");
    setDailyMinutes(profile.daily_minutes);
  }, [profile]);

  // First visit (no saved profile): preselect the first track. Never overrides a saved choice.
  useEffect(() => {
    if (profile === null && tracks?.length) setTrackId((current) => current || tracks[0].id);
  }, [profile, tracks]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (hasDate && !interviewDate) {
      setError("Pick your interview date, or choose “No date yet”.");
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      const isFirstSave = !profile;
      await saveProfile({ track_id: trackId, interview_date: hasDate ? interviewDate : null, daily_minutes: dailyMinutes });
      toast({ message: isFirstSave ? "You're set up — time to practise." : "Settings saved." });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow="Settings"
        title={profile === null ? "Set up your prep" : "Settings"}
        description="Choose the role you're preparing for and when the interview is. Your daily plan is built from this."
      />

      <div className="settings-layout">
        <form className="card settings-form" onSubmit={handleSubmit}>
          <fieldset className="field">
            <legend className="field__label">Career track</legend>
            {tracks === null ? (
              <div className="segmented">
                <Skeleton height={92} radius={12} />
                <Skeleton height={92} radius={12} />
              </div>
            ) : (
              <div className="segmented" role="radiogroup" aria-label="Career track">
                {tracks.map((track) => (
                  <button
                    key={track.id}
                    type="button"
                    role="radio"
                    aria-checked={trackId === track.id}
                    className={`segmented__option${trackId === track.id ? " segmented__option--selected" : ""}`}
                    onClick={() => setTrackId(track.id)}
                  >
                    <span className="segmented__label">{track.name}</span>
                    <span className="segmented__hint">{track.description}</span>
                    <span className="segmented__hint">
                      {track.topic_count} topics · {track.subtopic_count} subtopics
                    </span>
                  </button>
                ))}
              </div>
            )}
            {profile && trackId && trackId !== profile.track_id && (
              <p className="field__hint field__hint--warning">
                Switching track starts a new syllabus. What you learnt on {profile.track_name} stays in your notebook.
              </p>
            )}
          </fieldset>

          <fieldset className="field">
            <legend className="field__label">Interview date</legend>
            <div className="radio-row">
              <label className="radio-row__option">
                <input type="radio" name="has-date" checked={hasDate} onChange={() => setHasDate(true)} />
                I have a date
              </label>
              <label className="radio-row__option">
                <input type="radio" name="has-date" checked={!hasDate} onChange={() => setHasDate(false)} />
                No date yet — keep practising
              </label>
            </div>
            {hasDate && (
              <input
                type="date"
                className="input settings-form__date"
                min={todayIso()}
                value={interviewDate}
                onChange={(event) => setInterviewDate(event.target.value)}
                aria-label="Interview date"
              />
            )}
          </fieldset>

          <fieldset className="field">
            <legend className="field__label">Daily session</legend>
            <div className="segmented" role="radiogroup" aria-label="Daily session length">
              {SESSION_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  role="radio"
                  aria-checked={dailyMinutes === option.value}
                  className={`segmented__option${dailyMinutes === option.value ? " segmented__option--selected" : ""}`}
                  onClick={() => setDailyMinutes(option.value)}
                >
                  <span className="segmented__label">{option.label}</span>
                  <span className="segmented__hint">{option.hint}</span>
                </button>
              ))}
            </div>
          </fieldset>

          {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

          <div className="button-row">
            <button type="submit" className="button button--primary" disabled={isSaving || !trackId}>
              {isSaving ? <Check size={16} /> : <Save size={16} />} {isSaving ? "Saving…" : "Save"}
            </button>
            {profile && (
              <Link to="/practice" className="button button--ghost">
                Start practising <ArrowRight size={16} />
              </Link>
            )}
          </div>
        </form>

        {trackId && <SyllabusPreview trackId={trackId} />}
      </div>
    </div>
  );
}
