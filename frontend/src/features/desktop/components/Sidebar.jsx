import {
    LayoutDashboard,
    Table,
    BarChart3,
    Settings,
    LogOut,
    ChevronLeft,
    ChevronRight,
    Plus,
    Droplets
} from "lucide-react";
import { useDispatch } from "react-redux";
import { logoutThunk } from "../../../stores/authSlice";

const NAV_ITEMS = [
    { id: "dashboard", label: "Overview", icon: LayoutDashboard },
    { id: "records", label: "Records", icon: Table },
    { id: "analytics", label: "Analytics", icon: BarChart3 },
    { id: "settings", label: "Settings", icon: Settings },
];

export default function Sidebar({ active, setActive, collapsed, setCollapsed, onAddRecord }) {
    const dispatch = useDispatch();

    return (
        <aside
            className={`flex flex-col h-screen border-r border-white/8 bg-[#080808]/80 backdrop-blur-xl transition-all duration-300 relative z-20 ${collapsed ? "w-20" : "w-64"
                }`}
        >
            {/* Header / Logo */}
            <div className="h-16 flex items-center px-6 border-b border-white/5">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
                        <Droplets className="text-white" size={18} />
                    </div>
                    {!collapsed && (
                        <span className="text-white font-bold text-lg tracking-tight uppercase">
                            Fluid<span className="text-blue-400">Care</span>
                        </span>
                    )}
                </div>
            </div>

            {/* Nav links */}
            <nav className="flex-1 px-3 py-6 space-y-1.5 overflow-hidden">
                {NAV_ITEMS.map((item) => (
                    <button
                        key={item.id}
                        onClick={() => setActive(item.id)}
                        className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl transition-all group relative ${active === item.id
                            ? "bg-white text-black font-semibold shadow-xl shadow-white/5"
                            : "text-white/40 hover:text-white hover:bg-white/5"
                            }`}
                        title={collapsed ? item.label : ""}
                    >
                        <item.icon size={19} className={active === item.id ? "text-black" : "text-current"} />
                        {!collapsed && <span className="text-sm">{item.label}</span>}
                        {active === item.id && !collapsed && (
                            <div className="absolute right-3 w-1.5 h-1.5 rounded-full bg-black" />
                        )}
                    </button>
                ))}

                <div className="pt-8 pb-4">
                    <div className={`h-px bg-white/5 mx-3 mb-6 ${collapsed ? "opacity-0" : "opacity-100"}`} />
                    <button
                        onClick={onAddRecord}
                        className={`w-full flex items-center gap-3 px-3.5 py-3 rounded-xl bg-blue-500 text-white font-bold hover:bg-blue-600 active:scale-95 transition-all shadow-lg shadow-blue-500/20 ${collapsed ? "justify-center" : ""
                            }`}
                    >
                        <Plus size={20} />
                        {!collapsed && <span className="text-sm uppercase tracking-wider">New Record</span>}
                    </button>
                </div>
            </nav>

            {/* Bottom Actions */}
            <div className="p-3 border-t border-white/5 bg-white/2">
                <button
                    onClick={() => dispatch(logoutThunk())}
                    className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-red-400/70 hover:text-red-400 hover:bg-red-500/10 transition-all group"
                >
                    <LogOut size={19} />
                    {!collapsed && <span className="text-sm font-medium">Log out</span>}
                </button>

                <button
                    onClick={() => setCollapsed(!collapsed)}
                    className="mt-2 w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-white/20 hover:text-white/50 hover:bg-white/5 transition-all"
                >
                    {collapsed ? <ChevronRight size={19} /> : <ChevronLeft size={19} />}
                    {!collapsed && <span className="text-xs uppercase tracking-widest font-semibold">Collapse</span>}
                </button>
            </div>
        </aside>
    );
}