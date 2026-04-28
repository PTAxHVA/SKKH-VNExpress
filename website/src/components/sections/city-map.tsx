"use client";

import { Camera, Layers, MapPin, Radio, Route } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Container } from "@/components/ui/container";
import { SectionHeading } from "@/components/ui/section-heading";
import { cn } from "@/lib/utils";

const cameras = [
  { id: "le-duan", name: "Lê Duẩn - Mạc Đĩnh Chi", x: 36, y: 44, status: "Đang quan trắc", accent: "bio" },
  { id: "ql1-tran-dai-nghia", name: "Quốc lộ 1 - Trần Đại Nghĩa", x: 66, y: 31, status: "Ưu tiên mô phỏng", accent: "warn" },
  { id: "vo-van-kiet", name: "Võ Văn Kiệt - Quốc Lộ 1", x: 72, y: 57, status: "Camera sẵn có", accent: "cool" },
  { id: "an-lap", name: "QL1 - Cầu An Lập", x: 49, y: 72, status: "Chờ dữ liệu cảm biến", accent: "violet" },
  { id: "ho-hoc-lam", name: "Kinh Dương Vương - Hồ Học Lãm", x: 24, y: 68, status: "Camera sẵn có", accent: "bio" }
] as const;

const roads = [
  { path: "M44 250 C160 190 248 158 456 82", color: "var(--accent-bio)", width: 13 },
  { path: "M70 90 C170 132 284 184 520 254", color: "var(--accent-cool)", width: 10 },
  { path: "M108 318 C188 248 302 214 468 192", color: "var(--accent-warn)", width: 12 },
  { path: "M210 56 C230 142 228 246 238 324", color: "var(--accent-warn)", width: 8 },
  { path: "M330 42 C292 132 288 220 318 324", color: "var(--accent-bio)", width: 9 }
] as const;

const accentClass = {
  bio: "border-bio text-bio bg-bio/10",
  warn: "border-warn text-warn bg-warn/10",
  cool: "border-cool text-cool bg-cool/10",
  violet: "border-violet text-violet bg-violet/10"
} as const;

export function CityMapSection() {
  const [activeId, setActiveId] = useState<(typeof cameras)[number]["id"]>("le-duan");
  const active = cameras.find((camera) => camera.id === activeId) ?? cameras[0];

  return (
    <section id="ban-do" className="relative py-[var(--section-y)]">
      <Container>
        <SectionHeading
          eyebrow="07 / BẢN ĐỒ ĐÔ THỊ"
          title="Từ một camera đến mạng lưới điểm nóng phát thải."
          lead="Giao diện triển khai có thể đặt lớp phát thải lên bản đồ thành phố: mỗi camera là một điểm quan trắc, mỗi đoạn đường là một mô phỏng vi mô theo chu kỳ đèn."
        />
        <div className="mt-12 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="relative min-h-[560px] overflow-hidden rounded-[36px] border border-line-subtle bg-[#eaf1d8] shadow-card-dark">
            <div className="absolute inset-0 opacity-70 [background-image:linear-gradient(90deg,oklch(82%_0.04_140)_1px,transparent_1px),linear-gradient(0deg,oklch(82%_0.04_140)_1px,transparent_1px)] [background-size:52px_52px]" />
            <svg className="absolute inset-0 size-full" viewBox="0 0 560 380" role="img" aria-label="Bản đồ minh họa mạng camera giao thông">
              {roads.map((road) => (
                <path
                  key={road.path}
                  d={road.path}
                  fill="none"
                  stroke={road.color}
                  strokeLinecap="round"
                  strokeWidth={road.width}
                  opacity="0.82"
                />
              ))}
              <path d="M52 190 L510 190 M102 48 L458 330 M492 48 L76 330" stroke="oklch(86% 0.025 95)" strokeWidth="16" strokeLinecap="round" opacity="0.72" />
              {cameras.map((camera) => (
                <g key={camera.id} transform={`translate(${camera.x * 5.6} ${camera.y * 3.8})`}>
                  <circle r="18" fill="white" opacity="0.86" />
                  <circle r="13" fill={camera.id === active.id ? "var(--accent-warn)" : "var(--accent-bio)"} />
                  <path d="M-6 -1 h9 l4 -4 v14 l-4 -4 h-9z" fill="white" />
                </g>
              ))}
            </svg>
            <div className="absolute left-5 top-5 flex items-center gap-3 rounded-2xl border border-white/70 bg-white/85 px-4 py-3 text-slate-950 shadow-lg backdrop-blur">
              <MapPin className="size-5" />
              <span className="font-mono text-sm">(106.599, 10.723)</span>
            </div>
            <div className="absolute bottom-5 left-5 rounded-3xl border border-white/70 bg-white/90 p-4 text-slate-950 shadow-xl backdrop-blur">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Chú thích</p>
              <div className="mt-3 grid gap-2 text-sm">
                <span className="flex items-center gap-2"><i className="size-3 rounded-full bg-bio" /> Luồng ổn định</span>
                <span className="flex items-center gap-2"><i className="size-3 rounded-full bg-warn" /> Ưu tiên quan trắc</span>
                <span className="flex items-center gap-2"><i className="size-3 rounded-full bg-cool" /> Dữ liệu cảm biến</span>
              </div>
            </div>
          </div>

          <aside className="rounded-[36px] border border-line-subtle bg-bg-elevated/70 p-5 shadow-card-dark backdrop-blur-xl md:p-7">
            <div className="flex items-center justify-between gap-4">
              <Badge>Camera trong bán kính 5 km</Badge>
              <Layers className="size-5 text-bio" />
            </div>
            <div className="mt-6 grid gap-3">
              {cameras.map((camera) => (
                <button
                  key={camera.id}
                  type="button"
                  onClick={() => setActiveId(camera.id)}
                  className={cn(
                    "rounded-2xl border p-4 text-left transition hover:-translate-y-0.5 hover:border-line-strong",
                    camera.id === active.id ? accentClass[camera.accent] : "border-line-subtle bg-bg-surface/40 text-ink-secondary"
                  )}
                >
                  <span className="flex items-center gap-3">
                    <Camera className="size-5" />
                    <span className="font-semibold text-ink-primary">{camera.name}</span>
                  </span>
                  <span className="mt-2 block text-sm">{camera.status}</span>
                </button>
              ))}
            </div>
            <div className="mt-6 rounded-[28px] border border-line-subtle bg-bg-base/70 p-5">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-bio">Panel mô phỏng nút giao</p>
              <h3 className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-ink-primary">{active.name}</h3>
              <div className="mt-5 grid gap-3 text-sm text-ink-secondary">
                <p className="flex items-center gap-2"><Radio className="size-4 text-cool" /> Nguồn: camera giao thông + cảm biến LCS gần nút giao</p>
                <p className="flex items-center gap-2"><Route className="size-4 text-warn" /> Mô phỏng: mỗi chu kỳ đèn / mỗi đoạn tiếp cận</p>
              </div>
              <div className="mt-6 rounded-2xl border border-warn/25 bg-warn/10 p-4">
                <p className="text-sm text-ink-secondary">Ví dụ PDF Mục 3.1</p>
                <p className="mt-2 font-mono text-4xl font-semibold tracking-[-0.07em] text-ink-primary">148.4 g CO₂</p>
                <p className="mt-2 text-sm leading-6 text-ink-secondary">2 xe máy + 2 ô tô, đoạn 200m, dừng chờ 1.5 phút.</p>
              </div>
              <p className="mt-4 text-xs leading-5 text-ink-muted">Đây là mock giao diện triển khai. Màu tuyến đường minh họa mức ưu tiên quan trắc; không phải số đo thực địa.</p>
            </div>
          </aside>
        </div>
      </Container>
    </section>
  );
}
