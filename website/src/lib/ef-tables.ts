export const EF_MOVING = {
  motorbike_euro4: {
    speedRange: [25, 40],
    co2: [40, 55],
    nox: [0.08, 0.15],
    pm25: [0.015, 0.025]
  },
  motorbike_euro5: {
    speedRange: [25, 40],
    co2: [35, 50],
    nox: [0.05, 0.08],
    pm25: [0.005, 0.01]
  },
  car_gasoline_euro4: {
    speedRange: [40, 60],
    co2: [140, 180],
    nox: [0.08, 0.12],
    pm25: [0.002, 0.005]
  },
  car_diesel_euro5: {
    speedRange: [40, 60],
    co2: [130, 160],
    nox: [0.15, 0.3],
    pm25: [0.003, 0.005]
  },
  truck_euro4: {
    speedRange: [30, 50],
    co2: [600, 850],
    nox: [3, 5],
    pm25: [0.1, 0.3]
  },
  truck_euro6: {
    speedRange: [30, 50],
    co2: [550, 800],
    nox: [0.4, 0.8],
    pm25: [0.01, 0.02]
  }
} as const;

export const EF_IDLING = {
  motorbike: { co2: [3, 5], nox: 0.005, pm25: 0.001, co: [0.2, 0.5] },
  car_gasoline_ac_off: { co2: [8, 12], nox: [0.02, 0.05], co: [0.1, 0.2] },
  car_gasoline_ac_on: { co2: [18, 25], nox: [0.05, 0.1], co: [0.2, 0.4] },
  truck_diesel: { co2: [60, 90], nox: [1.2, 1.8], pm25: [0.02, 0.04], co: [1, 1.5] },
  bus_diesel: { co2: [80, 120], nox: [1.5, 2.5], pm25: [0.04, 0.06], co: [1.2, 2] }
} as const;

export const EF_CALC = {
  co2: {
    motorbike: { moving: 45, idling: 3.5 },
    car: { moving: 140, idling: 21.3 },
    unit: "g"
  },
  nox: {
    motorbike: { moving: 0.115, idling: 0.005 },
    car: { moving: 0.1, idling: 0.075 },
    unit: "g"
  },
  pm25: {
    motorbike: { moving: 0.02, idling: 0.001 },
    car: { moving: 0.0035, idling: 0 },
    unit: "g"
  }
} as const;
