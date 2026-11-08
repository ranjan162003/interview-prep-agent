import os from "node:os";
import path from "node:path";

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, `/api/*` is proxied to the FastAPI backend so the browser never
// needs CORS and the frontend can use relative URLs everywhere.
export default defineConfig({
  plugins: [react()],
  // Keep Vite's dependency cache outside the project: cloud-synced folders
  // (OneDrive, Dropbox) lock files inside node_modules/.vite and make the dev
  // server fail with EPERM when it re-optimizes dependencies.
  cacheDir: path.join(os.tmpdir(), "interview-prep-agent-vite"),
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_BACKEND_URL ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
