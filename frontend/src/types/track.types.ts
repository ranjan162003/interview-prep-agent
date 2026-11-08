// Mirrors backend/app/schemas/track_schemas.py and profile_schemas.py

export interface Subtopic {
  id: string;
  name: string;
  difficulty: 1 | 2 | 3;
  key_concepts: string[];
}

export interface Topic {
  id: string;
  name: string;
  description: string;
  subtopics: Subtopic[];
}

export interface Track {
  id: string;
  name: string;
  position: number;
  description: string;
  has_coding_problems: boolean;
  topics: Topic[];
}

export interface TrackSummary {
  id: string;
  name: string;
  description: string;
  has_coding_problems: boolean;
  topic_count: number;
  subtopic_count: number;
}

export type DailyMinutes = 60 | 120;

export interface ProfileUpdate {
  track_id: string;
  /** ISO date (YYYY-MM-DD), or null for "no date yet". */
  interview_date: string | null;
  daily_minutes: DailyMinutes;
}

export interface Profile extends ProfileUpdate {
  track_name: string;
  days_until_interview: number | null;
  updated_at: string;
}
