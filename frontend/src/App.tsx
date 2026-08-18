import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { VoiceAgentBridgeProvider } from './context/VoiceAgentBridgeContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { ForgotPasswordPage } from './pages/ForgotPasswordPage';
import { ResetPasswordPage } from './pages/ResetPasswordPage';
import { ProfilePage } from './pages/ProfilePage';
import { ChatListPage } from './pages/ChatListPage';
import { ChatDetailPage } from './pages/ChatDetailPage';
import { CodeLibraryPage } from './pages/CodeLibraryPage';
import { CodeSearchPage } from './pages/CodeSearchPage';
import { ModelQueryPage } from './pages/ModelQueryPage';
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import { AdminUsersPage } from './pages/AdminUsersPage';
import { AdminCodeDocsPage } from './pages/AdminCodeDocsPage';
import { AnalyticsPage } from './pages/AnalyticsPage';

export default function App() {
  return (
    <VoiceAgentBridgeProvider>
      <AuthProvider>
        <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />

          {/* Auth module (Module 1) */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            }
          />

          {/* Chat Copilot (Module 2) */}
          <Route
            path="/chat"
            element={
              <ProtectedRoute>
                <ChatListPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/chat/:sessionId"
            element={
              <ProtectedRoute>
                <ChatDetailPage />
              </ProtectedRoute>
            }
          />

          {/* Code-RAG (Module 3) */}
          <Route
            path="/code-library"
            element={
              <ProtectedRoute requireAdmin>
                <CodeLibraryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/code-search"
            element={
              <ProtectedRoute>
                <CodeSearchPage />
              </ProtectedRoute>
            }
          />

          {/* Model Query (Module 4) */}
          <Route
            path="/model-query"
            element={
              <ProtectedRoute>
                <ModelQueryPage />
              </ProtectedRoute>
            }
          />

          {/* Admin Panel (Module 5) -- requireAdmin gates on user.is_admin */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute requireAdmin>
                <AdminDashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/users"
            element={
              <ProtectedRoute requireAdmin>
                <AdminUsersPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/code-documents"
            element={
              <ProtectedRoute requireAdmin>
                <AdminCodeDocsPage />
              </ProtectedRoute>
            }
          />

          {/* Analytics (Module 6) */}
          <Route
            path="/analytics"
            element={
              <ProtectedRoute>
                <AnalyticsPage />
              </ProtectedRoute>
            }
          />
        </Routes>
        </BrowserRouter>
      </AuthProvider>
    </VoiceAgentBridgeProvider>
  );
}
