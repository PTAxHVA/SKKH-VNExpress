"use client";

import Link from "next/link";
import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { NAV_LINKS, VOTE_URL } from "@/lib/constants";

export function MobileNav() {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="icon" className="lg:hidden" aria-label="Mở menu">
          <Menu className="size-5" />
        </Button>
      </SheetTrigger>
      <SheetContent>
        <div className="mt-14">
          <p className="text-xs font-bold uppercase tracking-[0.22em] text-bio">Điều hướng</p>
          <nav className="mt-8 grid gap-4" aria-label="Điều hướng mobile">
            {NAV_LINKS.map((link) => (
              <a key={link.href} href={link.href} className="rounded-2xl border border-line-subtle bg-bg-surface/50 p-4 text-lg font-semibold text-ink-primary">
                {link.label}
              </a>
            ))}
            <Link href="/phuong-phap" className="rounded-2xl border border-line-subtle bg-bg-surface/50 p-4 text-lg font-semibold text-ink-primary">
              Phương pháp
            </Link>
            <a href={VOTE_URL} target="_blank" rel="noreferrer" className="rounded-2xl bg-bio p-4 text-lg font-bold text-slate-950">
              Bình chọn trên VNExpress
            </a>
          </nav>
        </div>
      </SheetContent>
    </Sheet>
  );
}
