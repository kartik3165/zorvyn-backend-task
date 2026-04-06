import { forwardRef } from "react";
import { cn } from "../lib/utils";

// ─── Checkbox ───────────────────────────────────────────────────────────────

const Checkbox = forwardRef(({ className, label, id, ...props }, ref) => {
    return (
        <label
            htmlFor={id}
            className="inline-flex items-center gap-2.5 cursor-pointer select-none group"
        >
            <div className="relative flex items-center justify-center">
                <input
                    ref={ref}
                    id={id}
                    type="checkbox"
                    className="sr-only peer"
                    {...props}
                />
                {/* Custom box */}
                <div
                    className={cn(
                        "w-4 h-4 rounded border border-white/30 bg-black/40 transition-all duration-150",
                        "peer-checked:bg-white peer-checked:border-white",
                        "peer-focus-visible:ring-2 peer-focus-visible:ring-white/40",
                        "group-hover:border-white/50",
                        className
                    )}
                />
                {/* Checkmark */}
                <svg
                    className="absolute w-2.5 h-2.5 text-black opacity-0 peer-checked:opacity-100 transition-opacity pointer-events-none"
                    viewBox="0 0 10 8"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                >
                    <path d="M1 4l3 3 5-6" />
                </svg>
            </div>
            {label && (
                <span className="text-sm text-white/70 group-hover:text-white/90 transition-colors">
                    {label}
                </span>
            )}
        </label>
    );
});

Checkbox.displayName = "Checkbox";

// ─── Toggle (Switch) ─────────────────────────────────────────────────────────

const Toggle = forwardRef(({ className, label, id, ...props }, ref) => {
    return (
        <label
            htmlFor={id}
            className="inline-flex items-center gap-3 cursor-pointer select-none group"
        >
            <div className="relative">
                <input
                    ref={ref}
                    id={id}
                    type="checkbox"
                    className="sr-only peer"
                    {...props}
                />
                {/* Track */}
                <div
                    className={cn(
                        "w-10 h-5 rounded-full border border-white/20 bg-black/40 transition-all duration-200",
                        "peer-checked:bg-white/90 peer-checked:border-white/60",
                        "peer-focus-visible:ring-2 peer-focus-visible:ring-white/40",
                        "group-hover:border-white/40",
                        className
                    )}
                />
                {/* Thumb */}
                <div
                    className="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white/40 transition-all duration-200 pointer-events-none
          peer-checked:translate-x-5 peer-checked:bg-black"
                    style={{ transition: "transform 0.2s, background 0.2s" }}
                />
                {/* We need the thumb to follow the peer state via JS since pure CSS sibling trick needs adjacent sibling */}
            </div>
            {label && (
                <span className="text-sm text-white/70 group-hover:text-white/90 transition-colors">
                    {label}
                </span>
            )}
        </label>
    );
});

Toggle.displayName = "Toggle";

export { Checkbox, Toggle };