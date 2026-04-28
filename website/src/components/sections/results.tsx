import { Activity, Gauge, Wind } from "lucide-react";
import { EmissionStackedBar } from "@/components/charts/emission-stacked-bar";
import { MiniHeatmap } from "@/components/charts/mini-heatmap";
import { PredictionLineChart } from "@/components/charts/prediction-line";
import { WeatherResidualScatter } from "@/components/charts/weather-residual";
import { BentoCard } from "@/components/ui/bento-card";
import { Container } from "@/components/ui/container";
import { MetricNumber } from "@/components/ui/metric-number";
import { SectionHeading } from "@/components/ui/section-heading";
import type { EmissionSample } from "@/lib/load-emissions-dataset";
import type { EmissionsReport } from "@/lib/load-emissions-report";
import { getGasMetrics } from "@/lib/load-emissions-report";

interface ResultsSectionProps {
  report: EmissionsReport;
  dataset: EmissionSample[];
}

export function ResultsSection({ report, dataset }: ResultsSectionProps) {
  const metrics = getGasMetrics(report, "co2");
  const rates = report.gases?.co2?.predicted_rates;
  const lineData = dataset.slice(0, 50).map((sample, index) => ({
    index,
    truth: Number(sample.ground_truth_total_co2 ?? 0),
    predicted: predictCo2(sample, rates)
  }));
  const weatherData = lineData.map((point, index) => {
    const sample = dataset[index];
    return {
      humidity: Number(sample?.hidden_weather_humidity ?? 0),
      temp: Number(sample?.hidden_weather_temp_c ?? 0),
      residual: point.truth - point.predicted
    };
  }).filter((point) => point.humidity > 0);
  const gasData = dataset.slice(0, 24).map((sample, index) => ({
    index,
    co2: Number(sample.ground_truth_total_co2 ?? 0) / 100,
    co: Number(sample.ground_truth_total_co ?? 0),
    nox: Number(sample.ground_truth_total_nox ?? 0)
  }));

  return (
    <section id="ket-qua" className="py-[var(--section-y)]">
      <Container>
        <SectionHeading
          eyebrow="05 / KẾT QUẢ"
          title="Số liệu nói thay lời chúng tôi."
          lead="Benchmark học máy chạy trên trace SUMO 200 step × 5 episode, cửa sổ 10 frame, có inject noise đo đạc thực tế (3% count, 5% target)."
        />
        <div className="mt-12 grid gap-5 lg:grid-cols-12">
          <BentoCard span="lg:col-span-6 lg:row-span-2" accent="bio">
            <h3 className="mb-6 text-xl font-semibold text-ink-primary">Predicted vs Ground Truth CO₂</h3>
            <PredictionLineChart data={lineData} />
          </BentoCard>
          <BentoCard span="lg:col-span-3" accent="cool">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cool">R²</p>
            <div className="mt-8"><MetricNumber value={metrics.r2} decimals={3} /></div>
          </BentoCard>
          <BentoCard span="lg:col-span-3" accent="warn">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-warn">MAE</p>
            <div className="mt-8"><MetricNumber value={metrics.mae} unit="g/frame" decimals={1} /></div>
          </BentoCard>
          <BentoCard span="lg:col-span-6" accent="violet">
            <h3 className="mb-6 text-xl font-semibold text-ink-primary">Emission breakdown by gas</h3>
            <EmissionStackedBar data={gasData} />
          </BentoCard>
          <BentoCard span="lg:col-span-6" accent="cool">
            <h3 className="mb-6 text-xl font-semibold text-ink-primary">Hidden weather impact on residuals</h3>
            <WeatherResidualScatter data={weatherData} />
          </BentoCard>
          <BentoCard span="lg:col-span-4" accent="bio">
            <Wind className="mb-8 size-8 text-bio" />
            <p className="font-mono text-6xl font-semibold text-ink-primary">5</p>
            <p className="mt-3 text-sm leading-6 text-ink-secondary">Khí được hỗ trợ: CO₂, CO, NOₓ, PM2.5, PM10</p>
          </BentoCard>
          <BentoCard span="lg:col-span-4" accent="warn">
            <Gauge className="mb-8 size-8 text-warn" />
            <p className="font-mono text-6xl font-semibold text-ink-primary">{report.window_size ?? 10}</p>
            <p className="mt-3 text-sm leading-6 text-ink-secondary">Cửa sổ phân tích</p>
          </BentoCard>
          <BentoCard span="lg:col-span-4" accent="violet">
            <Activity className="mb-6 size-8 text-violet" />
            <MiniHeatmap />
          </BentoCard>
        </div>
      </Container>
    </section>
  );
}

function predictCo2(sample: EmissionSample, rates?: Record<string, number>) {
  if (!rates) return Number(sample.observed_total_co2 ?? 0);

  return (
    Number(sample.observed_motorcycle_stopped_count ?? 0) * (rates.motorcycle_stopped_count ?? 0) +
    Number(sample.observed_motorcycle_moving_count ?? 0) * (rates.motorcycle_moving_count ?? 0) +
    Number(sample.observed_car_stopped_count ?? 0) * (rates.car_stopped_count ?? 0) +
    Number(sample.observed_car_moving_count ?? 0) * (rates.car_moving_count ?? 0)
  );
}
