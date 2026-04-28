"use client";

import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { useEffect } from "react";
import type { CalcOutput, Gas } from "@/lib/emissions-math";

interface CalculatorOutputProps {
  result: CalcOutput;
  gas: Gas;
}

const gasLabels: Record<Gas, string> = {
  co2: "CO₂",
  nox: "NOₓ",
  pm25: "PM2.5"
};

export function CalculatorOutput({ result, gas }: CalculatorOutputProps) {
  const raw = useMotionValue(result.total);
  const spring = useSpring(raw, { stiffness: 200, damping: 25 });
  const total = useTransform(spring, (latest) => latest.toFixed(gas === "co2" ? 1 : 3));
  const movingPercent = Math.max(0, Math.min(100, (result.moving / (result.total || 1)) * 100));

  useEffect(() => {
    raw.set(result.total);
  }, [raw, result.total]);

  return (
    <div className="rounded-[28px] border border-line-subtle bg-bg-base/60 p-6 shadow-card-dark">
      <p className="font-mono text-xs uppercase tracking-[0.22em] text-bio">E_total</p>
      <div className="mt-4 flex items-end gap-3">
        <motion.span className="font-mono text-6xl font-semibold tracking-[-0.08em] text-ink-primary md:text-7xl">
          {total}
        </motion.span>
        <span className="pb-3 text-xl font-semibold text-ink-secondary">{result.unit} {gasLabels[gas]}</span>
      </div>
      <div className="mt-8 overflow-hidden rounded-full border border-line-subtle bg-bg-elevated">
        <div className="relative h-4">
          <motion.div
            className="absolute inset-y-0 left-0 w-full origin-left bg-bio"
            animate={{ scaleX: movingPercent / 100 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          />
          <motion.div
            className="absolute inset-y-0 right-0 w-full origin-right bg-warn"
            animate={{ scaleX: (100 - movingPercent) / 100 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          />
        </div>
      </div>
      <div className="mt-5 grid gap-3 text-sm text-ink-secondary sm:grid-cols-2">
        <p><span className="text-bio">E_moving</span> {result.moving.toFixed(gas === "co2" ? 1 : 3)} {result.unit}</p>
        <p><span className="text-warn">E_idling</span> {result.idling.toFixed(gas === "co2" ? 1 : 3)} {result.unit}</p>
        <p>Xe máy chạy: {result.breakdown.motorbikeMoving.toFixed(gas === "co2" ? 1 : 3)}</p>
        <p>Ô tô dừng: {result.breakdown.carIdling.toFixed(gas === "co2" ? 1 : 3)}</p>
      </div>
    </div>
  );
}
