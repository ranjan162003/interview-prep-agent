import type { CodingTest, TestOutcome } from "../types/task.types";

// First run downloads Pyodide (~10 MB, then cached by the browser), so it gets longer.
const FIRST_RUN_TIMEOUT_MS = 90_000;
const RUN_TIMEOUT_MS = 8_000;

interface WorkerReply {
  id: number;
  ok: boolean;
  results?: TestOutcome[];
  error?: string;
}

export class PythonRunError extends Error {}

/**
 * Runs Python in a Web Worker (Pyodide). A run that takes too long — an infinite loop,
 * say — is stopped by terminating the worker; the next run starts a fresh one.
 */
class PythonRunner {
  private worker: Worker | null = null;
  private warmedUp = false;
  private nextId = 1;

  private getWorker(): Worker {
    if (!this.worker) {
      this.worker = new Worker("/pyodide-worker.js");
      this.warmedUp = false;
    }
    return this.worker;
  }

  /** Start downloading Pyodide early, e.g. when a coding problem opens. */
  warmUp(): void {
    this.getWorker();
  }

  run(code: string, functionName: string, tests: CodingTest[]): Promise<TestOutcome[]> {
    const worker = this.getWorker();
    const id = this.nextId++;
    const timeoutMs = this.warmedUp ? RUN_TIMEOUT_MS : FIRST_RUN_TIMEOUT_MS;

    return new Promise((resolve, reject) => {
      const timer = window.setTimeout(() => {
        worker.terminate();
        this.worker = null;
        reject(
          new PythonRunError(
            this.warmedUp
              ? `Your code ran longer than ${RUN_TIMEOUT_MS / 1000}s and was stopped — check for an infinite loop.`
              : "Loading Python in the browser took too long. Check your internet connection and try again.",
          ),
        );
      }, timeoutMs);

      const onMessage = (event: MessageEvent<WorkerReply>) => {
        if (event.data.id !== id) return;
        window.clearTimeout(timer);
        worker.removeEventListener("message", onMessage);
        this.warmedUp = true;
        if (event.data.ok && event.data.results) resolve(event.data.results);
        else reject(new PythonRunError(event.data.error ?? "Your code couldn't run."));
      };
      worker.addEventListener("message", onMessage);
      worker.postMessage({ id, code, functionName, tests });
    });
  }
}

export const pythonRunner = new PythonRunner();
