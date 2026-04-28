export function MiniHeatmap() {
  const cells = Array.from({ length: 64 }, (_, index) => {
    const intensity = 0.18 + ((index * 37 + Math.floor(index / 8) * 19) % 80) / 100;
    return intensity;
  });

  return (
    <div className="grid grid-cols-8 gap-1">
      {cells.map((intensity, index) => (
        <div
          key={index}
          className="aspect-square rounded-md"
          style={{
            background: `color-mix(in oklch, var(--accent-warn) ${intensity * 100}%, var(--accent-bio))`,
            opacity: 0.42 + intensity * 0.58
          }}
        />
      ))}
    </div>
  );
}
