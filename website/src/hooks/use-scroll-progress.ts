"use client";

import { useScroll } from "framer-motion";

export function useScrollProgress() {
  const { scrollYProgress } = useScroll();
  return scrollYProgress;
}
