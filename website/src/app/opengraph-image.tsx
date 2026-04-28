import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "SKKH 2026 giao thông xanh";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "linear-gradient(135deg,#071216,#192235)",
          color: "#effff8",
          padding: 72,
          fontFamily: "Inter"
        }}
      >
        <div style={{ color: "#47f0a1", letterSpacing: 6, fontSize: 24 }}>
          SÁNG KIẾN KHOA HỌC 2026 · SÁNG KIẾN XANH
        </div>
        <div style={{ fontSize: 82, lineHeight: 0.95, letterSpacing: -4, maxWidth: 980 }}>
          Mỗi nút giao là một điểm nóng phát thải.
        </div>
        <div style={{ display: "flex", gap: 20, color: "#9fb2b6", fontSize: 28 }}>
          <span>Computer Vision</span>
          <span>→</span>
          <span>Emission Model</span>
          <span>→</span>
          <span>IoT + ML</span>
        </div>
      </div>
    ),
    size
  );
}
