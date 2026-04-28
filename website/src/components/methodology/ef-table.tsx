import { EF_IDLING, EF_MOVING } from "@/lib/ef-tables";

export function EFMovingTable() {
  const rows = Object.entries(EF_MOVING);

  return (
    <table>
      <thead>
        <tr>
          <th>Phân loại phương tiện</th>
          <th>Vận tốc tối ưu</th>
          <th>CO₂ (g/km)</th>
          <th>NOₓ (g/km)</th>
          <th>PM2.5 (g/km)</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([key, value]) => (
          <tr key={key}>
            <td>{label(key)}</td>
            <td>{value.speedRange.join("–")} km/h</td>
            <td>{value.co2.join("–")}</td>
            <td>{value.nox.join("–")}</td>
            <td>{value.pm25.join("–")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function EFIdlingTable() {
  return (
    <table>
      <thead>
        <tr>
          <th>Phân loại phương tiện</th>
          <th>CO₂ (g/min)</th>
          <th>NOₓ (g/min)</th>
          <th>PM2.5 (g/min)</th>
          <th>CO (g/min)</th>
        </tr>
      </thead>
      <tbody>
        {Object.entries(EF_IDLING).map(([key, value]) => (
          <tr key={key}>
            <td>{label(key)}</td>
            <td>{format(value.co2)}</td>
            <td>{format(value.nox)}</td>
            <td>{"pm25" in value ? format(value.pm25) : "Không đáng kể"}</td>
            <td>{format(value.co)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function format(value: number | readonly number[]) {
  return Array.isArray(value) ? value.join("–") : `~${value}`;
}

function label(key: string) {
  return key
    .replaceAll("_", " ")
    .replace("motorbike", "Xe máy")
    .replace("car gasoline", "Ô tô con chạy xăng")
    .replace("car diesel", "Ô tô con chạy diesel")
    .replace("truck", "Xe tải / xe buýt")
    .replace("ac off", "A/C tắt")
    .replace("ac on", "A/C bật");
}
