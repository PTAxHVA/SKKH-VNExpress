import { EFIdlingTable, EFMovingTable } from "@/components/methodology/ef-table";
import { Formula } from "@/components/ui/formula";

export const METHODOLOGY_ITEMS = [
  { id: "tong-quan", title: "1. Tổng quan bài toán" },
  { id: "co-so-du-lieu", title: "2. Cơ sở dữ liệu EF" },
  { id: "khung-tinh-toan", title: "3. Khung tính toán" },
  { id: "thi-giac", title: "4. Thị giác máy tính" },
  { id: "iot-ml", title: "5. IoT + ML calibration" },
  { id: "khong-gian", title: "6. Ứng dụng smart city" },
  { id: "ket-luan", title: "7. Kết luận" }
] as const;

export function MethodologyContent() {
  return (
    <article className="prose-science max-w-none">
      <section id="tong-quan">
        <h2>1. Tổng quan về bài toán giám sát phát thải giao thông ở quy mô vi mô</h2>
        <p>Sự gia tăng nhanh của phương tiện cơ giới tại các đô thị đang tạo ra áp lực đáng kể lên chất lượng không khí và sức khỏe cộng đồng. Các phương pháp kiểm kê phát thải giao thông truyền thống có giá trị ở quy mô lớn, nhưng hạn chế khi cần đánh giá sự biến thiên phát thải theo không gian và thời gian tại các điểm giao thông cụ thể.</p>
        <p>Điểm cốt lõi của mô hình đề xuất là khả năng liên kết dữ liệu giao thông thu được từ camera với dữ liệu chất lượng không khí đo được từ cảm biến, tạo cơ sở hiệu chỉnh sai số do điều kiện khí tượng, đặc tính cảm biến và hiệu ứng phân tán.</p>
      </section>

      <section id="co-so-du-lieu">
        <h2>2. Cơ sở dữ liệu và động lực học hệ số phát thải phương tiện</h2>
        <p>Hệ số phát thải biểu thị khối lượng chất ô nhiễm phát sinh trên một đơn vị quãng đường di chuyển hoặc một đơn vị thời gian dừng chờ. Các chất thường được quan tâm gồm CO₂, NOₓ, PM2.5, PM10, CO và HC.</p>
        <Formula>EF = (αV² + βV + γ + δ/V) / (ϵV² + ζV + η) × (1 − RF)</Formula>
        <h3>Bảng 1: Hệ số phát thải khi phương tiện di chuyển</h3>
        <EFMovingTable />
        <h3>Bảng 2: Hệ số phát thải khi phương tiện dừng chờ</h3>
        <EFIdlingTable />
      </section>

      <section id="khung-tinh-toan">
        <h2>3. Khung tính toán phát thải và minh họa kịch bản tính toán</h2>
        <Formula>E_total = Σⱼ (NV_m,j × TD × EF_m,j(V)) + Σⱼ (NV_I,j × T_I × EF_I,j)</Formula>
        <p>Ví dụ PDF: 2 xe máy ở 25 km/h và 2 ô tô con ở 40 km/h trên đoạn 0.2 km, dừng chờ 1.5 phút. E_moving = 18 + 56 = 74 g CO₂; E_idling = 10.5 + 63.9 = 74.4 g CO₂; E_total = 148.4 g CO₂.</p>
        <Formula>s = sf / (1 + a(v/c)^b)</Formula>
      </section>

      <section id="thi-giac">
        <h2>4. Kiến trúc hệ thống thị giác máy tính và xử lý biên</h2>
        <p>Khối cốt lõi là mô hình phát hiện đối tượng thuộc họ YOLO, kết hợp DeepSORT hoặc ByteTrack để gán ID xuyên suốt video, theo dõi thời gian lưu trú, hướng chuyển động và trạng thái dừng chờ.</p>
        <Formula>V = D / T × 3.6</Formula>
        <p>Điện toán biên giúp giảm băng thông truyền tải, tăng tốc phản hồi và hạn chế rủi ro quyền riêng tư do không cần truyền toàn bộ video thô về trung tâm.</p>
      </section>

      <section id="iot-ml">
        <h2>5. Mạng cảm biến IoT và quy trình hiệu chỉnh điểm nóng bằng học máy</h2>
        <p>Low-Cost Sensors đo PM2.5, PM10, NO₂, CO, eCO₂ và O₃ với chi phí thấp nhưng chịu drift và cross-sensitivity. Học máy hiệu chuẩn tín hiệu theo chuỗi thời gian gồm dữ liệu đếm xe, E_total, nhiệt độ, độ ẩm và dữ liệu tham chiếu AQMS.</p>
        <Formula>∂c/∂t = -(∂Fx/∂x + ∂Fy/∂y + ∂Fz/∂z) + Rₙ</Formula>
      </section>

      <section id="khong-gian">
        <h2>6. Biểu diễn không gian phát thải và khả năng ứng dụng trong đô thị thông minh</h2>
        <p>Dữ liệu đầu ra được gắn với tọa độ không gian để đưa vào GIS. IDW hoặc Kriging có thể xây dựng bản đồ nhiệt theo từng thời điểm trong ngày, giờ cao điểm, ngày, tuần và tháng.</p>
        <p>Ứng dụng chính gồm điều khiển đèn tín hiệu thích ứng, lộ trình ít ô nhiễm, quy hoạch đô thị và phát hiện nhóm phương tiện có nguy cơ phát thải vượt mức.</p>
      </section>

      <section id="ket-luan">
        <h2>7. Kết luận</h2>
        <p>Mô hình tích hợp thị giác máy tính, điện toán biên và mạng cảm biến IoT cho phép mô tả chi tiết hơn sự biến thiên phát thải theo không gian và thời gian. Kết quả cần được hiểu như công cụ hỗ trợ đánh giá và tiếp tục kiểm chứng bằng dữ liệu thực nghiệm hiện trường.</p>
      </section>
    </article>
  );
}
