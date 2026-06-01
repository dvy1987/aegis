import { forwardRef, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  hint?: string;
}

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(function TextArea(
  { label, hint, id, className, ...rest },
  ref,
) {
  const tid = id ?? rest.name ?? "textarea";
  const hintId = hint ? `${tid}-hint` : undefined;
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={tid} className="font-body text-sm text-text-secondary">
        {label}
      </label>
      {hint && (
        <p id={hintId} className="font-body text-sm text-text-tertiary">
          {hint}
        </p>
      )}
      <textarea
        id={tid}
        ref={ref}
        aria-describedby={hintId}
        className={cn(
          "min-h-40 w-full rounded-md border border-border-default bg-surface-secondary p-4",
          "font-body text-base text-text-primary placeholder:text-text-muted",
          "focus-visible:outline-2 focus-visible:outline-accent-sage",
          className,
        )}
        {...rest}
      />
    </div>
  );
});
