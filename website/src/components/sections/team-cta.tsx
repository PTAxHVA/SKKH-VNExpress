import Image from "next/image";
import { ArrowUpRight } from "lucide-react";
import { SiteFooter } from "@/components/layout/site-footer";
import { Button } from "@/components/ui/button";
import { Container } from "@/components/ui/container";
import { Eyebrow } from "@/components/ui/eyebrow";
import { TEAM } from "@/content/team";
import { VOTE_URL } from "@/lib/constants";

export function TeamCTASection() {
  return (
    <section id="cta" className="pt-[var(--section-y)]">
      <Container>
        <Eyebrow>09 / ĐỘI NGŨ + LIÊN HỆ</Eyebrow>
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {TEAM.map((member) => (
            <article key={member.name} className="rounded-[28px] border border-line-subtle bg-bg-elevated/60 p-6 shadow-card-dark">
              <div className="relative mb-5 size-20 overflow-hidden rounded-3xl border border-bio/25 bg-bio/10">
                <Image src="/icon.svg" alt="" fill className="object-cover p-4" />
              </div>
              <h3 className="text-xl font-semibold text-ink-primary">{member.name}</h3>
              <p className="mt-2 text-sm leading-6 text-ink-secondary">{member.role}</p>
            </article>
          ))}
        </div>
        <div className="my-16 rounded-[36px] border border-bio/20 bg-[linear-gradient(135deg,oklch(78%_0.18_155_/_0.16),oklch(72%_0.2_50_/_0.08))] p-8 text-center shadow-glow-bio md:p-12">
          <p className="text-sm font-bold uppercase tracking-[0.22em] text-bio">Bình chọn cho dự án trên VNExpress</p>
          <h2 className="mx-auto mt-5 max-w-3xl font-serif text-headline leading-none tracking-[-0.04em]">
            Biến camera giao thông thành hạ tầng môi trường cho thành phố.
          </h2>
          <Button asChild className="mt-8">
            <a href={VOTE_URL} target="_blank" rel="noreferrer">
              Vote tại VNExpress <ArrowUpRight className="ml-2 inline size-4" />
            </a>
          </Button>
        </div>
      </Container>
      <SiteFooter />
    </section>
  );
}
