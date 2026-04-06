import { forwardRef, useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { cn } from "../lib/utils";

const baseInput =
    "w-full rounded-md border border-white/20 bg-black/40 px-3 py-2 text-base text-white placeholder:text-white/30 outline-none transition-all duration-150 focus:border-white/40 focus:ring-1 focus:ring-white/20 disabled:opacity-50 disabled:cursor-not-allowed";

const Input = forwardRef(
    ({ className, type = "text", error, ...props }, ref) => {
        return (
            <input
                ref={ref}
                type={type}
                className={cn(
                    baseInput,
                    error && "border-red-500/50 focus:border-red-500/60 focus:ring-red-500/20",
                    className
                )}
                {...props}
            />
        );
    }
);

Input.displayName = "Input";

// PasswordInput — wraps Input with show/hide toggle
const PasswordInput = forwardRef(({ className, error, ...props }, ref) => {
    const [show, setShow] = useState(false);

    return (
        <div className="relative">
            <input
                ref={ref}
                type={show ? "text" : "password"}
                className={cn(
                    baseInput,
                    "pr-10",
                    error && "border-red-500/50 focus:border-red-500/60 focus:ring-red-500/20",
                    className
                )}
                {...props}
            />
            <button
                type="button"
                onClick={() => setShow((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white transition-colors"
                tabIndex={-1}
                aria-label={show ? "Hide password" : "Show password"}
            >
                {show ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
        </div>
    );
});

PasswordInput.displayName = "PasswordInput";

export { Input, PasswordInput };
export default Input;