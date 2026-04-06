export default function KPI({ label, value, sub, up = true, icon: Icon, accent = "#e2e2e2" }) {
    return (
        <div className="rounded-xl border border-white/10 bg-white/5 p-5 backdrop-blur-sm">
            <div className="mb-4 flex items-start justify-between gap-3">
                <div>
                    <div className="text-xs uppercase tracking-[0.18em] text-white/35">{label}</div>
                    <div className="mt-2 text-2xl font-semibold text-white">{value}</div>
                </div>
                {Icon ? (
                    <div
                        className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10"
                        style={{ backgroundColor: `${accent}1A`, color: accent }}
                    >
                        <Icon size={18} />
                    </div>
                ) : null}
            </div>

            <div className={`text-xs ${up ? "text-white/60" : "text-red-300"}`}>{sub}</div>
        </div>
    );
}
