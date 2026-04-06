import { useEffect, useState, useCallback } from "react";
import { fetchSummary, fetchTrends } from "../api/dashboard";

/**
 * Fetches /dashboard/summary and /dashboard/trends in parallel.
 *
 * @param {{ startDate?: string, endDate?: string, months?: number, weeks?: number }} opts
 */
export function useDashboardStats(opts = {}) {
    const { startDate, endDate, months = 6, weeks = 8 } = opts;

    const [summary, setSummary] = useState(null);
    const [trends, setTrends] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const summaryParams = {};
            if (startDate) summaryParams.start_date = startDate;
            if (endDate) summaryParams.end_date = endDate;

            const [summaryData, trendsData] = await Promise.all([
                fetchSummary(summaryParams),
                fetchTrends({ months, weeks }),
            ]);

            setSummary(summaryData);
            setTrends(trendsData);
        } catch (err) {
            setError(err?.response?.data?.detail ?? "Failed to load dashboard data.");
        } finally {
            setLoading(false);
        }
    }, [startDate, endDate, months, weeks]);

    useEffect(() => { load(); }, [load]);

    return { summary, trends, loading, error, refetch: load };
}