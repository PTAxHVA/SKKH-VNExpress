"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

export const Sheet = Dialog.Root;
export const SheetTrigger = Dialog.Trigger;
export const SheetClose = Dialog.Close;

export function SheetContent({ className, children, ...props }: ComponentProps<typeof Dialog.Content>) {
  return (
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm" />
      <Dialog.Content
        className={cn("fixed right-0 top-0 z-50 h-dvh w-[min(88vw,24rem)] border-l border-line-subtle bg-bg-base p-6 shadow-card-dark", className)}
        {...props}
      >
        {children}
        <Dialog.Close className="absolute right-5 top-5 rounded-full p-2 text-ink-secondary hover:text-ink-primary" aria-label="Đóng menu">
          <X className="size-5" />
        </Dialog.Close>
      </Dialog.Content>
    </Dialog.Portal>
  );
}
