import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSelector } from "react-redux";
import { Plus } from "lucide-react";

import Sidebar from "./components/Sidebar";
import DashboardView from "./components/DashboardView";
import RecordsPage from "./pages/RecordsPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import SettingsPage from "./pages/SettingsPage";
import AddRecordModal from "./components/Modals/AddRecordModal";
import { useRecords } from "./hooks/useRecords";

function DotBg() {
    return (
        <div
            className="fixed inset-0 pointer-events-none"
            style={{
                backgroundImage:
                    "radial-gradient(circle, rgba(255,255,255,0.12) 1px, transparent 1px)",
                backgroundSize: "28px 28px",
                zIndex: 0,
            }}
        />
    );
}

const PAGE_TITLES = {
    dashboard: "Overview",
    records: "Records",
    analytics: "Analytics",
    settings: "Settings",
};

// page prop comes from router.jsx so the URL stays in sync with the sidebar
export default function AppShell({ page = "dashboard" }) {
    const navigate = useNavigate();
    const { user } = useSelector((s) => s.auth);
    const [collapsed, setCollapsed] = useState(false);
    const [showModal, setShowModal] = useState(false);

    // Single records context — shared between modal and RecordsPage
    const recordsCtx = useRecords();

    const pages = {
        dashboard: <DashboardView />,
        records: <RecordsPage recordsCtx={recordsCtx} />,
        analytics: <AnalyticsPage />,
        settings: <SettingsPage />,
    };

    return (
        <div
            className="flex h-screen bg-[#080808] overflow-hidden relative"
            style={{ fontFamily: "'DM Sans', sans-serif" }}
        >
            <link
                href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap"
                rel="stylesheet"
            />
            <DotBg />

            <Sidebar
                active={page}
                setActive={(id) => navigate(`/${id}`)}  // URL-driven navigation
                collapsed={collapsed}
                setCollapsed={setCollapsed}
                onAddRecord={() => setShowModal(true)}
            />

            <main className="flex-1 flex flex-col overflow-hidden relative z-10">
                {/* Topbar */}
                <header className="flex items-center justify-between px-6 py-4 border-b border-white/8 flex-shrink-0">
                    <div>
                        <h1 className="text-white font-semibold text-base">
                            {PAGE_TITLES[page]}
                        </h1>
                        <p className="text-white/30 text-xs mt-0.5">
                            {new Date().toLocaleDateString("en-IN", {
                                weekday: "long",
                                year: "numeric",
                                month: "long",
                                day: "numeric",
                            })}
                        </p>
                    </div>

                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => setShowModal(true)}
                            className="flex items-center gap-2 bg-white text-black text-sm font-semibold px-3.5 py-2 rounded-lg hover:bg-white/90 active:scale-[0.98] transition-all"
                        >
                            <Plus size={14} /> Add record
                        </button>

                        <div className="w-8 h-8 rounded-full bg-white/10 border border-white/15 flex items-center justify-center text-white text-xs font-semibold select-none">
                            {user?.full_name?.[0]?.toUpperCase() ?? "U"}
                        </div>
                    </div>
                </header>

                {/* Page */}
                <div className="flex-1 overflow-y-auto p-6">
                    {pages[page]}
                </div>
            </main>

            {showModal && (
                <AddRecordModal
                    onClose={() => setShowModal(false)}
                    onAdd={recordsCtx.addRecord}
                />
            )}
        </div>
    );
}