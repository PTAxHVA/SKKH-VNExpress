"use client";

import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { useEffect } from "react";

interface MetricNumberProps {
  value?: number;
  unit?: string;
  decimals?: number;
}

export function MetricNumber({ value, unit, decimals = 2 }: MetricNumberProps) {
  const raw = useMotionValue(0);
  const spring = useSpring(raw, { stiffness: 120, damping: 22 });
  const displayed = useTransform(spring, (latest) =>
    value === undefined ? "[Cập nhật]" : latest.toFixed(decimals)
  );

  useEffect(() => {
    raw.set(value ?? 0);
  }, [raw, value]);

  return (
    <div className="font-mono text-5xl font-semibold tracking-[-0.08em] text-ink-primary">
      <motion.span>{displayed}</motion.span>
      {unit ? <span className="ml-2 text-base tracking-normal text-ink-muted">{unit}</span> : null}
    </div>
  );
}
