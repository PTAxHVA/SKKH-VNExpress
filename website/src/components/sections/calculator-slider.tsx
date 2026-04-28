"use client";

import { Slider } from "@/components/ui/slider";

interface CalculatorSliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit?: string;
  onChange: (value: number) => void;
}

export function CalculatorSlider({
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange
}: CalculatorSliderProps) {
  return (
    <label className="block">
      <span className="mb-3 flex items-center justify-between gap-4 text-sm font-semibold text-ink-secondary">
        <span>{label}</span>
        <span className="font-mono text-ink-primary">
          {value}
          {unit}
        </span>
      </span>
      <Slider
        min={min}
        max={max}
        step={step}
        value={[value]}
        onValueChange={(next) => onChange(next[0] ?? value)}
      />
    </label>
  );
}
