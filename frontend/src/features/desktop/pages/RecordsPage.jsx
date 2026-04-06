import { useState } from "react";
import { Plus } from "lucide-react";
import { useRecords } from "../hooks/useRecords";
import RecordsTable from "../components/Records/RecordsTable";
import AddRecordModal from "../components/Modals/AddRecordModal";

const TYPE_OPTIONS = ["", "INCOME", "EXPENSE"];

/**
 * recordsCtx is passed from AppShell so adding a record via the
 * topbar "Add record" button and adding via the in-page button
 * both update the same list.
 *
 * If recordsCtx is not passed (e.g. standalone usage) the hook
 * is called locally as a fallback.
 */
export default function RecordsPage({ recordsCtx }) {
    const [showModal, setShowModal] = useState(false);
    const [typeFilter, setTypeFilter] = useState("");

    // Use the shared context from AppShell when available, else create local
    const localCtx = useRecords(typeFilter ? { type: typeFilter } : {});
    const { records, loading, error, addRecord, removeRecord } =
        recordsCtx ?? localCtx;

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-white font-semibold text-lg">Records</h2>
                    <p className="text-white/30 text-xs mt-0.5">
                        {loading ? "Loading…" : `${records.length} entries`}
                    </p>
                </div>
                <button
                    onClick={() => setShowModal(true)}
                    className="flex items-center gap-2 bg-white text-black text-sm font-semibold px-3.5 py-2 rounded-lg hover:bg-white/90 active:scale-[0.98] transition-all"
                >
                    <Plus size={14} /> Add record
                </button>
            </div>

            {/* Type filter */}
            <div className="flex items-center gap-2">
                {TYPE_OPTIONS.map((t) => (
                    <button
                        key={t}
                        onClick={() => setTypeFilter(t)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${typeFilter === t
                                ? "bg-white text-black border-white"
                                : "border-white/15 text-white/40 hover:text-white/70 hover:border-white/30"
                            }`}
                    >
                        {t === "" ? "All"
                            : t === "INCOME" ? "↑ Income"
                                : "↓ Expense"}
                    </button>
                ))}
            </div>

            {error && <p className="text-red-400 text-sm">{error}</p>}

            <RecordsTable
                records={records}
                loading={loading}
                onDelete={removeRecord}
            />

            {showModal && (
                <AddRecordModal
                    onClose={() => setShowModal(false)}
                    onAdd={addRecord}
                />
            )}
        </div>
    );
}