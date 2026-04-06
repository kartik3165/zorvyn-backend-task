import apiClient from "../../../config/api-client";

// ─── Dashboard ────────────────────────────────────────────────────────────────

/**
 * GET /dashboard/summary
 * @param {{ start_date?: string, end_date?: string }} params
 */
export async function fetchSummary(params = {}) {
    const { data } = await apiClient.get("/dashboard/summary", { params });
    return data.data; // unwrap StandardResponse
}

/**
 * GET /dashboard/trends
 * @param {{ months?: number, weeks?: number }} params
 */
export async function fetchTrends(params = { months: 6, weeks: 8 }) {
    const { data } = await apiClient.get("/dashboard/trends", { params });
    return data.data;
}

// ─── Records ──────────────────────────────────────────────────────────────────

/**
 * GET /records/
 * @param {{ type?: string, category_id?: number, start_date?: string, end_date?: string }} filters
 */
export async function fetchRecords(filters = {}) {
    // Strip out undefined/null so they don't become "?type=null"
    const params = Object.fromEntries(
        Object.entries(filters).filter(([, v]) => v != null && v !== "")
    );
    const { data } = await apiClient.get("/records/", { params });
    return data.data;
}

/**
 * POST /records/
 * @param {{ amount: number, type: string, category_id: number, notes?: string, date: string }} payload
 */
export async function createRecord(payload) {
    const { data } = await apiClient.post("/records/", payload);
    return data.data;
}

/**
 * PUT /records/:id
 */
export async function updateRecord(id, payload) {
    const { data } = await apiClient.put(`/records/${id}`, payload);
    return data.data;
}

/**
 * DELETE /records/:id
 */
export async function deleteRecord(id) {
    const { data } = await apiClient.delete(`/records/${id}`);
    return data;
}