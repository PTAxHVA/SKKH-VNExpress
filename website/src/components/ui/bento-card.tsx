import type { ReactNode } from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface BentoCardProps {
  children: ReactNode;
  className?: string;
  span?: string;
  accent?: "bio" | "cool" | "warn" | "violet";
}

const accents = {
  bio: "before:bg-bio",
  cool: "before:bg-cool",
  warn: "before:bg-warn",
  violet: "before:bg-violet"
} as const;

export function BentoCard({ children, className, span, accent = "bio" }: BentoCardProps) {
  return (
    <Card
      className={cn(
        "group relative overflow-hidden rounded-2xl p-6 transition duration-300 before:absolute before:inset-x-8 before:top-0 before:h-px before:opacity-70 hover:-translate-y-1 hover:border-line-strong md:p-8",
        accents[accent],
        span,
        className
      )}
    >
      {children}
    </Card>
  );
}
