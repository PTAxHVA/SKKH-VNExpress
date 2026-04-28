"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { useEffect, useState } from "react";
import { MobileNav } from "@/components/layout/mobile-nav";
import { Button } from "@/components/ui/button";
import { NAV_LINKS, VOTE_URL } from "@/lib/constants";
import { cn } from "@/lib/utils";

export function SiteHeader() {
  const [isSolid, setIsSolid] = useState(false);

  useEffect(() => {
    const onScroll = () => setIsSolid(window.scrollY > 48);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-50 transition duration-300",
        isSolid ? "border-b border-line-subtle bg-bg-base/80 backdrop-blur-xl" : "bg-transparent"
      )}
    >
      <div className="mx-auto flex h-20 max-w-[1280px] items-center justify-between px-6 md:px-10 lg:px-16">
        <Link href="/" className="group flex items-center gap-3" aria-label="Trang chủ SKKH">
          <span className="grid size-9 place-items-center rounded-2xl border border-bio/30 bg-bio/10 text-sm font-black text-bio shadow-glow-bio">
            SK
          </span>
          <span className="hidden text-sm font-semibold uppercase tracking-[0.18em] text-ink-primary sm:block">
            SKKH 2026
          </span>
        </Link>

        <nav className="hidden items-center gap-1 rounded-full border border-line-subtle bg-bg-surface/30 p-1 backdrop-blur-xl lg:flex" aria-label="Điều hướng chính">
          {NAV_LINKS.map((link) => (
            <a key={link.href} href={link.href} className="rounded-full px-4 py-2 text-sm font-medium text-ink-secondary transition hover:bg-bg-surface hover:text-ink-primary">
              {link.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-3 lg:flex">
          <Link href="/phuong-phap" className="text-sm font-semibold text-ink-secondary transition hover:text-ink-primary">
            Phương pháp
          </Link>
          <Button asChild>
            <a href={VOTE_URL} target="_blank" rel="noreferrer">
              Bình chọn <ArrowUpRight className="ml-2 inline size-4" />
            </a>
          </Button>
        </div>

        <MobileNav />
      </div>
    </header>
  );
}
