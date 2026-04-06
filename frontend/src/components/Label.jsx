import { forwardRef } from "react";
import { cn } from "../lib/utils";

const Label = forwardRef(({ children, className, required, ...props }, ref) => {
    return (
        <label
            ref={ref}
            className={cn("text-sm text-white/70 font-medium select-none", className)}
            {...props}
        >
            {children}
            {required && <span className="ml-1 text-red-400">*</span>}
        </label>
    );
});

Label.displayName = "Label";
export default Label;