# AI Traffic Light Demo

Demo mô phỏng tối ưu đèn giao thông bằng `Q-learning`, chạy mặc định trên backend `SUMO`.
Project hiện có hai backend:

- `sumo`: mô phỏng giao lộ thật hơn, có `TraCI`, exact replay theo xe, lane-level queue, throughput và delay.
- `toy`: mô hình nhẹ trong bộ nhớ, tiện để debug nhanh hoặc xuất video MP4.

Mô hình inbound hiện tại dùng 3 lane cho mỗi hướng:

- `left`: làn sát tim đường cho xe rẽ trái
- `main`: làn chính cho xe ô tô và một phần xe máy đi thẳng/rẽ phải
- `bike`: làn sát lề dành ưu tiên cho xe máy; xe máy có thể chạy cả `bike` và `main`

Trong `SUMO`, các lane inbound được map theo chỉ số nội bộ `0=bike`, `1=main`, `2=left`.

## Cấu trúc chính

- [traffic_ai_demo.py](/Users/tinngo/Documents/Traffic/traffic_ai_demo.py): file chính để train, evaluate, export trace và build replay.
- [sumo_minimal](/Users/tinngo/Documents/Traffic/sumo_minimal): mạng giao lộ SUMO tối thiểu dùng cho demo.
- `vendor/sumo-official/`: bản SUMO local dùng trực tiếp trong project.
- `.venv-sumo/`: Python env local có `traci` và `sumolib`.

## Chạy nhanh

Với backend `SUMO` mặc định:

```bash
cd /Users/tinngo/Documents/Traffic
./.venv-sumo/bin/python traffic_ai_demo.py
```

Ví dụ một lần chạy rõ ràng hơn:

```bash
./.venv-sumo/bin/python traffic_ai_demo.py --backend sumo --train-episodes 40 --eval-episodes 5 --steps 200 --fixed-cycle 30
```

Nếu muốn chạy bản nhẹ:

```bash
python3 traffic_ai_demo.py --backend toy
```

## Xuất số liệu

```bash
./.venv-sumo/bin/python traffic_ai_demo.py \
  --backend sumo \
  --train-episodes 40 \
  --eval-episodes 5 \
  --steps 200 \
  --fixed-cycle 30 \
  --export-json sumo_summary.json \
  --export-csv sumo_trace.csv
```

File tạo ra:

- `sumo_summary.json`: chỉ số tổng hợp như `avg_queue`, `avg_delay`, `throughput`, `switches`, `completed_vehicles`
- `sumo_trace.csv`: trace theo từng bước để phân tích thêm bằng Excel, pandas hoặc notebook

## Bộ đề khí thải

Repo hiện có thêm một benchmark ML để suy ra 4 hệ số khí thải ẩn:

- xe máy đứng yên
- xe máy chạy
- ô tô đứng yên
- ô tô chạy

Dataset được tạo từ trace `SUMO` theo từng cửa sổ `10 frame`. Mỗi sample gồm:

- `ground_truth_motorcycle_stopped_count`, `ground_truth_motorcycle_moving_count`
- `ground_truth_car_stopped_count`, `ground_truth_car_moving_count`
- `observed_motorcycle_stopped_count`, `observed_motorcycle_moving_count`
- `observed_car_stopped_count`, `observed_car_moving_count`
- `ground_truth_total_co2`, `observed_total_co2`
- nếu bật nhiều khí cùng lúc thì có thêm `ground_truth_total_co`, `observed_total_co`, `ground_truth_total_nox`, `observed_total_nox`

Ground truth hiện không còn là tổng tuyến tính đơn giản theo số xe nữa. Mỗi cửa sổ `10 frame` được sinh từ:

- hệ số cơ sở theo 4 nhóm `motorcycle/car x stopped/moving`
- biến ẩn không quan sát theo từng xe như `detailed subtype`
- tốc độ và gia tốc theo từng snapshot
- thời tiết ẩn theo từng cửa sổ như `temp`, `rain`, `humidity`, `wind`

Mô hình benchmark hiện vẫn fit một `linear regression` trên feature quan sát `observed_*`, nên đây là một bài toán `model misspecification` có chủ đích: model chỉ thấy counts thô, còn ground truth được sinh từ cơ chế phi tuyến và có biến ẩn.

Để bài toán bớt quá sạch, benchmark mặc định thêm noise đo đạc:

- noise tương đối cho số đếm xe: `--emissions-count-noise-std 0.03`
- noise tương đối cho tổng khí thải cửa sổ: `--emissions-target-noise-std 0.05`
- sensor tổng khí thải còn có drift/outlier nhẹ trong phần `observed_total_*`

Ví dụ chạy:

```bash
./.venv-sumo/bin/python traffic_ai_demo.py \
  --backend sumo \
  --train-episodes 40 \
  --eval-episodes 5 \
  --steps 200 \
  --fit-emissions \
  --emission-gases co2,co,nox
```

File tạo ra khi bật `--fit-emissions`:

- `emissions_dataset.csv`: bộ đề theo từng cửa sổ 10 frame, gồm cả cột `ground_truth_*`, `observed_*`, lỗi đo đạc và `hidden_weather_*`
- `emissions_report.json`: mô tả ground-truth nonlinear model, noise config, ground truth rates, predicted rates, MAE, RMSE, `R^2`

## HTML Replay

```bash
./.venv-sumo/bin/python traffic_ai_demo.py \
  --backend sumo \
  --train-episodes 40 \
  --eval-episodes 5 \
  --steps 200 \
  --fixed-cycle 30 \
  --visualize \
  --visualize-output sumo_visualization.html
```

Sau đó mở:

```bash
open -a Safari /Users/tinngo/Documents/Traffic/sumo_visualization.html
```

Nếu cần `MP4` để chèn slide, render trực tiếp từ replay HTML đã nhúng trace:

```bash
./.venv-video/bin/python render_sumo_mp4.py \
  --input-html sumo_visualization.html \
  --output-mp4 sumo_visualization.mp4 \
  --fps 10
```

Bản replay hiện tại có:

- so sánh song song `Fixed-Time` và `Q-Learning`
- exact replay từ `SUMO vehicle snapshots`
- zoom, pan, minimap, counter, timer
- xe xuất hiện từ rìa khung và rời khung theo mép giao lộ tự nhiên hơn
- nội suy theo `vehicle_id` giữa các snapshot để chuyển động mượt hơn
- exact replay của `SUMO` hiện hiển thị đủ `bike/main/left` và loại xe `motorcycle`

## SUMO GUI Live

Nếu muốn xem live GUI thay vì HTML replay:

```bash
./.venv-sumo/bin/python traffic_ai_demo.py \
  --backend sumo \
  --sumo-gui \
  --sumo-visualize-controller ai
```

Lưu ý:

- trên macOS, `sumo-gui` cần `XQuartz`
- sau khi cài `XQuartz`, thường cần `log out` rồi đăng nhập lại trước khi GUI mở ổn định

## Video MP4

Xuất video hiện chỉ hỗ trợ cho backend `toy`:

```bash
./.venv-video/bin/python traffic_ai_demo.py \
  --backend toy \
  --visualize \
  --export-video traffic_ai_10fps.mp4 \
  --video-fps 10
```

## Tham số quan trọng

- `--backend`: `sumo` hoặc `toy`, mặc định là `sumo`
- `--train-episodes`: số episode train
- `--eval-episodes`: số episode đánh giá
- `--steps`: số step mỗi episode, mặc định hiện là `200`
- `--fixed-cycle`: chu kỳ đổi pha của fixed-time controller
- `--ns-rate`: lưu lượng hướng Bắc-Nam
- `--ew-rate`: lưu lượng hướng Đông-Tây
- `--min-green`: thời gian xanh tối thiểu trước khi cho phép đổi pha
- `--switch-penalty`: thời gian clearance khi đổi pha
- `--left-rate`: tỉ lệ rẽ trái
- `--right-rate`: tỉ lệ rẽ phải
- `--motorcycle-rate`: tỉ lệ xe máy trong lưu lượng, mặc định `0.35`
- `--visualize`: xuất HTML replay
- `--visualize-output`: đường dẫn file HTML đầu ra
- `--trace-seed`: seed dùng cho replay
- `--export-json`: xuất summary JSON
- `--export-csv`: xuất trace CSV
- `--fit-emissions`: bật bài toán ML suy ra hệ số khí thải ẩn
- `--emission-gases`: danh sách khí, mặc định `co2`; hiện hỗ trợ thêm `co`, `nox`
- `--emissions-window`: số frame trên mỗi sample khí thải, mặc định `10`
- `--emissions-episodes`: số seed trace dùng để dựng dataset khí thải
- `--emissions-controllers`: lấy trace từ `fixed`, `ai` hoặc `both`
- `--emissions-count-noise-std`: noise tương đối cho số đếm xe trong mỗi cửa sổ
- `--emissions-target-noise-std`: noise tương đối cho tổng khí thải mỗi cửa sổ
- `--emissions-noise-seed`: seed cho noise đo đạc khí thải
- `--export-emissions-dataset`: đường dẫn CSV của bộ đề khí thải
- `--export-emissions-report`: đường dẫn JSON của báo cáo fit khí thải
- `--sumo-gui`: mở `sumo-gui`
- `--sumo-visualize-controller`: chọn replay live cho `fixed` hoặc `ai`
- `--sumo-gui-delay`: độ trễ giữa các step trong GUI
- `--export-video`: xuất video, hiện chỉ dành cho backend `toy`
- `--video-fps`: số FPS cho video

## Gợi ý phát triển tiếp

- exact replay còn có thể nâng tiếp bằng lịch sử dài hơn cho từng `vehicle_id`
- thêm baseline như `Max-Pressure` để so với `Q-learning`
- mở rộng từ 1 giao lộ sang nhiều giao lộ liên tiếp
- thêm benchmark nhiều seed và tự động xuất bảng kết quả
