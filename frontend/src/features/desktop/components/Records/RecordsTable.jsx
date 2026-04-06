import { Trash2 } from "lucide-react";
import { formatCurrency, formatDate } from "../../../../lib/format";

/**
 * @param {{
 *   records: Array,
 *   onDelete: (id: string) => void,
 *   loading: boolean
 * }} props
 */
export default function RecordsTable({ records = [], onDelete, loading }) {
    if (loading) {
        return (
            <div className="rounded-xl border border-white/10 bg-white/5 p-8 text-center text-white/30 text-sm">
                Loading records…
            </div>
        );
    }

    if (records.length === 0) {
        return (
            <div className="rounded-xl border border-white/10 bg-white/5 p-8 text-center text-white/30 text-sm">
                No records found. Add your first one.
            </div>
        );
    }

    return (
        <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm overflow-hidden">
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b border-white/10 text-white/30 text-xs uppercase tracking-wider">
                        <th className="text-left px-5 py-3 font-medium">Description</th>
                        <th className="text-left px-5 py-3 font-medium">Category</th>
                        <th className="text-left px-5 py-3 font-medium">Date</th>
                        <th className="text-left px-5 py-3 font-medium">Type</th>
                        <th className="text-right px-5 py-3 font-medium">Amount</th>
                        <th className="px-5 py-3" />
                    </tr>
                </thead>
                <tbody>
                    {records.map((r, i) => {
                        const isIncome = r.type === "INCOME";
                        const isLast = i === records.length - 1;
                        return (
                            <tr
                                key={r.id}
                                className={`hover:bg-white/3 transition-colors ${!isLast ? "border-b border-white/5" : ""}`}
                            >
                                <td className="px-5 py-3.5 text-white/80">{r.notes ?? "—"}</td>
                                <td className="px-5 py-3.5 text-white/40">
                                    {r.category ?? `Cat. ${r.category_id}`}
                                </td>
                                <td className="px-5 py-3.5 text-white/40">{formatDate(r.date)}</td>
                                <td className="px-5 py-3.5">
                                    <span
                                        className={`px-2 py-0.5 rounded text-xs font-medium ${isIncome
                                            ? "bg-emerald-500/15 text-emerald-400"
                                            : "bg-red-500/15 text-red-400"
                                            }`}
                                    >
                                        {r.type}
                                    </span>
                                </td>
                                <td
                                    className={`px-5 py-3.5 text-right font-semibold ${isIncome ? "text-emerald-400" : "text-red-400"
                                        }`}
                                >
                                    {isIncome ? "+" : "−"}{formatCurrency(r.amount)}
                                </td>
                                <td className="px-4 py-3.5 text-right">
                                    {onDelete && (
                                        <button
                                            onClick={() => onDelete(r.id)}
                                            className="text-white/20 hover:text-red-400 transition-colors"
                                            title="Delete record"
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                    )}
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}