"use client";

import { motion, useInView, useMotionValue, useSpring, useTransform } from "framer-motion";
import { useEffect, useRef } from "react";

interface BigStatProps {
  value: number;
  suffix?: string;
  label: string;
}

export function BigStat({ value, suffix = "%", label }: BigStatProps) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-20% 0px" });
  const raw = useMotionValue(0);
  const spring = useSpring(raw, { stiffness: 90, damping: 20 });
  const rounded = useTransform(spring, (latest) => Math.round(latest));

  useEffect(() => {
    if (isInView) raw.set(value);
  }, [isInView, raw, value]);

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, scale: 0.94 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true }}
      className="sticky top-28 rounded-[28px] border border-line-subtle bg-bg-surface/60 p-8 shadow-card-dark backdrop-blur-xl"
    >
      <div className="font-mono text-7xl font-bold tracking-[-0.08em] text-bio md:text-8xl">
        <motion.span>{rounded}</motion.span>
        <span>{suffix}</span>
      </div>
      <p className="mt-5 max-w-xs text-balance text-lg leading-7 text-ink-secondary">{label}</p>
    </motion.div>
  );
}
