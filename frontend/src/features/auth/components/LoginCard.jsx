import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { loginUser } from "../../../stores/authSlice";
import { showError } from "../../../lib/toast";
import Button from "../../../components/Button";
import { Input, PasswordInput } from "../../../components/Input";
import Label from "../../../components/Label";

export default function LoginCard() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [formError, setFormError] = useState("");
    const dispatch = useDispatch();
    const navigate = useNavigate();
    const { loading, error } = useSelector((state) => state.auth);

    useEffect(() => {
        if (error) {
            showError(error);
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setFormError(error);
        }
    }, [error]);

    const validate = () => {
        if (!email) { setFormError("Email is required"); showError("Email is required"); return false; }
        if (!/\S+@\S+\.\S+/.test(email)) { setFormError("Invalid email"); showError("Invalid email"); return false; }
        if (!password) { setFormError("Password is required"); showError("Password is required"); return false; }
        if (password.length < 6) { setFormError("Minimum 6 characters required"); showError("Minimum 6 characters required"); return false; }
        return true;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setFormError("");
        if (!validate()) return;
        const result = await dispatch(loginUser({ email, password }));
        if (result.meta.requestStatus === "fulfilled") {
            navigate("/dashboard");
        }
    };

    return (
        <div className="relative flex min-h-screen items-center justify-center bg-transparent px-6 overflow-hidden">

            {/* Background glow */}
            <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.08),transparent_60%)]" />

            {/* Glass Card */}
            <div className="relative w-full max-w-md rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 shadow-[0_8px_32px_rgba(0,0,0,0.37)] p-8">
                <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-white/10 via-transparent to-white/5 pointer-events-none" />

                <div className="relative z-10">

                    {/* Header */}
                    <div className="mb-6 text-center">
                        <h2 className="text-xl font-semibold text-white">
                            Login to your account
                        </h2>
                        <p className="text-base text-white/60">
                            Enter your email below to login to your account
                        </p>
                    </div>

                    <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>

                        {/* Email */}
                        <div className="flex flex-col gap-1">
                            <Label htmlFor="email">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(e) => { setEmail(e.target.value); setFormError(""); }}
                                placeholder="you@example.com"
                                autoComplete="username"
                                error={!!formError}
                            />
                        </div>

                        {/* Password */}
                        <div className="flex flex-col gap-1">
                            <div className="flex justify-between items-center">
                                <Label htmlFor="password">Password</Label>
                                <button
                                    type="button"
                                    className="text-xs text-white/40 hover:text-white transition-colors"
                                >
                                    Forgot your password?
                                </button>
                            </div>
                            <PasswordInput
                                id="password"
                                value={password}
                                onChange={(e) => { setPassword(e.target.value); setFormError(""); }}
                                placeholder="••••••••"
                                autoComplete="current-password"
                                error={!!formError}
                            />
                        </div>

                        {/* Error message */}
                        {formError && (
                            <p className="text-xs text-red-400">{formError}</p>
                        )}

                        {/* Submit */}
                        <Button
                            type="submit"
                            variant="primary"
                            size="lg"
                            loading={loading}
                            className="mt-2 w-full"
                        >
                            {loading ? "Signing in..." : "Login"}
                        </Button>

                    </form>
                </div>
            </div>
        </div>
    );
}