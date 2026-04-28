"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

interface PipelineLayerTextProps {
  eyebrow: string;
  title: string;
  children: ReactNode;
}

export function PipelineLayerText({ eyebrow, title, children }: PipelineLayerTextProps) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-20%" }}
      className="border-l border-line-subtle pl-6"
    >
      <p className="font-mono text-xs uppercase tracking-[0.22em] text-bio">{eyebrow}</p>
      <h3 className="mt-3 text-2xl font-bold tracking-[-0.04em] text-ink-primary">{title}</h3>
      <div className="mt-4 space-y-4 text-base leading-7 text-ink-secondary">{children}</div>
    </motion.article>
  );
}
