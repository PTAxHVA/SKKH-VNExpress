"use client";

import { motion, type MotionValue, useTransform } from "framer-motion";

interface Props {
  progress: MotionValue<number>;
}

const sensors = [
  { x: 92, y: 86 },
  { x: 438, y: 92 },
  { x: 120, y: 282 },
  { x: 430, y: 268 }
];

export function PipelineVisualLayer3({ progress }: Props) {
  const opacity = useTransform(progress, [0.65, 0.73, 0.95, 1], [0, 1, 1, 1]);
  const scale = useTransform(progress, [0.65, 0.95], [1.04, 1]);

  return (
    <motion.svg style={{ opacity, scale }} className="absolute inset-0 size-full" viewBox="0 0 540 360" aria-label="Layer 3 IoT và học máy">
      <rect x="24" y="28" width="492" height="304" rx="28" fill="var(--bg-base)" opacity="0.76" />
      <defs>
        <linearGradient id="heat" x1="0" x2="1">
          <stop stopColor="var(--accent-bio)" />
          <stop offset="1" stopColor="var(--accent-warn)" />
        </linearGradient>
      </defs>
      {sensors.map((sensor, index) => (
        <g key={`${sensor.x}-${sensor.y}`}>
          <motion.circle cx={sensor.x} cy={sensor.y} r="18" fill="var(--accent-cool)" opacity="0.12" animate={{ scale: [1, 1.8, 1] }} transition={{ duration: 1.8, repeat: Infinity, delay: index * 0.2 }} style={{ transformOrigin: `${sensor.x}px ${sensor.y}px` }} />
          <circle cx={sensor.x} cy={sensor.y} r="8" fill="var(--accent-cool)" />
          <path d={`M${sensor.x} ${sensor.y} L270 178`} stroke="var(--accent-cool)" strokeWidth="2" opacity="0.45" />
        </g>
      ))}
      <motion.circle cx="270" cy="178" r="46" fill="var(--accent-violet)" opacity="0.18" animate={{ scale: [1, 1.08, 1] }} transition={{ duration: 1.4, repeat: Infinity }} />
      <circle cx="270" cy="178" r="24" fill="var(--accent-violet)" />
      <text x="247" y="183" fill="white" fontSize="13" fontFamily="var(--font-jetbrains)">ML</text>
      <g transform="translate(318 190)">
        {Array.from({ length: 25 }, (_, index) => (
          <rect
            key={index}
            x={(index % 5) * 20}
            y={Math.floor(index / 5) * 20}
            width="18"
            height="18"
            rx="4"
            fill="url(#heat)"
            opacity={0.2 + ((index * 17) % 70) / 100}
          />
        ))}
      </g>
      <text x="54" y="312" fill="var(--ink-secondary)" fontSize="13" fontFamily="var(--font-jetbrains)">
        R² = real · MAE = real · drift calibrated
      </text>
    </motion.svg>
  );
}
