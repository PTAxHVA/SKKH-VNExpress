"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface Point {
  index: number;
  truth: number;
  predicted: number;
}

export function PredictionLineChart({ data }: { data: Point[] }) {
  return (
    <div className="h-[300px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
          <CartesianGrid stroke="var(--line-subtle)" strokeDasharray="4 8" />
          <XAxis dataKey="index" tick={{ fill: "var(--ink-muted)", fontSize: 12 }} />
          <YAxis tick={{ fill: "var(--ink-muted)", fontSize: 12 }} width={54} />
          <Tooltip
            contentStyle={{
              background: "var(--bg-surface)",
              border: "1px solid var(--line-subtle)",
              borderRadius: 16,
              color: "var(--ink-primary)"
            }}
          />
          <Line type="monotone" dataKey="truth" stroke="var(--accent-bio)" strokeWidth={2} dot={false} name="Ground truth" />
          <Line type="monotone" dataKey="predicted" stroke="var(--accent-warn)" strokeWidth={2} dot={false} name="Predicted" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
