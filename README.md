# PrepPilot: Interview Prep Agent

An AI interview coach that builds a personalised 1–2 hour practice plan every day for the role
you're targeting (software engineer, cybersecurity), up to your interview date. AI agents
generate questions, grade your answers against a rubric, review your code, and track your weak
topics so the next day's plan targets them.

## Features

- **Today:** a daily 60- or 120-minute plan (warm-up quiz, concept, coding problem or security lab,
  mock question, recap) with a session timer. Spaced repetition (SM-2) brings weak subtopics back.
- **Practice:** quizzes; beginner-friendly lessons with an **Ask the teacher** chat and graded
  explain-back; coding problems in a Monaco editor with tests run in the browser (Pyodide), hints and
  an AI code review; hands-on security labs (logs, vulnerable code, HTTP requests).
- **Mock interview:** multi-question interviews with follow-ups, scored per answer with a stronger answer.
- **Progress:** streak, minutes, topic mastery heat-map, 12-week activity calendar, interview readiness.
- **Notebook:** everything learnt, searchable, never repeated, and downloadable as a PDF revision book.
- **Coach:** a chat that looks up your scores, weak spots, syllabus and past answers.
- **Agent connectors:** Claude, Gemini or local Ollama; browser login or API key.

## Repo layout

| Folder | What's inside |
|---|---|
| [`backend/`](backend/) | Python 3.10+ · FastAPI · SQLAlchemy (SQLite) · LLM provider layer (Claude, Gemini, Ollama) |
| [`frontend/`](frontend/) | React 18 · TypeScript · Vite · react-router |
| [`scripts/`](scripts/) | One-command setup, dev server and tests |

## Requirements

- [Node.js](https://nodejs.org) 20+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (installs Python and the backend packages)
- At least one model: [Claude Code](https://claude.com/claude-code), the
  [Gemini CLI](https://github.com/google-gemini/gemini-cli), an API key, or [Ollama](https://ollama.com)

## Run it

```bash
cd scripts
npm run setup   # first time, and after pulling new dependencies
npm run dev     # backend on :8000, frontend on http://localhost:5173
npm test        # backend tests + frontend type-check and build
```

On Windows you can also double-click `scripts/start-dev.cmd`.

Then open **Agent connectors** in the sidebar and connect a model.

## Configuration

Backend settings use the `INTERVIEW_PREP_` prefix. Copy `backend/.env.example` to
`backend/.env` to override them. API keys are never stored in files: the app saves them in your
OS credential vault (Windows Credential Manager or macOS Keychain).
