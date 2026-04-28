import * as React from "react";
import { cn } from "@/lib/utils";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "border border-line-subtle bg-bg-elevated/60 shadow-card-dark backdrop-blur-xl",
        className
      )}
      {...props}
    />
  );
}
