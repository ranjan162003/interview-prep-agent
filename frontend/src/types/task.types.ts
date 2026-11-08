// Mirrors backend/app/schemas/task_schemas.py, notebook_schemas.py, mock_schemas.py, coach_schemas.py

import type { GradedCriterion, LearningStatus, LessonChatMessage, SubtopicRef } from "./practice.types";
import type { MockKind } from "./plan.types";

// ---------- coding ----------

export type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };

export interface CodingTest {
  args: JsonValue[];
  expected: JsonValue;
}

export interface CodingProblem {
  item_id: number;
  subtopic: SubtopicRef;
  title: string;
  statement_markdown: string;
  function_name: string;
  starter_code: string;
  tests: CodingTest[];
  reference_solution: string;
  hint_count: number;
  hints_used: number;
}

export interface Hint {
  level: number;
  hint: string;
  hints_used: number;
}

export interface TestOutcome {
  passed: boolean;
  args: JsonValue[];
  expected: JsonValue;
  got?: JsonValue;
  error?: string | null;
  stdout?: string;
}

export interface CodeReview {
  correctness: string;
  time_complexity: string;
  space_complexity: string;
  complexity_comment: string;
  edge_cases_missed: string[];
  style_comments: string[];
  improved_code: string;
  overall_feedback: string;
}

export interface CodeReviewResult {
  item_id: number;
  score: number;
  status: LearningStatus;
  passed: number;
  total: number;
  hints_used: number;
  review: CodeReview;
  reference_solution: string;
  key_points: string[];
}

// ---------- security labs ----------

export interface SecurityLab {
  item_id: number;
  subtopic: SubtopicRef;
  title: string;
  scenario_markdown: string;
  artifact_type: string;
  artifact: string;
  tasks: { question: string }[];
}

export interface LabTaskResult {
  question: string;
  your_answer: string;
  expected_answer: string;
  score: number;
  comment: string;
  missed: string[];
}

export interface LabResult {
  item_id: number;
  score: number;
  status: LearningStatus;
  tasks: LabTaskResult[];
  overall_feedback: string;
  walkthrough_markdown: string;
  key_points: string[];
}

// ---------- notebook ----------

export interface NotebookEntry {
  item_id: number;
  kind: string;
  title: string;
  track_id: string;
  topic_id: string;
  topic_name: string;
  subtopic_id: string;
  subtopic_name: string;
  is_review: boolean;
  status: LearningStatus;
  best_score: number | null;
  last_score: number | null;
  attempts: number;
  key_points: string[];
  has_chat: boolean;
  created_at: string;
}

export interface NotebookPage {
  track_id: string;
  entries: NotebookEntry[];
  total: number;
  counts_by_kind: Record<string, number>;
}

export interface NotebookAttempt {
  created_at: string;
  score: number;
  answer_text: string;
  selected_index: number | null;
  grade: Record<string, unknown> | null;
}

export interface NotebookItemDetail extends NotebookEntry {
  content: Record<string, unknown>;
  reference_answer: string | null;
  rubric: Record<string, unknown> | null;
  history: NotebookAttempt[];
  chat: LessonChatMessage[];
}

export interface NotebookFilters {
  kind?: string;
  status?: string;
  topic_id?: string;
  q?: string;
  date_from?: string;
  date_to?: string;
}

// ---------- mock interview ----------

export interface MockTurn {
  role: "interviewer" | "candidate";
  content: string;
  question_index: number;
  created_at: string;
}

export interface MockQuestionGrade {
  question_index: number;
  item_id: number;
  question: string;
  subtopic_name: string;
  score: number;
  criteria: GradedCriterion[];
  covered_points: string[];
  missed_points: string[];
  improved_answer: string;
  overall_feedback: string;
}

export interface MockSession {
  id: number;
  kind: MockKind;
  status: "in_progress" | "finished";
  question_count: number;
  current_index: number;
  turns: MockTurn[];
  grades: MockQuestionGrade[];
  overall_score: number | null;
  created_at: string;
}

export interface MockSessionSummary {
  id: number;
  kind: MockKind;
  status: "in_progress" | "finished";
  question_count: number;
  overall_score: number | null;
  first_question: string;
  created_at: string;
}

// ---------- coach ----------

export interface CoachMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  tools_used: string[];
  created_at: string;
}

export interface CoachConversationSummary {
  id: number;
  title: string;
  updated_at: string;
}

export interface CoachConversation extends CoachConversationSummary {
  messages: CoachMessage[];
}

export interface CoachReply {
  conversation: CoachConversationSummary;
  messages: CoachMessage[];
}
