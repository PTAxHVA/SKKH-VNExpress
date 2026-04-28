import { promises as fs } from "node:fs";
import path from "node:path";
import Papa from "papaparse";

const DATASET_PATH = path.resolve(process.cwd(), "data/emissions_dataset.csv");

export interface EmissionSample {
  controller?: string;
  seed?: number;
  window_size?: number;
  start_step?: number;
  end_step?: number;
  hidden_weather_temp_c?: number;
  hidden_weather_rain?: number;
  hidden_weather_humidity?: number;
  hidden_weather_wind?: number;
  ground_truth_motorcycle_stopped_count?: number;
  ground_truth_motorcycle_moving_count?: number;
  ground_truth_car_stopped_count?: number;
  ground_truth_car_moving_count?: number;
  observed_motorcycle_stopped_count?: number;
  observed_motorcycle_moving_count?: number;
  observed_car_stopped_count?: number;
  observed_car_moving_count?: number;
  ground_truth_total_co2?: number;
  ground_truth_total_co?: number;
  ground_truth_total_nox?: number;
  observed_total_co2?: number;
  observed_total_co?: number;
  observed_total_nox?: number;
  measurement_error_co2?: number;
  measurement_error_co?: number;
  measurement_error_nox?: number;
  [key: string]: number | string | undefined;
}

export async function loadEmissionsDataset(limit = 100): Promise<EmissionSample[]> {
  let raw: string;

  try {
    raw = await fs.readFile(DATASET_PATH, "utf-8");
  } catch {
    throw new Error(
      `Không đọc được emissions_dataset.csv tại ${DATASET_PATH}. ` +
        "Chạy `pnpm prebuild` để copy dữ liệu từ Source code/Traffic/."
    );
  }

  const parsed = Papa.parse<Record<string, string>>(raw, {
    header: true,
    skipEmptyLines: true
  });

  if (parsed.errors.length > 0) {
    throw new Error(`CSV parse lỗi: ${parsed.errors[0]?.message ?? "unknown error"}`);
  }

  return parsed.data.slice(0, limit).map((row) => {
    return Object.fromEntries(
      Object.entries(row).map(([key, value]) => {
        const numberValue = Number(value);
        return [key, Number.isFinite(numberValue) ? numberValue : value];
      })
    ) as EmissionSample;
  });
}
