// Plans, progress, coding problems, labs, notebook, mock interviews and the coach.

import type { AgentChoice } from "../types/practice.types";
import type { DailyPlan, DailyRecap, MockKind, Progress } from "../types/plan.types";
import type {
  CodeReviewResult,
  CodingProblem,
  CoachConversation,
  CoachConversationSummary,
  CoachReply,
  Hint,
  LabResult,
  MockSession,
  MockSessionSummary,
  NotebookFilters,
  NotebookItemDetail,
  NotebookPage,
  SecurityLab,
  TestOutcome,
} from "../types/task.types";
import { requestJson } from "./httpClient";

const post = (body?: unknown): RequestInit => ({ method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

function queryString(params: Record<string, string | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) if (value) search.set(key, value);
  const text = search.toString();
  return text ? `?${text}` : "";
}

export const planApi = {
  getToday: () => requestJson<DailyPlan>("/api/plans/today"),
  regenerate: () => requestJson<DailyPlan>("/api/plans/today/regenerate", post()),
  completeBlock: (blockId: string) =>
    requestJson<DailyPlan>(`/api/plans/today/blocks/${encodeURIComponent(blockId)}/complete`, post()),
  getRecap: () => requestJson<DailyRecap>("/api/plans/today/recap"),
};

export const progressApi = {
  get: () => requestJson<Progress>("/api/progress"),
};

export const taskApi = {
  createCodingProblem: (agent: AgentChoice, subtopicId: string | null) =>
    requestJson<CodingProblem>("/api/practice/coding", post({ ...agent, subtopic_id: subtopicId })),
  revealHint: (itemId: number) => requestJson<Hint>(`/api/practice/coding/${itemId}/hint`, post()),
  submitCode: (itemId: number, agent: AgentChoice, code: string, results: TestOutcome[]) =>
    requestJson<CodeReviewResult>(`/api/practice/coding/${itemId}/submit`, post({ ...agent, code, results })),
  createLab: (agent: AgentChoice, subtopicId: string | null) =>
    requestJson<SecurityLab>("/api/practice/lab", post({ ...agent, subtopic_id: subtopicId })),
  submitLab: (itemId: number, agent: AgentChoice, answers: string[]) =>
    requestJson<LabResult>(`/api/practice/lab/${itemId}/submit`, post({ ...agent, answers })),
};

export const notebookApi = {
  list: (filters: NotebookFilters) =>
    requestJson<NotebookPage>(`/api/notebook${queryString({ ...filters })}`),
  getItem: (itemId: number) => requestJson<NotebookItemDetail>(`/api/notebook/items/${itemId}`),
  /** A plain link (not fetch) so the browser downloads the PDF itself. */
  exportUrl: (filters: NotebookFilters, mode: "full" | "notes") =>
    `${import.meta.env.VITE_API_BASE_URL ?? ""}/api/notebook/export.pdf${queryString({ ...filters, mode })}`,
};

export const mockApi = {
  list: () => requestJson<MockSessionSummary[]>("/api/mock/sessions"),
  get: (sessionId: number) => requestJson<MockSession>(`/api/mock/sessions/${sessionId}`),
  start: (agent: AgentChoice, kind: MockKind, questionCount: number, subtopicId: string | null) =>
    requestJson<MockSession>(
      "/api/mock/sessions",
      post({ ...agent, kind, question_count: questionCount, subtopic_id: subtopicId }),
    ),
  answer: (sessionId: number, agent: AgentChoice, answer: string) =>
    requestJson<MockSession>(`/api/mock/sessions/${sessionId}/answer`, post({ ...agent, answer })),
  end: (sessionId: number, agent: AgentChoice) => requestJson<MockSession>(`/api/mock/sessions/${sessionId}/end`, post(agent)),
};

export const coachApi = {
  send: (agent: AgentChoice, message: string, conversationId: number | null) =>
    requestJson<CoachReply>("/api/coach/messages", post({ ...agent, message, conversation_id: conversationId })),
  list: () => requestJson<CoachConversationSummary[]>("/api/coach/conversations"),
  get: (conversationId: number) => requestJson<CoachConversation>(`/api/coach/conversations/${conversationId}`),
  remove: (conversationId: number) =>
    requestJson<void>(`/api/coach/conversations/${conversationId}`, { method: "DELETE" }),
};
