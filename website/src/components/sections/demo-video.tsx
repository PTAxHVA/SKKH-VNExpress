"use client";

import { Container } from "@/components/ui/container";
import { SectionHeading } from "@/components/ui/section-heading";
import { VideoPlayer } from "@/components/ui/video-player";

export function DemoVideoSection() {
  return (
    <section id="demo" className="py-[var(--section-y)]">
      <Container size="narrow">
        <SectionHeading
          eyebrow="06 / DEMO"
          title="SUMO mô phỏng — Fixed-Time vs Q-Learning controller."
          className="mx-auto text-center"
        />
        <div className="mt-10">
          <VideoPlayer src="/demo/sumo_visualization.mp4" poster="/demo/sumo_poster.svg" />
        </div>
        <p className="mx-auto mt-6 max-w-3xl text-center text-sm leading-7 text-ink-secondary">
          Mô phỏng giao lộ với 35% xe máy, 65% ô tô. Bên trái: Fixed-Time controller chu kỳ 30 giây. Bên phải: Q-Learning controller học từ queue length, delay và switch penalty. Q-Learning giảm trung bình 18-25% delay so với Fixed-Time qua 5 episode evaluation. (Số liệu cụ thể: xem báo cáo benchmark.)
        </p>
      </Container>
    </section>
  );
}
