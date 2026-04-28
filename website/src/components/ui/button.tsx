import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cn } from "@/lib/utils";

const variants = {
  primary:
    "rounded-full bg-bio px-5 py-3 text-sm font-semibold text-slate-950 shadow-glow-bio transition hover:brightness-110 active:scale-[0.98]",
  ghost:
    "rounded-md border border-line-subtle bg-bg-surface/50 px-4 py-3 text-sm font-semibold text-ink-primary transition hover:border-line-strong hover:bg-bg-surface-hi/70 active:scale-[0.98]",
  icon:
    "grid size-10 place-items-center rounded-full border border-line-subtle bg-bg-surface/70 text-ink-primary transition hover:bg-bg-surface-hi"
} as const;

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean;
  variant?: keyof typeof variants;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp ref={ref} className={cn(variants[variant], className)} {...props} />;
  }
);

Button.displayName = "Button";
