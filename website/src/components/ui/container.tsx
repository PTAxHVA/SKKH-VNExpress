import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface ContainerProps extends HTMLAttributes<HTMLDivElement> {
  size?: "default" | "narrow" | "wide";
}

const sizes = {
  default: "max-w-[1280px]",
  narrow: "max-w-[920px]",
  wide: "max-w-[1440px]"
} as const;

export function Container({ className, size = "default", ...props }: ContainerProps) {
  return <div className={cn("mx-auto w-full px-6 md:px-10 lg:px-16", sizes[size], className)} {...props} />;
}
