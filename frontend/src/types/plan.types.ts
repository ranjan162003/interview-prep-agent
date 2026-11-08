// Mirrors backend/app/schemas/plan_schemas.py and progress_schemas.py

import type { CoverageStatus, LearningStatus } from "./practice.types";

export type BlockKind = "quiz" | "concept" | "coding" | "lab" | "mock" | "recap";
export type MockKind = "technical" | "behavioural" | "mixed";

export interface PlanBlock {
  id: string;
  kind: BlockKind;
  title: string;
  minutes: number;
  subtopic_id: string | null;
  subtopic_name: string | null;
  topic_name: string | null;
  reason: string;
  is_review: boolean;
  mock_kind: MockKind | null;
  done: boolean;
}

export interface DailyPlan {
  plan_date: string;
  track_id: string;
  daily_minutes: number;
  blocks: PlanBlock[];
  minutes_done: number;
  days_until_interview: number | null;
}

export interface RecapItem {
  item_id: number;
  kind: string;
  title: string;
  subtopic_name: string;
  score: number | null;
  status: LearningStatus;
  key_points: string[];
}

export interface DailyRecap {
  plan_date: string;
  minutes_done: number;
  items: RecapItem[];
  weak_subtopics: string[];
  next_up: string | null;
  reviews_due_tomorrow: number;
}

export interface ActivityDay {
  day: string;
  answers: number;
  minutes: number;
}

export interface SubtopicMastery {
  subtopic_id: string;
  name: string;
  difficulty: number;
  mastery: number | null;
  coverage: number;
  status: CoverageStatus;
  next_review_on: string | null;
}

export interface TopicMastery {
  topic_id: string;
  name: string;
  mastery: number | null;
  coverage: number;
  subtopics: SubtopicMastery[];
}

export interface Readiness {
  score: number;
  label: string;
  coverage_percent: number;
  mastery_percent: number | null;
  mock_average: number | null;
}

export interface Progress {
  track_id: string;
  track_name: string;
  days_until_interview: number | null;
  streak_days: number;
  longest_streak: number;
  minutes_total: number;
  minutes_this_week: number;
  items_seen: number;
  items_learnt: number;
  answers_total: number;
  average_recent_score: number | null;
  reviews_due: number;
  readiness: Readiness;
  activity: ActivityDay[];
  topics: TopicMastery[];
}
