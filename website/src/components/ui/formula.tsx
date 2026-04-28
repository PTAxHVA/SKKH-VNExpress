import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface FormulaProps {
  children?: ReactNode;
  latex?: string;
  className?: string;
}

export function Formula({ children, latex, className }: FormulaProps) {
  return (
    <div className={cn("overflow-x-auto rounded-2xl border border-line-subtle bg-bg-elevated/70 p-5 font-mono text-sm text-bio", className)}>
      {children ?? latex}
    </div>
  );
}
