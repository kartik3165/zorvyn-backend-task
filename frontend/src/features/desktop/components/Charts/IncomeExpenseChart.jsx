import {
    Area,
    AreaChart,
    CartesianGrid,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import { formatCurrency } from "../../../../lib/format";

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function ChartTooltip({ active, payload, label }) {
    if (!active || !payload?.length) return null;

    return (
        <div className="rounded-lg border border-white/15 bg-[#111] px-3 py-2 text-xs shadow-xl">
            <div className="mb-1 text-white/50">{label}</div>
            {payload.map((item) => (
                <div key={item.dataKey} className="flex items-center justify-between gap-4">
                    <span style={{ color: item.color }}>{item.name}</span>
                    <span className="font-semibold text-white">{formatCurrency(item.value)}</span>
                </div>
            ))}
        </div>
    );
}

export default function IncomeExpenseChart({ monthly = [] }) {
    const data = [...monthly]
        .sort((a, b) => (a.year !== b.year ? a.year - b.year : a.month - b.month))
        .map((item) => ({
            label: `${MONTH_NAMES[(item.month ?? 1) - 1]} ${String(item.year).slice(-2)}`,
            income: item.income ?? 0,
            expense: item.expense ?? 0,
        }));

    return (
        <div className="rounded-xl border border-white/10 bg-white/5 p-5 backdrop-blur-sm">
            <div className="mb-1 text-sm font-medium text-white">Income vs expense</div>
            <div className="mb-4 text-xs text-white/30">Monthly cashflow trend</div>

            <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                    <defs>
                        <linearGradient id="incomeFill" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#6ee7b7" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#6ee7b7" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="expenseFill" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#fca5a5" stopOpacity={0.28} />
                            <stop offset="95%" stopColor="#fca5a5" stopOpacity={0} />
                        </linearGradient>
                    </defs>
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
                    <Tooltip content={<ChartTooltip />} />
                    <Area
                        type="monotone"
                        dataKey="income"
                        name="Income"
                        stroke="#6ee7b7"
                        fill="url(#incomeFill)"
                        strokeWidth={2}
                        dot={false}
                    />
                    <Area
                        type="monotone"
                        dataKey="expense"
                        name="Expense"
                        stroke="#fca5a5"
                        fill="url(#expenseFill)"
                        strokeWidth={2}
                        dot={false}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}
