import Link from "next/link";
import { Container } from "@/components/ui/container";

export default function NotFound() {
  return (
    <main id="main-content" className="min-h-screen py-40">
      <Container size="narrow">
        <p className="font-mono text-sm uppercase tracking-[0.22em] text-bio">404</p>
        <h1 className="mt-4 font-serif text-headline tracking-[-0.04em]">Không tìm thấy trang.</h1>
        <p className="mt-5 text-ink-secondary">Đường dẫn này không nằm trong website showcase SKKH 2026.</p>
        <Link href="/" className="mt-8 inline-flex rounded-full bg-bio px-5 py-3 font-semibold text-slate-950">
          Về trang chủ
        </Link>
      </Container>
    </main>
  );
}
