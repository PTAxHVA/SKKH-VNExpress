import { Eyebrow } from "@/components/ui/eyebrow";
import { cn } from "@/lib/utils";

interface SectionHeadingProps {
  eyebrow: string;
  title: string;
  lead?: string;
  className?: string;
}

export function SectionHeading({ eyebrow, title, lead, className }: SectionHeadingProps) {
  return (
    <div className={cn("max-w-3xl", className)}>
      <Eyebrow className="mb-5">{eyebrow}</Eyebrow>
      <h2 className="font-serif text-headline leading-[0.95] tracking-[-0.03em] text-ink-primary">
        {title}
      </h2>
      {lead ? <p className="mt-6 text-lg leading-8 text-ink-secondary md:text-xl">{lead}</p> : null}
    </div>
  );
}
