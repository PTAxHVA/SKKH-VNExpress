import { promises as fs } from "node:fs";
import path from "node:path";

const ROOT = process.cwd();
const TRAFFIC = path.resolve(ROOT, "../Traffic");

const tasks = [
  {
    src: path.join(TRAFFIC, "sumo_visualization.mp4"),
    dst: path.join(ROOT, "public/demo/sumo_visualization.mp4")
  },
  {
    src: path.join(TRAFFIC, "emissions_report.json"),
    dst: path.join(ROOT, "data/emissions_report.json")
  },
  {
    src: path.join(TRAFFIC, "emissions_dataset.csv"),
    dst: path.join(ROOT, "data/emissions_dataset.csv")
  }
];

for (const { src, dst } of tasks) {
  await fs.access(src);
  await fs.mkdir(path.dirname(dst), { recursive: true });
  await fs.copyFile(src, dst);
  console.log(`✓ ${path.basename(src)}`);
}

const poster = `<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
<defs>
<linearGradient id="bg" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#081316"/><stop offset="1" stop-color="#192235"/></linearGradient>
<linearGradient id="road" x1="0" x2="1"><stop stop-color="#37f2a5"/><stop offset="1" stop-color="#ff9b38"/></linearGradient>
</defs>
<rect width="1280" height="720" fill="url(#bg)"/>
<path d="M150 560 C420 420 650 420 1130 160" fill="none" stroke="url(#road)" stroke-width="18" stroke-linecap="round" opacity=".7"/>
<path d="M150 160 C430 310 720 320 1130 560" fill="none" stroke="#56b8ff" stroke-width="14" stroke-linecap="round" opacity=".35"/>
<circle cx="640" cy="360" r="76" fill="#37f2a5" opacity=".14"/>
<path d="M612 310 L705 360 L612 410 Z" fill="#eafff6"/>
<text x="80" y="104" fill="#eafff6" font-family="Inter,Arial" font-size="38" font-weight="700">SUMO mô phỏng — Fixed-Time vs Q-Learning</text>
<text x="82" y="646" fill="#9fb2b6" font-family="Inter,Arial" font-size="24">35% xe máy · 65% ô tô · queue + delay + switch penalty</text>
</svg>`;

await fs.writeFile(path.join(ROOT, "public/demo/sumo_poster.svg"), poster);
