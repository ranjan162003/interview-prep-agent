import { ArrowRight, RotateCcw, Send } from "lucide-react";
import { useState, type FormEvent } from "react";

import { practiceApi } from "../../api/practiceApi";
import type { AgentChoice, ConceptLesson, ExplainResult } from "../../types/practice.types";
import { ErrorAlert } from "../common/ErrorAlert";
import { LoadingSpinner } from "../common/LoadingSpinner";
import { Markdown } from "../common/Markdown";
import { DifficultyPill } from "./DifficultyPill";
import { GradeCard } from "./GradeCard";
import { LessonChat } from "./LessonChat";

const MIN_ANSWER_LENGTH = 20;

interface ConceptSessionProps {
  lesson: ConceptLesson;
  agent: AgentChoice;
  agentLabel: string;
  isReady: boolean;
  onGraded: () => void;
  onNextConcept: () => void;
}

/**
 * Read a lesson (with the teacher chat beside it for doubts), explain it back in your own words,
 * then get graded against the rubric.
 */
export function ConceptSession({ lesson, agent, agentLabel, isReady, onGraded, onNextConcept }: ConceptSessionProps) {
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<ExplainResult | null>(null);
  const [isGrading, setIsGrading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setIsGrading(true);
    setError(null);
    try {
      setResult(await practiceApi.gradeExplanation(lesson.item_id, agent, answer));
      onGraded();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsGrading(false);
    }
  }

  function tryAgain() {
    setResult(null);
    setAnswer("");
  }

  return (
    <div className="lesson-layout">
      <article className="card lesson lesson-layout__lesson" aria-label="Lesson">
        <div className="quiz__meta">
          <span className="page-header__eyebrow">
            {lesson.subtopic.topic_name} · {lesson.subtopic.subtopic_name}
          </span>
          <DifficultyPill difficulty={lesson.subtopic.difficulty} />
          {lesson.is_review && <span className="review-pill">Review</span>}
        </div>
        <h2 className="lesson__title">{lesson.title}</h2>
        <Markdown text={lesson.lesson_markdown} className="lesson__body" />
      </article>

      <div className="lesson-layout__chat">
        <LessonChat itemId={lesson.item_id} agent={agent} agentLabel={agentLabel} isReady={isReady} />
      </div>

      {result ? (
        <div className="lesson-layout__answer">
          <GradeCard result={result} />
          <div className="button-row">
            <button type="button" className="button button--ghost" onClick={tryAgain}>
              <RotateCcw size={16} /> Answer again
            </button>
            <button type="button" className="button button--primary" onClick={onNextConcept}>
              Next concept <ArrowRight size={16} />
            </button>
          </div>
        </div>
      ) : (
        <form className="card explain lesson-layout__answer" onSubmit={handleSubmit}>
          <span className="page-header__eyebrow">Explain it back</span>
          <h3 className="explain__prompt">{lesson.explain_prompt}</h3>
          <p className="muted">
            Answer as you would in the interview, in your own words. You'll be graded on correctness, depth, clarity and
            structure.
          </p>
          <textarea
            className="input explain__answer"
            rows={8}
            value={answer}
            onChange={(event) => setAnswer(event.target.value)}
            placeholder="Type your explanation…"
            disabled={isGrading}
            aria-label="Your explanation"
          />
          {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}
          {isGrading ? (
            <LoadingSpinner label={`${agentLabel} is grading your answer…`} />
          ) : (
            <div className="button-row">
              <button
                type="submit"
                className="button button--primary"
                disabled={answer.trim().length < MIN_ANSWER_LENGTH}
                title={answer.trim().length < MIN_ANSWER_LENGTH ? "Write a little more first" : undefined}
              >
                <Send size={16} /> Submit for grading
              </button>
            </div>
          )}
        </form>
      )}
    </div>
  );
}
