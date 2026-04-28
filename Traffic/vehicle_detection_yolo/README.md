# Vehicle Type Detection with YOLO

Thư mục này chứa một workspace riêng cho bài toán nhận diện loại xe bằng YOLO.

## Thành phần

- `ultralytics/`: repo YOLO chính thức từ Ultralytics
- `.venv/`: môi trường Python 3.11 riêng cho workspace này
- `models/yolo26s.pt`: pretrained weight nhạy hơn cho xe nhỏ
- `data/bellevue_ne8th_190824_short.mp4`: clip giao lộ Bellevue đã cắt ngắn
- `runs/vehicle_types/`: kết quả detect đã annotate

## Chạy lại

```bash
cd /Users/tinngo/Documents/Traffic
./vehicle_detection_yolo/run_vehicle_detection.sh
```

## Các lớp xe đang detect

- `car`

Mặc định demo hiện chỉ detect `car` với class ID COCO `2`, dùng model `yolo26s.pt` với `conf=0.12`, `imgsz=1280` để ưu tiên độ ổn định trên clip giao lộ Bellevue.

Nếu cần bật lại cả `motorcycle`, chỉ việc đổi `classes=2` thành `classes=2,3` trong `run_vehicle_detection.sh`.

Video mặc định hiện là một clip giao lộ thật từ bộ Bellevue Traffic Video Dataset, phù hợp hơn cho bài toán đếm xe ở nút giao.
