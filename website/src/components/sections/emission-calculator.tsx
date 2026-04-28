"use client";

import { useState } from "react";
import { CalculatorOutput } from "@/components/sections/calculator-output";
import { CalculatorSlider } from "@/components/sections/calculator-slider";
import { Container } from "@/components/ui/container";
import { Eyebrow } from "@/components/ui/eyebrow";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { computeEmission, DEFAULT_CALC_INPUT, type Gas } from "@/lib/emissions-math";

export function EmissionCalculator() {
  const [input, setInput] = useState(DEFAULT_CALC_INPUT);
  const result = computeEmission(input);

  const update = (patch: Partial<typeof input>) => {
    setInput((current) => ({ ...current, ...patch }));
  };

  return (
    <section id="tinh-toan" className="relative py-[var(--section-y)]">
      <Container className="grid gap-10 lg:grid-cols-[5fr_7fr]">
        <div>
          <Eyebrow>04 / TÍNH TOÁN</Eyebrow>
          <h2 className="mt-5 font-serif text-headline leading-[0.98] tracking-[-0.04em]">
            Tự tay tính phát thải tại nút giao của bạn.
          </h2>
          <p className="mt-6 text-lg leading-8 text-ink-secondary">
            Mô hình tham chiếu COPERT, hệ số EF lấy từ Bảng 1 và Bảng 2 báo cáo gốc. Mặc định khởi tạo theo ví dụ tính toán trong báo cáo: 2 xe máy ở 25 km/h + 2 ô tô con ở 40 km/h, đoạn quan trắc 200m, đèn đỏ 1.5 phút.
          </p>
          <details className="mt-8 rounded-2xl border border-line-subtle bg-bg-surface/40 p-5">
            <summary className="cursor-pointer font-semibold text-bio">Xem công thức</summary>
            <p className="mt-4 font-mono text-sm leading-7 text-ink-secondary">
              E_total = Σⱼ NV_m,j × TD × EF_m,j(V) + Σⱼ NV_I,j × T_I × EF_I,j
            </p>
          </details>
        </div>
        <div className="rounded-[32px] border border-line-subtle bg-bg-elevated/60 p-5 shadow-card-dark backdrop-blur-xl md:p-8">
          <CalculatorOutput result={result} gas={input.gas} />
          <div className="mt-8 grid gap-6">
            <CalculatorSlider label="Xe máy" value={input.motorbikes} min={0} max={20} step={1} onChange={(motorbikes) => update({ motorbikes })} />
            <CalculatorSlider label="Ô tô con" value={input.cars} min={0} max={20} step={1} onChange={(cars) => update({ cars })} />
            <CalculatorSlider label="Vận tốc xe máy" value={input.motorbikeSpeedKmh} min={5} max={80} step={1} unit=" km/h" onChange={(motorbikeSpeedKmh) => update({ motorbikeSpeedKmh })} />
            <CalculatorSlider label="Vận tốc ô tô" value={input.carSpeedKmh} min={5} max={80} step={1} unit=" km/h" onChange={(carSpeedKmh) => update({ carSpeedKmh })} />
            <CalculatorSlider label="Khoảng cách" value={input.distanceKm} min={0.05} max={1} step={0.05} unit=" km" onChange={(distanceKm) => update({ distanceKm })} />
            <CalculatorSlider label="Thời gian dừng" value={input.idleMinutes} min={0} max={5} step={0.1} unit=" phút" onChange={(idleMinutes) => update({ idleMinutes: Number(idleMinutes.toFixed(1)) })} />
          </div>
          <div className="mt-7 flex items-center justify-between gap-4">
            <span className="text-sm font-semibold text-ink-secondary">Khí</span>
            <Tabs value={input.gas} onValueChange={(gas) => update({ gas: gas as Gas })}>
              <TabsList>
                <TabsTrigger value="co2">CO₂</TabsTrigger>
                <TabsTrigger value="nox">NOₓ</TabsTrigger>
                <TabsTrigger value="pm25">PM2.5</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </div>
      </Container>
    </section>
  );
}
