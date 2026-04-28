"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface Point {
  index: number;
  co2: number;
  co: number;
  nox: number;
}

export function EmissionStackedBar({ data }: { data: Point[] }) {
  return (
    <div className="h-[230px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
          <CartesianGrid stroke="var(--line-subtle)" strokeDasharray="4 8" />
          <XAxis dataKey="index" tick={{ fill: "var(--ink-muted)", fontSize: 12 }} />
          <YAxis tick={{ fill: "var(--ink-muted)", fontSize: 12 }} width={46} />
          <Tooltip
            contentStyle={{
              background: "var(--bg-surface)",
              border: "1px solid var(--line-subtle)",
              borderRadius: 16,
              color: "var(--ink-primary)"
            }}
          />
          <Bar dataKey="co2" stackId="a" fill="var(--accent-bio)" name="CO₂ / 100" />
          <Bar dataKey="co" stackId="a" fill="var(--accent-cool)" name="CO" />
          <Bar dataKey="nox" stackId="a" fill="var(--accent-warn)" name="NOₓ" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
