# SKKH 2026 Website Showcase

Website Next.js cho đề tài "Tích hợp thị giác máy tính và mạng lưới cảm biến IoT trong ước lượng phát thải giao thông đô thị theo thời gian thực".

## Yêu cầu

- Node.js 20+
- pnpm 9+
- Dữ liệu nguồn nằm tại `../Traffic/`: `sumo_visualization.mp4`, `emissions_report.json`, `emissions_dataset.csv`

## Chạy local

```bash
pnpm install
pnpm prebuild
pnpm dev
```

## Kiểm tra production

```bash
pnpm prebuild
pnpm tsc --noEmit
pnpm lint
pnpm build
pnpm start
```

`prebuild` copy MP4 vào `public/demo/` và copy JSON/CSV vào `data/` để website deploy độc lập trên Vercel. Nếu thiếu file nguồn, script fail-fast thay vì dùng dữ liệu giả.

## Deploy Vercel

1. Push repo lên GitHub.
2. Vào Vercel Dashboard → Import Project.
3. Root Directory: `Source code/website`.
4. Framework Preset: Next.js.
5. Build Command: `pnpm build` (Vercel tự chạy `prebuild` trước `build`).
6. Install Command: `pnpm install`.
7. Environment Variables: không cần.
8. Deploy và dùng URL `*.vercel.app` cho hồ sơ VNExpress.

## Ghi chú dữ liệu

- Calculator dùng EF midpoint từ Bảng 1 và Bảng 2 của báo cáo gốc.
- Results đọc dữ liệu thật từ `data/emissions_report.json` và `data/emissions_dataset.csv`.
- Schema JSON hiện đặt metrics theo từng khí trong `gases.co2.test_metrics_ground_truth`, không phải field `metrics` top-level.
