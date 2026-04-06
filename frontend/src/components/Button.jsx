import { forwardRef } from "react";
import { cn } from "../lib/utils";

const variants = {
    primary:
        "bg-white text-black hover:bg-white/90 active:scale-[0.98] disabled:opacity-50",
    secondary:
        "bg-white/10 text-white border border-white/20 hover:bg-white/20 active:scale-[0.98] disabled:opacity-50",
    ghost:
        "bg-transparent text-white/70 hover:bg-white/10 hover:text-white active:scale-[0.98] disabled:opacity-50",
    destructive:
        "bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 hover:text-red-300 active:scale-[0.98] disabled:opacity-50",
};

const sizes = {
    sm: "px-3 py-1.5 text-sm rounded-md",
    md: "px-4 py-2 text-base rounded-md",
    lg: "px-5 py-2.5 text-base rounded-lg",
};

const Button = forwardRef(
    (
        {
            children,
            variant = "primary",
            size = "md",
            className,
            disabled,
            loading,
            ...props
        },
        ref
    ) => {
        return (
            <button
                ref={ref}
                disabled={disabled || loading}
                className={cn(
                    "inline-flex items-center justify-center gap-2 font-semibold transition-all duration-150 outline-none focus-visible:ring-2 focus-visible:ring-white/40 cursor-pointer disabled:cursor-not-allowed select-none",
                    variants[variant],
                    sizes[size],
                    className
                )}
                {...props}
            >
                {loading && (
                    <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                )}
                {children}
            </button>
        );
    }
);

Button.displayName = "Button";
export default Button;