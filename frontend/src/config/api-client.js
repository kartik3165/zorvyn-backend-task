import { API_CONFIG } from "../config/api";
import { getCSRFToken } from "../config/csrf";

let isRefreshing = false;
let refreshPromise = null;

async function refreshToken() {
    if (!refreshPromise) {
        refreshPromise = fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.REFRESH}`, {
            method: "POST",
            credentials: "include",
        })
            .then((res) => {
                if (!res.ok) throw new Error("Refresh failed");
                return res.json();
            })
            .finally(() => {
                refreshPromise = null;
            });
    }

    return refreshPromise;
}

export async function apiClient(endpoint, options = {}, retry = true) {
    const { params, ...fetchOptions } = options;
    const searchParams = params ? new URLSearchParams(params) : null;
    const query = searchParams && searchParams.toString() ? `?${searchParams.toString()}` : "";
    const url = `${API_CONFIG.BASE_URL}${endpoint}${query}`;

    const isAuthEndpoint =
        endpoint.includes("/auth/login") ||
        endpoint.includes("/auth/signup") ||
        endpoint.includes("/auth/refresh");

    const headers = {
        "Content-Type": "application/json",
        ...(fetchOptions.headers || {}),
    };

    if (!isAuthEndpoint && ["POST", "PUT", "PATCH", "DELETE"].includes(fetchOptions.method)) {
        const csrf = getCSRFToken();
        if (csrf) headers[API_CONFIG.CSRF_HEADER_NAME] = csrf;
    }

    const response = await fetch(url, {
        credentials: "include",
        ...fetchOptions,
        headers,
    });

    if (response.status === 401 && retry && !isAuthEndpoint) {
        try {
            await refreshToken();
            return apiClient(endpoint, options, false);
        } catch (err) {
            throw new Error("Session expired");
        }
    }

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || "API Error");
    }

    return data;
}

async function request(method, endpoint, payloadOrOptions, maybeOptions) {
    const hasBody = ["POST", "PUT", "PATCH"].includes(method);
    const body =
        hasBody && payloadOrOptions !== undefined ? JSON.stringify(payloadOrOptions) : undefined;
    const options = hasBody ? maybeOptions || {} : payloadOrOptions || {};

    const data = await apiClient(endpoint, {
        method,
        ...options,
        ...(body ? { body } : {}),
    });

    return { data };
}

apiClient.get = (endpoint, options) => request("GET", endpoint, options);
apiClient.post = (endpoint, payload, options) => request("POST", endpoint, payload, options);
apiClient.put = (endpoint, payload, options) => request("PUT", endpoint, payload, options);
apiClient.patch = (endpoint, payload, options) => request("PATCH", endpoint, payload, options);
apiClient.delete = (endpoint, options) => request("DELETE", endpoint, options);

export default apiClient;
