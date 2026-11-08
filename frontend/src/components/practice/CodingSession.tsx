import Editor from "@monaco-editor/react";
import { ArrowRight, CheckCircle2, Lightbulb, Loader2, Play, Send, XCircle } from "lucide-react";
import { useEffect, useState } from "react";

import { taskApi } from "../../api/studyApi";
import { useColorScheme } from "../../hooks/useColorScheme";
import type { AgentChoice } from "../../types/practice.types";
import type { CodeReviewResult, CodingProblem, CodingTest, JsonValue, TestOutcome } from "../../types/task.types";
import { pythonRunner } from "../../utils/pythonRunner";
import { ErrorAlert } from "../common/ErrorAlert";
import { LoadingSpinner } from "../common/LoadingSpinner";
import { Markdown, renderInline } from "../common/Markdown";
import { DifficultyPill } from "./DifficultyPill";
import { ScoreRing } from "./ScoreRing";

interface CodingSessionProps {
  problem: CodingProblem;
  agent: AgentChoice;
  agentLabel: string;
  onFinished: () => void;
  onNextProblem: () => void;
}

const show = (value: JsonValue | undefined) => (value === undefined ? "—" : JSON.stringify(value));

/**
 * Solve a problem in the browser: Monaco editor, tests run locally with Pyodide, three levels
 * of hints, then an AI code review. Tests decide correctness; the model only explains.
 */
export function CodingSession({ problem, agent, agentLabel, onFinished, onNextProblem }: CodingSessionProps) {
  const scheme = useColorScheme();
  const [code, setCode] = useState(problem.starter_code);
  const [tests, setTests] = useState<CodingTest[] | null>(null);
  const [droppedTests, setDroppedTests] = useState(0);
  const [results, setResults] = useState<TestOutcome[] | null>(null);
  const [hints, setHints] = useState<string[]>([]);
  const [busy, setBusy] = useState<"running" | "submitting" | "hint" | null>(null);
  const [review, setReview] = useState<CodeReviewResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Check the model's tests against its own reference solution first, and drop any that are wrong.
  useEffect(() => {
    let cancelled = false;
    pythonRunner.warmUp();
    pythonRunner
      .run(problem.reference_solution, problem.function_name, problem.tests)
      .then((outcomes) => {
        if (cancelled) return;
        const valid = problem.tests.filter((_, i) => outcomes[i]?.passed);
        setTests(valid.length ? valid : problem.tests);
        setDroppedTests(valid.length ? problem.tests.length - valid.length : 0);
      })
      .catch(() => !cancelled && setTests(problem.tests));
    return () => {
      cancelled = true;
    };
  }, [problem]);

  async function runTests(): Promise<TestOutcome[] | null> {
    if (!tests) return null;
    setError(null);
    try {
      const outcomes = await pythonRunner.run(code, problem.function_name, tests);
      setResults(outcomes);
      return outcomes;
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      return null;
    }
  }

  async function handleRun() {
    setBusy("running");
    await runTests();
    setBusy(null);
  }

  async function handleSubmit() {
    setBusy("submitting");
    const outcomes = await runTests();
    if (outcomes) {
      try {
        setReview(await taskApi.submitCode(problem.item_id, agent, code, outcomes));
        onFinished();
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    }
    setBusy(null);
  }

  async function handleHint() {
    setBusy("hint");
    try {
      const hint = await taskApi.revealHint(problem.item_id);
      setHints((current) => (current.includes(hint.hint) ? current : [...current, hint.hint]));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
    setBusy(null);
  }

  const passed = results?.filter((r) => r.passed).length ?? 0;
  const hintsLeft = problem.hint_count - Math.max(hints.length, problem.hints_used);

  return (
    <div className="coding">
      <article className="card coding__statement" aria-label="Problem">
        <div className="quiz__meta">
          <span className="page-header__eyebrow">
            {problem.subtopic.topic_name} · {problem.subtopic.subtopic_name}
          </span>
          <DifficultyPill difficulty={problem.subtopic.difficulty} />
        </div>
        <h2 className="lesson__title">{problem.title}</h2>
        <Markdown text={problem.statement_markdown} className="lesson__body" />

        <div className="coding__hints">
          {hints.map((hint, i) => (
            <p key={i} className="quiz__key-point">
              <Lightbulb size={16} aria-hidden="true" />
              <span>
                <strong>Hint {i + 1}:</strong> {renderInline(hint)}
              </span>
            </p>
          ))}
          {!review && hintsLeft > 0 && (
            <button type="button" className="button button--ghost button--small" onClick={() => void handleHint()} disabled={busy !== null}>
              <Lightbulb size={14} /> {hints.length ? "Next hint" : "Get a hint"} ({hintsLeft} left, −10 points each)
            </button>
          )}
        </div>
      </article>

      <section className="card coding__workspace" aria-label="Your solution">
        <div className="coding__editor">
          <Editor
            height="360px"
            defaultLanguage="python"
            value={code}
            onChange={(value) => setCode(value ?? "")}
            theme={scheme === "dark" ? "vs-dark" : "light"}
            options={{ minimap: { enabled: false }, fontSize: 14, scrollBeyondLastLine: false, tabSize: 4, automaticLayout: true }}
            loading={<LoadingSpinner label="Loading editor…" />}
          />
        </div>

        <div className="button-row">
          <button type="button" className="button button--ghost" onClick={() => void handleRun()} disabled={busy !== null || !tests}>
            {busy === "running" ? <Loader2 size={16} className="spin" /> : <Play size={16} />} Run tests
          </button>
          <button type="button" className="button button--primary" onClick={() => void handleSubmit()} disabled={busy !== null || !tests}>
            {busy === "submitting" ? <Loader2 size={16} className="spin" /> : <Send size={16} />} Submit for review
          </button>
          {!tests && <span className="muted coding__note">Loading Python in your browser…</span>}
          {droppedTests > 0 && (
            <span className="muted coding__note">
              {droppedTests} generated test{droppedTests > 1 ? "s were" : " was"} wrong and skipped.
            </span>
          )}
        </div>

        {busy === "submitting" && <LoadingSpinner label={`${agentLabel} is reviewing your code…`} />}
        {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

        {results && (
          <div className="test-results" aria-label="Test results">
            <p className={`test-results__summary${passed === results.length ? " test-results__summary--pass" : ""}`}>
              {passed}/{results.length} tests passed
            </p>
            <ul>
              {results.map((result, i) => (
                <li key={i} className={result.passed ? "test-result--pass" : "test-result--fail"}>
                  {result.passed ? <CheckCircle2 size={16} aria-label="Passed" /> : <XCircle size={16} aria-label="Failed" />}
                  <code className="test-result__call">
                    {problem.function_name}({result.args.map((a) => show(a)).join(", ")})
                  </code>
                  {!result.passed && (
                    <span className="test-result__detail">
                      {result.error ? (
                        <>error: {result.error}</>
                      ) : (
                        <>
                          expected <code>{show(result.expected)}</code>, got <code>{show(result.got)}</code>
                        </>
                      )}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {review && (
        <>
          <CodeReviewCard result={review} />
          <div className="button-row">
            <button type="button" className="button button--primary" onClick={onNextProblem}>
              Next problem <ArrowRight size={16} />
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function CodeReviewCard({ result }: { result: CodeReviewResult }) {
  const { review } = result;
  return (
    <section className="card grade" aria-label="Code review">
      <div className="grade__header">
        <ScoreRing score={result.score} />
        <div>
          <p className="grade__status">
            {result.passed}/{result.total} tests passed
            {result.hints_used ? ` · ${result.hints_used} hint${result.hints_used > 1 ? "s" : ""} used` : ""}
          </p>
          <p className="muted">{renderInline(review.overall_feedback)}</p>
        </div>
      </div>

      <div className="grade__points">
        <div>
          <h3 className="card__title">Correctness</h3>
          <p>{renderInline(review.correctness)}</p>
        </div>
        <div>
          <h3 className="card__title">
            Complexity: <code>{review.time_complexity}</code> time, <code>{review.space_complexity}</code> space
          </h3>
          <p>{renderInline(review.complexity_comment)}</p>
        </div>
      </div>

      {(review.edge_cases_missed.length > 0 || review.style_comments.length > 0) && (
        <div className="grade__points">
          {review.edge_cases_missed.length > 0 && (
            <div>
              <h3 className="card__title">Edge cases missed</h3>
              <ul className="key-points">
                {review.edge_cases_missed.map((item) => (
                  <li key={item} className="key-points__item--missed">
                    <XCircle size={16} aria-hidden="true" />
                    <span>{renderInline(item)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {review.style_comments.length > 0 && (
            <div>
              <h3 className="card__title">Style</h3>
              <ul className="key-points">
                {review.style_comments.map((item) => (
                  <li key={item}>
                    <Lightbulb size={16} aria-hidden="true" />
                    <span>{renderInline(item)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <details className="grade__details" open>
        <summary>Improved version of your code</summary>
        <pre className="markdown__code">
          <code>{review.improved_code}</code>
        </pre>
      </details>
      <details className="grade__details">
        <summary>
          <Lightbulb size={16} aria-hidden="true" /> Pattern to remember and reference solution
        </summary>
        <ul className="key-points">
          {result.key_points.map((point) => (
            <li key={point}>
              <Lightbulb size={16} aria-hidden="true" />
              <span>{renderInline(point)}</span>
            </li>
          ))}
        </ul>
        <pre className="markdown__code">
          <code>{result.reference_solution}</code>
        </pre>
      </details>
    </section>
  );
}
