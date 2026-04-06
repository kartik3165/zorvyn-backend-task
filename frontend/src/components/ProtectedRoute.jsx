import { Navigate } from "react-router-dom";
import { useSelector } from "react-redux";

export default function ProtectedRoute({ children }) {
    const { user, loading } = useSelector((state) => state.auth);

    if (loading) return (
        <div className="flex h-screen items-center justify-center text-sm text-[var(--muted-foreground)]">
            Loading...
        </div>
    );

    if (!user) return <Navigate to="/login" replace />;

    return children;
}