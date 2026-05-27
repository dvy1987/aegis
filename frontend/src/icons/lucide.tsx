/**
 * Lucide tuning wrapper.
 *
 * All Lucide icon usage in the app must go through this module. The wrapper
 * applies the project's stroke / size / linecap rules so we never ship a
 * default Lucide drop-in (the second-biggest vibecoded tell after Inter-on-purple).
 *
 * Tuning rules (per .design/aegis/ICONS.md):
 *   - strokeWidth: 1.5 at 24/20px, 1.25 at 16px
 *   - strokeLinecap: round
 *   - strokeLinejoin: round
 *   - color: currentColor (so token-driven CSS controls everything)
 *   - size: 16 | 20 | 24 | 32 only
 *
 * Importing `lucide-react` directly anywhere else is a lint error
 * (rule to be added in T6.3).
 */

import type { LucideIcon, LucideProps } from "lucide-react";

export type IconSize = 16 | 20 | 24 | 32;

export interface TunedIconProps extends Omit<LucideProps, "size"> {
  size?: IconSize;
  title?: string;
}

export function tuneLucide(Icon: LucideIcon) {
  function Tuned({ size = 24, title, ...rest }: TunedIconProps) {
    const stroke = size <= 16 ? 1.25 : 1.5;
    return (
      <Icon
        size={size}
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden={title ? undefined : true}
        role={title ? "img" : undefined}
        {...rest}
      >
        {title ? <title>{title}</title> : null}
      </Icon>
    );
  }
  Tuned.displayName = `Tuned(${Icon.displayName ?? Icon.name ?? "LucideIcon"})`;
  return Tuned;
}

export type { LucideIcon };
