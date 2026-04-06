import { ArrowUpRight, ArrowDownRight, Clock } from "lucide-react";
import { formatCurrency, formatDate } from "../../../../lib/format";

/**
 * @param {{ records: Array<{ id, notes, category?, type, amount, date }> }} props
 */
export default function RecentActivity({ records = [] }) {
    return (
        <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-5">
            <div className="flex items-center justify-between mb-4">
                <div>
                    <div className="text-white font-medium text-sm">Recent activity</div>
                    <div className="text-white/30 text-xs mt-0.5">Latest transactions</div>
                </div>
                <Clock size={14} className="text-white/20" />
            </div>

            {records.length === 0 ? (
                <p className="text-white/20 text-sm text-center py-6">No recent records.</p>
            ) : (
                <div className="space-y-0">
                    {records.map((r) => {
                        const isIncome = r.type === "INCOME";
                        return (
                            <div
                                key={r.id}
                                className="flex items-center justify-between py-2.5 border-b border-white/5 last:border-0"
                            >
                                <div className="flex items-center gap-3">
                                    <div
                                        className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${isIncome ? "bg-emerald-500/15" : "bg-red-500/15"
                                            }`}
                                    >
                                        {isIncome
                                            ? <ArrowUpRight size={13} className="text-emerald-400" />
                                            : <ArrowDownRight size={13} className="text-red-400" />}
                                    </div>
                                    <div>
                                        <div className="text-white/80 text-sm leading-tight">
                                            {r.notes ?? "—"}
                                        </div>
                                        <div className="text-white/30 text-xs mt-0.5">
                                            {r.category ?? `Cat. ${r.category_id}`} · {formatDate(r.date)}
                                        </div>
                                    </div>
                                </div>
                                <span
                                    className={`text-sm font-semibold ${isIncome ? "text-emerald-400" : "text-red-400"
                                        }`}
                                >
                                    {isIncome ? "+" : "−"}{formatCurrency(r.amount)}
                                </span>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}