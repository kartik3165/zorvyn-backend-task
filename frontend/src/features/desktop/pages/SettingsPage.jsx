import { useState } from "react";
import { useSelector } from "react-redux";
import { LogOut, Check } from "lucide-react";
import { useAuth } from "../../auth/hooks/useAuth";
import { updateProfileRequest } from "../../auth/api/me";
import { toast } from "../../../lib/toast";

export default function SettingsPage() {
    const { user, logout } = useAuth();
    const [fullName, setFullName] = useState(user?.full_name ?? "");
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);

    // Password change fields
    const [oldPw, setOldPw] = useState("");
    const [newPw, setNewPw] = useState("");

    async function handleSave() {
        const payload = {};
        if (fullName.trim() !== user?.full_name) payload.full_name = fullName.trim();
        if (newPw) { payload.old_password = oldPw; payload.new_password = newPw; }
        if (!Object.keys(payload).length) return;

        setSaving(true);
        try {
            await updateProfileRequest(payload);
            setSaved(true);
            toast.success("Profile updated.");
            setOldPw(""); setNewPw("");
            setTimeout(() => setSaved(false), 2000);
        } catch (err) {
            toast.error(err?.response?.data?.detail ?? "Update failed.");
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="space-y-4 max-w-lg">
            <h2 className="text-white font-semibold text-lg">Settings</h2>

            {/* Profile card */}
            <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-5 space-y-4">
                <div>
                    <label className="text-xs text-white/50 block mb-1.5">Display name</label>
                    <input
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        className="w-full rounded-lg border border-white/15 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-white/30 transition-colors"
                    />
                </div>

                <div>
                    <label className="text-xs text-white/50 block mb-1.5">Email</label>
                    <input
                        value={user?.email ?? ""}
                        disabled
                        className="w-full rounded-lg border border-white/10 bg-white/3 px-3 py-2.5 text-sm text-white/40 cursor-not-allowed"
                    />
                </div>

                <div>
                    <label className="text-xs text-white/50 block mb-1.5">Role</label>
                    <input
                        value={user?.role ?? "—"}
                        disabled
                        className="w-full rounded-lg border border-white/10 bg-white/3 px-3 py-2.5 text-sm text-white/40 cursor-not-allowed capitalize"
                    />
                </div>

                {/* Password change */}
                <div className="pt-2 border-t border-white/10">
                    <p className="text-xs text-white/30 mb-3">Change password (optional)</p>
                    <div className="space-y-3">
                        <div>
                            <label className="text-xs text-white/50 block mb-1.5">Current password</label>
                            <input
                                type="password"
                                value={oldPw}
                                onChange={(e) => setOldPw(e.target.value)}
                                placeholder="••••••••"
                                className="w-full rounded-lg border border-white/15 bg-white/5 px-3 py-2.5 text-sm text-white placeholder:text-white/20 outline-none focus:border-white/30 transition-colors"
                            />
                        </div>
                        <div>
                            <label className="text-xs text-white/50 block mb-1.5">New password</label>
                            <input
                                type="password"
                                value={newPw}
                                onChange={(e) => setNewPw(e.target.value)}
                                placeholder="••••••••"
                                className="w-full rounded-lg border border-white/15 bg-white/5 px-3 py-2.5 text-sm text-white placeholder:text-white/20 outline-none focus:border-white/30 transition-colors"
                            />
                        </div>
                    </div>
                </div>

                <button
                    onClick={handleSave}
                    disabled={saving}
                    className={`flex items-center gap-2 text-sm font-semibold px-4 py-2 rounded-lg transition-all active:scale-[0.98] disabled:opacity-60 ${saved
                            ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                            : "bg-white text-black hover:bg-white/90"
                        }`}
                >
                    {saved ? <><Check size={14} /> Saved</> : saving ? "Saving…" : "Save changes"}
                </button>
            </div>

            {/* Danger zone */}
            <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm p-5">
                <div className="text-white/80 text-sm font-medium mb-1">Danger zone</div>
                <p className="text-white/30 text-xs mb-4">
                    These actions are irreversible.
                </p>
                <button
                    onClick={logout}
                    className="text-red-400 border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 text-sm px-4 py-2 rounded-lg transition-all font-medium flex items-center gap-2"
                >
                    <LogOut size={14} /> Sign out
                </button>
            </div>
        </div>
    );
}