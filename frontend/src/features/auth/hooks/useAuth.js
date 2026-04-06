import { useEffect, useState } from "react";
import { getMe } from "../api/me";

export function useAuth() {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getMe()
            .then((res) => {
                setUser(res.data);
            })
            .catch(() => {
                setUser(null);
            })
            .finally(() => {
                setLoading(false);
            });
    }, []);

    const logout = async () => {
        try {
            await fetch("http://localhost:8000/auth/logout", {
                method: "POST",
                credentials: "include"
            });
        } catch (e) {
            // Silently fail if API is down
        } finally {
            window.location.href = "/login";
        }
    };

    return { user, loading, logout };
}