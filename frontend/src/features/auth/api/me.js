import { apiClient } from "../../../config/api-client";
import { API_CONFIG } from "../../../config/api";

export function getMe() {
    return apiClient(API_CONFIG.ENDPOINTS.ME, {
        method: "GET",
    });
}

/**
 * Updates profile (name, avatar, or password)
 * @param {object} payload
 */
export function updateProfileRequest(payload) {
    return apiClient(API_CONFIG.ENDPOINTS.UPDATE_PROFILE, {
        method: "PATCH",
        body: JSON.stringify(payload),
    });
}