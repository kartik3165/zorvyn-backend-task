import { useEffect, useState, useCallback } from "react";
import { fetchRecords, createRecord, updateRecord, deleteRecord } from "../api/dashboard";
import { toast } from "../../../lib/toast";

/**
 * Full CRUD hook for /records/.
 * Keeps a local list so the UI updates instantly without re-fetching the whole list.
 *
 * @param {object} filters  - Passed as query params to GET /records/
 */
export function useRecords(filters = {}) {
    const [records, setRecords] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Stable key so useEffect only re-runs when filters actually change
    const filterKey = JSON.stringify(filters);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await fetchRecords(JSON.parse(filterKey));
            setRecords(data ?? []);
        } catch (err) {
            setError(err?.response?.data?.detail ?? "Failed to load records.");
        } finally {
            setLoading(false);
        }
    }, [filterKey]);

    useEffect(() => { load(); }, [load]);

    // ── Create ──────────────────────────────────────────────────────────────
    async function addRecord(payload) {
        try {
            const created = await createRecord(payload);
            setRecords((prev) => [created, ...prev]);
            toast.success("Record created.");
            return created;
        } catch (err) {
            toast.error(err?.response?.data?.detail ?? "Failed to create record.");
            throw err;
        }
    }

    // ── Update ──────────────────────────────────────────────────────────────
    async function editRecord(id, payload) {
        try {
            const updated = await updateRecord(id, payload);
            setRecords((prev) => prev.map((r) => (r.id === id ? updated : r)));
            toast.success("Record updated.");
            return updated;
        } catch (err) {
            toast.error(err?.response?.data?.detail ?? "Failed to update record.");
            throw err;
        }
    }

    // ── Delete ──────────────────────────────────────────────────────────────
    async function removeRecord(id) {
        setRecords((prev) => prev.filter((r) => r.id !== id));
        try {
            await deleteRecord(id);
            toast.success("Record deleted.");
        } catch (err) {
            load();
            toast.error(err?.response?.data?.detail ?? "Failed to delete record.");
            throw err;
        }
    }

    return { records, loading, error, refetch: load, addRecord, editRecord, removeRecord };
}