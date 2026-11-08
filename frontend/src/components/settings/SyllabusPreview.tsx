import { useEffect, useState } from "react";

import { trackApi } from "../../api/trackApi";
import type { Track } from "../../types/track.types";
import { ErrorAlert } from "../common/ErrorAlert";
import { SkeletonList } from "../common/Skeleton";
import { DifficultyPill } from "../practice/DifficultyPill";

/** The selected track's topics and subtopics, in the order the planner works through them. */
export function SyllabusPreview({ trackId }: { trackId: string }) {
  const [track, setTrack] = useState<Track | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setTrack(null);
    setError(null);
    trackApi
      .getTrack(trackId)
      .then((loaded) => !cancelled && setTrack(loaded))
      .catch((err: unknown) => !cancelled && setError(err instanceof Error ? err.message : String(err)));
    return () => {
      cancelled = true;
    };
  }, [trackId]);

  return (
    <section className="card syllabus" aria-label="Syllabus">
      <div className="card__title-row">
        <h2 className="card__title">Syllabus{track ? `: ${track.name}` : ""}</h2>
      </div>
      <p className="muted syllabus__intro">You'll work through these in order. Weak topics come back for review.</p>
      {error && <ErrorAlert message={error} />}
      {!track && !error && <SkeletonList rows={5} label="Loading syllabus" />}
      {track?.topics.map((topic, index) => (
        <details key={topic.id} className="syllabus__topic" open={index === 0}>
          <summary>
            <span className="syllabus__topic-name">{topic.name}</span>
            <span className="muted">{topic.subtopics.length} subtopics</span>
          </summary>
          <p className="muted syllabus__topic-description">{topic.description}</p>
          <ul className="syllabus__subtopics">
            {topic.subtopics.map((subtopic) => (
              <li key={subtopic.id}>
                <span>{subtopic.name}</span>
                <DifficultyPill difficulty={subtopic.difficulty} />
              </li>
            ))}
          </ul>
        </details>
      ))}
    </section>
  );
}
