import { AlertTriangle, Footprints, TrafficCone, Trees } from "lucide-react";
import { Container } from "@/components/ui/container";
import { ImpactCard } from "@/components/ui/impact-card";
import { SectionHeading } from "@/components/ui/section-heading";

const impacts = [
  {
    icon: TrafficCone,
    title: "Đèn tín hiệu thích ứng",
    body: "Tích hợp dữ liệu phát thải vào điều khiển tín hiệu. Hệ thống không chỉ tối ưu lưu lượng xe mà còn xét mục tiêu giảm thời gian dừng chờ tại các vị trí có nguy cơ ô nhiễm cao.",
    accent: "bio" as const,
    className: "md:translate-y-8"
  },
  {
    icon: Footprints,
    title: "Lộ trình ít ô nhiễm",
    body: "Bản đồ phát thải vi mô hỗ trợ xây dựng lộ trình an toàn hơn cho người đi bộ, người đi xe đạp và các nhóm nhạy cảm như trẻ em, người cao tuổi, người có bệnh lý hô hấp.",
    accent: "cool" as const
  },
  {
    icon: Trees,
    title: "Quy hoạch đô thị",
    body: "Thông tin tích lũy dài hạn hỗ trợ xác định khu vực cần bổ sung cây xanh, tổ chức lại luồng giao thông, hoặc bố trí biện pháp giảm tiếp xúc ô nhiễm gần trường học và khu dân cư.",
    accent: "violet" as const
  },
  {
    icon: AlertTriangle,
    title: "Phát hiện xe vi phạm",
    body: "Khi kết hợp nhận diện hình ảnh với phân tích hành vi và dấu hiệu khí xả bất thường, hệ thống hỗ trợ phát hiện nhóm phương tiện có nguy cơ phát thải vượt mức để phục vụ kiểm tra chuyên sâu.",
    accent: "warn" as const,
    className: "md:translate-y-8"
  }
];

export function ImpactSection() {
  return (
    <section id="tac-dong" className="py-[var(--section-y)]">
      <Container>
        <SectionHeading
          eyebrow="08 / TÁC ĐỘNG"
          title="Từ dữ liệu phát thải đến quyết định đô thị."
          lead="Bốn hướng ứng dụng bám sát use case trong báo cáo gốc, tập trung vào giao thông thích ứng và giảm phơi nhiễm ô nhiễm."
        />
        <div className="mt-12 grid gap-5 md:grid-cols-2">
          {impacts.map((impact) => (
            <ImpactCard key={impact.title} {...impact} />
          ))}
        </div>
      </Container>
    </section>
  );
}
