import { promises as fs } from "node:fs";
import path from "node:path";

const REPORT_PATH = path.resolve(process.cwd(), "data/emissions_report.json");

export interface GasMetrics {
  mae?: number;
  rmse?: number;
  r2?: number;
}

export interface GasReport {
  unit?: string;
  ground_truth_rates?: Record<string, number>;
  predicted_rates?: Record<string, number>;
  test_metrics_ground_truth?: GasMetrics;
  test_metrics_observed?: GasMetrics;
  train_metrics_ground_truth?: GasMetrics;
  train_metrics_observed?: GasMetrics;
}

export interface EmissionsReport {
  window_size?: number;
  samples?: number;
  train_samples?: number;
  test_samples?: number;
  controllers?: string[];
  seeds?: number;
  features?: string[];
  measurement_noise?: {
    count_noise_std?: number;
    target_noise_std?: number;
    noise_seed?: number;
  };
  gases?: Record<string, GasReport>;
}

export interface NormalizedMetrics {
  r2?: number;
  mae?: number;
  rmse?: number;
  unit?: string;
}

export async function loadEmissionsReport(): Promise<EmissionsReport> {
  try {
    const raw = await fs.readFile(REPORT_PATH, "utf-8");
    return JSON.parse(raw) as EmissionsReport;
  } catch {
    throw new Error(
      `Không đọc được emissions_report.json tại ${REPORT_PATH}. ` +
        "Chạy `pnpm prebuild` để copy dữ liệu từ Source code/Traffic/."
    );
  }
}

export function getGasMetrics(report: EmissionsReport, gas = "co2"): NormalizedMetrics {
  const gasReport = report.gases?.[gas];
  const metrics =
    gasReport?.test_metrics_ground_truth ??
    gasReport?.test_metrics_observed ??
    gasReport?.train_metrics_ground_truth;

  return {
    r2: metrics?.r2,
    mae: metrics?.mae,
    rmse: metrics?.rmse,
    unit: gasReport?.unit
  };
}
