import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";
import { Layout } from "@/components/layout/Layout";
import DashboardPage from "@/pages/DashboardPage";
import ContactsPage from "@/pages/ContactsPage";
import PipelinePage from "@/pages/PipelinePage";
import ChatPage from "@/pages/ChatPage";
import SettingsPage from "@/pages/SettingsPage";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import { useAuthStore } from "@/stores/authStore";

/** Redirect to /login if not authenticated */
function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

/** Redirect to / if already authenticated */
function PublicRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  return isAuthenticated ? <Navigate to="/" replace /> : <>{children}</>;
}

function App() {
  const fetchUser = useAuthStore((s) => s.fetchUser);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  // Hydrate user on mount if a token exists
  useEffect(() => {
    if (isAuthenticated) {
      fetchUser();
    }
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <BrowserRouter>
      <Routes>
        {/* Public auth routes */}
        <Route
          path="/login"
          element={
            <PublicRoute>
              <LoginPage />
            </PublicRoute>
          }
        />
        <Route
          path="/register"
          element={
            <PublicRoute>
              <RegisterPage />
            </PublicRoute>
          }
        />

        {/* Protected app routes */}
        <Route
          element={
            <PrivateRoute>
              <Layout />
            </PrivateRoute>
          }
        >
          <Route path="/" element={<DashboardPage />} />
          <Route path="/contacts" element={<ContactsPage />} />
          <Route path="/pipeline" element={<PipelinePage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
