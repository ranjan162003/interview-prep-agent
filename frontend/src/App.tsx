import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import { ProfileProvider } from "./context/ProfileContext";
import { ProviderConnectionsProvider } from "./context/ProviderConnectionsContext";
import { ToastProvider } from "./context/ToastContext";
import { AgentConnectorsPage } from "./pages/AgentConnectorsPage";
import { CoachPage } from "./pages/CoachPage";
import { MockInterviewPage } from "./pages/MockInterviewPage";
import { NotebookPage } from "./pages/NotebookPage";
import { PracticePage } from "./pages/PracticePage";
import { ProgressPage } from "./pages/ProgressPage";
import { SettingsPage } from "./pages/SettingsPage";
import { TodayPage } from "./pages/TodayPage";

export function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ToastProvider>
        <ProviderConnectionsProvider>
          <ProfileProvider>
            <Routes>
              <Route element={<AppShell />}>
                <Route path="/" element={<TodayPage />} />
                <Route path="/practice" element={<PracticePage />} />
                <Route path="/mock-interview" element={<MockInterviewPage />} />
                <Route path="/progress" element={<ProgressPage />} />
                <Route path="/notebook" element={<NotebookPage />} />
                <Route path="/coach" element={<CoachPage />} />
                <Route path="/connectors" element={<AgentConnectorsPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </ProfileProvider>
        </ProviderConnectionsProvider>
      </ToastProvider>
    </BrowserRouter>
  );
}
