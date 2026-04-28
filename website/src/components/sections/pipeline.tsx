"use client";

import { useRef } from "react";
import { motion, useScroll } from "framer-motion";
import { Container } from "@/components/ui/container";
import { Eyebrow } from "@/components/ui/eyebrow";
import { PipelineLayerText } from "@/components/sections/pipeline-layer-text";
import { PipelineVisualLayer1 } from "@/components/sections/pipeline-visual-layer-1";
import { PipelineVisualLayer2 } from "@/components/sections/pipeline-visual-layer-2";
import { PipelineVisualLayer3 } from "@/components/sections/pipeline-visual-layer-3";

export function PipelineSection() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });

  return (
    <section id="giai-phap" ref={ref} className="relative min-h-[300vh]">
      <div className="sticky top-0 flex min-h-screen items-center py-24">
        <Container className="grid gap-10 lg:grid-cols-[0.58fr_0.42fr]">
          <div className="relative min-h-[360px] overflow-hidden rounded-[36px] border border-line-subtle bg-bg-elevated/50 shadow-card-dark backdrop-blur-xl lg:min-h-[560px]">
            <PipelineVisualLayer1 progress={scrollYProgress} />
            <PipelineVisualLayer2 progress={scrollYProgress} />
            <PipelineVisualLayer3 progress={scrollYProgress} />
          </div>
          <div className="max-h-[78vh] overflow-y-auto pr-2">
            <Eyebrow>03 / GIẢI PHÁP</Eyebrow>
            <h2 className="mt-5 font-serif text-headline leading-[0.98] tracking-[-0.04em]">
              Pipeline 3 lớp để biến camera thành trạm quan trắc.
            </h2>
            <p className="mt-6 text-lg leading-8 text-ink-secondary">
              Mỗi camera giao thông trở thành một cảm biến môi trường thông qua chuỗi xử lý: nhận diện → ước lượng động học → hiệu chuẩn bằng dữ liệu thực địa.
            </p>
            <div className="mt-10 space-y-14">
              <PipelineLayerText eyebrow="Layer 01" title="THỊ GIÁC MÁY TÍNH">
                <p>YOLO phát hiện và phân loại xe (motorbike, car, truck, bus). DeepSORT/ByteTrack gán ID xuyên suốt video, tránh đếm trùng.</p>
                <p>Hệ thống đồng thời trích xuất:</p>
                <ul className="list-disc space-y-2 pl-5">
                  <li>Vận tốc tức thời từ homography hai chiều: V = D/T × 3.6</li>
                  <li>Thời gian dừng chờ tại nút giao</li>
                  <li>Trạng thái lane (bike / main / left)</li>
                  <li>Mật độ và thành phần dòng xe</li>
                </ul>
                <p>→ Output: bộ siêu dữ liệu giao thông ở độ phân giải giây.</p>
              </PipelineLayerText>
              <PipelineLayerText eyebrow="Layer 02" title="MÔ HÌNH ĐỘNG HỌC PHÁT THẢI">
                <p>Hệ số phát thải (EF) tham chiếu COPERT/MOVES, tách hai chế độ vận hành:</p>
                <ul className="list-disc space-y-2 pl-5">
                  <li>EF_moving (g/km) — phụ thuộc vận tốc V theo phương trình EF = (αV² + βV + γ + δ/V) / (εV² + ζV + η)</li>
                  <li>EF_idling (g/phút) — phụ thuộc loại xe và phụ tải động cơ</li>
                </ul>
                <p>Tổng phát thải tại một quan sát: E_total = Σⱼ NV_m,j × TD × EF_m,j(V) + Σⱼ NV_I,j × T_I × EF_I,j</p>
                <p>Hiệu chỉnh vận tốc dòng xe theo BPR khi mật độ cao: s = sf / (1 + a(v/c)^b)</p>
                <p>→ Output: bản đồ phát thải vi mô theo thời gian thực.</p>
              </PipelineLayerText>
              <PipelineLayerText eyebrow="Layer 03" title="CẢM BIẾN IOT + HỌC MÁY">
                <p>Mạng Low-Cost Sensors (LCS) đo CO₂, NOₓ, PM2.5, PM10, CO, O₃ với mật độ cao nhưng có drift và cross-sensitivity.</p>
                <ul className="list-disc space-y-2 pl-5">
                  <li>Random Forest / GPR / SVM hiệu chuẩn drift theo thời tiết ẩn</li>
                  <li>Graph Attention Network dung hợp đa cảm biến láng giềng</li>
                  <li>Closed-loop validation giữa nguồn (camera) và nồng độ (sensor)</li>
                </ul>
                <p>Mô hình phân tán Fick: ∂c/∂t = -(∂Fx/∂x + ∂Fy/∂y + ∂Fz/∂z) + Rₙ</p>
                <p>→ Output: chỉ số AQI tiệm cận thiết bị phòng thí nghiệm, dù phần cứng rẻ tiền.</p>
              </PipelineLayerText>
            </div>
          </div>
        </Container>
      </div>
      <motion.div className="absolute bottom-0 left-0 h-px w-full bg-gradient-to-r from-transparent via-bio to-transparent" />
    </section>
  );
}
