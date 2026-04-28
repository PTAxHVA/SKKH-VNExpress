import { EF_CALC } from "@/lib/ef-tables";

export type Gas = keyof typeof EF_CALC;

export interface CalcInput {
  motorbikes: number;
  cars: number;
  motorbikeSpeedKmh: number;
  carSpeedKmh: number;
  distanceKm: number;
  idleMinutes: number;
  gas: Gas;
}

export interface CalcOutput {
  moving: number;
  idling: number;
  total: number;
  unit: string;
  breakdown: {
    motorbikeMoving: number;
    motorbikeIdling: number;
    carMoving: number;
    carIdling: number;
  };
}

export const DEFAULT_CALC_INPUT: CalcInput = {
  motorbikes: 2,
  cars: 2,
  motorbikeSpeedKmh: 25,
  carSpeedKmh: 40,
  distanceKm: 0.2,
  idleMinutes: 1.5,
  gas: "co2"
};

export function computeEmission(input: CalcInput): CalcOutput {
  const ef = EF_CALC[input.gas];
  const motorbikeMoving = input.motorbikes * input.distanceKm * ef.motorbike.moving;
  const carMoving = input.cars * input.distanceKm * ef.car.moving;
  const motorbikeIdling = input.motorbikes * input.idleMinutes * ef.motorbike.idling;
  const carIdling = input.cars * input.idleMinutes * ef.car.idling;
  const moving = motorbikeMoving + carMoving;
  const idling = motorbikeIdling + carIdling;

  return {
    moving,
    idling,
    total: moving + idling,
    unit: ef.unit,
    breakdown: {
      motorbikeMoving,
      motorbikeIdling,
      carMoving,
      carIdling
    }
  };
}
