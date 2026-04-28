"use client";

import { motion, type MotionValue, useTransform } from "framer-motion";

interface Props {
  progress: MotionValue<number>;
}

const particles = Array.from({ length: 18 }, (_, index) => ({
  x: 92 + (index % 6) * 70,
  y: 132 + Math.floor(index / 6) * 58,
  color: index % 3 === 0 ? "var(--accent-warn)" : index % 3 === 1 ? "var(--ink-muted)" : "var(--accent-bio)"
}));

export function PipelineVisualLayer2({ progress }: Props) {
  const opacity = useTransform(progress, [0.32, 0.4, 0.62, 0.7], [0, 1, 1, 0]);
  const scale = useTransform(progress, [0.32, 0.62], [1.04, 1]);

  return (
    <motion.svg style={{ opacity, scale }} className="absolute inset-0 size-full" viewBox="0 0 540 360" aria-label="Layer 2 mô hình phát thải">
      <rect x="24" y="28" width="492" height="304" rx="28" fill="var(--bg-base)" opacity="0.72" />
      <g opacity="0.28">
        <rect x="82" y="96" width="76" height="38" rx="8" stroke="var(--accent-bio)" fill="transparent" />
        <rect x="190" y="158" width="98" height="52" rx="8" stroke="var(--accent-bio)" fill="transparent" />
        <rect x="330" y="108" width="84" height="44" rx="8" stroke="var(--accent-bio)" fill="transparent" />
      </g>
      {particles.map((particle, index) => (
        <motion.circle
          key={`${particle.x}-${particle.y}`}
          cx={particle.x}
          cy={particle.y}
          r="4"
          fill={particle.color}
          animate={{ x: [0, 16, -10, 0], y: [0, -14, 10, 0], opacity: [0.35, 1, 0.4] }}
          transition={{ duration: 2.6, repeat: Infinity, delay: index * 0.08 }}
        />
      ))}
      <foreignObject x="54" y="44" width="432" height="110">
        <div className="rounded-2xl border border-line-subtle bg-bg-surface/80 p-4 font-mono text-[13px] leading-6 text-bio">
          E_total = Σ(NV × TD × EF(V)) + Σ(NV × T_I × EF_I)
        </div>
      </foreignObject>
      <foreignObject x="290" y="238" width="190" height="58">
        <div className="rounded-xl border border-warn/30 bg-warn/10 p-3 font-mono text-xs text-warn">
          s = sf / (1 + a(v/c)^b)
        </div>
      </foreignObject>
    </motion.svg>
  );
}
