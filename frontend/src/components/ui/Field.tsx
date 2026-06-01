import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
}

export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field(
  { label, hint, id, className, ...rest },
  ref,
) {
  const fid = id ?? rest.name ?? "field";
  const hintId = hint ? `${fid}-hint` : undefined;
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={fid} className="font-body text-sm text-text-secondary">
        {label}
      </label>
      {hint && (
        <p id={hintId} className="font-body text-sm text-text-tertiary">
          {hint}
        </p>
      )}
      <input
        id={fid}
        ref={ref}
        aria-describedby={hintId}
        className={cn(
          "h-14 w-full rounded-md border border-border-default bg-surface-secondary px-4",
          "font-body text-base text-text-primary placeholder:text-text-muted",
          "focus-visible:outline-2 focus-visible:outline-accent-sage",
          className,
        )}
        {...rest}
      />
    </div>
  );
});
