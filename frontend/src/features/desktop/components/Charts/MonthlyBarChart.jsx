import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatCurrency } from "../../../../lib/format";

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function ChartTooltip({ active, payload, label }) {
    if (!active || !payload?.length) return null;

    return (
        <div className="rounded-lg border border-white/15 bg-[#111] px-3 py-2 text-xs shadow-xl">
            <div className="mb-1 text-white/50">{label}</div>
            {payload.map((item) => (
                <div key={item.dataKey} className="flex items-center justify-between gap-4">
                    <span style={{ color: item.fill }}>{item.name}</span>
                    <span className="font-semibold text-white">{formatCurrency(item.value)}</span>
                </div>
            ))}
        </div>
    );
}

export default function MonthlyBarChart({ monthly = [] }) {
    const data = [...monthly]
        .sort((a, b) => (a.year !== b.year ? a.year - b.year : a.month - b.month))
        .map((item) => ({
            label: MONTH_NAMES[(item.month ?? 1) - 1],
            net: item.net ?? (item.income ?? 0) - (item.expense ?? 0),
        }));

    return (
        <div className="rounded-xl border border-white/10 bg-white/5 p-5 backdrop-blur-sm">
            <div className="mb-1 text-sm font-medium text-white">Net by month</div>
            <div className="mb-4 text-xs text-white/30">Positive and negative swings</div>

            <ResponsiveContainer width="100%" height={220}>
                <BarChart data={data} margin={{ top: 8, right: 0, left: -18, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.08)" />
                    <XAxis
                        dataKey="label"
                        tick={{ fill: "rgba(255,255,255,0.38)", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                    />
                    <YAxis
                        tickFormatter={(value) => formatCurrency(value)}
                        tick={{ fill: "rgba(255,255,255,0.38)", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                        width={72}
                    />
                    <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
                    <Bar
                        dataKey="net"
                        name="Net"
                        radius={[8, 8, 0, 0]}
                        fill="#93c5fd"
                    />
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}
