import { Navigate, Route, Routes } from "react-router-dom";

import RequireAuth from "./auth/RequireAuth";
import AppLayout from "./components/AppLayout";
import AnalyticsPage from "./pages/AnalyticsPage";
import BillingPage from "./pages/BillingPage";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import MembersPage from "./pages/MembersPage";
import OAuthCallbackPage from "./pages/OAuthCallbackPage";
import SignupPage from "./pages/SignupPage";
import WorkspaceSelectPage from "./pages/WorkspaceSelectPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/oauth/callback" element={<OAuthCallbackPage />} />

      <Route element={<RequireAuth />}>
        <Route path="/workspaces" element={<WorkspaceSelectPage />} />
        <Route path="/w/:workspaceId" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="members" element={<MembersPage />} />
          <Route path="billing" element={<BillingPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/workspaces" replace />} />
      <Route path="*" element={<Navigate to="/workspaces" replace />} />
    </Routes>
  );
}
