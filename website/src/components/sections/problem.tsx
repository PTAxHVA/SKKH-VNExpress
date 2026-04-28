"use client";

import { motion } from "framer-motion";
import { BigStat } from "@/components/ui/big-stat";
import { Container } from "@/components/ui/container";
import { Eyebrow } from "@/components/ui/eyebrow";

const points = [
  {
    title: "Mô hình vĩ mô",
    body: "Phù hợp thống kê quốc gia, không phản ánh điểm nóng cục bộ tại nút giao, đoạn đường ùn tắc."
  },
  {
    title: "Camera giao thông",
    body: "Phần lớn dừng ở phát hiện và đếm xe, chưa nội suy sang phát thải động học."
  },
  {
    title: "Cảm biến IoT chi phí thấp",
    body: "Đo được nồng độ ô nhiễm nhưng không gắn với nguồn phát từ giao thông theo thời gian thực."
  }
];

export function ProblemSection() {
  return (
    <section id="van-de" className="relative py-[var(--section-y)]">
      <Container className="grid gap-12 lg:grid-cols-[5fr_7fr]">
        <div>
          <Eyebrow className="mb-6">02 / VẤN ĐỀ</Eyebrow>
          <BigStat value={85} label="phát thải vi mô tại nút giao bị bỏ sót bởi mô hình vĩ mô" />
        </div>
        <div>
          <h2 className="font-serif text-headline leading-[0.98] tracking-[-0.04em] text-ink-primary">
            Khoảng trống giữa &quot;đếm xe&quot; và &quot;đo phát thải&quot;
          </h2>
          <p className="mt-7 max-w-3xl text-xl leading-9 text-ink-secondary">
            Trong nhiều năm, các phương pháp kiểm kê phát thải giao thông chủ yếu được xây dựng theo hướng vĩ mô, dựa trên dữ liệu tổng hợp như lượng nhiên liệu tiêu thụ hoặc số phương tiện đăng ký. Cách này có giá trị ở quy mô lớn nhưng hạn chế khi cần đánh giá sự biến thiên phát thải theo không gian và thời gian tại các điểm giao thông cụ thể.
          </p>
          <div className="mt-10 grid gap-4">
            {points.map((point, index) => (
              <motion.article
                key={point.title}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-15%" }}
                transition={{ duration: 0.45, delay: index * 0.1, ease: [0.16, 1, 0.3, 1] }}
                className="rounded-[1.5rem] border border-line-subtle bg-bg-surface/45 p-6 shadow-card-dark backdrop-blur-xl odd:mr-10 even:ml-10 max-sm:mx-0"
              >
                <h3 className="text-xl font-semibold tracking-[-0.03em] text-ink-primary">{point.title}</h3>
                <p className="mt-3 leading-7 text-ink-secondary">{point.body}</p>
              </motion.article>
            ))}
          </div>
        </div>
      </Container>
    </section>
  );
}
