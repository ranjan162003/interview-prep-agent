/** The big round score (0–100) used on every graded result. */
export function ScoreRing({ score, size = "large" }: { score: number; size?: "large" | "small" }) {
  const tone = score >= 70 ? "good" : score >= 40 ? "warning" : "critical";
  return (
    <div className={`grade__score grade__score--${tone}${size === "small" ? " grade__score--small" : ""}`}>
      <span className="grade__score-value">{Math.round(score)}</span>
      <span className="grade__score-max">/100</span>
    </div>
  );
}
