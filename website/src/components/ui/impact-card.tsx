import type { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface ImpactCardProps {
  icon: LucideIcon;
  title: string;
  body: string;
  accent: "bio" | "cool" | "violet" | "warn";
  className?: string;
}

const colors = {
  bio: "text-bio border-bio/25",
  cool: "text-cool border-cool/25",
  violet: "text-violet border-violet/25",
  warn: "text-warn border-warn/25"
} as const;

export function ImpactCard({ icon: Icon, title, body, accent, className }: ImpactCardProps) {
  return (
    <Card className={cn("rounded-[28px] p-7", colors[accent], className)}>
      <div className="mb-8 inline-grid size-12 place-items-center rounded-2xl border border-current/30 bg-current/10">
        <Icon className="size-6" />
      </div>
      <h3 className="text-2xl font-semibold tracking-[-0.04em] text-ink-primary">{title}</h3>
      <p className="mt-4 text-base leading-7 text-ink-secondary">{body}</p>
    </Card>
  );
}
