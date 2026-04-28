"use client";

import type { ComponentProps } from "react";
import * as ScrollAreaPrimitive from "@radix-ui/react-scroll-area";
import { cn } from "@/lib/utils";

export function ScrollArea({
  className,
  children,
  ...props
}: ComponentProps<typeof ScrollAreaPrimitive.Root>) {
  return (
    <ScrollAreaPrimitive.Root className={cn("overflow-hidden", className)} {...props}>
      <ScrollAreaPrimitive.Viewport className="size-full">{children}</ScrollAreaPrimitive.Viewport>
      <ScrollAreaPrimitive.Scrollbar className="flex touch-none select-none bg-bg-surface p-0.5" orientation="vertical">
        <ScrollAreaPrimitive.Thumb className="relative flex-1 rounded-full bg-line-strong" />
      </ScrollAreaPrimitive.Scrollbar>
    </ScrollAreaPrimitive.Root>
  );
}
