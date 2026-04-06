import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { useDashboardStats } from "../hooks/useDashboardStats";
import { formatCurrency } from "../../../lib/format";

const MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function ChartTooltip({ active, payload, label }) {
    if (!active || !payload?.length) return null;
    return (
        <div className="rounded-lg border border-white/15 bg-[#111] px-3 py-2 text-xs">
            <div className="text-white/50 mb-1">{label}</div>
            {payload.map((p, i) => (
                <div key={i} style={{ color: p.color }} className="flex gap-2">
                    <span>{p.name}</span>
                    <span className="font-semibold">{formatCurrency(p.value)}</span>
                </div>
            ))}
        </div>
    );
}

function Skeleton({ className = "" }) {
    return <div className={`rounded-xl bg-white/5 animate-pulse ${className}`} />;
}

export default function AnalyticsPage() {
    const { summary, trends, loading, error } = useDashboardStats({ months: 12 });

    if (error) {
        return <div className="text-red-400 text-sm">{error}</div>;
    }

    if (loading) {
        return (
            <div className="space-y-4">
                <Skeleton className="h-8 w-32" />
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <Skeleton className="h-72" />
                    <Skeleton className="h-72" />
                </div>
            </div>
        );
    }

    const netData = [...(trends?.monthly ?? [])]
        .sort((a, b) => a.year !== b.year ? a.year - b.year : a.month - b.month)
        .map((d) => ({
            month: MONTH_NAMES[d.month],
            net: d.income - d.expense,
        }));

    const categories = summary?.category_totals ?? [];
    const maxCatTotal = Math.max(...categories.map((c) => c.total), 1);

    return (
        <div className="space-y-4">
            <h2 className="text-white font-semibold text-lg">Analytics</h2>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Net trend */}
                <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-5">
                    <div className="text-white font-medium text-sm mb-1">Monthly net trend</div>
                    <div className="text-white/30 text-xs mb-4">Income minus expense per month</div>
                    <ResponsiveContainer width="100%" height={220}>
                        <AreaChart data={netData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                            <defs>
                                <linearGradient id="gNet" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#a78bfa" stopOpacity={0.2} />
                                    <stop offset="95%" stopColor="#a78bfa" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <XAxis dataKey="month" tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 11 }} axisLine={false} tickLine={false} />
                            <YAxis tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 11 }} axisLine={false} tickLine={false} />
                            <Tooltip content={<ChartTooltip />} />
                            <Area type="monotone" dataKey="net" name="Net" stroke="#a78bfa" strokeWidth={2} fill="url(#gNet)" dot={false} />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>

                {/* Category bars */}
                <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-5">
                    <div className="text-white font-medium text-sm mb-1">Category breakdown</div>
                    <div className="text-white/30 text-xs mb-5">All-time totals by category</div>

                    {categories.length === 0 ? (
                        <p className="text-white/20 text-sm">No category data yet.</p>
                    ) : (
                        <div className="space-y-4">
                            {categories.map((c) => (
                                <div key={c.category_id}>
                                    <div className="flex justify-between text-xs mb-1">
                                        <span className="text-white/50">
                                            {c.name ?? `Category ${c.category_id}`}
                                        </span>
                                        <span className="text-white/70 font-medium">
                                            {formatCurrency(c.total)}
                                        </span>
                                    </div>
                                    <div className="h-1.5 rounded-full bg-white/8 overflow-hidden">
                                        <div
                                            className="h-full rounded-full transition-all duration-700"
                                            style={{
                                                width: `${(c.total / maxCatTotal) * 100}%`,
                                                background: "rgba(167,139,250,0.6)",
                                            }}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Weekly trend table */}
            {(trends?.weekly ?? []).length > 0 && (
                <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-5">
                    <div className="text-white font-medium text-sm mb-4">Weekly breakdown</div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        {trends.weekly.slice(0, 8).map((w) => (
                            <div key={`${w.year}-${w.week}`} className="rounded-lg border border-white/10 bg-white/3 p-3">
                                <div className="text-white/30 text-xs mb-2">
                                    Week {w.week}, {w.year}
                                </div>
                                <div className="text-emerald-400 text-xs">+{formatCurrency(w.income)}</div>
                                <div className="text-red-400 text-xs">−{formatCurrency(w.expense)}</div>
                                <div className={`text-xs font-semibold mt-1 ${w.net >= 0 ? "text-white/70" : "text-red-400"}`}>
                                    Net: {formatCurrency(w.net)}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}