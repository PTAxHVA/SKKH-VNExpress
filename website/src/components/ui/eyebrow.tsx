import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface EyebrowProps {
  children?: ReactNode;
  className?: string;
  index?: string;
  label?: string;
}

export function Eyebrow({ children, className, index, label }: EyebrowProps) {
  return (
    <p className={cn("text-xs font-bold uppercase tracking-[0.22em] text-bio", className)}>
      {children ?? `${index ? `${index} / ` : ""}${label ?? ""}`}
    </p>
  );
}
