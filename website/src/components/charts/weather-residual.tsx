"use client";

import { ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";

interface Point {
  humidity: number;
  residual: number;
  temp: number;
}

export function WeatherResidualScatter({ data }: { data: Point[] }) {
  if (data.length === 0) {
    return <p className="text-sm leading-6 text-ink-muted">[Cập nhật khi có dữ liệu thời tiết]</p>;
  }

  return (
    <div className="h-[230px]">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
          <XAxis type="number" dataKey="humidity" name="Độ ẩm" tick={{ fill: "var(--ink-muted)", fontSize: 12 }} />
          <YAxis type="number" dataKey="residual" name="Residual" tick={{ fill: "var(--ink-muted)", fontSize: 12 }} width={54} />
          <ZAxis type="number" dataKey="temp" range={[40, 160]} />
          <Tooltip
            cursor={{ strokeDasharray: "3 3" }}
            contentStyle={{
              background: "var(--bg-surface)",
              border: "1px solid var(--line-subtle)",
              borderRadius: 16,
              color: "var(--ink-primary)"
            }}
          />
          <Scatter name="Residual" data={data} fill="var(--accent-cool)" />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
