import type { Metadata } from "next";
import { MethodologyContent, METHODOLOGY_ITEMS } from "@/components/methodology/content";
import { ReadingProgress } from "@/components/methodology/reading-progress";
import { MethodologyTOC } from "@/components/methodology/toc";
import { Container } from "@/components/ui/container";

export const metadata: Metadata = {
  title: "Phương pháp",
  description: "Diễn giải phương pháp khoa học, công thức và bảng hệ số phát thải của đề tài SKKH 2026."
};

export default function MethodologyPage() {
  return (
    <main id="main-content" data-theme="light" className="min-h-screen bg-bg-base pt-32 text-ink-primary">
      <ReadingProgress />
      <Container className="grid gap-10 pb-24 lg:grid-cols-[260px_1fr]" size="wide">
        <MethodologyTOC items={METHODOLOGY_ITEMS} />
        <div className="rounded-[32px] border border-line-subtle bg-bg-elevated/80 p-6 shadow-card-dark md:p-10">
          <p className="text-xs font-bold uppercase tracking-[0.22em] text-bio">Báo cáo phương pháp</p>
          <h1 className="mt-5 font-serif text-headline leading-none tracking-[-0.04em]">
            Tích hợp thị giác máy tính và mạng lưới cảm biến IoT trong ước lượng phát thải giao thông đô thị theo thời gian thực
          </h1>
          <div className="mt-10">
            <MethodologyContent />
          </div>
        </div>
      </Container>
    </main>
  );
}
