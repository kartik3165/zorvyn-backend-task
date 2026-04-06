import { useState } from "react";
import { X, Plus, ArrowUpRight, ArrowDownLeft } from "lucide-react";
import Button from "../../../../components/Button";
import Input from "../../../../components/Input";
import Label from "../../../../components/Label";

export default function AddRecordModal({ onClose, onAdd }) {
    const [formData, setFormData] = useState({
        amount: "",
        type: "EXPENSE",
        category: "",
        date: new Date().toISOString().split("T")[0],
        notes: "",
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!formData.amount || !formData.category) return;

        onAdd({
            ...formData,
            amount: parseFloat(formData.amount),
        });
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="w-full max-w-md bg-[#0D0D0D] border border-white/10 rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-white/2">
                    <div>
                        <h2 className="text-white font-semibold text-lg">Add New Record</h2>
                        <p className="text-white/30 text-xs">Enter transaction details below</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 text-white/40 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                    >
                        <X size={18} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-5">
                    {/* Amount & Type */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label required>Amount</Label>
                            <div className="relative">
                                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30 text-sm">$</span>
                                <Input
                                    required
                                    type="number"
                                    step="0.01"
                                    placeholder="0.00"
                                    className="pl-7"
                                    value={formData.amount}
                                    onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                                />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label required>Type</Label>
                            <div className="flex p-1 bg-white/5 rounded-lg border border-white/10">
                                <button
                                    type="button"
                                    onClick={() => setFormData({ ...formData, type: "INCOME" })}
                                    className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-xs font-semibold transition-all ${formData.type === "INCOME"
                                        ? "bg-emerald-500 text-white shadow-lg shadow-emerald-500/20"
                                        : "text-white/40 hover:text-white/60"
                                        }`}
                                >
                                    <ArrowUpRight size={14} /> Income
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setFormData({ ...formData, type: "EXPENSE" })}
                                    className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md text-xs font-semibold transition-all ${formData.type === "EXPENSE"
                                        ? "bg-red-500 text-white shadow-lg shadow-red-500/20"
                                        : "text-white/40 hover:text-white/60"
                                        }`}
                                >
                                    <ArrowDownLeft size={14} /> Expense
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Category & Date */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label required>Category</Label>
                            <Input
                                required
                                placeholder="Food, Rent, etc."
                                value={formData.category}
                                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label required>Date</Label>
                            <Input
                                required
                                type="date"
                                value={formData.date}
                                onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                            />
                        </div>
                    </div>

                    {/* Notes */}
                    <div className="space-y-2">
                        <Label>Description / Notes</Label>
                        <textarea
                            className="w-full min-h-[80px] rounded-md border border-white/20 bg-black/40 px-3 py-2 text-base text-white placeholder:text-white/30 outline-none transition-all duration-150 focus:border-white/40 focus:ring-1 focus:ring-white/20"
                            placeholder="Optional details..."
                            value={formData.notes}
                            onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                        />
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-3 pt-2">
                        <Button
                            type="button"
                            variant="secondary"
                            onClick={onClose}
                            className="flex-1"
                        >
                            Cancel
                        </Button>
                        <Button type="submit" className="flex-1 gap-2">
                            <Plus size={16} /> Add Record
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    );
}
