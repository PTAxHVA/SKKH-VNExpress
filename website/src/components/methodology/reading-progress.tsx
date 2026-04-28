"use client";

import { motion } from "framer-motion";
import { useScrollProgress } from "@/hooks/use-scroll-progress";

export function ReadingProgress() {
  const progress = useScrollProgress();

  return (
    <motion.div
      className="fixed left-0 top-0 z-[70] h-1 origin-left bg-bio"
      style={{ scaleX: progress, width: "100%" }}
    />
  );
}
