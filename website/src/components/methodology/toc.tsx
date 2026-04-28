"use client";

interface TocItem {
  id: string;
  title: string;
}

export function MethodologyTOC({ items }: { items: readonly TocItem[] }) {
  return (
    <nav className="sticky top-28 hidden rounded-2xl border border-line-subtle bg-bg-elevated/80 p-5 text-sm shadow-card-dark lg:block" aria-label="Mục lục phương pháp">
      <p className="mb-4 font-bold uppercase tracking-[0.2em] text-bio">Mục lục</p>
      <div className="grid gap-3">
        {items.map((item) => (
          <a key={item.id} href={`#${item.id}`} className="text-ink-secondary transition hover:text-ink-primary">
            {item.title}
          </a>
        ))}
      </div>
    </nav>
  );
}
