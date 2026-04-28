"use client";

import { motion } from "framer-motion";

const sensors = [
  { x: 92, y: 76, delay: 0 },
  { x: 252, y: 122, delay: 0.28 },
  { x: 390, y: 68, delay: 0.56 },
  { x: 126, y: 262, delay: 0.84 },
  { x: 300, y: 292, delay: 1.12 },
  { x: 460, y: 226, delay: 1.4 }
];

export function HeroVisual() {
  return (
    <div className="relative min-h-[360px] overflow-hidden rounded-[36px] border border-line-subtle bg-bg-elevated/40 shadow-card-dark backdrop-blur-xl">
      <div className="city-grid absolute inset-0 opacity-60" />
      <svg className="absolute inset-0 size-full" viewBox="0 0 560 380" role="img" aria-label="Lưới giao thông với sáu điểm cảm biến phát sáng">
        <defs>
          <linearGradient id="artery" x1="0" x2="1" y1="0" y2="1">
            <stop stopColor="var(--accent-warn)" />
            <stop offset="1" stopColor="var(--accent-bio)" />
          </linearGradient>
        </defs>
        <motion.path
          d="M36 316 C162 176 270 170 520 62"
          fill="none"
          stroke="url(#artery)"
          strokeWidth="10"
          strokeLinecap="round"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 0.8 }}
          transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1], delay: 1 }}
        />
        <motion.path
          d="M42 92 C182 158 338 205 516 306"
          fill="none"
          stroke="var(--accent-cool)"
          strokeWidth="6"
          strokeLinecap="round"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 0.42 }}
          transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1], delay: 1.15 }}
        />
        {sensors.map((sensor) => (
          <g key={`${sensor.x}-${sensor.y}`}>
            <motion.circle
              cx={sensor.x}
              cy={sensor.y}
              r="18"
              fill="var(--accent-bio)"
              opacity="0.1"
              animate={{ scale: [1, 2.2, 1], opacity: [0.12, 0, 0.12] }}
              transition={{ duration: 1.6, repeat: Infinity, delay: 2.2 + sensor.delay }}
              style={{ transformOrigin: `${sensor.x}px ${sensor.y}px` }}
            />
            <motion.circle
              cx={sensor.x}
              cy={sensor.y}
              r="5"
              fill="var(--accent-bio)"
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.4, delay: 1.8 + sensor.delay }}
            />
          </g>
        ))}
        <motion.g initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.35 }}>
          <rect x="54" y="36" width="164" height="44" rx="14" fill="var(--bg-base)" opacity="0.88" />
          <text x="72" y="63" fill="var(--accent-bio)" fontSize="14" fontFamily="var(--font-jetbrains)">
            CO₂ + NOₓ live
          </text>
        </motion.g>
      </svg>
      <div className="absolute bottom-5 left-5 right-5 flex items-center justify-between rounded-2xl border border-white/10 bg-bg-base/70 px-4 py-3 text-xs text-ink-secondary backdrop-blur-xl">
        <span>Camera → EF model → IoT calibration</span>
        <span className="font-mono text-bio">R² real data</span>
      </div>
    </div>
  );
}
