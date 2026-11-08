const LABELS: Record<number, string> = { 1: "Easy", 2: "Medium", 3: "Hard" };

export function DifficultyPill({ difficulty }: { difficulty: number }) {
  return <span className={`difficulty-pill difficulty-pill--${difficulty}`}>{LABELS[difficulty] ?? "—"}</span>;
}
