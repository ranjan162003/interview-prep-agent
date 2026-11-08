import type {
  AgentChoice,
  ConceptLesson,
  ExplainResult,
  LessonChatMessage,
  PracticeOverview,
  QuizAnswerResult,
  QuizSet,
} from "../types/practice.types";
import { requestJson } from "./httpClient";

const post = (body: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(body) });

export const practiceApi = {
  getOverview: () => requestJson<PracticeOverview>("/api/practice/overview"),

  createQuiz: (agent: AgentChoice, subtopicId: string | null, questionCount = 5) =>
    requestJson<QuizSet>("/api/practice/quiz", post({ ...agent, subtopic_id: subtopicId, question_count: questionCount })),

  answerQuizQuestion: (itemId: number, selectedIndex: number) =>
    requestJson<QuizAnswerResult>(`/api/practice/quiz/${itemId}/answer`, post({ selected_index: selectedIndex })),

  createConceptLesson: (agent: AgentChoice, subtopicId: string | null) =>
    requestJson<ConceptLesson>("/api/practice/concept", post({ ...agent, subtopic_id: subtopicId })),

  gradeExplanation: (itemId: number, agent: AgentChoice, answer: string) =>
    requestJson<ExplainResult>(`/api/practice/concept/${itemId}/explain`, post({ ...agent, answer })),

  getLessonChat: (itemId: number) => requestJson<LessonChatMessage[]>(`/api/practice/concept/${itemId}/chat`),

  /** Returns the saved question and the teacher's reply. */
  askTeacher: (itemId: number, agent: AgentChoice, message: string) =>
    requestJson<LessonChatMessage[]>(`/api/practice/concept/${itemId}/chat`, post({ ...agent, message })),
};
