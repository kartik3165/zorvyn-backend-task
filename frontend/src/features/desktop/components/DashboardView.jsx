import { Wallet, ArrowUpRight, ArrowDownRight, BarChart3 } from "lucide-react";
import { useDashboardStats } from "../hooks/useDashboardStats";
import KPI from "./KPI";
import IncomeExpenseChart from "./Charts/IncomeExpenseChart";
import MonthlyBarChart from "./Charts/MonthlyBarChart";
import CategoryPieChart from "./Charts/CategoryPieChart";
import RecentActivity from "./Records/RecentActivity";
import { formatCurrency } from "../../../lib/format";

function Skeleton({ className = "" }) {
    return <div className={`rounded-xl bg-white/5 animate-pulse ${className}`} />;
}

export default function DashboardView() {
    const { summary, trends, loading, error } = useDashboardStats();

    if (error) {
        return (
            <div className="flex items-center justify-center h-40 text-red-400 text-sm">
                {error}
            </div>
        );
    }

    if (loading || !summary) {
        return (
            <div className="space-y-6">
                <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
                    {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-28" />)}
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <Skeleton className="lg:col-span-2 h-72" />
                    <Skeleton className="h-72" />
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <Skeleton className="h-56" />
                    <Skeleton className="lg:col-span-2 h-56" />
                </div>
            </div>
        );
    }

    const {
        total_income, total_expense, net_balance,
        record_count, income_count, expense_count,
        category_totals, recent_records,
    } = summary;

    return (
        <div className="space-y-6">
            {/* KPI row */}
            <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
                <KPI
                    label="Net balance"
                    value={formatCurrency(net_balance)}
                    sub="Current period"
                    up={net_balance >= 0}
                    icon={Wallet}
                    accent="#e2e2e2"
                />
                <KPI
                    label="Total income"
                    value={formatCurrency(total_income)}
                    sub={`${income_count} transactions`}
                    up={true}
                    icon={ArrowUpRight}
                    accent="#6ee7b7"
                />
                <KPI
                    label="Total expense"
                    value={formatCurrency(total_expense)}
                    sub={`${expense_count} transactions`}
                    up={false}
                    icon={ArrowDownRight}
                    accent="#fca5a5"
                />
                <KPI
                    label="Transactions"
                    value={record_count}
                    sub={`${income_count} in · ${expense_count} out`}
                    up={true}
                    icon={BarChart3}
                    accent="#93c5fd"
                />
            </div>

            {/* Area chart + pie */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div className="lg:col-span-2">
                    <IncomeExpenseChart monthly={trends?.monthly ?? []} />
                </div>
                <CategoryPieChart categoryTotals={category_totals} />
            </div>

            {/* Bar chart + recent activity */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <MonthlyBarChart monthly={trends?.monthly ?? []} />
                <div className="lg:col-span-2">
                    <RecentActivity records={recent_records} />
                </div>
            </div>
        </div>
    );
}