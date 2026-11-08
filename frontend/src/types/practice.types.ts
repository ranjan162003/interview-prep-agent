// Mirrors backend/app/schemas/practice_schemas.py

import type { ProviderId } from "./provider.types";

export type LearningStatus = "new" | "learnt" | "weak" | "mastered";
export type CoverageStatus = "not_started" | "in_progress" | "covered" | "weak";

export interface AgentChoice {
  provider_id: ProviderId;
  model_name: string | null;
}

export interface SubtopicRef {
  track_id: string;
  topic_id: string;
  topic_name: string;
  subtopic_id: string;
  subtopic_name: string;
  difficulty: number;
}

export interface SubtopicCoverage {
  topic_id: string;
  subtopic_id: string;
  concepts_taught: number;
  key_concept_count: number;
  quiz_answered: number;
  quiz_correct: number;
  status: CoverageStatus;
}

export interface PracticeOverview {
  track_id: string;
  next_subtopic_id: string | null;
  subtopics: SubtopicCoverage[];
}

export interface QuizQuestion {
  item_id: number;
  question: string;
  options: string[];
}

export interface QuizSet {
  subtopic: SubtopicRef;
  questions: QuizQuestion[];
  duplicates_skipped: number;
}

export interface QuizAnswerResult {
  item_id: number;
  selected_index: number;
  correct: boolean;
  correct_index: number;
  explanation: string;
  key_point: string;
  status: LearningStatus;
}

export interface ConceptLesson {
  item_id: number;
  subtopic: SubtopicRef;
  focus_concept: string;
  is_review: boolean;
  title: string;
  lesson_markdown: string;
  explain_prompt: string;
}

export interface GradedCriterion {
  name: string;
  score: number;
  comment: string;
}

export interface GradedEvidence {
  quote: string;
  comment: string;
}

export interface ExplainResult {
  item_id: number;
  attempt_id: number;
  score: number;
  status: LearningStatus;
  criteria: GradedCriterion[];
  covered_points: string[];
  missed_points: string[];
  evidence: GradedEvidence[];
  improved_answer: string;
  overall_feedback: string;
  key_points: string[];
  reference_answer: string;
}

export interface LessonChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}
