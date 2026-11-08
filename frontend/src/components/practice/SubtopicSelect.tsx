import type { CoverageStatus, PracticeOverview } from "../../types/practice.types";
import type { Track } from "../../types/track.types";

const STATUS_LABELS: Record<CoverageStatus, string> = {
  not_started: "",
  in_progress: " · in progress",
  covered: " · covered ✓",
  weak: " · needs review",
};

interface SubtopicSelectProps {
  track: Track;
  overview: PracticeOverview | null;
  /** "" means "next for me". */
  value: string;
  onChange: (subtopicId: string) => void;
}

/** Subtopics grouped by topic, each labelled with how far the learner has got. */
export function SubtopicSelect({ track, overview, value, onChange }: SubtopicSelectProps) {
  const coverage = new Map(overview?.subtopics.map((s) => [s.subtopic_id, s]) ?? []);
  const nextId = overview?.next_subtopic_id;
  const nextName = track.topics.flatMap((t) => t.subtopics).find((s) => s.id === nextId)?.name;

  return (
    <label className="field">
      <span className="field__label">Subtopic</span>
      <select className="input" value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">{nextName ? `Next for me: ${nextName}` : "Next for me"}</option>
        {track.topics.map((topic) => (
          <optgroup key={topic.id} label={topic.name}>
            {topic.subtopics.map((subtopic) => {
              const item = coverage.get(subtopic.id);
              return (
                <option key={subtopic.id} value={subtopic.id}>
                  {subtopic.name}
                  {item ? STATUS_LABELS[item.status] : ""}
                </option>
              );
            })}
          </optgroup>
        ))}
      </select>
    </label>
  );
}
