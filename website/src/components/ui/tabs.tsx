"use client";

import type { ComponentProps } from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/utils";

export const Tabs = TabsPrimitive.Root;

export function TabsList({ className, ...props }: ComponentProps<typeof TabsPrimitive.List>) {
  return <TabsPrimitive.List className={cn("inline-flex rounded-full border border-line-subtle bg-bg-base/60 p-1", className)} {...props} />;
}

export function TabsTrigger({ className, ...props }: ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cn("rounded-full px-3 py-1.5 text-xs font-semibold text-ink-muted transition data-[state=active]:bg-bio data-[state=active]:text-slate-950", className)}
      {...props}
    />
  );
}

export const TabsContent = TabsPrimitive.Content;
