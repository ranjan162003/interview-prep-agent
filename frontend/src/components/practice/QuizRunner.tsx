import { ArrowRight, CheckCircle2, Lightbulb, RotateCcw, XCircle } from "lucide-react";
import { useState } from "react";

import { practiceApi } from "../../api/practiceApi";
import type { QuizAnswerResult, QuizSet } from "../../types/practice.types";
import { ErrorAlert } from "../common/ErrorAlert";
import { renderInline } from "../common/Markdown";
import { DifficultyPill } from "./DifficultyPill";

interface QuizRunnerProps {
  quiz: QuizSet;
  onFinished: () => void;
  onAnotherQuiz: () => void;
}

/** One question at a time: pick an option, see right/wrong with the explanation, then move on. */
export function QuizRunner({ quiz, onFinished, onAnotherQuiz }: QuizRunnerProps) {
  const [index, setIndex] = useState(0);
  const [results, setResults] = useState<Record<number, QuizAnswerResult>>({});
  const [pendingIndex, setPendingIndex] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDone, setIsDone] = useState(false);

  const question = quiz.questions[index];
  const result = question ? results[question.item_id] : undefined;
  const correctCount = Object.values(results).filter((r) => r.correct).length;

  async function choose(optionIndex: number) {
    if (result || pendingIndex !== null) return;
    setPendingIndex(optionIndex);
    setError(null);
    try {
      const answer = await practiceApi.answerQuizQuestion(question.item_id, optionIndex);
      setResults((current) => ({ ...current, [question.item_id]: answer }));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setPendingIndex(null);
    }
  }

  function next() {
    if (index + 1 < quiz.questions.length) {
      setIndex(index + 1);
    } else {
      setIsDone(true);
      onFinished();
    }
  }

  if (isDone) {
    const total = quiz.questions.length;
    return (
      <section className="card quiz-summary" aria-label="Quiz result">
        <span className="page-header__eyebrow">Warm-up quiz · {quiz.subtopic.subtopic_name}</span>
        <p className="quiz-summary__score">
          {correctCount}
          <span className="muted">/{total}</span>
        </p>
        <p className="muted">
          {correctCount === total
            ? "Perfect round."
            : `${total - correctCount} to review — they're saved in your notebook and will come back.`}
        </p>
        <div>
          <h3 className="card__title">Key points from this quiz</h3>
          <ul className="key-points">
            {quiz.questions.map((q) => {
              const r = results[q.item_id];
              return (
                <li key={q.item_id} className={r && !r.correct ? "key-points__item--missed" : undefined}>
                  {r?.correct ? <CheckCircle2 size={16} aria-label="Correct" /> : <XCircle size={16} aria-label="Wrong" />}
                  <span>{renderInline(r?.key_point || q.question)}</span>
                </li>
              );
            })}
          </ul>
        </div>
        <div className="button-row">
          <button type="button" className="button button--primary" onClick={onAnotherQuiz}>
            <RotateCcw size={16} /> Another quiz
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="card quiz" aria-label="Quiz">
      <div className="quiz__meta">
        <span className="page-header__eyebrow">
          {quiz.subtopic.topic_name} · {quiz.subtopic.subtopic_name}
        </span>
        <DifficultyPill difficulty={quiz.subtopic.difficulty} />
        <span className="quiz__progress">
          Question {index + 1} of {quiz.questions.length}
        </span>
      </div>
      <div className="quiz__bar" aria-hidden="true">
        <span style={{ width: `${((index + (result ? 1 : 0)) / quiz.questions.length) * 100}%` }} />
      </div>

      <h2 className="quiz__question">{renderInline(question.question)}</h2>

      <div className="quiz__options" role="group" aria-label="Answer options">
        {question.options.map((option, optionIndex) => {
          let state = "";
          if (result) {
            if (optionIndex === result.correct_index) state = " quiz-option--correct";
            else if (optionIndex === result.selected_index) state = " quiz-option--wrong";
            else state = " quiz-option--dimmed";
          } else if (pendingIndex === optionIndex) {
            state = " quiz-option--pending";
          }
          return (
            <button
              key={optionIndex}
              type="button"
              className={`quiz-option${state}`}
              onClick={() => void choose(optionIndex)}
              disabled={Boolean(result) || pendingIndex !== null}
            >
              <span className="quiz-option__letter">{String.fromCharCode(65 + optionIndex)}</span>
              <span>{renderInline(option)}</span>
            </button>
          );
        })}
      </div>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

      {result && (
        <div className={`quiz__feedback${result.correct ? " quiz__feedback--correct" : " quiz__feedback--wrong"}`} role="status">
          <p className="quiz__verdict">
            {result.correct ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
            {result.correct ? "Correct" : "Not quite"}
          </p>
          <p>{renderInline(result.explanation)}</p>
          {result.key_point && (
            <p className="quiz__key-point">
              <Lightbulb size={16} aria-hidden="true" /> <span>{renderInline(result.key_point)}</span>
            </p>
          )}
          <div className="button-row">
            <button type="button" className="button button--primary" onClick={next}>
              {index + 1 < quiz.questions.length ? "Next question" : "See results"} <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
