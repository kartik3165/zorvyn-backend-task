import { API_CONFIG } from "../config/api";

export function getCSRFToken() {
    const cookie = document.cookie
        .split("; ")
        .find((row) => row.startsWith(`${API_CONFIG.CSRF_COOKIE_NAME}=`));

    return cookie ? cookie.split("=")[1] : null;
}