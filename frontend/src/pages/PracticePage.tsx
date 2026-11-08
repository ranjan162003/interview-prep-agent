import { BookOpen, Code2, ListChecks, Play, Settings, ShieldCheck, type LucideIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { practiceApi } from "../api/practiceApi";
import { planApi, taskApi } from "../api/studyApi";
import { trackApi } from "../api/trackApi";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { SkeletonResults } from "../components/common/Skeleton";
import { ActiveModelSelector } from "../components/connectors/ActiveModelSelector";
import { PageHeader } from "../components/layout/PageHeader";
import { CodingSession } from "../components/practice/CodingSession";
import { ConceptSession } from "../components/practice/ConceptSession";
import { LabSession } from "../components/practice/LabSession";
import { QuizRunner } from "../components/practice/QuizRunner";
import { SubtopicSelect } from "../components/practice/SubtopicSelect";
import { useProfile } from "../context/ProfileContext";
import { useToast } from "../context/ToastContext";
import { useAgentChoice } from "../hooks/useAgentChoice";
import type { ConceptLesson, PracticeOverview, QuizSet } from "../types/practice.types";
import type { CodingProblem, SecurityLab } from "../types/task.types";
import type { Track } from "../types/track.types";

export type PracticeMode = "quiz" | "concept" | "coding" | "lab";

type Session =
  | { kind: "idle" }
  | { kind: "loading"; message: string }
  | { kind: "quiz"; quiz: QuizSet }
  | { kind: "concept"; lesson: ConceptLesson }
  | { kind: "coding"; problem: CodingProblem }
  | { kind: "lab"; lab: SecurityLab };

interface ModeOption {
  value: PracticeMode;
  label: string;
  hint: string;
  icon: LucideIcon;
  loading: string;
}

const QUIZ: ModeOption = { value: "quiz", label: "Warm-up quiz", hint: "Quick questions, instant answers", icon: ListChecks, loading: "writing a quiz on" };
const CONCEPT: ModeOption = { value: "concept", label: "Learn a concept", hint: "A lesson, then explain it back", icon: BookOpen, loading: "preparing a lesson on" };
const CODING: ModeOption = { value: "coding", label: "Coding problem", hint: "Editor, tests, hints, code review", icon: Code2, loading: "writing a coding problem on" };
const LAB: ModeOption = { value: "lab", label: "Security lab", hint: "Analyse real-looking evidence", icon: ShieldCheck, loading: "building a lab on" };

const DEFAULT_QUIZ_QUESTIONS = 5;
const MODES = new Set<PracticeMode>(["quiz", "concept", "coding", "lab"]);

export function PracticePage() {
  const { profile } = useProfile();
  const { agent, isReady, label: agentLabel } = useAgentChoice();
  const toast = useToast();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedMode = searchParams.get("mode") as PracticeMode | null;
  const subtopicId = searchParams.get("subtopic") ?? "";
  // Set when started from a block of Today's plan: finishing the activity ticks the block off.
  const blockId = searchParams.get("block");
  const questionCount = Number(searchParams.get("count")) || DEFAULT_QUIZ_QUESTIONS;

  const [track, setTrack] = useState<Track | null>(null);
  const [overview, setOverview] = useState<PracticeOverview | null>(null);
  const [session, setSession] = useState<Session>({ kind: "idle" });
  // Remounts the session view so "Another one" starts fresh even for the same subtopic.
  const [sessionKey, setSessionKey] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const autoStarted = useRef(false);
  const blockCompleted = useRef(false);

  const modeOptions = track ? [QUIZ, CONCEPT, track.has_coding_problems ? CODING : LAB] : [QUIZ, CONCEPT];
  const mode: PracticeMode =
    requestedMode && MODES.has(requestedMode) && modeOptions.some((o) => o.value === requestedMode) ? requestedMode : "quiz";

  const refreshOverview = useCallback(() => {
    practiceApi.getOverview().then(setOverview).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!profile) return;
    trackApi.getTrack(profile.track_id).then(setTrack).catch((err: unknown) => setError(String(err)));
    refreshOverview();
  }, [profile, refreshOverview]);

  function updateParams(next: { mode?: PracticeMode; subtopic?: string }) {
    const params = new URLSearchParams(searchParams);
    if (next.mode) params.set("mode", next.mode);
    if (next.subtopic !== undefined) {
      if (next.subtopic) params.set("subtopic", next.subtopic);
      else params.delete("subtopic");
    }
    // Changing the activity by hand detaches it from the plan block.
    params.delete("block");
    params.delete("count");
    setSearchParams(params, { replace: true });
  }

  const subtopicName = (id: string | null | undefined) =>
    track?.topics.flatMap((t) => t.subtopics).find((s) => s.id === id)?.name;

  const start = useCallback(
    async (startMode: PracticeMode = mode) => {
      const option = [QUIZ, CONCEPT, CODING, LAB].find((o) => o.value === startMode)!;
      const target = subtopicName(subtopicId || overview?.next_subtopic_id) ?? "your next subtopic";
      const chosen = subtopicId || null;
      setError(null);
      setSession({ kind: "loading", message: `${agentLabel} is ${option.loading} ${target}…` });
      try {
        if (startMode === "quiz") setSession({ kind: "quiz", quiz: await practiceApi.createQuiz(agent, chosen, questionCount) });
        else if (startMode === "concept") setSession({ kind: "concept", lesson: await practiceApi.createConceptLesson(agent, chosen) });
        else if (startMode === "coding") setSession({ kind: "coding", problem: await taskApi.createCodingProblem(agent, chosen) });
        else setSession({ kind: "lab", lab: await taskApi.createLab(agent, chosen) });
        setSessionKey((k) => k + 1);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        setSession({ kind: "idle" });
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [mode, subtopicId, overview, agent, agentLabel, questionCount, track],
  );

  // Arriving from Today's plan: start straight away (once).
  useEffect(() => {
    if (blockId && track && isReady && session.kind === "idle" && !autoStarted.current) {
      autoStarted.current = true;
      void start();
    }
  }, [blockId, track, isReady, session.kind, start]);

  const handleFinished = useCallback(() => {
    refreshOverview();
    if (!blockId || blockCompleted.current) return;
    blockCompleted.current = true;
    planApi
      .completeBlock(blockId)
      .then(() =>
        toast({
          message: "Block done — nice work.",
          action: { label: "Back to Today", onClick: () => navigate("/") },
          durationMs: 8000,
        }),
      )
      .catch(() => undefined);
  }, [blockId, refreshOverview, toast, navigate]);

  if (profile === undefined) {
    return (
      <div className="page">
        <PageHeader eyebrow="Prepare" title="Practice" />
        <SkeletonResults label="Loading" />
      </div>
    );
  }

  if (profile === null) {
    return (
      <div className="page">
        <PageHeader eyebrow="Prepare" title="Practice" />
        <div className="card">
          <EmptyState
            icon={Settings}
            title="Pick your career track first"
            description="Choose software engineer or cybersecurity and your interview date. Practice follows that syllabus."
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

  const isBusy = session.kind === "loading";
  const startLabel = { quiz: "Start quiz", concept: "Start lesson", coding: "Get a problem", lab: "Start lab" }[mode];

  return (
    <div className="page">
      <PageHeader
        eyebrow={`Prepare · ${profile.track_name}`}
        title="Practice"
        description="Every question, lesson and problem is new — nothing you've already seen is repeated — and everything is saved to your notebook."
      />

      <section className="card practice-setup" aria-label="Practice setup">
        <div className="segmented segmented--three" role="radiogroup" aria-label="Practice mode">
          {modeOptions.map(({ value, label, hint, icon: Icon }) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={mode === value}
              className={`segmented__option${mode === value ? " segmented__option--selected" : ""}`}
              onClick={() => updateParams({ mode: value })}
              disabled={isBusy}
            >
              <span className="segmented__label practice-setup__mode-label">
                <Icon size={16} aria-hidden="true" /> {label}
              </span>
              <span className="segmented__hint">{hint}</span>
            </button>
          ))}
        </div>

        <div className="practice-setup__row">
          {track ? (
            <SubtopicSelect track={track} overview={overview} value={subtopicId} onChange={(id) => updateParams({ subtopic: id })} />
          ) : (
            <LoadingSpinner label="Loading syllabus…" />
          )}
          <ActiveModelSelector />
        </div>

        <div className="button-row">
          <button
            type="button"
            className="button button--primary button--large"
            onClick={() => void start()}
            disabled={isBusy || !isReady || !track}
            title={isReady ? undefined : "Connect a model first"}
          >
            <Play size={16} /> {startLabel}
          </button>
          {blockId && <span className="muted">Part of today's plan — it's ticked off when you finish.</span>}
        </div>
      </section>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {session.kind === "loading" && (
        <div className="card practice-loading">
          <LoadingSpinner label={session.message} />
          <p className="muted">This can take up to a minute, depending on the model.</p>
        </div>
      )}

      {session.kind === "quiz" && (
        <QuizRunner key={sessionKey} quiz={session.quiz} onFinished={handleFinished} onAnotherQuiz={() => void start("quiz")} />
      )}

      {session.kind === "concept" && (
        <ConceptSession
          key={sessionKey}
          lesson={session.lesson}
          agent={agent}
          agentLabel={agentLabel}
          isReady={isReady}
          onGraded={handleFinished}
          onNextConcept={() => void start("concept")}
        />
      )}

      {session.kind === "coding" && (
        <CodingSession
          key={sessionKey}
          problem={session.problem}
          agent={agent}
          agentLabel={agentLabel}
          onFinished={handleFinished}
          onNextProblem={() => void start("coding")}
        />
      )}

      {session.kind === "lab" && (
        <LabSession
          key={sessionKey}
          lab={session.lab}
          agent={agent}
          agentLabel={agentLabel}
          onFinished={handleFinished}
          onNextLab={() => void start("lab")}
        />
      )}
    </div>
  );
}
