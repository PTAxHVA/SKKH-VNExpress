"use client";

import type { ComponentProps } from "react";
import * as SliderPrimitive from "@radix-ui/react-slider";
import { cn } from "@/lib/utils";

export function Slider({
  className,
  ...props
}: ComponentProps<typeof SliderPrimitive.Root>) {
  return (
    <SliderPrimitive.Root className={cn("relative flex h-5 w-full touch-none select-none items-center", className)} {...props}>
      <SliderPrimitive.Track className="relative h-2 grow overflow-hidden rounded-full bg-bg-base">
        <SliderPrimitive.Range className="absolute h-full rounded-full bg-gradient-to-r from-bio to-warn" />
      </SliderPrimitive.Track>
      <SliderPrimitive.Thumb
        className="block size-5 rounded-full border border-bio bg-ink-primary shadow-glow-bio transition focus-visible:outline-none"
        aria-label="Điều chỉnh giá trị"
      />
    </SliderPrimitive.Root>
  );
}
