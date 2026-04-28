"use client";

import { useEffect, useState } from "react";

export function useReducedMotion() {
  const [isReduced, setIsReduced] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    setIsReduced(media.matches);
    const onChange = () => setIsReduced(media.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  return isReduced;
}
