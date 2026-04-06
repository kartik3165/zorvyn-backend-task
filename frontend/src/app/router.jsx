import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useSelector } from "react-redux";

import LoginPage from "../features/auth/routes/login";
import ProtectedRoute from "../components/ProtectedRoute";
import AppShell from "../features/desktop/AppShell";

export default function AppRouter() {
    const { user, loading, initialized } = useSelector((state) => state.auth);

    // Wait until the /auth/me call resolves before rendering any route
    if (!initialized || loading) {
        return (
            <div className="flex h-screen items-center justify-center bg-[#080808]">
                <div className="w-5 h-5 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <BrowserRouter>
            <Routes>
                {/* Public */}
                <Route
                    path="/login"
                    element={user ? <Navigate to="/dashboard" replace /> : <LoginPage />}
                />

                {/* Protected — AppShell handles the sidebar + sub-page routing internally */}
                <Route
                    path="/dashboard"
                    element={<ProtectedRoute><AppShell page="dashboard" /></ProtectedRoute>}
                />
                <Route
                    path="/records"
                    element={<ProtectedRoute><AppShell page="records" /></ProtectedRoute>}
                />
                <Route
                    path="/analytics"
                    element={<ProtectedRoute><AppShell page="analytics" /></ProtectedRoute>}
                />
                <Route
                    path="/settings"
                    element={<ProtectedRoute><AppShell page="settings" /></ProtectedRoute>}
                />

                {/* Default redirect */}
                <Route
                    path="/"
                    element={<Navigate to={user ? "/dashboard" : "/login"} replace />}
                />

                {/* Fallback */}
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </BrowserRouter>
    );
}