"use client";

import { motion, type MotionValue, useTransform } from "framer-motion";

interface Props {
  progress: MotionValue<number>;
}

const boxes = [
  { x: 82, y: 96, w: 76, h: 38, label: "motorbike 0.94", id: "ID 07" },
  { x: 190, y: 158, w: 98, h: 52, label: "car 0.91", id: "ID 12" },
  { x: 330, y: 108, w: 84, h: 44, label: "truck 0.88", id: "ID 21" },
  { x: 382, y: 240, w: 74, h: 36, label: "motorbike 0.92", id: "ID 25" }
];

export function PipelineVisualLayer1({ progress }: Props) {
  const opacity = useTransform(progress, [0, 0.05, 0.3, 0.38], [0, 1, 1, 0]);
  const scale = useTransform(progress, [0, 0.3], [1, 0.96]);

  return (
    <motion.svg style={{ opacity, scale }} className="absolute inset-0 size-full" viewBox="0 0 540 360" aria-label="Layer 1 thị giác máy tính">
      <rect x="24" y="28" width="492" height="304" rx="28" fill="var(--bg-base)" opacity="0.68" />
      <path d="M70 300 L210 46 M210 300 L300 46 M350 300 L330 46 M470 300 L390 46" stroke="var(--grid-line)" strokeWidth="2" />
      <path d="M48 236 C176 188 348 184 492 132" stroke="var(--accent-cool)" strokeWidth="3" fill="none" opacity="0.55" />
      <path d="M58 280 C188 228 370 228 500 194" stroke="var(--accent-bio)" strokeWidth="3" fill="none" opacity="0.55" />
      <text x="54" y="58" fill="var(--ink-muted)" fontSize="13" fontFamily="var(--font-jetbrains)">
        lane: bike | main | left
      </text>
      {boxes.map((box, index) => (
        <motion.g key={box.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.12 }}>
          <rect x={box.x} y={box.y} width={box.w} height={box.h} rx="8" fill="transparent" stroke="var(--accent-bio)" strokeWidth="2" />
          <rect x={box.x} y={box.y - 22} width={box.w + 28} height="18" rx="6" fill="var(--accent-bio)" opacity="0.16" />
          <text x={box.x + 7} y={box.y - 9} fill="var(--accent-bio)" fontSize="10" fontFamily="var(--font-jetbrains)">
            {box.label}
          </text>
          <text x={box.x + 6} y={box.y + box.h - 8} fill="var(--ink-primary)" fontSize="10" fontFamily="var(--font-jetbrains)">
            {box.id}
          </text>
          <path d={`M${box.x + box.w + 8} ${box.y + box.h / 2} l26 -10`} stroke="var(--accent-warn)" strokeWidth="3" strokeLinecap="round" />
        </motion.g>
      ))}
    </motion.svg>
  );
}
