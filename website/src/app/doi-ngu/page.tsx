import type { Metadata } from "next";
import Image from "next/image";
import { Container } from "@/components/ui/container";
import { TEAM } from "@/content/team";

export const metadata: Metadata = {
  title: "Đội ngũ",
  description: "Thông tin đội ngũ thực hiện đề tài giao thông xanh SKKH 2026."
};

export default function TeamPage() {
  return (
    <main id="main-content" className="min-h-screen pt-32">
      <Container>
        <p className="text-xs font-bold uppercase tracking-[0.22em] text-bio">Đội ngũ</p>
        <h1 className="mt-5 font-serif text-headline leading-none tracking-[-0.04em]">
          Nhóm Giao Thông DHBK
        </h1>
        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {TEAM.map((member) => (
            <article key={member.name} className="rounded-[32px] border border-line-subtle bg-bg-elevated/60 p-8 shadow-card-dark">
              <div className="relative mb-6 size-24 overflow-hidden rounded-[28px] border border-bio/25 bg-bio/10">
                <Image src="/icon.svg" alt="" fill className="object-cover p-5" />
              </div>
              <h2 className="text-2xl font-semibold text-ink-primary">{member.name}</h2>
              <p className="mt-2 text-ink-secondary">{member.role}</p>
            </article>
          ))}
        </div>
      </Container>
    </main>
  );
}
