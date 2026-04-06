import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { formatCurrency } from "../../../../lib/format";

// Grayscale palette matching the dark theme
const COLORS = ["#e2e2e2", "#a0a0a0", "#707070", "#888", "#555", "#444", "#333", "#222"];

/**
 * @param {{ categoryTotals: Array<{ category_id, name?, total, count }> }} props
 */
export default function CategoryPieChart({ categoryTotals = [] }) {
    const pieData = categoryTotals.map((c, i) => ({
        name: c.name ?? `Category ${c.category_id}`,
        value: c.total,
        color: COLORS[i % COLORS.length],
    }));

    return (
        <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-5">
            <div className="text-white font-medium text-sm mb-1">By category</div>
            <div className="text-white/30 text-xs mb-3">Breakdown</div>

            <ResponsiveContainer width="100%" height={140}>
                <PieChart>
                    <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={42}
                        outerRadius={64}
                        paddingAngle={3}
                        dataKey="value"
                        strokeWidth={0}
                    >
                        {pieData.map((entry, i) => (
                            <Cell key={i} fill={entry.color} />
                        ))}
                    </Pie>
                    <Tooltip
                        formatter={(v) => formatCurrency(v)}
                        contentStyle={{
                            background: "#111",
                            border: "1px solid rgba(255,255,255,0.1)",
                            borderRadius: 8,
                            fontSize: 12,
                        }}
                    />
                </PieChart>
            </ResponsiveContainer>

            {/* Legend */}
            <div className="mt-3 space-y-1.5">
                {pieData.slice(0, 5).map((c, i) => (
                    <div key={i} className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                            <span
                                className="w-2 h-2 rounded-full flex-shrink-0"
                                style={{ background: c.color }}
                            />
                            <span className="text-white/50">{c.name}</span>
                        </div>
                        <span className="text-white/70 font-medium">{formatCurrency(c.value)}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}