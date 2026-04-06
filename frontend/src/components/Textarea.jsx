import { forwardRef } from "react";
import { cn } from "../lib/utils";

const Textarea = forwardRef(({ className, error, ...props }, ref) => {
    return (
        <textarea
            ref={ref}
            className={cn(
                "w-full rounded-md border border-white/20 bg-black/40 px-3 py-2 text-base text-white placeholder:text-white/30 outline-none transition-all duration-150 focus:border-white/40 focus:ring-1 focus:ring-white/20 disabled:opacity-50 disabled:cursor-not-allowed min-h-[100px]",
                error && "border-red-500/50 focus:border-red-500/60 focus:ring-red-500/20",
                className
            )}
            {...props}
        />
    );
});

Textarea.displayName = "Textarea";
export default Textarea;
