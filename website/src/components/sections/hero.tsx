"use client";

import { motion } from "framer-motion";
import { ArrowDown, Play } from "lucide-react";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { HeroVisual } from "@/components/sections/hero-visual";

const lines = ["Mỗi nút giao là", "một điểm nóng", "phát thải."];

export function Hero() {
  return (
    <section id="hero" className="relative min-h-screen overflow-hidden pt-32">
      <div className="absolute inset-x-0 top-0 h-[42rem] bg-[radial-gradient(circle_at_82%_18%,oklch(78%_0.18_155_/_0.16),transparent_26rem)]" />
      <Container className="relative grid min-h-[calc(100vh-8rem)] items-center gap-12 pb-20 lg:grid-cols-[1fr_0.85fr]">
        <div>
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, delay: 0.1 }}
            className="mb-7 text-xs font-bold uppercase tracking-[0.22em] text-bio"
          >
            SÁNG KIẾN KHOA HỌC 2026 · MÔI TRƯỜNG · SÁNG KIẾN XANH
          </motion.p>
          <h1 className="max-w-5xl font-serif text-display leading-[0.88] tracking-[-0.055em] text-ink-primary">
            {lines.map((line, index) => (
              <motion.span
                key={line}
                className="block overflow-hidden pb-2"
                initial={{ opacity: 0, clipPath: "inset(100% 0 0 0)" }}
                animate={{ opacity: 1, clipPath: "inset(0% 0 0 0)" }}
                transition={{ duration: 0.55, delay: 0.2 + index * 0.16, ease: [0.16, 1, 0.3, 1] }}
              >
                {line === "một điểm nóng" ? (
                  <span className="relative inline-block">
                    một <span className="italic text-warn">điểm nóng</span>
                    <span className="absolute -bottom-1 left-0 h-2 w-full overflow-hidden rounded-full">
                      <span className="block h-full rounded-full bg-gradient-to-r from-warn via-bio to-cool opacity-80 [animation:underline-flow_2.8s_ease-in-out_infinite_alternate]" />
                    </span>
                  </span>
                ) : (
                  line
                )}
              </motion.span>
            ))}
          </h1>
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.68 }}
            className="mt-7 max-w-2xl text-xl leading-8 text-ink-secondary"
          >
            Hệ thống ước lượng phát thải giao thông đô thị theo thời gian thực — tích hợp thị giác máy tính, mạng cảm biến IoT và học máy để biến mọi camera giao thông thành một trạm quan trắc môi trường.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 12, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.3, delay: 0.88 }}
            className="mt-9 flex flex-col gap-3 sm:flex-row"
          >
            <Button asChild>
              <a href="#giai-phap">
                Khám phá giải pháp <ArrowDown className="ml-2 inline size-4" />
              </a>
            </Button>
            <Button asChild variant="ghost">
              <a href="#demo">
                <Play className="mr-2 inline size-4 fill-current" /> Xem video demo
              </a>
            </Button>
          </motion.div>
        </div>
        <motion.div initial={{ opacity: 0, filter: "blur(12px)" }} animate={{ opacity: 1, filter: "blur(0px)" }} transition={{ duration: 0.7, delay: 0.9 }}>
          <HeroVisual />
        </motion.div>
      </Container>
    </section>
  );
}
