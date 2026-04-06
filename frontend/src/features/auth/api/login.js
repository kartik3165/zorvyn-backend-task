import { apiClient } from "../../../config/api-client";
import { API_CONFIG } from "../../../config/api";

export function loginApi(payload) {
    return apiClient(API_CONFIG.ENDPOINTS.LOGIN, {
        method: "POST",
        body: JSON.stringify(payload),
    });
}