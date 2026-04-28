#!/usr/bin/env python3
"""Minimal runnable demo for AI-based traffic light optimization.

This script simulates a single intersection with two traffic phases:
North-South (NS) and East-West (EW). It trains a tabular Q-learning
agent to choose when to switch phases and compares it against a fixed-time
controller.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import socket
import subprocess
from collections import deque
from dataclasses import dataclass
from pathlib import Path


PHASES = ("NS", "EW")
SUMO_NS_GREEN = "GGGGggrrrrrrGGGGggrrrrrr"
SUMO_EW_GREEN = "rrrrrrGGGGggrrrrrrGGGGgg"
SUMO_NS_YELLOW = "yyyyyyrrrrrryyyyyyrrrrrr"
SUMO_EW_YELLOW = "rrrrrryyyyyyrrrrrryyyyyy"
SUMO_ALL_RED = "r" * len(SUMO_NS_GREEN)
# In the generated 3-lane SUMO net, incoming lane index 2 is nearest the
# center line, index 1 is the main through lane, and index 0 is nearest the
# curb shoulder used by motorcycles.
SUMO_LEFT_LANE_INDEX = "2"
SUMO_MAIN_LANE_INDEX = "1"
SUMO_BIKE_LANE_INDEX = "0"
HALTED_SPEED_THRESHOLD = 0.1
EMISSION_FEATURE_KEYS = (
    "motorcycle_stopped_count",
    "motorcycle_moving_count",
    "car_stopped_count",
    "car_moving_count",
)
EMISSION_GROUND_TRUTH = {
    "co2": {
        "unit": "g/frame",
        "rates": {
            "motorcycle_stopped_count": 8.4,
            "motorcycle_moving_count": 11.1,
            "car_stopped_count": 26.8,
            "car_moving_count": 39.5,
        },
    },
    "co": {
        "unit": "g/frame",
        "rates": {
            "motorcycle_stopped_count": 0.62,
            "motorcycle_moving_count": 0.78,
            "car_stopped_count": 1.45,
            "car_moving_count": 1.95,
        },
    },
    "nox": {
        "unit": "g/frame",
        "rates": {
            "motorcycle_stopped_count": 0.08,
            "motorcycle_moving_count": 0.11,
            "car_stopped_count": 0.22,
            "car_moving_count": 0.34,
        },
    },
}
HIDDEN_VEHICLE_DETAIL_MIX = {
    "motorcycle": (
        ("scooter", 0.55, {"co2": 0.92, "co": 1.06, "nox": 0.88}),
        ("commuter", 0.30, {"co2": 1.00, "co": 1.00, "nox": 1.00}),
        ("delivery", 0.15, {"co2": 1.10, "co": 0.96, "nox": 1.14}),
    ),
    "car": (
        ("compact", 0.34, {"co2": 0.89, "co": 0.93, "nox": 0.91}),
        ("sedan", 0.41, {"co2": 1.00, "co": 1.00, "nox": 1.00}),
        ("suv", 0.25, {"co2": 1.19, "co": 1.12, "nox": 1.15}),
    ),
}
HIDDEN_WEATHER_REGIMES = (
    {"name": "clear", "temp_c": 28.0, "rain": 0.00, "humidity": 0.48, "wind": 0.18},
    {"name": "humid", "temp_c": 31.0, "rain": 0.08, "humidity": 0.76, "wind": 0.14},
    {"name": "rain", "temp_c": 24.0, "rain": 0.54, "humidity": 0.91, "wind": 0.24},
    {"name": "heat", "temp_c": 36.0, "rain": 0.00, "humidity": 0.57, "wind": 0.10},
)
EMISSION_SPEED_SENSITIVITY = {"co2": 0.32, "co": 0.10, "nox": 0.24}
EMISSION_ACCEL_SENSITIVITY = {"co2": 0.20, "co": 0.16, "nox": 0.33}
EMISSION_WEATHER_SENSITIVITY = {"co2": 0.10, "co": 0.08, "nox": 0.14}
State = tuple[int, ...]


@dataclass
class StepResult:
    total_wait: int
    departed: int
    switched: bool
    departed_wait_total: float = 0.0


@dataclass
class TraceFrame:
    step: int
    phase: str
    ns_queue: int
    ew_queue: int
    total_wait: int
    departed: int
    switched: bool
    departed_wait_total: float
    mean_departed_wait: float
    action: str
    phase_age: int
    switch_cooldown: int
    countdown: int
    countdown_mode: str
    flow_rate: float
    left_rate: float
    right_rate: float
    straight_rate: float
    motorcycle_rate: float
    arrivals_detail: list[dict[str, str]]
    departures_detail: list[dict[str, str]]
    lane_queues: dict[str, int]
    lane_vehicle_ids: dict[str, list[str]] | None = None
    vehicle_snapshots: list[dict[str, object]] | None = None


class IntersectionEnv:
    def __init__(
        self,
        ns_arrival_rate: float = 0.65,
        ew_arrival_rate: float = 0.45,
        depart_rate: int = 2,
        min_green: int = 15,
        switch_penalty_steps: int = 2,
        left_rate: float = 0.2,
        right_rate: float = 0.25,
        motorcycle_rate: float = 0.35,
    ) -> None:
        if left_rate < 0 or right_rate < 0 or left_rate + right_rate >= 1:
            raise ValueError("left_rate and right_rate must be non-negative and sum to less than 1.")
        if motorcycle_rate < 0 or motorcycle_rate > 1:
            raise ValueError("motorcycle_rate must be between 0 and 1.")
        self.ns_arrival_rate = ns_arrival_rate
        self.ew_arrival_rate = ew_arrival_rate
        self.depart_rate = depart_rate
        self.min_green = min_green
        self.switch_penalty_steps = switch_penalty_steps
        self.left_rate = left_rate
        self.right_rate = right_rate
        self.straight_rate = 1.0 - left_rate - right_rate
        self.motorcycle_rate = motorcycle_rate
        self.reset(0)

    @staticmethod
    def _lane_id_map() -> dict[str, tuple[str, str]]:
        return {
            "north_left": ("north", "NS"),
            "north_main": ("north", "NS"),
            "north_bike": ("north", "NS"),
            "south_left": ("south", "NS"),
            "south_main": ("south", "NS"),
            "south_bike": ("south", "NS"),
            "west_left": ("west", "EW"),
            "west_main": ("west", "EW"),
            "west_bike": ("west", "EW"),
            "east_left": ("east", "EW"),
            "east_main": ("east", "EW"),
            "east_bike": ("east", "EW"),
        }

    @classmethod
    def _empty_lane_queues(cls) -> dict[str, deque[dict[str, object]]]:
        return {lane_key: deque() for lane_key in cls._lane_id_map()}

    @classmethod
    def _lane_keys_for_phase(cls, phase: int) -> tuple[str, ...]:
        if phase == 0:
            return ("north_left", "north_main", "north_bike", "south_left", "south_main", "south_bike")
        return ("west_left", "west_main", "west_bike", "east_left", "east_main", "east_bike")

    def _reward(self, total_wait: int, imbalance: int, departed: int, switched: bool) -> float:
        # Reward lower backlog and active discharge while keeping switching cheap but not dominant.
        return (
            -1.1 * float(total_wait)
            -0.35 * float(max(self.ns_queue, self.ew_queue))
            -0.10 * float(imbalance)
            +1.75 * float(departed)
            - (0.20 if switched else 0.0)
        )

    def reset(self, seed: int) -> State:
        self.rng = random.Random(seed)
        self._lane_vehicles = self._empty_lane_queues()
        self._vehicle_counter = 0
        self._phase_service_cursor = 0
        self.ns_queue = 0
        self.ew_queue = 0
        self.phase = 0
        self.phase_age = 0
        self.switch_cooldown = 0
        self.last_ns_arrivals = 0
        self.last_ew_arrivals = 0
        self.last_arrivals_detail = []
        self.last_departures_detail = []
        self.last_lane_queues = {lane_key: 0 for lane_key in self._lane_id_map()}
        self.completed_wait_total = 0.0
        self.completed_vehicle_count = 0
        return self._state()

    def _sample_turn(self) -> str:
        roll = self.rng.random()
        if roll < self.left_rate:
            return "left"
        if roll < self.left_rate + self.right_rate:
            return "right"
        return "straight"

    def _sample_vehicle_type(self) -> str:
        return "motorcycle" if self.rng.random() < self.motorcycle_rate else "car"

    def _choose_arrival_lane(self, source: str, turn: str, vehicle_type: str) -> str:
        if turn == "left":
            return f"{source}_left"
        if vehicle_type != "motorcycle":
            return f"{source}_main"

        bike_lane = f"{source}_bike"
        main_lane = f"{source}_main"
        bike_depth = len(self._lane_vehicles[bike_lane])
        main_depth = len(self._lane_vehicles[main_lane])
        if bike_depth < main_depth:
            return bike_lane
        if main_depth < bike_depth:
            return main_lane
        return bike_lane if self.rng.random() < 0.5 else main_lane

    def _append_arrival(self, source: str) -> None:
        turn = self._sample_turn()
        vehicle_type = self._sample_vehicle_type()
        lane_key = self._choose_arrival_lane(source, turn, vehicle_type)
        lane = lane_key.split("_", 1)[1]
        self._vehicle_counter += 1
        self._lane_vehicles[lane_key].append(
            {
                "id": f"{lane_key}_{self._vehicle_counter}",
                "source": source,
                "lane": lane,
                "turn": turn,
                "vehicle_type": vehicle_type,
                "wait": 0.0,
            }
        )
        self.last_arrivals_detail.append({"source": source, "lane": lane, "vehicle_type": vehicle_type})
        if source in {"north", "south"}:
            self.last_ns_arrivals += 1
        else:
            self.last_ew_arrivals += 1

    def _arrivals(self) -> None:
        self.last_ns_arrivals = 0
        self.last_ew_arrivals = 0
        self.last_arrivals_detail = []
        if self.rng.random() < self.ns_arrival_rate:
            self._append_arrival("north" if self.rng.random() < 0.5 else "south")
        if self.rng.random() < self.ew_arrival_rate:
            self._append_arrival("west" if self.rng.random() < 0.5 else "east")

    def _refresh_lane_counts(self) -> None:
        self.last_lane_queues = {
            lane_key: len(vehicles) for lane_key, vehicles in self._lane_vehicles.items()
        }
        self.ns_queue = sum(self.last_lane_queues[lane_key] for lane_key in self._lane_keys_for_phase(0))
        self.ew_queue = sum(self.last_lane_queues[lane_key] for lane_key in self._lane_keys_for_phase(1))

    def _peak_lane_queue(self, axis: str) -> int:
        lane_keys = self._lane_keys_for_phase(0 if axis == "NS" else 1)
        return max((self.last_lane_queues.get(lane_key, 0) for lane_key in lane_keys), default=0)

    def _increment_waits(self) -> None:
        for lane_vehicles in self._lane_vehicles.values():
            for vehicle in lane_vehicles:
                vehicle["wait"] = float(vehicle["wait"]) + 1.0

    def _departures(self) -> tuple[int, float]:
        departed = 0
        departed_wait_total = 0.0
        self.last_departures_detail = []
        phase_lanes = self._lane_keys_for_phase(self.phase)

        for _ in range(self.depart_rate):
            available_lanes = [lane_key for lane_key in phase_lanes if self._lane_vehicles[lane_key]]
            if not available_lanes:
                break
            max_depth = max(len(self._lane_vehicles[lane_key]) for lane_key in available_lanes)
            start_index = self._phase_service_cursor % len(phase_lanes)
            selected_lane = None
            for offset in range(len(phase_lanes)):
                lane_key = phase_lanes[(start_index + offset) % len(phase_lanes)]
                if len(self._lane_vehicles[lane_key]) == max_depth:
                    selected_lane = lane_key
                    self._phase_service_cursor = (start_index + offset + 1) % len(phase_lanes)
                    break
            if selected_lane is None:
                selected_lane = available_lanes[0]

            vehicle = self._lane_vehicles[selected_lane].popleft()
            departed += 1
            departed_wait_total += float(vehicle["wait"])
            self.completed_wait_total += float(vehicle["wait"])
            self.completed_vehicle_count += 1
            self.last_departures_detail.append(
                {
                    "source": str(vehicle["source"]),
                    "turn": str(vehicle["turn"]),
                    "lane": str(vehicle["lane"]),
                    "vehicle_type": str(vehicle["vehicle_type"]),
                }
            )
        return departed, departed_wait_total

    def _bucket(self, q: int) -> int:
        if q <= 2:
            return q
        if q <= 5:
            return 3
        if q <= 8:
            return 4
        return 5

    def _age_bucket(self) -> int:
        if self.phase_age < self.min_green:
            return 0
        if self.phase_age < self.min_green + 4:
            return 1
        return 2

    def _state(self) -> State:
        return (
            self._bucket(self.ns_queue),
            self._bucket(self.ew_queue),
            self._bucket(self._peak_lane_queue("NS")),
            self._bucket(self._peak_lane_queue("EW")),
            self.phase,
            self._age_bucket(),
            1 if self.switch_cooldown > 0 else 0,
        )

    def step(self, action: int) -> tuple[State, float, StepResult]:
        switched = False
        if (
            action == 1
            and self.switch_cooldown == 0
            and self.phase_age >= self.min_green
        ):
            self.phase = 1 - self.phase
            self.phase_age = 0
            self.switch_cooldown = self.switch_penalty_steps
            switched = True

        self.last_departures_detail = []
        if self.switch_cooldown > 0:
            departed = 0
            departed_wait_total = 0.0
            self.switch_cooldown -= 1
        else:
            departed, departed_wait_total = self._departures()
            self.phase_age += 1
        self._increment_waits()
        self._arrivals()
        self._refresh_lane_counts()

        total_wait = self.ns_queue + self.ew_queue
        imbalance = abs(self.ns_queue - self.ew_queue)
        reward = self._reward(total_wait, imbalance, departed, switched)
        return self._state(), reward, StepResult(total_wait, departed, switched, departed_wait_total)


class SumoIntersectionEnv:
    def __init__(
        self,
        sumo_home: str,
        assets_dir: str,
        steps: int,
        connection_label: str = "sumo_env",
        use_gui: bool = False,
        gui_delay_ms: int = 100,
        ns_arrival_rate: float = 0.65,
        ew_arrival_rate: float = 0.45,
        min_green: int = 15,
        switch_penalty_steps: int = 2,
        left_rate: float = 0.2,
        right_rate: float = 0.25,
        motorcycle_rate: float = 0.35,
    ) -> None:
        if left_rate < 0 or right_rate < 0 or left_rate + right_rate >= 1:
            raise ValueError("left_rate and right_rate must be non-negative and sum to less than 1.")
        if motorcycle_rate < 0 or motorcycle_rate > 1:
            raise ValueError("motorcycle_rate must be between 0 and 1.")
        self.sumo_home = Path(sumo_home).resolve()
        self.assets_dir = Path(assets_dir).resolve()
        self.steps = steps
        self.use_gui = use_gui
        self.gui_delay_ms = gui_delay_ms
        self.ns_arrival_rate = ns_arrival_rate
        self.ew_arrival_rate = ew_arrival_rate
        self.min_green = min_green
        self.switch_penalty_steps = switch_penalty_steps
        self.left_rate = left_rate
        self.right_rate = right_rate
        self.straight_rate = 1.0 - left_rate - right_rate
        self.motorcycle_rate = motorcycle_rate
        self.net_path = self.assets_dir / "cross.net.xml"
        self.route_path = self.assets_dir / "routes.rou.xml"
        self.config_path = self.assets_dir / "cross.sumocfg"
        self.connection_label = connection_label
        self._started = False
        self._sumo_process = None
        self._vehicle_route_ids: dict[str, str] = {}
        self._vehicle_wait_times: dict[str, float] = {}
        self._vehicle_type_ids: dict[str, str] = {}
        self._clearance_source_phase = 0
        self.last_arrivals_detail: list[dict[str, str]] = []
        self.last_departures_detail: list[dict[str, str]] = []
        self.last_lane_queues: dict[str, int] = self._empty_lane_queues()
        self.last_lane_vehicle_ids: dict[str, list[str]] = self._empty_lane_vehicle_ids()
        self.last_vehicle_snapshots: list[dict[str, object]] | None = None
        self.completed_wait_total = 0.0
        self.completed_vehicle_count = 0
        self.route_meta = {
            "north_straight": {"source": "north", "turn": "straight"},
            "north_left": {"source": "north", "turn": "left"},
            "north_right": {"source": "north", "turn": "right"},
            "south_straight": {"source": "south", "turn": "straight"},
            "south_left": {"source": "south", "turn": "left"},
            "south_right": {"source": "south", "turn": "right"},
            "west_straight": {"source": "west", "turn": "straight"},
            "west_left": {"source": "west", "turn": "left"},
            "west_right": {"source": "west", "turn": "right"},
            "east_straight": {"source": "east", "turn": "straight"},
            "east_left": {"source": "east", "turn": "left"},
            "east_right": {"source": "east", "turn": "right"},
        }
        self._ensure_local_sumo_assets()
        self.phase = 0
        self.phase_age = 0
        self.switch_cooldown = 0
        self.ns_queue = 0
        self.ew_queue = 0
        self.last_ns_arrivals = 0
        self.last_ew_arrivals = 0

    @staticmethod
    def _lane_id_map() -> dict[str, str]:
        return {
            "north_left": "top0A0_2",
            "north_main": "top0A0_1",
            "north_bike": "top0A0_0",
            "south_left": "bottom0A0_2",
            "south_main": "bottom0A0_1",
            "south_bike": "bottom0A0_0",
            "west_left": "left0A0_2",
            "west_main": "left0A0_1",
            "west_bike": "left0A0_0",
            "east_left": "right0A0_2",
            "east_main": "right0A0_1",
            "east_bike": "right0A0_0",
        }

    @classmethod
    def _empty_lane_queues(cls) -> dict[str, int]:
        return {lane_key: 0 for lane_key in cls._lane_id_map()}

    @classmethod
    def _empty_lane_vehicle_ids(cls) -> dict[str, list[str]]:
        return {lane_key: [] for lane_key in cls._lane_id_map()}

    @classmethod
    def _lane_keys_for_phase(cls, phase: int) -> tuple[str, ...]:
        if phase == 0:
            return ("north_left", "north_main", "north_bike", "south_left", "south_main", "south_bike")
        return ("west_left", "west_main", "west_bike", "east_left", "east_main", "east_bike")

    def _reward(self, total_wait: int, imbalance: int, departed: int, switched: bool) -> float:
        return (
            -1.1 * float(total_wait)
            -0.35 * float(max(self.ns_queue, self.ew_queue))
            -0.10 * float(imbalance)
            +1.75 * float(departed)
            - (0.20 if switched else 0.0)
        )

    def _ensure_runtime_env(self) -> None:
        os.environ["SUMO_HOME"] = str(self.sumo_home)
        lib_path = str(self.sumo_home / "lib")
        current = os.environ.get("DYLD_LIBRARY_PATH", "")
        if lib_path not in current.split(":"):
            os.environ["DYLD_LIBRARY_PATH"] = f"{lib_path}:{current}" if current else lib_path

    def _run_local_binary(self, binary_name: str, args: list[str]) -> None:
        self._ensure_runtime_env()
        cmd = [str(self.sumo_home / "bin" / binary_name), *args]
        completed = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy(), timeout=30)
        if completed.returncode != 0:
            raise RuntimeError(
                f"{binary_name} failed with code {completed.returncode}: {completed.stderr.strip() or completed.stdout.strip()}"
            )

    def _net_requires_regeneration(self) -> bool:
        if not self.net_path.exists():
            return True
        try:
            net_text = self.net_path.read_text(encoding="utf-8")
        except OSError:
            return True
        return (
            'default.lanenumber value="3"' not in net_text
            or 'state="GGGGggrrrrrrGGGGggrrrrrr"' not in net_text
            or 'top0A0_2' not in net_text
        )

    def _ensure_local_sumo_assets(self) -> None:
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        if self._net_requires_regeneration():
            self._run_local_binary(
                "netgenerate",
                [
                    "--grid",
                    "--grid.x-number",
                    "1",
                    "--grid.y-number",
                    "1",
                    "--grid.x-length",
                    "100",
                    "--grid.y-length",
                    "100",
                    "--grid.attach-length",
                    "100",
                    "--default.lanenumber",
                    "3",
                    "--tls.guess",
                    "--tls.default-type",
                    "static",
                    "--output-file",
                    str(self.net_path),
                ],
            )
        if not self.config_path.exists():
            self.config_path.write_text(
                """<configuration>
    <input>
        <net-file value="cross.net.xml"/>
        <route-files value="routes.rou.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="100000"/>
    </time>
    <report>
        <no-step-log value="true"/>
        <verbose value="false"/>
    </report>
</configuration>
""",
                encoding="utf-8",
            )

    def _write_routes(self, seed: int) -> None:
        per_approach_ns = self.ns_arrival_rate / 2.0
        per_approach_ew = self.ew_arrival_rate / 2.0
        flow_end = max(self.steps, 1)
        route_lines = [
            "<routes>",
            '    <vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="13.9"/>',
            '    <vType id="motorcycle" vClass="motorcycle" accel="4.0" decel="6.0" sigma="0.35" length="2.2" minGap="1.0" maxSpeed="12.5" guiShape="motorcycle"/>',
            '    <route id="north_straight" edges="top0A0 A0bottom0"/>',
            '    <route id="north_left" edges="top0A0 A0right0"/>',
            '    <route id="north_right" edges="top0A0 A0left0"/>',
            '    <route id="south_straight" edges="bottom0A0 A0top0"/>',
            '    <route id="south_left" edges="bottom0A0 A0left0"/>',
            '    <route id="south_right" edges="bottom0A0 A0right0"/>',
            '    <route id="west_straight" edges="left0A0 A0right0"/>',
            '    <route id="west_left" edges="left0A0 A0top0"/>',
            '    <route id="west_right" edges="left0A0 A0bottom0"/>',
            '    <route id="east_straight" edges="right0A0 A0left0"/>',
            '    <route id="east_left" edges="right0A0 A0bottom0"/>',
            '    <route id="east_right" edges="right0A0 A0top0"/>',
        ]
        flows = [
            ("north", per_approach_ns),
            ("south", per_approach_ns),
            ("west", per_approach_ew),
            ("east", per_approach_ew),
        ]

        def add_flow(flow_id: str, type_id: str, route_id: str, probability: float, depart_lane: str) -> None:
            if probability <= 0:
                return
            route_lines.append(
                f'    <flow id="{flow_id}" type="{type_id}" route="{route_id}" begin="0" end="{flow_end}" '
                f'probability="{probability:.4f}" departLane="{depart_lane}" departSpeed="max"/>'
            )

        for source, base_rate in flows:
            car_share = 1.0 - self.motorcycle_rate
            bike_share = self.motorcycle_rate
            add_flow(
                f"{source}_car_straight_flow",
                "car",
                f"{source}_straight",
                base_rate * self.straight_rate * car_share,
                SUMO_MAIN_LANE_INDEX,
            )
            add_flow(
                f"{source}_car_left_flow",
                "car",
                f"{source}_left",
                base_rate * self.left_rate * car_share,
                SUMO_LEFT_LANE_INDEX,
            )
            add_flow(
                f"{source}_car_right_flow",
                "car",
                f"{source}_right",
                base_rate * self.right_rate * car_share,
                SUMO_BIKE_LANE_INDEX,
            )

            motorcycle_straight_probability = base_rate * self.straight_rate * bike_share
            add_flow(
                f"{source}_motorcycle_straight_bike_flow",
                "motorcycle",
                f"{source}_straight",
                motorcycle_straight_probability * 0.55,
                SUMO_BIKE_LANE_INDEX,
            )
            add_flow(
                f"{source}_motorcycle_straight_main_flow",
                "motorcycle",
                f"{source}_straight",
                motorcycle_straight_probability * 0.45,
                SUMO_MAIN_LANE_INDEX,
            )
            add_flow(
                f"{source}_motorcycle_left_flow",
                "motorcycle",
                f"{source}_left",
                base_rate * self.left_rate * bike_share,
                SUMO_LEFT_LANE_INDEX,
            )
            motorcycle_right_probability = base_rate * self.right_rate * bike_share
            add_flow(
                f"{source}_motorcycle_right_bike_flow",
                "motorcycle",
                f"{source}_right",
                motorcycle_right_probability * 0.7,
                SUMO_BIKE_LANE_INDEX,
            )
            add_flow(
                f"{source}_motorcycle_right_main_flow",
                "motorcycle",
                f"{source}_right",
                motorcycle_right_probability * 0.3,
                SUMO_MAIN_LANE_INDEX,
            )
        route_lines.append("</routes>")
        self.route_path.write_text("\n".join(route_lines) + "\n", encoding="utf-8")

    def _close_connection(self) -> None:
        if not self._started:
            if self._sumo_process is not None:
                self._sumo_process.terminate()
                self._sumo_process = None
            return
        try:
            import traci

            traci.switch(self.connection_label)
            traci.close()
        except Exception:
            pass
        if self._sumo_process is not None:
            self._sumo_process.terminate()
            self._sumo_process = None
        self._started = False

    def _get_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as handle:
            handle.bind(("127.0.0.1", 0))
            handle.listen(1)
            return int(handle.getsockname()[1])

    def _bucket(self, q: int) -> int:
        if q <= 2:
            return q
        if q <= 5:
            return 3
        if q <= 8:
            return 4
        return 5

    def _age_bucket(self) -> int:
        if self.phase_age < self.min_green:
            return 0
        if self.phase_age < self.min_green + 4:
            return 1
        return 2

    def _peak_lane_queue(self, axis: str) -> int:
        lane_keys = self._lane_keys_for_phase(0 if axis == "NS" else 1)
        return max((self.last_lane_queues.get(lane_key, 0) for lane_key in lane_keys), default=0)

    def _state(self) -> State:
        return (
            self._bucket(self.ns_queue),
            self._bucket(self.ew_queue),
            self._bucket(self._peak_lane_queue("NS")),
            self._bucket(self._peak_lane_queue("EW")),
            self.phase,
            self._age_bucket(),
            1 if self.switch_cooldown > 0 else 0,
        )

    def _set_signal_state(self) -> None:
        import traci

        traci.switch(self.connection_label)
        if self.switch_cooldown > 0:
            if self.switch_penalty_steps > 0 and self.switch_cooldown == self.switch_penalty_steps:
                yellow_state = SUMO_NS_YELLOW if self._clearance_source_phase == 0 else SUMO_EW_YELLOW
                traci.trafficlight.setRedYellowGreenState("A0", yellow_state)
            else:
                traci.trafficlight.setRedYellowGreenState("A0", SUMO_ALL_RED)
        elif self.phase == 0:
            traci.trafficlight.setRedYellowGreenState("A0", SUMO_NS_GREEN)
        else:
            traci.trafficlight.setRedYellowGreenState("A0", SUMO_EW_GREEN)

    def _update_queues(self) -> None:
        import traci

        traci.switch(self.connection_label)
        lane_map = self._lane_id_map()
        ns_lanes = [
            lane_map["north_main"],
            lane_map["north_left"],
            lane_map["north_bike"],
            lane_map["south_main"],
            lane_map["south_left"],
            lane_map["south_bike"],
        ]
        ew_lanes = [
            lane_map["west_main"],
            lane_map["west_left"],
            lane_map["west_bike"],
            lane_map["east_main"],
            lane_map["east_left"],
            lane_map["east_bike"],
        ]
        self.ns_queue = sum(int(traci.lane.getLastStepHaltingNumber(lane)) for lane in ns_lanes)
        self.ew_queue = sum(int(traci.lane.getLastStepHaltingNumber(lane)) for lane in ew_lanes)
        lane_vehicle_ids: dict[str, list[str]] = {}
        for lane_key, lane_id in lane_map.items():
            vehicle_ids = list(traci.lane.getLastStepVehicleIDs(lane_id))
            vehicle_ids.sort(key=lambda vehicle_id: traci.vehicle.getLanePosition(vehicle_id), reverse=True)
            lane_vehicle_ids[lane_key] = vehicle_ids

        # Keep replay lanes populated by all cars still on the inbound edge, not just halted cars.
        self.last_lane_vehicle_ids = lane_vehicle_ids
        self.last_lane_queues = {
            lane_key: len(vehicle_ids) for lane_key, vehicle_ids in lane_vehicle_ids.items()
        }

    def _capture_vehicle_snapshots(
        self,
        current_vehicle_ids: list[str],
        current_route_ids: dict[str, str],
        current_wait_times: dict[str, float],
    ) -> list[dict[str, object]]:
        import traci

        snapshots: list[dict[str, object]] = []
        for vehicle_id in current_vehicle_ids:
            x, y = traci.vehicle.getPosition(vehicle_id)
            angle = float(traci.vehicle.getAngle(vehicle_id))
            road_id = traci.vehicle.getRoadID(vehicle_id)
            lane_id = traci.vehicle.getLaneID(vehicle_id)
            lane_position = float(traci.vehicle.getLanePosition(vehicle_id))
            type_id = traci.vehicle.getTypeID(vehicle_id)
            meta = self._route_info(current_route_ids.get(vehicle_id, ""))
            snapshots.append(
                {
                    "id": vehicle_id,
                    "source": meta["source"],
                    "turn": meta["turn"],
                    "vehicle_type": type_id,
                    "x": float(x),
                    "y": float(y),
                    "angle": angle,
                    "length": float(traci.vehicletype.getLength(type_id)),
                    "width": float(traci.vehicletype.getWidth(type_id)),
                    "road_id": road_id,
                    "lane_id": lane_id,
                    "lane_position": lane_position,
                    "speed": float(traci.vehicle.getSpeed(vehicle_id)),
                    "waiting_time": float(current_wait_times.get(vehicle_id, 0.0)),
                }
            )
        snapshots.sort(key=lambda item: (str(item["road_id"]).startswith(":"), float(item["y"])))
        return snapshots

    def _route_info(self, route_id: str) -> dict[str, str]:
        return self.route_meta.get(route_id, {"source": "north", "turn": "straight"})

    def reset(self, seed: int) -> State:
        self._close_connection()
        self._ensure_runtime_env()
        self._write_routes(seed)
        self.phase = 0
        self.phase_age = 0
        self.switch_cooldown = 0
        self.ns_queue = 0
        self.ew_queue = 0
        self.last_ns_arrivals = 0
        self.last_ew_arrivals = 0
        self.last_arrivals_detail = []
        self.last_departures_detail = []
        self.last_lane_queues = self._empty_lane_queues()
        self.last_lane_vehicle_ids = self._empty_lane_vehicle_ids()
        self.last_vehicle_snapshots = []
        self._vehicle_route_ids = {}
        self._vehicle_wait_times = {}
        self._vehicle_type_ids = {}
        self._clearance_source_phase = 0
        self.completed_wait_total = 0.0
        self.completed_vehicle_count = 0

        import traci

        sumo_binary = str(self.sumo_home / "bin" / ("sumo-gui" if self.use_gui else "sumo"))
        remote_port = self._get_free_port()
        cmd = [
            sumo_binary,
            "-c",
            str(self.config_path),
            "--seed",
            str(seed),
            "--remote-port",
            str(remote_port),
            "--no-step-log",
            "true",
            "--duration-log.disable",
            "true",
        ]
        if self.use_gui:
            cmd.extend(["--start", "--delay", str(self.gui_delay_ms)])
        self._sumo_process = subprocess.Popen(
            cmd,
            env=os.environ.copy(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            traci.init(remote_port, label=self.connection_label, proc=self._sumo_process)
        except Exception as exc:
            stderr_output = ""
            if self._sumo_process is not None and self._sumo_process.stderr is not None:
                try:
                    stderr_output = self._sumo_process.stderr.read().strip()
                except Exception:
                    stderr_output = ""
            self._close_connection()
            message = f"Failed to start {'SUMO GUI' if self.use_gui else 'SUMO'} via TraCI."
            if stderr_output:
                message += f" stderr: {stderr_output}"
            raise RuntimeError(message) from exc
        self._started = True
        self._set_signal_state()
        self._update_queues()
        return self._state()

    def step(self, action: int) -> tuple[State, float, StepResult]:
        import traci

        switched = False
        if action == 1 and self.switch_cooldown == 0 and self.phase_age >= self.min_green:
            self._clearance_source_phase = self.phase
            self.phase = 1 - self.phase
            self.phase_age = 0
            self.switch_cooldown = self.switch_penalty_steps
            switched = True

        traci.switch(self.connection_label)
        self._set_signal_state()
        traci.simulationStep()
        departed_ids = list(traci.simulation.getDepartedIDList())
        starting_teleport_ids = set(traci.simulation.getStartingTeleportIDList())
        colliding_vehicle_ids = set(traci.simulation.getCollidingVehiclesIDList())
        current_vehicle_ids = list(traci.vehicle.getIDList())
        current_route_ids = {vehicle_id: traci.vehicle.getRouteID(vehicle_id) for vehicle_id in current_vehicle_ids}
        current_wait_times = {
            vehicle_id: float(traci.vehicle.getAccumulatedWaitingTime(vehicle_id))
            for vehicle_id in current_vehicle_ids
        }
        current_type_ids = {vehicle_id: traci.vehicle.getTypeID(vehicle_id) for vehicle_id in current_vehicle_ids}
        previous_lane_vehicle_ids = {
            lane_key: list(vehicle_ids) for lane_key, vehicle_ids in self.last_lane_vehicle_ids.items()
        }
        previous_route_ids = dict(self._vehicle_route_ids)
        previous_wait_times = dict(self._vehicle_wait_times)
        previous_type_ids = dict(self._vehicle_type_ids)
        self._update_queues()
        self.last_vehicle_snapshots = self._capture_vehicle_snapshots(
            current_vehicle_ids,
            current_route_ids,
            current_wait_times,
        )

        departures_detail: list[dict[str, str]] = []
        departed_wait_total = 0.0
        current_inbound_vehicle_ids = {
            vehicle_id
            for vehicle_ids in self.last_lane_vehicle_ids.values()
            for vehicle_id in vehicle_ids
        }
        invalid_departure_ids = starting_teleport_ids | colliding_vehicle_ids
        for lane_key in self._lane_id_map():
            for vehicle_id in previous_lane_vehicle_ids.get(lane_key, []):
                if vehicle_id in current_inbound_vehicle_ids:
                    continue
                if vehicle_id in invalid_departure_ids:
                    continue
                route_id = current_route_ids.get(vehicle_id) or previous_route_ids.get(vehicle_id, "")
                meta = self._route_info(route_id)
                vehicle_type = current_type_ids.get(vehicle_id) or previous_type_ids.get(vehicle_id, "car")
                departures_detail.append({"source": meta["source"], "turn": meta["turn"]})
                wait_time = current_wait_times.get(vehicle_id, previous_wait_times.get(vehicle_id, 0.0))
                departed_wait_total += wait_time
                self.completed_wait_total += wait_time
                self.completed_vehicle_count += 1
                departures_detail[-1]["lane"] = lane_key.split("_", 1)[1]
                departures_detail[-1]["vehicle_type"] = vehicle_type

        arrivals_detail: list[dict[str, str]] = []
        ns_arrivals = 0
        ew_arrivals = 0
        lane_key_by_lane_id = {lane_id: lane_key for lane_key, lane_id in self._lane_id_map().items()}
        for vehicle_id in departed_ids:
            meta = self._route_info(current_route_ids.get(vehicle_id) or previous_route_ids.get(vehicle_id, ""))
            vehicle_type = current_type_ids.get(vehicle_id, previous_type_ids.get(vehicle_id, "car"))
            lane_key = lane_key_by_lane_id.get(traci.vehicle.getLaneID(vehicle_id), "")
            lane = lane_key.split("_", 1)[1] if lane_key else ("left" if meta["turn"] == "left" else ("bike" if vehicle_type == "motorcycle" else "main"))
            arrivals_detail.append({"source": meta["source"], "lane": lane, "vehicle_type": vehicle_type})
            if meta["source"] in {"north", "south"}:
                ns_arrivals += 1
            else:
                ew_arrivals += 1
        departed = len(departures_detail)
        self.last_arrivals_detail = arrivals_detail
        self.last_departures_detail = departures_detail
        self.last_ns_arrivals = ns_arrivals
        self.last_ew_arrivals = ew_arrivals
        self._vehicle_route_ids = current_route_ids
        self._vehicle_wait_times = current_wait_times
        self._vehicle_type_ids = current_type_ids

        if self.switch_cooldown > 0:
            self.switch_cooldown -= 1
        else:
            self.phase_age += 1

        total_wait = self.ns_queue + self.ew_queue
        imbalance = abs(self.ns_queue - self.ew_queue)
        reward = self._reward(total_wait, imbalance, departed, switched)
        return self._state(), reward, StepResult(total_wait, departed, switched, departed_wait_total)


class QLearningAgent:
    def __init__(
        self,
        alpha: float = 0.2,
        gamma: float = 0.95,
        epsilon: float = 0.15,
        epsilon_min: float = 0.02,
        epsilon_decay: float = 0.996,
    ) -> None:
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.q_table: dict[tuple[State, int], float] = {}

    def value(self, state: State, action: int) -> float:
        return self.q_table.get((state, action), 0.0)

    def act(self, state: State, explore: bool = True) -> int:
        if explore and random.random() < self.epsilon:
            return random.randint(0, 1)

        keep_value = self.value(state, 0)
        switch_value = self.value(state, 1)
        return 1 if switch_value >= keep_value else 0

    def learn(
        self,
        state: State,
        action: int,
        reward: float,
        next_state: State,
    ) -> None:
        old_value = self.value(state, action)
        next_best = max(self.value(next_state, 0), self.value(next_state, 1))
        updated = old_value + self.alpha * (reward + self.gamma * next_best - old_value)
        self.q_table[(state, action)] = updated

    def decay(self) -> None:
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)


def _axis_lane_pressure(env: IntersectionEnv | SumoIntersectionEnv, axis: str) -> float:
    lane_queues = getattr(env, "last_lane_queues", None) or {}
    if not lane_queues:
        return float(env.ns_queue if axis == "NS" else env.ew_queue)

    if axis == "NS":
        left_total = lane_queues.get("north_left", 0) + lane_queues.get("south_left", 0)
        through_peak = max(
            lane_queues.get("north_main", 0) + lane_queues.get("north_bike", 0),
            lane_queues.get("south_main", 0) + lane_queues.get("south_bike", 0),
        )
        bike_total = lane_queues.get("north_bike", 0) + lane_queues.get("south_bike", 0)
        axis_total = env.ns_queue
    else:
        left_total = lane_queues.get("west_left", 0) + lane_queues.get("east_left", 0)
        through_peak = max(
            lane_queues.get("west_main", 0) + lane_queues.get("west_bike", 0),
            lane_queues.get("east_main", 0) + lane_queues.get("east_bike", 0),
        )
        bike_total = lane_queues.get("west_bike", 0) + lane_queues.get("east_bike", 0)
        axis_total = env.ew_queue
    return float(through_peak) + 0.7 * float(left_total) + 0.25 * float(bike_total) + 0.15 * float(axis_total)


def heuristic_switch_action(env: IntersectionEnv | SumoIntersectionEnv) -> int | None:
    if env.switch_cooldown > 0 or env.phase_age < env.min_green:
        return None

    active_queue = env.ns_queue if env.phase == 0 else env.ew_queue
    inactive_queue = env.ew_queue if env.phase == 0 else env.ns_queue
    active_axis = "NS" if env.phase == 0 else "EW"
    inactive_axis = "EW" if env.phase == 0 else "NS"
    active_pressure = _axis_lane_pressure(env, active_axis)
    inactive_pressure = _axis_lane_pressure(env, inactive_axis)
    max_green = max(env.min_green + 10, 30)

    if inactive_queue > 0 and active_queue == 0:
        return 1
    if inactive_queue >= max(6, active_queue + 3):
        return 1
    if inactive_pressure >= max(5.0, active_pressure + 2.5) and inactive_queue >= max(2, active_queue - 1):
        return 1
    if env.phase_age >= max_green and inactive_queue >= max(2, active_queue):
        return 1
    if env.phase_age >= env.min_green + 4 and inactive_pressure > active_pressure * 1.35 and inactive_queue > 0:
        return 1
    return None


def choose_action_with_policy(
    env: IntersectionEnv | SumoIntersectionEnv,
    agent: QLearningAgent,
    state: State,
    explore: bool,
) -> int:
    forced_action = heuristic_switch_action(env)
    if forced_action is not None:
        return forced_action
    return agent.act(state, explore=explore)


def train_agent(env: IntersectionEnv | SumoIntersectionEnv, episodes: int, steps: int) -> QLearningAgent:
    agent = QLearningAgent()
    for episode in range(episodes):
        state = env.reset(seed=episode)
        for _ in range(steps):
            action = choose_action_with_policy(env, agent, state, explore=True)
            next_state, reward, _ = env.step(action)
            agent.learn(state, action, reward, next_state)
            state = next_state
        agent.decay()
    return agent


def choose_action(
    controller: str,
    env: IntersectionEnv | SumoIntersectionEnv,
    step_index: int,
    state: State,
    fixed_cycle: int,
    agent: QLearningAgent | None = None,
) -> int:
    if controller == "fixed":
        target_green = max(1, fixed_cycle, env.min_green)
        if env.switch_cooldown > 0:
            return 0
        return 1 if env.phase_age >= target_green else 0
    if controller == "ai" and agent is not None:
        return choose_action_with_policy(env, agent, state, explore=False)
    raise ValueError(f"Unsupported controller: {controller}")


def run_controller(
    env: IntersectionEnv | SumoIntersectionEnv,
    steps: int,
    seed: int,
    controller: str,
    agent: QLearningAgent | None = None,
    fixed_cycle: int = 10,
) -> dict[str, float]:
    state = env.reset(seed=seed)
    total_wait = 0
    total_departed = 0
    switch_count = 0

    for t in range(steps):
        action = choose_action(controller, env, t, state, fixed_cycle, agent)

        state, _, result = env.step(action)
        total_wait += result.total_wait
        total_departed += result.departed
        switch_count += 1 if result.switched else 0

    avg_queue = total_wait / steps
    completed_vehicle_count = float(getattr(env, "completed_vehicle_count", 0))
    completed_wait_total = float(getattr(env, "completed_wait_total", 0.0))
    return {
        "avg_queue": avg_queue,
        "avg_wait": avg_queue,
        "avg_delay": completed_wait_total / completed_vehicle_count if completed_vehicle_count else 0.0,
        "throughput": total_departed / steps,
        "switches": switch_count,
        "completed_vehicles": completed_vehicle_count,
    }


def collect_trace(
    env: IntersectionEnv | SumoIntersectionEnv,
    steps: int,
    seed: int,
    controller: str,
    agent: QLearningAgent | None = None,
    fixed_cycle: int = 10,
) -> list[TraceFrame]:
    state = env.reset(seed=seed)
    frames: list[TraceFrame] = []
    recent_departed: list[int] = []
    route_rng = random.Random((seed + 1) * (11 if controller == "fixed" else 17))
    arrival_rng = random.Random((seed + 1) * (23 if controller == "fixed" else 31))

    def sample_turn() -> str:
        roll = route_rng.random()
        if roll < env.left_rate:
            return "left"
        if roll < env.left_rate + env.right_rate:
            return "right"
        return "straight"

    def sample_vehicle_type() -> str:
        return "motorcycle" if arrival_rng.random() < getattr(env, "motorcycle_rate", 0.0) else "car"

    def sample_lane(turn: str, vehicle_type: str) -> str:
        if turn == "left":
            return "left"
        if vehicle_type != "motorcycle":
            return "main"
        return "bike" if arrival_rng.random() < 0.55 else "main"

    for t in range(steps):
        action = choose_action(controller, env, t, state, fixed_cycle, agent)

        state, _, result = env.step(action)
        recent_departed.append(result.departed)
        flow_window = recent_departed[-5:]
        flow_rate = sum(flow_window) / len(flow_window)

        if env.switch_cooldown > 0:
            countdown = env.switch_cooldown
            countdown_mode = "clear"
        elif controller == "fixed":
            target_green = max(1, fixed_cycle, env.min_green)
            countdown = max(0, target_green - env.phase_age)
            countdown_mode = "switch"
        else:
            countdown = max(0, env.min_green - env.phase_age)
            countdown_mode = "ready"

        arrivals_detail = [detail.copy() for detail in getattr(env, "last_arrivals_detail", [])]
        departures_detail = [detail.copy() for detail in getattr(env, "last_departures_detail", [])]
        if not arrivals_detail:
            for arrival_index in range(env.last_ns_arrivals):
                turn = sample_turn()
                vehicle_type = sample_vehicle_type()
                arrivals_detail.append(
                    {
                        "source": "north" if (t + arrival_index + int(arrival_rng.random() * 10)) % 2 == 0 else "south",
                        "lane": sample_lane(turn, vehicle_type),
                        "vehicle_type": vehicle_type,
                    }
                )
            for arrival_index in range(env.last_ew_arrivals):
                turn = sample_turn()
                vehicle_type = sample_vehicle_type()
                arrivals_detail.append(
                    {
                        "source": "west" if (t + arrival_index + int(arrival_rng.random() * 10)) % 2 == 0 else "east",
                        "lane": sample_lane(turn, vehicle_type),
                        "vehicle_type": vehicle_type,
                    }
                )
        if not departures_detail:
            frame_phase = PHASES[env.phase]
            for departed_index in range(result.departed):
                turn = sample_turn()
                vehicle_type = sample_vehicle_type()
                if frame_phase == "NS":
                    source = "north" if (t + departed_index) % 2 == 0 else "south"
                else:
                    source = "west" if (t + departed_index) % 2 == 0 else "east"
                departures_detail.append(
                    {
                        "source": source,
                        "turn": turn,
                        "lane": sample_lane(turn, vehicle_type),
                        "vehicle_type": vehicle_type,
                    }
                )

        lane_queues = getattr(env, "last_lane_queues", None)
        lane_vehicle_ids = getattr(env, "last_lane_vehicle_ids", None)
        if not lane_queues:
            north_total = (env.ns_queue + 1) // 2
            south_total = env.ns_queue // 2
            west_total = (env.ew_queue + 1) // 2
            east_total = env.ew_queue // 2

            def split_lane_count(total_count: int) -> tuple[int, int, int]:
                left_count = round(total_count * env.left_rate)
                remaining = max(0, total_count - left_count)
                bike_count = round(remaining * getattr(env, "motorcycle_rate", 0.0) * 0.55)
                main_count = max(0, remaining - bike_count)
                return left_count, main_count, bike_count

            north_left, north_main, north_bike = split_lane_count(north_total)
            south_left, south_main, south_bike = split_lane_count(south_total)
            west_left, west_main, west_bike = split_lane_count(west_total)
            east_left, east_main, east_bike = split_lane_count(east_total)
            lane_queues = {
                "north_left": north_left,
                "north_main": north_main,
                "north_bike": north_bike,
                "south_left": south_left,
                "south_main": south_main,
                "south_bike": south_bike,
                "west_left": west_left,
                "west_main": west_main,
                "west_bike": west_bike,
                "east_left": east_left,
                "east_main": east_main,
                "east_bike": east_bike,
            }
        else:
            lane_queues = dict(lane_queues)

        if lane_vehicle_ids:
            lane_vehicle_ids = {
                lane_key: list(vehicle_ids)
                for lane_key, vehicle_ids in lane_vehicle_ids.items()
            }
        else:
            lane_vehicle_ids = None

        vehicle_snapshots = getattr(env, "last_vehicle_snapshots", None)
        if vehicle_snapshots is not None:
            vehicle_snapshots = [dict(snapshot) for snapshot in vehicle_snapshots]
        else:
            vehicle_snapshots = None

        frames.append(
            TraceFrame(
                step=t,
                phase=PHASES[env.phase],
                ns_queue=env.ns_queue,
                ew_queue=env.ew_queue,
                total_wait=result.total_wait,
                departed=result.departed,
                switched=result.switched,
                departed_wait_total=result.departed_wait_total,
                mean_departed_wait=(result.departed_wait_total / result.departed) if result.departed else 0.0,
                action="switch" if action == 1 else "keep",
                phase_age=env.phase_age,
                switch_cooldown=env.switch_cooldown,
                countdown=countdown,
                countdown_mode=countdown_mode,
                flow_rate=flow_rate,
                left_rate=env.left_rate,
                right_rate=env.right_rate,
                straight_rate=env.straight_rate,
                motorcycle_rate=getattr(env, "motorcycle_rate", 0.0),
                arrivals_detail=arrivals_detail,
                departures_detail=departures_detail,
                lane_queues=lane_queues,
                lane_vehicle_ids=lane_vehicle_ids,
                vehicle_snapshots=vehicle_snapshots,
            )
        )

    return frames


def evaluate(
    env: IntersectionEnv,
    agent: QLearningAgent,
    episodes: int,
    steps: int,
    fixed_cycle: int,
) -> dict[str, dict[str, float]]:
    fixed_metrics = {"avg_queue": 0.0, "avg_wait": 0.0, "avg_delay": 0.0, "throughput": 0.0, "switches": 0.0, "completed_vehicles": 0.0}
    ai_metrics = {"avg_queue": 0.0, "avg_wait": 0.0, "avg_delay": 0.0, "throughput": 0.0, "switches": 0.0, "completed_vehicles": 0.0}

    for seed in range(episodes):
        fixed_run = run_controller(env, steps, seed, "fixed", fixed_cycle=fixed_cycle)
        ai_run = run_controller(env, steps, seed, "ai", agent=agent, fixed_cycle=fixed_cycle)
        for key in fixed_metrics:
            fixed_metrics[key] += fixed_run[key]
            ai_metrics[key] += ai_run[key]

    for key in fixed_metrics:
        fixed_metrics[key] /= episodes
        ai_metrics[key] /= episodes

    return {"fixed": fixed_metrics, "ai": ai_metrics}


def print_report(results: dict[str, dict[str, float]]) -> None:
    fixed_queue = results["fixed"].get("avg_queue", results["fixed"]["avg_wait"])
    ai_queue = results["ai"].get("avg_queue", results["ai"]["avg_wait"])
    fixed_delay = results["fixed"].get("avg_delay", 0.0)
    ai_delay = results["ai"].get("avg_delay", 0.0)
    queue_improvement = ((fixed_queue - ai_queue) / fixed_queue * 100.0) if fixed_queue else 0.0
    delay_improvement = ((fixed_delay - ai_delay) / fixed_delay * 100.0) if fixed_delay else 0.0

    print("=== AI Traffic Light Demo ===")
    print(f"Fixed-time average queue length : {fixed_queue:.2f}")
    print(f"AI average queue length         : {ai_queue:.2f}")
    print(f"Queue reduction                 : {queue_improvement:.2f}%")
    print(f"Fixed average vehicle delay     : {fixed_delay:.2f} s")
    print(f"AI average vehicle delay        : {ai_delay:.2f} s")
    print(f"Delay reduction                 : {delay_improvement:.2f}%")
    print(f"Fixed throughput                : {results['fixed']['throughput']:.2f} veh/step")
    print(f"AI throughput                   : {results['ai']['throughput']:.2f} veh/step")
    print(f"Fixed switches                  : {results['fixed']['switches']:.2f}")
    print(f"AI switches                     : {results['ai']['switches']:.2f}")

    if ai_delay < fixed_delay or (ai_delay == fixed_delay and ai_queue < fixed_queue):
        print("\nConclusion: the Q-learning controller outperformed the fixed-time baseline.")
    else:
        print("\nConclusion: the current AI setup did not beat the fixed-time baseline.")


def _build_visualization_html(payload: dict[str, object]) -> str:
    template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Traffic Light Visualization</title>
  <style>
    :root {
      --bg: #ebe2d1;
      --bg-deep: #ddd0b9;
      --panel: rgba(255, 249, 239, 0.88);
      --panel-strong: rgba(255, 252, 247, 0.96);
      --ink: #18212d;
      --muted: #5a6776;
      --road: #32363f;
      --lane: #d9dce3;
      --ai: #0d766c;
      --fixed: #b46619;
      --accent: #c0392b;
      --edge: rgba(24,33,45,0.12);
      --shadow: 0 24px 60px rgba(24,33,45,0.12);
      --hero-shadow: 0 30px 80px rgba(24,33,45,0.14);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Avenir Next", "Helvetica Neue", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(13,118,108,0.18), transparent 28%),
        radial-gradient(circle at top right, rgba(180,102,25,0.18), transparent 24%),
        radial-gradient(circle at 50% 0%, rgba(255,255,255,0.58), transparent 42%),
        linear-gradient(180deg, #f7f2e8 0%, var(--bg) 58%, var(--bg-deep) 100%);
      color: var(--ink);
      min-height: 100vh;
    }
    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background:
        linear-gradient(90deg, rgba(24,33,45,0.025) 1px, transparent 1px),
        linear-gradient(rgba(24,33,45,0.025) 1px, transparent 1px);
      background-size: 28px 28px;
      mask-image: linear-gradient(180deg, rgba(0,0,0,0.34), transparent 86%);
    }
    .wrap {
      position: relative;
      max-width: 1320px;
      margin: 0 auto;
      padding: 28px 20px 48px;
    }
    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.9fr);
      gap: 20px;
      align-items: stretch;
      padding: 22px;
      border-radius: 30px;
      background:
        linear-gradient(135deg, rgba(255,255,255,0.82), rgba(255,248,236,0.7)),
        radial-gradient(circle at top left, rgba(13,118,108,0.16), transparent 40%),
        radial-gradient(circle at bottom right, rgba(180,102,25,0.16), transparent 36%);
      border: 1px solid rgba(255,255,255,0.68);
      box-shadow: var(--hero-shadow);
      overflow: hidden;
      position: relative;
    }
    .hero::after {
      content: "";
      position: absolute;
      inset: auto -12% -36% auto;
      width: 280px;
      height: 280px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(13,118,108,0.12), transparent 68%);
      pointer-events: none;
    }
    .hero-copy {
      position: relative;
      z-index: 1;
    }
    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 7px 12px;
      border-radius: 999px;
      background: rgba(24,33,45,0.08);
      color: var(--ink);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      margin-bottom: 14px;
    }
    h1 {
      margin: 0 0 10px;
      font-size: 42px;
      line-height: 1.02;
      letter-spacing: 0.02em;
      font-family: "Avenir Next", "Iowan Old Style", "Palatino Linotype", serif;
    }
    p {
      margin: 0;
      color: var(--muted);
      line-height: 1.5;
    }
    .hero-copy p {
      max-width: 720px;
      font-size: 15px;
    }
    .hero-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }
    .hero-tag {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 9px 13px;
      border-radius: 999px;
      background: rgba(255,255,255,0.72);
      border: 1px solid rgba(24,33,45,0.08);
      color: var(--ink);
      font-size: 13px;
      font-weight: 700;
      box-shadow: 0 8px 24px rgba(24,33,45,0.06);
    }
    .hero-stats {
      position: relative;
      z-index: 1;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      align-content: center;
    }
    .hero-metric {
      padding: 16px;
      border-radius: 20px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.92), rgba(255,248,239,0.84));
      border: 1px solid rgba(24,33,45,0.08);
      box-shadow: 0 16px 34px rgba(24,33,45,0.08);
    }
    .hero-metric strong {
      display: block;
      margin-top: 8px;
      font-size: 30px;
      line-height: 1;
      color: var(--ink);
    }
    .hero-k {
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--muted);
    }
    .hero-sub {
      display: block;
      margin-top: 6px;
      font-size: 13px;
      color: var(--muted);
    }
    .topbar {
      display: flex;
      flex-direction: column;
      gap: 14px;
      margin: 22px 0 24px;
      padding: 16px;
      background: rgba(255,250,240,0.66);
      border: 1px solid rgba(255,255,255,0.62);
      border-radius: 24px;
      backdrop-filter: blur(14px);
      box-shadow: 0 22px 48px rgba(24,33,45,0.08);
    }
    .topbar-main,
    .topbar-advanced {
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      align-items: stretch;
      width: 100%;
    }
    .topbar-advanced {
      display: none;
      padding-top: 4px;
      border-top: 1px dashed rgba(24,33,45,0.1);
    }
    .topbar-advanced.open {
      display: flex;
    }
    .control-cluster {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      padding: 12px 14px;
      border-radius: 18px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.78), rgba(255,250,240,0.66));
      border: 1px solid rgba(24,33,45,0.08);
      box-shadow: 0 10px 26px rgba(24,33,45,0.06);
    }
    .control-label {
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
    }
    .timeline-cluster {
      flex: 1 1 320px;
    }
    .options-cluster {
      flex: 0 0 auto;
      margin-left: auto;
    }
    .layer-cluster {
      flex: 1 1 420px;
    }
    button {
      border: 0;
      border-radius: 999px;
      padding: 11px 18px;
      font-weight: 700;
      cursor: pointer;
      background: linear-gradient(135deg, #213041, #101723);
      color: white;
      box-shadow: 0 10px 18px rgba(24,33,45,0.16);
      transition: transform 140ms ease, box-shadow 140ms ease, background 140ms ease, border-color 140ms ease;
    }
    button:hover {
      transform: translateY(-1px);
      box-shadow: 0 14px 24px rgba(24,33,45,0.2);
    }
    button:active {
      transform: translateY(0);
    }
    button.secondary {
      background: rgba(255,255,255,0.94);
      color: var(--ink);
      border: 1px solid rgba(24,33,45,0.12);
      box-shadow: none;
    }
    .options-toggle {
      min-width: 138px;
      justify-content: center;
    }
    button.active-speed {
      background: linear-gradient(135deg, #0d766c, #09423d);
      color: white;
      border: 1px solid var(--ai);
    }
    input[type="range"] {
      flex: 1 1 260px;
      accent-color: var(--ai);
    }
    .badge {
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 13px;
      background: rgba(24,33,45,0.07);
      color: var(--ink);
      border: 1px solid rgba(24,33,45,0.06);
    }
    .toggle-pill {
      position: relative;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid rgba(31,41,51,0.12);
      background: white;
      color: var(--ink);
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      user-select: none;
      transition: transform 140ms ease, border-color 140ms ease, background 140ms ease, box-shadow 140ms ease;
    }
    .toggle-pill:hover {
      transform: translateY(-1px);
      border-color: rgba(13,118,108,0.24);
      box-shadow: 0 10px 18px rgba(24,33,45,0.08);
    }
    .toggle-pill input {
      margin: 0;
      accent-color: var(--ai);
    }
    .toggle-pill:has(input:checked) {
      background: linear-gradient(135deg, rgba(13,118,108,0.14), rgba(13,118,108,0.04));
      border-color: rgba(13,118,108,0.3);
      color: #0b5f58;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(520px, 1fr));
      gap: 20px;
    }
    .panel {
      position: relative;
      background:
        linear-gradient(180deg, rgba(255,252,247,0.88), rgba(255,247,236,0.78));
      border-radius: 28px;
      padding: 18px;
      box-shadow: var(--shadow);
      border: 1px solid rgba(255,255,255,0.58);
      overflow: hidden;
    }
    .panel::before {
      content: "";
      position: absolute;
      inset: 0 auto auto 0;
      width: 100%;
      height: 4px;
      background: linear-gradient(90deg, rgba(180,102,25,0.95), rgba(13,118,108,0.95));
      opacity: 0.9;
    }
    .panel-head {
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: flex-start;
      margin-bottom: 12px;
    }
    .panel h2 {
      margin: 0 0 14px;
      font-size: 24px;
      line-height: 1.05;
      font-family: "Avenir Next", "Iowan Old Style", "Palatino Linotype", serif;
    }
    .panel-note {
      margin: -4px 0 0;
      font-size: 13px;
      color: var(--muted);
    }
    .panel-flags {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .panel-flag {
      display: inline-flex;
      align-items: center;
      padding: 7px 11px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      background: rgba(24,33,45,0.07);
      color: var(--ink);
      border: 1px solid rgba(24,33,45,0.08);
    }
    .panel.fixed-panel .panel-flag.primary {
      background: rgba(180,102,25,0.14);
      color: #9a5614;
      border-color: rgba(180,102,25,0.18);
    }
    .panel.ai-panel .panel-flag.primary {
      background: rgba(13,118,108,0.14);
      color: #0b5f58;
      border-color: rgba(13,118,108,0.18);
    }
    .label-fixed { color: var(--fixed); }
    .label-ai { color: var(--ai); }
    .canvas-shell {
      position: relative;
      padding: 10px;
      border-radius: 24px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.76), rgba(255,248,237,0.46));
      border: 1px solid rgba(24,33,45,0.08);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.72);
    }
    canvas {
      width: 100%;
      aspect-ratio: 5 / 4;
      border-radius: 18px;
      background:
        linear-gradient(0deg, rgba(255,255,255,0.35), rgba(255,255,255,0.35)),
        repeating-linear-gradient(45deg, rgba(31,41,51,0.03) 0 12px, rgba(31,41,51,0.05) 12px 24px);
      display: block;
    }
    .canvas-hint {
      position: absolute;
      left: 18px;
      right: 18px;
      bottom: 16px;
      display: flex;
      justify-content: space-between;
      gap: 12px;
      pointer-events: none;
    }
    .canvas-chip {
      padding: 7px 11px;
      border-radius: 999px;
      background: rgba(17,24,39,0.72);
      color: rgba(255,255,255,0.92);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.04em;
      backdrop-filter: blur(8px);
      border: 1px solid rgba(255,255,255,0.14);
    }
    .mini-map {
      position: absolute;
      right: 14px;
      bottom: 14px;
      width: 168px;
      height: 132px;
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,0.55);
      box-shadow: 0 12px 28px rgba(31,41,51,0.18);
      background: rgba(17,24,39,0.84);
      backdrop-filter: blur(10px);
      pointer-events: none;
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }
    .stat {
      position: relative;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.96), rgba(246,242,235,0.92));
      border-radius: 18px;
      padding: 14px 14px 12px;
      border: 1px solid rgba(24,33,45,0.08);
      box-shadow: 0 10px 22px rgba(24,33,45,0.06);
      overflow: hidden;
    }
    .stat::before {
      content: "";
      position: absolute;
      inset: 0 auto auto 0;
      width: 100%;
      height: 3px;
      background: linear-gradient(90deg, rgba(180,102,25,0.9), rgba(13,118,108,0.9));
    }
    .stat .k {
      display: block;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin-bottom: 5px;
    }
    .stat .v {
      font-size: 28px;
      font-weight: 900;
      line-height: 1;
    }
    .summary {
      margin-top: 24px;
      padding: 22px;
      border-radius: 26px;
      background:
        linear-gradient(135deg, rgba(255,250,240,0.92), rgba(255,245,233,0.84));
      border: 1px solid rgba(255,255,255,0.64);
      box-shadow: 0 20px 48px rgba(24,33,45,0.08);
      display: grid;
      grid-template-columns: minmax(220px, 0.9fr) minmax(0, 1.2fr);
      gap: 18px;
      align-items: center;
    }
    .summary strong {
      display: block;
      font-size: 24px;
      line-height: 1.1;
      font-family: "Avenir Next", "Iowan Old Style", "Palatino Linotype", serif;
    }
    .summary p {
      font-size: 15px;
    }
    @media (max-width: 980px) {
      .hero {
        grid-template-columns: 1fr;
      }
      .hero-stats {
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }
      .summary {
        grid-template-columns: 1fr;
      }
    }
    @media (max-width: 720px) {
      .wrap { padding: 18px 14px 32px; }
      h1 { font-size: 32px; }
      .hero { padding: 18px; border-radius: 24px; }
      .hero-stats { grid-template-columns: 1fr 1fr; }
      .grid { grid-template-columns: 1fr; }
      .stats { grid-template-columns: 1fr 1fr; }
      .panel-head { flex-direction: column; }
      .canvas-hint { display: none; }
      .mini-map { width: 138px; height: 108px; }
      .options-cluster { margin-left: 0; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="hero-copy">
        <div class="eyebrow">Traffic Replay Studio</div>
        <h1>AI Traffic Light Visualization</h1>
        <p>Side-by-side replay of a single intersection. The same traffic arrivals are fed to the fixed-time controller and the Q-learning controller so you can compare them fairly while still exposing lane-level queues, red timers, zoom tools, and exact SUMO objects.</p>
        <div class="hero-tags">
          <span class="hero-tag">SUMO exact replay</span>
          <span class="hero-tag">Lane 0 / lane 1 counters</span>
          <span class="hero-tag">Interactive debug overlays</span>
        </div>
      </div>
      <div class="hero-stats">
        <div class="hero-metric">
          <span class="hero-k">Frames</span>
          <strong id="heroFrames">0</strong>
          <span class="hero-sub">Replay steps available</span>
        </div>
        <div class="hero-metric">
          <span class="hero-k">Delay Gain</span>
          <strong id="heroGain">0%</strong>
          <span class="hero-sub">AI vs fixed-time baseline</span>
        </div>
        <div class="hero-metric">
          <span class="hero-k">Visual Mode</span>
          <strong id="heroMode">SUMO</strong>
          <span class="hero-sub">Exact object snapshots</span>
        </div>
        <div class="hero-metric">
          <span class="hero-k">Tools</span>
          <strong id="heroTools">6</strong>
          <span class="hero-sub">Toggles ready to inspect</span>
        </div>
      </div>
    </section>

    <div class="topbar">
      <div class="topbar-main">
        <div class="control-cluster">
          <span class="control-label">Playback</span>
          <button id="playBtn">Play</button>
          <button id="resetBtn" class="secondary">Reset</button>
          <button id="speedQuarterBtn" class="secondary">0.25x</button>
          <button id="speedHalfBtn" class="secondary">0.5x</button>
          <button id="speedNormalBtn" class="secondary">1x</button>
          <button id="speedDoubleBtn" class="secondary">2x</button>
        </div>
        <div class="control-cluster timeline-cluster">
          <span class="control-label">Timeline</span>
          <input id="timeline" type="range" min="0" max="0" value="0">
          <div class="badge" id="stepLabel">Step 0</div>
          <div class="badge" id="speedLabel">Playback 1x</div>
        </div>
        <div class="control-cluster options-cluster">
          <span class="control-label">More</span>
          <button id="optionsToggleBtn" class="secondary options-toggle" aria-expanded="false" aria-controls="advancedControls">Show Options</button>
          <div class="badge" id="viewLabel">100%</div>
        </div>
      </div>
      <div id="advancedControls" class="topbar-advanced">
        <div class="control-cluster">
          <span class="control-label">Jump</span>
          <button id="jumpQueueBtn" class="secondary">Max Queue</button>
          <button id="jumpSwitchBtn" class="secondary">Next Switch</button>
          <button id="jumpObjectsBtn" class="secondary">Most Cars</button>
        </div>
        <div class="control-cluster">
          <span class="control-label">View</span>
          <button id="zoomOutBtn" class="secondary">Zoom -</button>
          <button id="zoomInBtn" class="secondary">Zoom +</button>
          <button id="resetViewBtn" class="secondary">Reset View</button>
        </div>
        <div class="control-cluster layer-cluster">
          <span class="control-label">Layers</span>
          <label class="toggle-pill"><input id="toggleCars" type="checkbox" checked>Cars</label>
          <label class="toggle-pill"><input id="toggleCounters" type="checkbox" checked>Counters</label>
          <label class="toggle-pill"><input id="toggleTimers" type="checkbox" checked>Red Timers</label>
          <label class="toggle-pill"><input id="toggleLabels" type="checkbox" checked>Lane Labels</label>
          <label class="toggle-pill"><input id="toggleHighlight" type="checkbox" checked>Halted</label>
          <label class="toggle-pill"><input id="toggleExact" type="checkbox" checked>Exact Replay</label>
        </div>
      </div>
    </div>

    <div class="grid">
      <section class="panel fixed-panel">
        <div class="panel-head">
          <div>
            <h2 class="label-fixed">Fixed-Time Controller</h2>
            <p class="panel-note" id="fixedTurnRates">Turn split L 20% | S 55% | R 25%</p>
          </div>
          <div class="panel-flags">
            <span class="panel-flag primary">Baseline</span>
            <span class="panel-flag">Static Cycle</span>
          </div>
        </div>
        <div class="canvas-shell">
          <canvas id="fixedCanvas" width="800" height="640"></canvas>
          <canvas id="fixedMiniMap" class="mini-map" width="168" height="132"></canvas>
          <div class="canvas-hint">
            <span class="canvas-chip">Drag to pan</span>
            <span class="canvas-chip">Scroll to zoom</span>
          </div>
        </div>
        <div class="stats">
          <div class="stat"><span class="k">Phase</span><span class="v" id="fixedPhase">NS</span></div>
          <div class="stat"><span class="k">Queue</span><span class="v" id="fixedQueue">0</span></div>
          <div class="stat"><span class="k">Departed</span><span class="v" id="fixedDeparted">0</span></div>
          <div class="stat"><span class="k">Flow</span><span class="v" id="fixedFlow">0.0</span></div>
        </div>
      </section>

      <section class="panel ai-panel">
        <div class="panel-head">
          <div>
            <h2 class="label-ai">Q-Learning Controller</h2>
            <p class="panel-note" id="aiTurnRates">Turn split L 20% | S 55% | R 25%</p>
          </div>
          <div class="panel-flags">
            <span class="panel-flag primary">Adaptive</span>
            <span class="panel-flag">Lane-Aware</span>
          </div>
        </div>
        <div class="canvas-shell">
          <canvas id="aiCanvas" width="800" height="640"></canvas>
          <canvas id="aiMiniMap" class="mini-map" width="168" height="132"></canvas>
          <div class="canvas-hint">
            <span class="canvas-chip">Drag to pan</span>
            <span class="canvas-chip">Scroll to zoom</span>
          </div>
        </div>
        <div class="stats">
          <div class="stat"><span class="k">Phase</span><span class="v" id="aiPhase">NS</span></div>
          <div class="stat"><span class="k">Queue</span><span class="v" id="aiQueue">0</span></div>
          <div class="stat"><span class="k">Departed</span><span class="v" id="aiDeparted">0</span></div>
          <div class="stat"><span class="k">Flow</span><span class="v" id="aiFlow">0.0</span></div>
        </div>
      </section>
    </div>

    <div class="summary">
      <strong id="summaryHeadline"></strong>
      <p id="summaryText"></p>
    </div>
  </div>

  <script>
    const payload = __TRACE_JSON__;
    const fixedFrames = payload.fixed_frames;
    const aiFrames = payload.ai_frames;
    const metrics = payload.metrics;
    const fixedCanvasEl = document.getElementById("fixedCanvas");
    const aiCanvasEl = document.getElementById("aiCanvas");
    const timeline = document.getElementById("timeline");
    const playBtn = document.getElementById("playBtn");
    const resetBtn = document.getElementById("resetBtn");
    const speedQuarterBtn = document.getElementById("speedQuarterBtn");
    const speedHalfBtn = document.getElementById("speedHalfBtn");
    const speedNormalBtn = document.getElementById("speedNormalBtn");
    const speedDoubleBtn = document.getElementById("speedDoubleBtn");
    const jumpQueueBtn = document.getElementById("jumpQueueBtn");
    const jumpSwitchBtn = document.getElementById("jumpSwitchBtn");
    const jumpObjectsBtn = document.getElementById("jumpObjectsBtn");
    const optionsToggleBtn = document.getElementById("optionsToggleBtn");
    const advancedControls = document.getElementById("advancedControls");
    const zoomOutBtn = document.getElementById("zoomOutBtn");
    const zoomInBtn = document.getElementById("zoomInBtn");
    const resetViewBtn = document.getElementById("resetViewBtn");
    const stepLabel = document.getElementById("stepLabel");
    const speedLabel = document.getElementById("speedLabel");
    const viewLabel = document.getElementById("viewLabel");
    const toggleCars = document.getElementById("toggleCars");
    const toggleCounters = document.getElementById("toggleCounters");
    const toggleTimers = document.getElementById("toggleTimers");
    const toggleLabels = document.getElementById("toggleLabels");
    const toggleHighlight = document.getElementById("toggleHighlight");
    const toggleExact = document.getElementById("toggleExact");
    const totalFrames = Math.max(fixedFrames.length, aiFrames.length);
    const baseFps = 10;
    const playbackSubsteps = 4;
    let playbackRate = 1;
    let timer = null;
    let current = 0;
    const fixedSchedule = buildVisualSchedule(fixedFrames, fixedCanvasEl.width, fixedCanvasEl.height);
    const aiSchedule = buildVisualSchedule(aiFrames, aiCanvasEl.width, aiCanvasEl.height);
    const fixedLaneState = buildLaneState(fixedFrames);
    const aiLaneState = buildLaneState(aiFrames);
    const fixedLightTimers = buildApproachRedTimers(fixedFrames);
    const aiLightTimers = buildApproachRedTimers(aiFrames);
    const layerState = {
      cars: true,
      counters: true,
      timers: true,
      labels: true,
      halted: true,
      exact: true,
    };
    const defaultViewState = () => ({ zoom: 1, panX: 0, panY: 0 });
    const viewStates = {
      fixedCanvas: defaultViewState(),
      aiCanvas: defaultViewState(),
    };
    const importantFrames = computeImportantFrames();
    let dragState = null;

    timeline.max = Math.max(0, totalFrames - 1);
    speedLabel.textContent = `Playback ${playbackRate}x (${baseFps} fps base)`;
    updateViewLabel();

    function signalState(frame, axis) {
      if (frame.countdown_mode === "clear") {
        if (frame.switched) {
          const previousPhase = frame.phase === "NS" ? "EW" : "NS";
          return axis === previousPhase ? "yellow" : "red";
        }
        return "red";
      }
      return frame.phase === axis ? "green" : "red";
    }

    function lerp(a, b, t) {
      return a + (b - a) * t;
    }

    function axisForApproach(approach) {
      return approach === "north" || approach === "south" ? "NS" : "EW";
    }

    function buildApproachRedTimers(frames) {
      return frames.map((frame, index) => {
        const timers = {};
        for (const approach of ["north", "south", "west", "east"]) {
          const axis = axisForApproach(approach);
          const currentState = signalState(frame, axis);
          if (currentState === "green") {
            timers[approach] = 0;
            continue;
          }
          let waitSeconds = null;
          for (let future = index + 1; future < frames.length; future++) {
            if (signalState(frames[future], axis) === "green") {
              waitSeconds = future - index;
              break;
            }
          }
          timers[approach] = waitSeconds;
        }
        return timers;
      });
    }

    function updateViewLabel() {
      const avgZoom = (viewStates.fixedCanvas.zoom + viewStates.aiCanvas.zoom) / 2;
      viewLabel.textContent = `${Math.round(avgZoom * 100)}%`;
    }

    function setAdvancedControlsOpen(open) {
      advancedControls.classList.toggle("open", open);
      optionsToggleBtn.setAttribute("aria-expanded", open ? "true" : "false");
      optionsToggleBtn.textContent = open ? "Hide Options" : "Show Options";
    }

    function clampView(canvasId) {
      const canvas = document.getElementById(canvasId);
      const view = viewStates[canvasId];
      const maxPanX = canvas.width * 0.45 * Math.max(0, view.zoom - 1);
      const maxPanY = canvas.height * 0.45 * Math.max(0, view.zoom - 1);
      view.panX = Math.max(-maxPanX, Math.min(maxPanX, view.panX));
      view.panY = Math.max(-maxPanY, Math.min(maxPanY, view.panY));
    }

    function inverseViewPoint(canvasId, sx, sy) {
      const canvas = document.getElementById(canvasId);
      const view = viewStates[canvasId];
      return {
        x: (sx - canvas.width / 2 - view.panX) / view.zoom + canvas.width / 2,
        y: (sy - canvas.height / 2 - view.panY) / view.zoom + canvas.height / 2,
      };
    }

    function applyViewTransform(ctx, canvasId) {
      const canvas = document.getElementById(canvasId);
      const view = viewStates[canvasId];
      ctx.translate(canvas.width / 2 + view.panX, canvas.height / 2 + view.panY);
      ctx.scale(view.zoom, view.zoom);
      ctx.translate(-canvas.width / 2, -canvas.height / 2);
    }

    function setAllViewsZoom(delta) {
      for (const canvasId of Object.keys(viewStates)) {
        const view = viewStates[canvasId];
        view.zoom = Math.max(0.72, Math.min(2.8, view.zoom + delta));
        clampView(canvasId);
      }
      updateViewLabel();
      render(current);
    }

    function resetAllViews() {
      for (const canvasId of Object.keys(viewStates)) {
        viewStates[canvasId] = defaultViewState();
      }
      updateViewLabel();
      render(current);
    }

    function computeImportantFrames() {
      let maxQueueIndex = 0;
      let maxQueueValue = -1;
      let maxObjectsIndex = 0;
      let maxObjectsValue = -1;
      const switchFrames = [];

      for (let index = 0; index < totalFrames; index++) {
        const fixed = fixedFrames[index] || fixedFrames[fixedFrames.length - 1];
        const ai = aiFrames[index] || aiFrames[aiFrames.length - 1];
        const queueValue = Math.max(fixed.total_wait || 0, ai.total_wait || 0);
        const objectValue = Math.max(
          Array.isArray(fixed.vehicle_snapshots) ? fixed.vehicle_snapshots.length : 0,
          Array.isArray(ai.vehicle_snapshots) ? ai.vehicle_snapshots.length : 0
        );
        if (queueValue > maxQueueValue) {
          maxQueueValue = queueValue;
          maxQueueIndex = index;
        }
        if (objectValue > maxObjectsValue) {
          maxObjectsValue = objectValue;
          maxObjectsIndex = index;
        }
        if (fixed.switched || ai.switched) {
          switchFrames.push(index);
        }
      }

      return { maxQueueIndex, maxObjectsIndex, switchFrames };
    }

    function jumpToFrame(index) {
      stopPlayback();
      render(Math.max(0, Math.min(totalFrames - 1, index)));
    }

    function routeGeometry(source, turn, laneKey, cx, cy, w, h) {
      const leftNear = 14;
      const mainFar = 42;
      const bikeFar = 70;
      const stop = 86;
      const laneType = laneKey && laneKey.endsWith("_bike")
        ? "bike"
        : laneKey && laneKey.endsWith("_left")
          ? "left"
          : "main";
      const routes = {
        north: {
          straight: {
            bike: {
              lane: "north_bike",
              points: [{ x: cx - bikeFar, y: cy - 136 }, { x: cx - bikeFar, y: h + 34 }],
              zones: [],
            },
            main: {
              lane: "north_main",
              points: [{ x: cx - mainFar, y: cy - 136 }, { x: cx - mainFar, y: h + 34 }],
              zones: [],
            },
          },
          left: {
            lane: "north_left",
            points: [
              { x: cx - leftNear, y: cy - 136 },
              { x: cx - leftNear, y: cy - stop },
              { x: cx - 18, y: cy - 18 },
              { x: w + 34, y: cy + leftNear },
            ],
            zones: [
              { zone: "north_left_vs_south_straight", start: 0.32, end: 0.60 },
              { zone: "ns_left_shared", start: 0.48, end: 0.80 },
            ],
          },
          right: {
            bike: {
              lane: "north_bike",
              points: [
                { x: cx - bikeFar, y: cy - 136 },
                { x: cx - bikeFar, y: cy - stop },
                { x: cx - stop, y: cy - 74 },
                { x: -34, y: cy - bikeFar },
              ],
              zones: [{ zone: "corner_nw", start: 0.42, end: 0.70 }],
            },
            main: {
              lane: "north_main",
              points: [
                { x: cx - mainFar, y: cy - 136 },
                { x: cx - mainFar, y: cy - stop },
                { x: cx - stop, y: cy - 48 },
                { x: -34, y: cy - mainFar },
              ],
              zones: [{ zone: "corner_nw", start: 0.42, end: 0.70 }],
            },
          },
        },
        south: {
          straight: {
            bike: {
              lane: "south_bike",
              points: [{ x: cx + bikeFar, y: cy + 136 }, { x: cx + bikeFar, y: -34 }],
              zones: [],
            },
            main: {
              lane: "south_main",
              points: [{ x: cx + mainFar, y: cy + 136 }, { x: cx + mainFar, y: -34 }],
              zones: [],
            },
          },
          left: {
            lane: "south_left",
            points: [
              { x: cx + leftNear, y: cy + 136 },
              { x: cx + leftNear, y: cy + stop },
              { x: cx + 18, y: cy + 18 },
              { x: -34, y: cy - leftNear },
            ],
            zones: [
              { zone: "south_left_vs_north_straight", start: 0.32, end: 0.60 },
              { zone: "ns_left_shared", start: 0.48, end: 0.80 },
            ],
          },
          right: {
            bike: {
              lane: "south_bike",
              points: [
                { x: cx + bikeFar, y: cy + 136 },
                { x: cx + bikeFar, y: cy + stop },
                { x: cx + stop, y: cy + 74 },
                { x: w + 34, y: cy + bikeFar },
              ],
              zones: [{ zone: "corner_se", start: 0.42, end: 0.70 }],
            },
            main: {
              lane: "south_main",
              points: [
                { x: cx + mainFar, y: cy + 136 },
                { x: cx + mainFar, y: cy + stop },
                { x: cx + stop, y: cy + 48 },
                { x: w + 34, y: cy + mainFar },
              ],
              zones: [{ zone: "corner_se", start: 0.42, end: 0.70 }],
            },
          },
        },
        west: {
          straight: {
            bike: {
              lane: "west_bike",
              points: [{ x: cx - 136, y: cy + bikeFar }, { x: w + 34, y: cy + bikeFar }],
              zones: [],
            },
            main: {
              lane: "west_main",
              points: [{ x: cx - 136, y: cy + mainFar }, { x: w + 34, y: cy + mainFar }],
              zones: [],
            },
          },
          left: {
            lane: "west_left",
            points: [
              { x: cx - 136, y: cy + leftNear },
              { x: cx - stop, y: cy + leftNear },
              { x: cx - 18, y: cy + 18 },
              { x: cx + leftNear, y: -34 },
            ],
            zones: [
              { zone: "west_left_vs_east_straight", start: 0.32, end: 0.60 },
              { zone: "ew_left_shared", start: 0.48, end: 0.80 },
            ],
          },
          right: {
            bike: {
              lane: "west_bike",
              points: [
                { x: cx - 136, y: cy + bikeFar },
                { x: cx - stop, y: cy + bikeFar },
                { x: cx - 74, y: cy + stop },
                { x: cx - bikeFar, y: h + 34 },
              ],
              zones: [{ zone: "corner_sw", start: 0.42, end: 0.70 }],
            },
            main: {
              lane: "west_main",
              points: [
                { x: cx - 136, y: cy + mainFar },
                { x: cx - stop, y: cy + mainFar },
                { x: cx - 48, y: cy + stop },
                { x: cx - mainFar, y: h + 34 },
              ],
              zones: [{ zone: "corner_sw", start: 0.42, end: 0.70 }],
            },
          },
        },
        east: {
          straight: {
            bike: {
              lane: "east_bike",
              points: [{ x: cx + 136, y: cy - bikeFar }, { x: -34, y: cy - bikeFar }],
              zones: [],
            },
            main: {
              lane: "east_main",
              points: [{ x: cx + 136, y: cy - mainFar }, { x: -34, y: cy - mainFar }],
              zones: [],
            },
          },
          left: {
            lane: "east_left",
            points: [
              { x: cx + 136, y: cy - leftNear },
              { x: cx + stop, y: cy - leftNear },
              { x: cx + 18, y: cy - 18 },
              { x: cx - leftNear, y: h + 34 },
            ],
            zones: [
              { zone: "east_left_vs_west_straight", start: 0.32, end: 0.60 },
              { zone: "ew_left_shared", start: 0.48, end: 0.80 },
            ],
          },
          right: {
            bike: {
              lane: "east_bike",
              points: [
                { x: cx + 136, y: cy - bikeFar },
                { x: cx + stop, y: cy - bikeFar },
                { x: cx + 74, y: cy - stop },
                { x: cx + bikeFar, y: -34 },
              ],
              zones: [{ zone: "corner_ne", start: 0.42, end: 0.70 }],
            },
            main: {
              lane: "east_main",
              points: [
                { x: cx + 136, y: cy - mainFar },
                { x: cx + stop, y: cy - mainFar },
                { x: cx + 48, y: cy - stop },
                { x: cx + mainFar, y: -34 },
              ],
              zones: [{ zone: "corner_ne", start: 0.42, end: 0.70 }],
            },
          },
        },
      };
      if (turn === "left") {
        return routes[source].left;
      }
      return routes[source][turn][laneType === "bike" ? "bike" : "main"];
    }

    function sourceColor(source, fallback) {
      const colors = {
        north: "#2563eb",
        south: "#dc2626",
        west: "#ca8a04",
        east: "#7c3aed",
      };
      return colors[source] || fallback;
    }

    function movementLane(source, turn, lane = null) {
      if (turn === "left" || lane === "left") {
        return `${source}_left`;
      }
      if (lane === "bike") {
        return `${source}_bike`;
      }
      return `${source}_main`;
    }

    function emptyLaneMap() {
      return {
        north_left: [],
        north_main: [],
        north_bike: [],
        south_left: [],
        south_main: [],
        south_bike: [],
        west_left: [],
        west_main: [],
        west_bike: [],
        east_left: [],
        east_main: [],
        east_bike: [],
      };
    }

    function cloneLaneSnapshot(rawSnapshot) {
      const snapshot = emptyLaneMap();
      if (!rawSnapshot) {
        return snapshot;
      }
      for (const laneKey of Object.keys(snapshot)) {
        snapshot[laneKey] = Array.isArray(rawSnapshot[laneKey]) ? [...rawSnapshot[laneKey]] : [];
      }
      return snapshot;
    }

    function buildLaneState(frames) {
      const hasExactSnapshots = frames.some((frame) => frame.lane_vehicle_ids);
      if (hasExactSnapshots) {
        const snapshots = [];
        const arrivals = [];
        const vehicleTypes = {};
        let previousSnapshot = emptyLaneMap();

        for (let step = 0; step < frames.length; step++) {
          const frame = frames[step];
          const snapshot = cloneLaneSnapshot(frame.lane_vehicle_ids);
          const snapshotTypes = new Map(
            Array.isArray(frame.vehicle_snapshots)
              ? frame.vehicle_snapshots.map((item) => [item.id, item.vehicle_type || "car"])
              : []
          );
          const previousIds = new Set(
            Object.values(previousSnapshot).flatMap((ids) => ids)
          );

          for (const [laneKey, ids] of Object.entries(snapshot)) {
            let sequence = 0;
            for (const vehicleId of ids) {
              vehicleTypes[vehicleId] = snapshotTypes.get(vehicleId) || vehicleTypes[vehicleId] || (laneKey.endsWith("_bike") ? "motorcycle" : "car");
              if (previousIds.has(vehicleId)) {
                continue;
              }
              const [source, laneType] = laneKey.split("_");
              arrivals.push({
                id: vehicleId,
                source,
                lane: laneType === "left" ? "left" : laneType === "bike" ? "bike" : "main",
                laneKey,
                step,
                sequence,
              });
              sequence += 1;
            }
          }

          snapshots.push(snapshot);
          previousSnapshot = snapshot;
        }

        return { snapshots, arrivals, vehicleTypes };
      }

      const lanes = emptyLaneMap();
      const snapshots = [];
      const arrivals = [];
      const vehicleTypes = {};
      let nextVehicleId = 1;
      let nextSyntheticId = 1;

      for (let step = 0; step < frames.length; step++) {
        const frame = frames[step];

        for (let i = 0; i < frame.arrivals_detail.length; i++) {
          const item = frame.arrivals_detail[i];
          const laneKey =
            item.lane === "left" ? `${item.source}_left` : item.lane === "bike" ? `${item.source}_bike` : `${item.source}_main`;
          const vehicle = {
            id: `${laneKey}_${nextVehicleId++}`,
            source: item.source,
            vehicleType: item.vehicle_type || "car",
          };
          lanes[laneKey].push(vehicle);
          vehicleTypes[vehicle.id] = vehicle.vehicleType;
          arrivals.push({
            id: vehicle.id,
            source: item.source,
            lane: item.lane,
            laneKey,
            step,
            sequence: i,
            vehicle_type: vehicle.vehicleType,
          });
        }

        for (const item of frame.departures_detail) {
          const laneKey = movementLane(item.source, item.turn, item.lane || null);
          if (lanes[laneKey].length > 0) {
            lanes[laneKey].shift();
          }
        }

        const desiredQueues = frame.lane_queues || {};
        for (const laneKey of Object.keys(lanes)) {
          const desiredCount = desiredQueues[laneKey];
          if (typeof desiredCount !== "number") {
            continue;
          }
          while (lanes[laneKey].length < desiredCount) {
            const syntheticVehicleType = laneKey.endsWith("_bike") ? "motorcycle" : "car";
            const syntheticVehicle = {
              id: `${laneKey}_synthetic_${nextSyntheticId++}`,
              source: laneKey.split("_")[0],
              vehicleType: syntheticVehicleType,
            };
            lanes[laneKey].push(syntheticVehicle);
            vehicleTypes[syntheticVehicle.id] = syntheticVehicle.vehicleType;
          }
          while (lanes[laneKey].length > desiredCount) {
            lanes[laneKey].pop();
          }
        }

        snapshots.push(
          Object.fromEntries(
            Object.entries(lanes).map(([laneKey, vehicles]) => [laneKey, vehicles.map((vehicle) => vehicle.id)])
          )
        );
      }

      return { snapshots, arrivals, vehicleTypes };
    }

    function laneGeometry(laneKey, cx, cy) {
      const map = {
        north_left: { orientation: "vertical", x: cx - 14, y: cy - 136, direction: -1, label: "L", source: "north", available: 188 },
        north_main: { orientation: "vertical", x: cx - 42, y: cy - 136, direction: -1, label: "T", source: "north", available: 188 },
        north_bike: { orientation: "vertical", x: cx - 70, y: cy - 136, direction: -1, label: "M", source: "north", available: 188 },
        south_left: { orientation: "vertical", x: cx + 14, y: cy + 136, direction: 1, label: "L", source: "south", available: 188 },
        south_main: { orientation: "vertical", x: cx + 42, y: cy + 136, direction: 1, label: "T", source: "south", available: 188 },
        south_bike: { orientation: "vertical", x: cx + 70, y: cy + 136, direction: 1, label: "M", source: "south", available: 188 },
        west_left: { orientation: "horizontal", x: cx - 136, y: cy + 14, direction: -1, label: "L", source: "west", available: 236 },
        west_main: { orientation: "horizontal", x: cx - 136, y: cy + 42, direction: -1, label: "T", source: "west", available: 236 },
        west_bike: { orientation: "horizontal", x: cx - 136, y: cy + 70, direction: -1, label: "M", source: "west", available: 236 },
        east_left: { orientation: "horizontal", x: cx + 136, y: cy - 14, direction: 1, label: "L", source: "east", available: 236 },
        east_main: { orientation: "horizontal", x: cx + 136, y: cy - 42, direction: 1, label: "T", source: "east", available: 236 },
        east_bike: { orientation: "horizontal", x: cx + 136, y: cy - 70, direction: 1, label: "M", source: "east", available: 236 },
      };
      return map[laneKey];
    }

    function sampleRoute(route, progress) {
      if (!route._segments) {
        route._segments = [];
        route._totalLength = 0;
        for (let i = 0; i < route.points.length - 1; i++) {
          const start = route.points[i];
          const end = route.points[i + 1];
          const dx = end.x - start.x;
          const dy = end.y - start.y;
          const length = Math.hypot(dx, dy);
          route._segments.push({ start, end, dx, dy, length });
          route._totalLength += length;
        }
      }
      let remaining = progress * route._totalLength;
      for (const segment of route._segments) {
        if (remaining <= segment.length || segment === route._segments[route._segments.length - 1]) {
          const t = segment.length === 0 ? 0 : Math.max(0, Math.min(1, remaining / segment.length));
          return {
            x: lerp(segment.start.x, segment.end.x, t),
            y: lerp(segment.start.y, segment.end.y, t),
            dx: segment.dx,
            dy: segment.dy,
          };
        }
        remaining -= segment.length;
      }
      const fallback = route._segments[route._segments.length - 1];
      return { x: fallback.end.x, y: fallback.end.y, dx: fallback.dx, dy: fallback.dy };
    }

    function buildVisualSchedule(frames, w, h) {
      const cx = w / 2;
      const cy = h / 2;
      const travelFrames = 22;
      const laneHeadway = 1.5;
      const laneNextFree = {};
      const zoneNextFree = {};
      const schedule = [];
      const oppositeStraightFree = {};
      let intersectionClearUntil = 0;
      let lastFramePhase = null;

      function opposingStraightZone(source) {
        if (source === "north") return "south_straight";
        if (source === "south") return "north_straight";
        if (source === "west") return "east_straight";
        return "west_straight";
      }

      for (let step = 0; step < frames.length; step++) {
        const frame = frames[step];
        const phaseChanged = lastFramePhase !== null && frame.phase !== lastFramePhase;
        for (let departedIndex = 0; departedIndex < frame.departures_detail.length; departedIndex++) {
          const detail = frame.departures_detail[departedIndex];
          const route = routeGeometry(detail.source, detail.turn, movementLane(detail.source, detail.turn, detail.lane || null), cx, cy, w, h);
          const routeKey = route.lane;
          let startTime = step + departedIndex * 0.25;
          startTime = Math.max(startTime, laneNextFree[routeKey] || 0);
          if (phaseChanged) {
            startTime = Math.max(startTime, intersectionClearUntil + 0.2);
          }

          for (const usage of route.zones) {
            const blockedUntil = zoneNextFree[usage.zone] || 0;
            startTime = Math.max(startTime, blockedUntil - usage.start * travelFrames);
          }

          if (detail.turn === "left") {
            const oppositeBlocked = oppositeStraightFree[opposingStraightZone(detail.source)] || 0;
            startTime = Math.max(startTime, oppositeBlocked + 0.2);
          }

          laneNextFree[routeKey] = startTime + laneHeadway;
          for (const usage of route.zones) {
            zoneNextFree[usage.zone] = startTime + usage.end * travelFrames + 0.35;
          }
          const routeClearTime = startTime + 0.82 * travelFrames;
          if (detail.turn === "straight") {
            oppositeStraightFree[`${detail.source}_straight`] = startTime + 0.58 * travelFrames;
          }
          intersectionClearUntil = Math.max(intersectionClearUntil, routeClearTime);

          schedule.push({
            source: detail.source,
            turn: detail.turn,
            vehicle_type: detail.vehicle_type || "car",
            route,
            startTime,
            travelFrames,
          });
        }
        lastFramePhase = frame.phase;
      }
      return schedule;
    }

    function buildTransitCars(schedule, index, theme) {
      const cars = [];
      for (const item of schedule) {
        const age = index - item.startTime;
        if (age < 0 || age > item.travelFrames) {
          continue;
        }
        const progress = age / item.travelFrames;
        const pose = sampleRoute(item.route, progress);
        const horizontal = Math.abs(pose.dx) >= Math.abs(pose.dy);
        const isMotorcycle = item.vehicle_type === "motorcycle";
        cars.push({
          x: pose.x,
          y: pose.y,
          w: horizontal ? (isMotorcycle ? 18 : 22) : (isMotorcycle ? 12 : 18),
          h: horizontal ? (isMotorcycle ? 12 : 18) : (isMotorcycle ? 18 : 22),
          color: sourceColor(item.source, theme),
          vehicleType: item.vehicle_type || "car",
        });
      }
      return cars;
    }

    function remap(value, inStart, inEnd, outStart, outEnd) {
      if (Math.abs(inEnd - inStart) < 1e-6) {
        return outStart;
      }
      return outStart + ((value - inStart) / (inEnd - inStart)) * (outEnd - outStart);
    }

    function buildExactProjection(w, h) {
      const cx = w / 2;
      const cy = h / 2;
      const road = 184;
      const roadHalf = road / 2;
      const viewportX = 34;
      const viewportY = 30;
      const approachMin = 86.4;
      const approachMax = 113.6;
      const junctionMin = 86.4;
      const junctionMax = 113.6;
      const approachScaleX = (cx - roadHalf - viewportX) / approachMin;
      const approachScaleY = (cy - roadHalf - viewportY) / approachMin;
      const vehicleScale = Math.sqrt(approachScaleX * approachScaleY);

      function mapX(x) {
        if (x <= approachMin) {
          return remap(x, 0, approachMin, viewportX, cx - roadHalf);
        }
        if (x >= approachMax) {
          return remap(x, approachMax, 200, cx + roadHalf, w - viewportX);
        }
        return remap(x, approachMin, approachMax, cx - roadHalf, cx + roadHalf);
      }

      function mapY(y) {
        if (y >= approachMax) {
          return remap(y, 200, approachMax, viewportY, cy - roadHalf);
        }
        if (y <= approachMin) {
          return remap(y, approachMin, 0, cy + roadHalf, h - viewportY);
        }
        return remap(y, approachMax, approachMin, cy - roadHalf, cy + roadHalf);
      }

      return {
        cx,
        cy,
        road,
        roadHalf,
        mapX,
        mapY,
        vehicleScale,
        viewportLeft: viewportX,
        viewportRight: w - viewportX,
        viewportTop: viewportY,
        viewportBottom: h - viewportY,
        roadLeft: cx - roadHalf,
        roadRight: cx + roadHalf,
        roadTop: cy - roadHalf,
        roadBottom: cy + roadHalf,
        junctionLeft: mapX(junctionMin),
        junctionRight: mapX(junctionMax),
        junctionTop: mapY(junctionMax),
        junctionBottom: mapY(junctionMin),
        laneDividerWestOuter: mapX(93.6),
        laneDividerWestInner: mapX(96.8),
        laneDividerCenterX: mapX(100.0),
        laneDividerEastInner: mapX(103.2),
        laneDividerEastOuter: mapX(106.4),
        laneDividerNorthOuter: mapY(106.4),
        laneDividerNorthInner: mapY(103.2),
        laneDividerCenterY: mapY(100.0),
        laneDividerSouthInner: mapY(96.8),
        laneDividerSouthOuter: mapY(93.6),
        northStopY: mapY(113.6),
        southStopY: mapY(86.4),
        westStopX: mapX(86.4),
        eastStopX: mapX(113.6),
      };
    }

    function drawRoadSurface(ctx, cx, cy, road, w, h) {
      ctx.fillStyle = "#dde5d3";
      ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = "#32363f";
      ctx.fillRect(cx - road / 2, 0, road, h);
      ctx.fillRect(0, cy - road / 2, w, road);
    }

    function drawExactRoadSurface(ctx, projection, w, h) {
      ctx.fillStyle = "#dde5d3";
      ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = "#32363f";
      ctx.fillRect(
        projection.roadLeft,
        projection.viewportTop,
        projection.road,
        projection.viewportBottom - projection.viewportTop
      );
      ctx.fillRect(
        projection.viewportLeft,
        projection.roadTop,
        projection.viewportRight - projection.viewportLeft,
        projection.road
      );
      ctx.fillRect(
        projection.junctionLeft,
        projection.junctionTop,
        projection.junctionRight - projection.junctionLeft,
        projection.junctionBottom - projection.junctionTop
      );
    }

    function drawStylizedRoadMarkings(ctx, cx, cy, w, h) {
      ctx.strokeStyle = "rgba(255,255,255,0.5)";
      ctx.lineWidth = 3;
      ctx.setLineDash([14, 12]);
      ctx.beginPath();
      ctx.moveTo(cx, 0);
      ctx.lineTo(cx, cy - 98);
      ctx.moveTo(cx, cy + 98);
      ctx.lineTo(cx, h);
      ctx.moveTo(0, cy);
      ctx.lineTo(cx - 98, cy);
      ctx.moveTo(cx + 98, cy);
      ctx.lineTo(w, cy);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.strokeStyle = "rgba(255,255,255,0.26)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      for (const offset of [28, 56]) {
        ctx.moveTo(cx - offset, 0);
        ctx.lineTo(cx - offset, cy - 100);
        ctx.moveTo(cx + offset, cy + 100);
        ctx.lineTo(cx + offset, h);
        ctx.moveTo(0, cy + offset);
        ctx.lineTo(cx - 100, cy + offset);
        ctx.moveTo(cx + 100, cy - offset);
        ctx.lineTo(w, cy - offset);
      }
      ctx.stroke();
    }

    function drawExactRoadMarkings(ctx, projection, w, h) {
      drawExactRoadSurface(ctx, projection, w, h);

      ctx.strokeStyle = "rgba(255,255,255,0.5)";
      ctx.lineWidth = 3;
      ctx.setLineDash([14, 12]);
      ctx.beginPath();
      ctx.moveTo(projection.laneDividerCenterX, projection.viewportTop);
      ctx.lineTo(projection.laneDividerCenterX, projection.northStopY);
      ctx.moveTo(projection.laneDividerCenterX, projection.southStopY);
      ctx.lineTo(projection.laneDividerCenterX, projection.viewportBottom);
      ctx.moveTo(projection.viewportLeft, projection.laneDividerCenterY);
      ctx.lineTo(projection.westStopX, projection.laneDividerCenterY);
      ctx.moveTo(projection.eastStopX, projection.laneDividerCenterY);
      ctx.lineTo(projection.viewportRight, projection.laneDividerCenterY);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.strokeStyle = "rgba(255,255,255,0.26)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      for (const x of [projection.laneDividerWestOuter, projection.laneDividerWestInner]) {
        ctx.moveTo(x, projection.viewportTop);
        ctx.lineTo(x, projection.northStopY);
      }
      for (const x of [projection.laneDividerEastInner, projection.laneDividerEastOuter]) {
        ctx.moveTo(x, projection.southStopY);
        ctx.lineTo(x, projection.viewportBottom);
      }
      for (const y of [projection.laneDividerSouthInner, projection.laneDividerSouthOuter]) {
        ctx.moveTo(projection.viewportLeft, y);
        ctx.lineTo(projection.westStopX, y);
      }
      for (const y of [projection.laneDividerNorthOuter, projection.laneDividerNorthInner]) {
        ctx.moveTo(projection.eastStopX, y);
        ctx.lineTo(projection.viewportRight, y);
      }
      ctx.stroke();
    }

    function interpolateAngle(a, b, t) {
      let delta = b - a;
      while (delta > Math.PI) delta -= Math.PI * 2;
      while (delta < -Math.PI) delta += Math.PI * 2;
      return a + delta * t;
    }

    function movementExitSide(source, turn) {
      const map = {
        north: { straight: "south", left: "east", right: "west" },
        south: { straight: "north", left: "west", right: "east" },
        west: { straight: "east", left: "north", right: "south" },
        east: { straight: "west", left: "south", right: "north" },
      };
      return (map[source] && map[source][turn]) || source;
    }

    function edgePoseForSide(side, projection, refX, refY, width, height) {
      if (side === "north") {
        return { x: refX, y: projection.viewportTop - height * 0.8 };
      }
      if (side === "south") {
        return { x: refX, y: projection.viewportBottom + height * 0.8 };
      }
      if (side === "west") {
        return { x: projection.viewportLeft - width * 0.8, y: refY };
      }
      return { x: projection.viewportRight + width * 0.8, y: refY };
    }

    function angleFromPoints(x1, y1, x2, y2, fallback) {
      const dx = x2 - x1;
      const dy = y2 - y1;
      if (Math.abs(dx) < 0.001 && Math.abs(dy) < 0.001) {
        return fallback;
      }
      return Math.atan2(dy, dx);
    }

    function buildExactCars(frame, projection, theme, nextFrame = null, blend = 0) {
      const cars = [];
      const snapshots = Array.isArray(frame.vehicle_snapshots) ? frame.vehicle_snapshots : [];
      const currentSnapshots = new Map(snapshots.map((item) => [item.id, item]));
      const nextSnapshots = new Map(
        Array.isArray(nextFrame?.vehicle_snapshots)
          ? nextFrame.vehicle_snapshots.map((item) => [item.id, item])
          : []
      );
      for (const item of snapshots) {
        const nextItem = nextSnapshots.get(item.id);
        const baseAngle = ((90 - item.angle) * Math.PI) / 180;
        const isMotorcycle = item.vehicle_type === "motorcycle";
        const width = Math.max(isMotorcycle ? 10 : 16, item.length * projection.vehicleScale * 1.02);
        const height = Math.max(isMotorcycle ? 6 : 8, item.width * projection.vehicleScale * 1.15);
        let px = projection.mapX(item.x);
        let py = projection.mapY(item.y);
        let angle = baseAngle;
        let halted = (typeof item.speed === "number" ? item.speed : 1) < 0.1;

        if (nextItem) {
          px = lerp(projection.mapX(item.x), projection.mapX(nextItem.x), blend);
          py = lerp(projection.mapY(item.y), projection.mapY(nextItem.y), blend);
          angle = interpolateAngle(baseAngle, ((90 - nextItem.angle) * Math.PI) / 180, blend);
          halted = lerp(item.speed || 0, nextItem.speed || 0, blend) < 0.1;
        } else {
          const exitSide = movementExitSide(item.source, item.turn);
          const edgePose = edgePoseForSide(exitSide, projection, px, py, width, height);
          px = lerp(px, edgePose.x, blend);
          py = lerp(py, edgePose.y, blend);
          angle = angleFromPoints(projection.mapX(item.x), projection.mapY(item.y), edgePose.x, edgePose.y, baseAngle);
          halted = false;
        }

        cars.push({
          id: item.id,
          x: px,
          y: py,
          w: width,
          h: height,
          angle,
          color: sourceColor(item.source, theme),
          roadId: item.road_id,
          halted,
          vehicleType: item.vehicle_type || "car",
        });
      }

      if (blend > 0) {
        for (const nextItem of nextSnapshots.values()) {
          if (currentSnapshots.has(nextItem.id)) {
            continue;
          }
          const isMotorcycle = nextItem.vehicle_type === "motorcycle";
          const width = Math.max(isMotorcycle ? 10 : 16, nextItem.length * projection.vehicleScale * 1.02);
          const height = Math.max(isMotorcycle ? 6 : 8, nextItem.width * projection.vehicleScale * 1.15);
          const targetX = projection.mapX(nextItem.x);
          const targetY = projection.mapY(nextItem.y);
          const edgePose = edgePoseForSide(nextItem.source, projection, targetX, targetY, width, height);
          const fallbackAngle = ((90 - nextItem.angle) * Math.PI) / 180;
          cars.push({
            id: nextItem.id,
            x: lerp(edgePose.x, targetX, blend),
            y: lerp(edgePose.y, targetY, blend),
            w: width,
            h: height,
            angle: angleFromPoints(edgePose.x, edgePose.y, targetX, targetY, fallbackAngle),
            color: sourceColor(nextItem.source, theme),
            roadId: nextItem.road_id,
            halted: false,
            vehicleType: nextItem.vehicle_type || "car",
          });
        }
      }
      return cars;
    }

    function vehicleFootprint(orientation, vehicleType) {
      const isMotorcycle = vehicleType === "motorcycle";
      if (orientation === "vertical") {
        return {
          w: isMotorcycle ? 12 : 18,
          h: isMotorcycle ? 18 : 22,
        };
      }
      return {
        w: isMotorcycle ? 18 : 22,
        h: isMotorcycle ? 12 : 18,
      };
    }

    function laneVehiclePose(laneKey, slotIndex, cx, cy, vehicleType = "car") {
      const lane = laneGeometry(laneKey, cx, cy);
      const spacing = 30;
      const size = vehicleFootprint(lane.orientation, vehicleType);
      if (lane.orientation === "vertical") {
        return {
          x: lane.x,
          y: lane.y + lane.direction * slotIndex * spacing,
          w: size.w,
          h: size.h,
        };
      }
      return {
        x: lane.x + lane.direction * slotIndex * spacing,
        y: lane.y,
        w: size.w,
        h: size.h,
      };
    }

    function laneEdgePose(laneKey, cx, cy, w, h, vehicleType = "car") {
      const lane = laneGeometry(laneKey, cx, cy);
      const basePose = laneVehiclePose(laneKey, 0, cx, cy, vehicleType);
      if (lane.orientation === "vertical") {
        return {
          x: lane.x,
          y: lane.direction < 0 ? -basePose.h : h + basePose.h,
          w: basePose.w,
          h: basePose.h,
        };
      }
      return {
        x: lane.direction < 0 ? -basePose.w : w + basePose.w,
        y: lane.y,
        w: basePose.w,
        h: basePose.h,
      };
    }

    function buildIncomingCars(laneState, index, cx, cy, w, h, theme) {
      const cars = [];
      const activeIds = new Set();
      const arrivalTravel = 8;
      const snapshot = laneState.snapshots[index] || laneState.snapshots[laneState.snapshots.length - 1];
      const positions = {};
      for (const [laneKey, ids] of Object.entries(snapshot)) {
        for (let slotIndex = 0; slotIndex < ids.length; slotIndex++) {
          positions[ids[slotIndex]] = { laneKey, slotIndex };
        }
      }

      for (const item of laneState.arrivals) {
        if (item.step < index - arrivalTravel - 1 || item.step > index) {
          continue;
        }
        const poseRef = positions[item.id];
        if (!poseRef) {
          continue;
        }
        const age = index - item.step - item.sequence * 0.18;
        if (age < 0 || age > arrivalTravel) {
          continue;
        }
        const progress = age / arrivalTravel;
        const vehicleType = item.vehicle_type || laneState.vehicleTypes[item.id] || "car";
        const startPose = laneEdgePose(poseRef.laneKey, cx, cy, w, h, vehicleType);
        const targetPose = laneVehiclePose(poseRef.laneKey, poseRef.slotIndex, cx, cy, vehicleType);
        cars.push({
          x: lerp(startPose.x, targetPose.x, progress),
          y: lerp(startPose.y, targetPose.y, progress),
          w: targetPose.w,
          h: targetPose.h,
          color: sourceColor(item.source, theme),
          vehicleType,
        });
        activeIds.add(item.id);
      }
      return { cars, activeIds };
    }

    function drawTransitCars(ctx, cars) {
      for (const car of cars) {
        const x = car.x - car.w / 2;
        const y = car.y - car.h / 2;
        drawCar(ctx, x, y, car.w, car.h, car.color, { halted: false, vehicleType: car.vehicleType });
      }
    }

    function drawExactCars(ctx, cars) {
      for (const car of cars) {
        ctx.save();
        ctx.translate(car.x, car.y);
        ctx.rotate(car.angle);
        drawCar(ctx, -car.w / 2, -car.h / 2, car.w, car.h, car.color, { halted: car.halted, vehicleType: car.vehicleType });
        ctx.restore();
      }
    }

    function drawIntersection(canvasId, frames, position, theme) {
      const canvas = document.getElementById(canvasId);
      const ctx = canvas.getContext("2d");
      const index = Math.max(0, Math.min(frames.length - 1, Math.floor(position)));
      const blend = Math.max(0, Math.min(1, position - index));
      const frame = frames[index] || frames[frames.length - 1];
      const nextFrame = frames[Math.min(index + 1, frames.length - 1)] || frame;
      const w = canvas.width;
      const h = canvas.height;
      const cx = w / 2;
      const cy = h / 2;
      const road = 184;
      const hasExactReplay = Array.isArray(frame.vehicle_snapshots);
      const useExactReplay = hasExactReplay && layerState.exact;
      const exactProjection = useExactReplay ? buildExactProjection(w, h) : null;
      const lightTimers = canvasId === "fixedCanvas" ? fixedLightTimers : aiLightTimers;
      const lightTimerFrame = lightTimers[index] || lightTimers[lightTimers.length - 1] || {};
      const nsState = signalState(frame, "NS");
      const ewState = signalState(frame, "EW");
      const queueBreakdown = approachQueueBreakdown(frame);

      ctx.clearRect(0, 0, w, h);
      ctx.save();
      applyViewTransform(ctx, canvasId);

      if (useExactReplay) {
        drawExactRoadMarkings(ctx, exactProjection, w, h);
      } else {
        drawRoadSurface(ctx, cx, cy, road, w, h);
        drawStylizedRoadMarkings(ctx, cx, cy, w, h);
      }

      drawLight(ctx, cx - 26, cy - 92, nsState);
      drawLight(ctx, cx + 26, cy + 92, nsState);
      drawLight(ctx, cx + 92, cy - 26, ewState);
      drawLight(ctx, cx - 92, cy + 26, ewState);
      drawLightCounter(ctx, cx - 26, cy - 92, queueBreakdown.north, "top");
      drawLightCounter(ctx, cx + 26, cy + 92, queueBreakdown.south, "bottom");
      drawLightCounter(ctx, cx + 92, cy - 26, queueBreakdown.east, "right");
      drawLightCounter(ctx, cx - 92, cy + 26, queueBreakdown.west, "left");
      drawRedSeconds(ctx, cx - 26, cy - 92, lightTimerFrame.north, "top", nsState);
      drawRedSeconds(ctx, cx + 26, cy + 92, lightTimerFrame.south, "bottom", nsState);
      drawRedSeconds(ctx, cx + 92, cy - 26, lightTimerFrame.east, "right", ewState);
      drawRedSeconds(ctx, cx - 92, cy + 26, lightTimerFrame.west, "left", ewState);

      if (useExactReplay) {
        if (layerState.cars) {
          drawExactCars(ctx, buildExactCars(frame, exactProjection, theme, nextFrame, blend));
        }
      } else {
        const laneState = canvasId === "fixedCanvas" ? fixedLaneState : aiLaneState;
        const transitCars = buildTransitCars(canvasId === "fixedCanvas" ? fixedSchedule : aiSchedule, index, theme);
        const incomingState = buildIncomingCars(laneState, index, cx, cy, w, h, theme);
        const laneSnapshot = laneState.snapshots[index] || laneState.snapshots[laneState.snapshots.length - 1];
        if (layerState.cars) {
          for (const laneKey of ["north_left", "north_main", "north_bike", "south_left", "south_main", "south_bike", "west_left", "west_main", "west_bike", "east_left", "east_main", "east_bike"]) {
            drawQueueLane(
              ctx,
              laneKey,
              laneSnapshot[laneKey] || [],
              laneState.vehicleTypes || {},
              incomingState.activeIds,
              cx,
              cy,
              sourceColor(laneKey.split("_")[0], theme)
            );
          }
          drawTransitCars(ctx, incomingState.cars);
          drawTransitCars(ctx, transitCars);
        }

        const timerLabel =
          frame.countdown_mode === "clear"
            ? `Clear ${frame.countdown}s`
            : frame.countdown_mode === "switch"
              ? `Swap ${frame.countdown}s`
              : `Ready ${frame.countdown}s`;
        ctx.fillStyle = "rgba(17,24,39,0.92)";
        ctx.beginPath();
        ctx.arc(cx, cy - 8, 22, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 15px Avenir Next";
        ctx.textAlign = "center";
        ctx.fillText(`${frame.countdown}`, cx, cy - 2);
        ctx.textAlign = "start";
        ctx.fillStyle = "#1f2933";
        ctx.font = "14px Avenir Next";
        ctx.fillText(timerLabel, cx - 44, cy - 124);
      }

      ctx.restore();
      drawMiniMap(canvasId, frame, position, theme, useExactReplay, nextFrame, blend);

      ctx.fillStyle = "rgba(255,250,240,0.92)";
      ctx.fillRect(16, 16, 256, 92);
      ctx.fillStyle = "#1f2933";
      ctx.font = "bold 16px Avenir Next";
      ctx.fillText(`Action: ${frame.action}`, 28, 42);
      ctx.font = "14px Avenir Next";
      if (useExactReplay) {
        ctx.fillText(`Objects: ${frame.vehicle_snapshots.length}`, 28, 66);
        ctx.fillText(`Lane 0=bike | 1=main | 2=left`, 28, 88);
      } else {
        ctx.fillText(`Switched: ${frame.switched ? "yes" : "no"}`, 28, 66);
        ctx.fillText(`Approx queue mode`, 28, 88);
      }
    }

    function drawLight(ctx, x, y, state) {
      ctx.fillStyle = "#111827";
      ctx.fillRect(x - 11, y - 22, 22, 44);
      ctx.beginPath();
      ctx.arc(x, y - 9, 6, 0, Math.PI * 2);
      ctx.fillStyle = state === "red" ? "#ef4444" : state === "yellow" ? "#facc15" : "#4b1d1d";
      ctx.fill();
      ctx.beginPath();
      ctx.arc(x, y + 9, 6, 0, Math.PI * 2);
      ctx.fillStyle = state === "green" ? "#22c55e" : "#19351f";
      ctx.fill();
    }

    function approachQueueBreakdown(frame) {
      const laneQueues = frame.lane_queues || {};
      const keys = Object.keys(laneQueues);
      if (keys.length > 0) {
        return {
          north: {
            bike: laneQueues.north_bike || 0,
            main: laneQueues.north_main || 0,
            left: laneQueues.north_left || 0,
            total: (laneQueues.north_bike || 0) + (laneQueues.north_main || 0) + (laneQueues.north_left || 0),
          },
          south: {
            bike: laneQueues.south_bike || 0,
            main: laneQueues.south_main || 0,
            left: laneQueues.south_left || 0,
            total: (laneQueues.south_bike || 0) + (laneQueues.south_main || 0) + (laneQueues.south_left || 0),
          },
          west: {
            bike: laneQueues.west_bike || 0,
            main: laneQueues.west_main || 0,
            left: laneQueues.west_left || 0,
            total: (laneQueues.west_bike || 0) + (laneQueues.west_main || 0) + (laneQueues.west_left || 0),
          },
          east: {
            bike: laneQueues.east_bike || 0,
            main: laneQueues.east_main || 0,
            left: laneQueues.east_left || 0,
            total: (laneQueues.east_bike || 0) + (laneQueues.east_main || 0) + (laneQueues.east_left || 0),
          },
        };
      }

      function splitApproach(total) {
        const left = Math.round(total * (frame.left_rate || 0));
        const remaining = Math.max(0, total - left);
        const bike = Math.round(remaining * (frame.motorcycle_rate || 0) * 0.55);
        const main = Math.max(0, remaining - bike);
        return { bike, main, left, total };
      }

      return {
        north: splitApproach(Math.ceil((frame.ns_queue || 0) / 2)),
        south: splitApproach(Math.floor((frame.ns_queue || 0) / 2)),
        west: splitApproach(Math.ceil((frame.ew_queue || 0) / 2)),
        east: splitApproach(Math.floor((frame.ew_queue || 0) / 2)),
      };
    }

    function drawLightCounter(ctx, x, y, breakdown, side) {
      if (!layerState.counters) {
        return;
      }
      const label = breakdown.total > 99 ? "99+" : `${breakdown.total}`;
      const laneLabel = `B:${breakdown.bike} M:${breakdown.main} L:${breakdown.left}`;
      ctx.save();
      ctx.font = "bold 12px Avenir Next";
      const textWidth = Math.max(ctx.measureText(label).width, ctx.measureText(laneLabel).width);
      const boxW = Math.max(54, textWidth + 14);
      const boxH = 36;
      let boxX = x - boxW / 2;
      let boxY = y - boxH / 2;

      if (side === "top") {
        boxY = y - 54;
      } else if (side === "bottom") {
        boxY = y + 20;
      } else if (side === "left") {
        boxX = x - boxW - 16;
        boxY = y - 6;
      } else {
        boxX = x + 16;
        boxY = y - 6;
      }

      ctx.fillStyle = "rgba(17,24,39,0.95)";
      roundRect(ctx, boxX, boxY, boxW, boxH, 8);
      ctx.fill();
      ctx.fillStyle = "#ffffff";
      ctx.textAlign = "center";
      ctx.textBaseline = "alphabetic";
      ctx.fillText(label, boxX + boxW / 2, boxY + 14);
      ctx.font = "10.5px Avenir Next";
      ctx.fillText(laneLabel, boxX + boxW / 2, boxY + 29);
      ctx.restore();
    }

    function drawRedSeconds(ctx, x, y, seconds, side, state) {
      if (!layerState.timers) {
        return;
      }
      if (seconds == null || seconds <= 0 || state === "green") {
        return;
      }
      const label = `${seconds}s`;
      ctx.save();
      ctx.font = "bold 11px Avenir Next";
      const textWidth = ctx.measureText(label).width;
      const boxW = Math.max(28, textWidth + 12);
      const boxH = 18;
      let boxX = x - boxW / 2;
      let boxY = y - boxH / 2;

      if (side === "top") {
        boxY = y - 17;
      } else if (side === "bottom") {
        boxY = y + 44;
      } else if (side === "left") {
        boxX = x - boxW - 16;
        boxY = y + 8;
      } else {
        boxX = x + 16;
        boxY = y + 8;
      }

      ctx.fillStyle = state === "yellow" ? "rgba(202,138,4,0.96)" : "rgba(185,28,28,0.96)";
      roundRect(ctx, boxX, boxY, boxW, boxH, 7);
      ctx.fill();
      ctx.fillStyle = "#ffffff";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(label, boxX + boxW / 2, boxY + boxH / 2 + 0.5);
      ctx.restore();
    }

    function queueRenderParams(availableLength, orientation) {
      const carLong = orientation === "vertical" ? 22 : 22;
      const carShort = orientation === "vertical" ? 18 : 18;
      const gap = 2;
      const spacing = carLong + gap;
      const maxShown = Math.max(1, Math.floor(availableLength / spacing));
      return { maxShown, spacing, carLong, carShort };
    }

    function drawQueueLane(ctx, laneKey, laneIds, laneVehicleTypes, activeIncomingIds, cx, cy, color) {
      const lane = laneGeometry(laneKey, cx, cy);
      const layout = queueRenderParams(lane.available, lane.orientation);
      let hiddenSettled = 0;

      for (let slotIndex = 0; slotIndex < laneIds.length; slotIndex++) {
        const vehicleId = laneIds[slotIndex];
        if (activeIncomingIds.has(vehicleId)) {
          continue;
        }
        if (slotIndex >= layout.maxShown) {
          hiddenSettled += 1;
          continue;
        }
        const vehicleType = laneVehicleTypes[vehicleId] || (laneKey.endsWith("_bike") ? "motorcycle" : "car");
        const pose = laneVehiclePose(laneKey, slotIndex, cx, cy, vehicleType);
        drawCar(ctx, pose.x - pose.w / 2, pose.y - pose.h / 2, pose.w, pose.h, color, { halted: true, vehicleType });
      }

      if (layerState.labels) {
        ctx.fillStyle = "#111827";
        ctx.font = "12px Avenir Next";
        if (lane.orientation === "vertical") {
          ctx.textAlign = "center";
          ctx.fillText(lane.label, lane.x, lane.y + lane.direction * 20);
          ctx.textAlign = "start";
        } else {
          ctx.fillText(lane.label, lane.x + lane.direction * 18, lane.y - 18);
        }
      }

      if (hiddenSettled > 0) {
        ctx.font = "bold 14px Avenir Next";
        const overflow = `+${hiddenSettled}`;
        if (lane.orientation === "vertical") {
          ctx.fillText(overflow, lane.x - 14, lane.y + lane.direction * (layout.maxShown + 1) * layout.spacing);
        } else {
          ctx.fillText(overflow, lane.x + lane.direction * (layout.maxShown + 1) * layout.spacing, lane.y - 16);
        }
      }
    }

    function drawCar(ctx, x, y, w, h, color, options = {}) {
      ctx.fillStyle = color;
      roundRect(ctx, x, y, w, h, Math.min(6, Math.min(w, h) / 2 - 1));
      ctx.fill();
      if (layerState.halted && options.halted) {
        ctx.strokeStyle = "rgba(255,255,255,0.92)";
        ctx.lineWidth = 2;
        roundRect(ctx, x - 1, y - 1, w + 2, h + 2, Math.min(7, Math.min(w, h) / 2));
        ctx.stroke();
      }
      ctx.fillStyle = "rgba(255,255,255,0.65)";
      if (options.vehicleType === "motorcycle") {
        if (w >= h) {
          roundRect(ctx, x + 4, y + h * 0.28, Math.max(6, w - 8), Math.max(3, h * 0.24), 3);
        } else {
          roundRect(ctx, x + w * 0.28, y + 4, Math.max(3, w * 0.24), Math.max(6, h - 8), 3);
        }
      } else if (w >= h) {
        roundRect(ctx, x + 3, y + 3, w - 6, Math.max(4, h * 0.34), 3);
      } else {
        roundRect(ctx, x + 3, y + 3, Math.max(4, w * 0.34), h - 6, 3);
      }
      ctx.fill();
    }

    function drawMiniMap(canvasId, frame, position, theme, useExactReplay, nextFrame, blend) {
      const miniCanvas = document.getElementById(canvasId === "fixedCanvas" ? "fixedMiniMap" : "aiMiniMap");
      const mainCanvas = document.getElementById(canvasId);
      const miniCtx = miniCanvas.getContext("2d");
      const mw = miniCanvas.width;
      const mh = miniCanvas.height;
      const ratioX = mw / mainCanvas.width;
      const ratioY = mh / mainCanvas.height;

      miniCtx.clearRect(0, 0, mw, mh);
      miniCtx.fillStyle = "#dce5d7";
      miniCtx.fillRect(0, 0, mw, mh);

      if (useExactReplay) {
        const projection = buildExactProjection(mainCanvas.width, mainCanvas.height);
        miniCtx.fillStyle = "#32363f";
        miniCtx.fillRect(
          projection.roadLeft * ratioX,
          projection.viewportTop * ratioY,
          projection.road * ratioX,
          (projection.viewportBottom - projection.viewportTop) * ratioY
        );
        miniCtx.fillRect(
          projection.viewportLeft * ratioX,
          projection.roadTop * ratioY,
          (projection.viewportRight - projection.viewportLeft) * ratioX,
          projection.road * ratioY
        );
        miniCtx.fillRect(
          projection.junctionLeft * ratioX,
          projection.junctionTop * ratioY,
          (projection.junctionRight - projection.junctionLeft) * ratioX,
          (projection.junctionBottom - projection.junctionTop) * ratioY
        );
        if (layerState.cars) {
          for (const car of buildExactCars(frame, projection, theme, nextFrame, blend)) {
            miniCtx.fillStyle = car.color;
            miniCtx.fillRect((car.x - 2) * ratioX, (car.y - 2) * ratioY, 4, 4);
          }
        }
      } else {
        const road = 184;
        const cx = mainCanvas.width / 2;
        const cy = mainCanvas.height / 2;
        miniCtx.fillStyle = "#32363f";
        miniCtx.fillRect((cx - road / 2) * ratioX, 0, road * ratioX, mh);
        miniCtx.fillRect(0, (cy - road / 2) * ratioY, mw, road * ratioY);
      }

      const topLeft = inverseViewPoint(canvasId, 0, 0);
      const bottomRight = inverseViewPoint(canvasId, mainCanvas.width, mainCanvas.height);
      miniCtx.strokeStyle = "rgba(255,255,255,0.95)";
      miniCtx.lineWidth = 2;
      miniCtx.strokeRect(
        topLeft.x * ratioX,
        topLeft.y * ratioY,
        (bottomRight.x - topLeft.x) * ratioX,
        (bottomRight.y - topLeft.y) * ratioY
      );
    }

    function roundRect(ctx, x, y, w, h, r) {
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.lineTo(x + w - r, y);
      ctx.quadraticCurveTo(x + w, y, x + w, y + r);
      ctx.lineTo(x + w, y + h - r);
      ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
      ctx.lineTo(x + r, y + h);
      ctx.quadraticCurveTo(x, y + h, x, y + h - r);
      ctx.lineTo(x, y + r);
      ctx.quadraticCurveTo(x, y, x + r, y);
      ctx.closePath();
    }

    function render(position) {
      current = Math.max(0, Math.min(totalFrames - 1, position));
      const index = Math.floor(current);
      const fixed = fixedFrames[index] || fixedFrames[fixedFrames.length - 1];
      const ai = aiFrames[index] || aiFrames[aiFrames.length - 1];

      drawIntersection("fixedCanvas", fixedFrames, current, "#b45309");
      drawIntersection("aiCanvas", aiFrames, current, "#0f766e");

      document.getElementById("fixedPhase").textContent = fixed.phase;
      document.getElementById("fixedQueue").textContent = fixed.total_wait;
      document.getElementById("fixedDeparted").textContent = fixed.departed;
      document.getElementById("fixedFlow").textContent = fixed.flow_rate.toFixed(1);
      document.getElementById("fixedTurnRates").textContent =
        `Turn split L ${Math.round(fixed.left_rate * 100)}% | S ${Math.round(fixed.straight_rate * 100)}% | R ${Math.round(fixed.right_rate * 100)}% | Moto ${Math.round((fixed.motorcycle_rate || 0) * 100)}%`;
      document.getElementById("aiPhase").textContent = ai.phase;
      document.getElementById("aiQueue").textContent = ai.total_wait;
      document.getElementById("aiDeparted").textContent = ai.departed;
      document.getElementById("aiFlow").textContent = ai.flow_rate.toFixed(1);
      document.getElementById("aiTurnRates").textContent =
        `Turn split L ${Math.round(ai.left_rate * 100)}% | S ${Math.round(ai.straight_rate * 100)}% | R ${Math.round(ai.right_rate * 100)}% | Moto ${Math.round((ai.motorcycle_rate || 0) * 100)}%`;

      timeline.value = index;
      stepLabel.textContent = `Step ${index + 1} / ${totalFrames}`;
    }

    function syncViewsFrom(canvasId) {
      const source = viewStates[canvasId];
      for (const otherId of Object.keys(viewStates)) {
        if (otherId === canvasId) {
          continue;
        }
        viewStates[otherId] = { ...source };
      }
      updateViewLabel();
    }

    function applyLayerStateFromInputs() {
      layerState.cars = toggleCars.checked;
      layerState.counters = toggleCounters.checked;
      layerState.timers = toggleTimers.checked;
      layerState.labels = toggleLabels.checked;
      layerState.halted = toggleHighlight.checked;
      layerState.exact = toggleExact.checked;
      render(current);
    }

    function attachCanvasInteractions(canvasId) {
      const canvas = document.getElementById(canvasId);
      canvas.addEventListener("wheel", (event) => {
        event.preventDefault();
        const delta = event.deltaY < 0 ? 0.12 : -0.12;
        setAllViewsZoom(delta);
      }, { passive: false });

      canvas.addEventListener("mousedown", (event) => {
        dragState = { canvasId, clientX: event.clientX, clientY: event.clientY };
        canvas.style.cursor = "grabbing";
      });

      canvas.addEventListener("mousemove", (event) => {
        if (!dragState || dragState.canvasId !== canvasId) {
          return;
        }
        const dx = event.clientX - dragState.clientX;
        const dy = event.clientY - dragState.clientY;
        dragState.clientX = event.clientX;
        dragState.clientY = event.clientY;
        for (const otherId of Object.keys(viewStates)) {
          viewStates[otherId].panX += dx;
          viewStates[otherId].panY += dy;
          clampView(otherId);
        }
        render(current);
      });

      const stopDrag = () => {
        if (dragState && dragState.canvasId === canvasId) {
          dragState = null;
        }
        canvas.style.cursor = "default";
      };

      canvas.addEventListener("mouseup", stopDrag);
      canvas.addEventListener("mouseleave", stopDrag);
      window.addEventListener("mouseup", stopDrag);
    }

    function stopPlayback() {
      if (timer) {
        clearInterval(timer);
        timer = null;
        playBtn.textContent = "Play";
      }
    }

    function startPlayback() {
      stopPlayback();
      playBtn.textContent = "Pause";
      timer = setInterval(() => {
        if (current >= totalFrames - 1) {
          stopPlayback();
          render(totalFrames - 1);
          return;
        }
        render(current + playbackRate / playbackSubsteps);
      }, 1000 / (baseFps * playbackSubsteps));
    }

    function setPlaybackRate(rate) {
      playbackRate = rate;
      speedLabel.textContent = `Playback ${playbackRate}x (${baseFps} fps base)`;
      speedQuarterBtn.classList.toggle("active-speed", rate === 0.25);
      speedHalfBtn.classList.toggle("active-speed", rate === 0.5);
      speedNormalBtn.classList.toggle("active-speed", rate === 1);
      speedDoubleBtn.classList.toggle("active-speed", rate === 2);
      if (timer) {
        startPlayback();
      }
    }

    playBtn.addEventListener("click", () => {
      if (timer) {
        stopPlayback();
      } else {
        startPlayback();
      }
    });

    resetBtn.addEventListener("click", () => {
      stopPlayback();
      render(0);
    });

    speedQuarterBtn.addEventListener("click", () => setPlaybackRate(0.25));
    speedHalfBtn.addEventListener("click", () => setPlaybackRate(0.5));
    speedNormalBtn.addEventListener("click", () => setPlaybackRate(1));
    speedDoubleBtn.addEventListener("click", () => setPlaybackRate(2));
    optionsToggleBtn.addEventListener("click", () => {
      const isOpen = advancedControls.classList.contains("open");
      setAdvancedControlsOpen(!isOpen);
    });
    zoomOutBtn.addEventListener("click", () => setAllViewsZoom(-0.12));
    zoomInBtn.addEventListener("click", () => setAllViewsZoom(0.12));
    resetViewBtn.addEventListener("click", () => resetAllViews());
    jumpQueueBtn.addEventListener("click", () => jumpToFrame(importantFrames.maxQueueIndex));
    jumpObjectsBtn.addEventListener("click", () => jumpToFrame(importantFrames.maxObjectsIndex));
    jumpSwitchBtn.addEventListener("click", () => {
      const nextSwitch = importantFrames.switchFrames.find((index) => index > current);
      jumpToFrame(nextSwitch ?? importantFrames.switchFrames[0] ?? current);
    });
    toggleCars.addEventListener("input", applyLayerStateFromInputs);
    toggleCounters.addEventListener("input", applyLayerStateFromInputs);
    toggleTimers.addEventListener("input", applyLayerStateFromInputs);
    toggleLabels.addEventListener("input", applyLayerStateFromInputs);
    toggleHighlight.addEventListener("input", applyLayerStateFromInputs);
    toggleExact.addEventListener("input", applyLayerStateFromInputs);

    timeline.addEventListener("input", (event) => {
      stopPlayback();
      render(Number(event.target.value));
    });

    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && advancedControls.classList.contains("open")) {
        setAdvancedControlsOpen(false);
      }
    });

    attachCanvasInteractions("fixedCanvas");
    attachCanvasInteractions("aiCanvas");

    const fixedQueue = (metrics.fixed.avg_queue ?? metrics.fixed.avg_wait).toFixed(2);
    const aiQueue = (metrics.ai.avg_queue ?? metrics.ai.avg_wait).toFixed(2);
    const fixedDelay = (metrics.fixed.avg_delay ?? 0).toFixed(2);
    const aiDelay = (metrics.ai.avg_delay ?? 0).toFixed(2);
    const improvement = metrics.fixed.avg_delay
      ? (((metrics.fixed.avg_delay - metrics.ai.avg_delay) / metrics.fixed.avg_delay) * 100).toFixed(2)
      : "0.00";
    const exactReplayAvailable =
      fixedFrames.some((frame) => Array.isArray(frame.vehicle_snapshots) && frame.vehicle_snapshots.length > 0) ||
      aiFrames.some((frame) => Array.isArray(frame.vehicle_snapshots) && frame.vehicle_snapshots.length > 0);
    document.getElementById("heroFrames").textContent = `${totalFrames}`;
    document.getElementById("heroGain").textContent = `${improvement}%`;
    document.getElementById("heroMode").textContent = exactReplayAvailable ? "SUMO" : "Approx";
    document.getElementById("heroTools").textContent = `${document.querySelectorAll('.toggle-pill').length}`;
    document.getElementById("summaryHeadline").textContent = `Average vehicle delay reduced from ${fixedDelay}s to ${aiDelay}s`;
    document.getElementById("summaryText").textContent =
      `Across the evaluation run, the AI controller changed average queue length from ${fixedQueue} to ${aiQueue} while reducing discharged-vehicle delay by ${improvement}%.`;

    setAdvancedControlsOpen(false);
    setPlaybackRate(1);
    render(0);
  </script>
</body>
</html>
"""
    return template.replace("__TRACE_JSON__", json.dumps(payload))


def export_visualization(
    env: IntersectionEnv,
    agent: QLearningAgent,
    results: dict[str, dict[str, float]],
    steps: int,
    fixed_cycle: int,
    seed: int,
    output_path: str,
) -> Path:
    fixed_frames = [frame.__dict__ for frame in collect_trace(env, steps, seed, "fixed", fixed_cycle=fixed_cycle)]
    ai_frames = [frame.__dict__ for frame in collect_trace(env, steps, seed, "ai", agent=agent, fixed_cycle=fixed_cycle)]
    payload = {
        "fixed_frames": fixed_frames,
        "ai_frames": ai_frames,
        "metrics": results,
        "seed": seed,
        "steps": steps,
    }
    html = _build_visualization_html(payload)
    path = Path(output_path)
    path.write_text(html, encoding="utf-8")
    return path


def export_summary_json(results: dict[str, dict[str, float]], output_path: str) -> Path:
    path = Path(output_path)
    fixed_queue = results["fixed"].get("avg_queue", results["fixed"]["avg_wait"])
    ai_queue = results["ai"].get("avg_queue", results["ai"]["avg_wait"])
    fixed_delay = results["fixed"].get("avg_delay", 0.0)
    ai_delay = results["ai"].get("avg_delay", 0.0)
    queue_improvement = ((fixed_queue - ai_queue) / fixed_queue * 100.0) if fixed_queue else 0.0
    delay_improvement = ((fixed_delay - ai_delay) / fixed_delay * 100.0) if fixed_delay else 0.0
    payload = {
        "fixed": results["fixed"],
        "ai": results["ai"],
        "queue_reduction_percent": queue_improvement,
        "delay_reduction_percent": delay_improvement,
        "wait_reduction_percent": delay_improvement,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def export_trace_csv(
    fixed_frames: list[TraceFrame],
    ai_frames: list[TraceFrame],
    output_path: str,
) -> Path:
    path = Path(output_path)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "step",
                "fixed_phase",
                "fixed_ns_queue",
                "fixed_ew_queue",
                "fixed_total_wait",
                "fixed_departed",
                "fixed_departed_wait_total",
                "fixed_mean_departed_wait",
                "fixed_switched",
                "ai_phase",
                "ai_ns_queue",
                "ai_ew_queue",
                "ai_total_wait",
                "ai_departed",
                "ai_departed_wait_total",
                "ai_mean_departed_wait",
                "ai_switched",
            ]
        )
        for fixed, ai in zip(fixed_frames, ai_frames):
            writer.writerow(
                [
                    fixed.step,
                    fixed.phase,
                    fixed.ns_queue,
                    fixed.ew_queue,
                    fixed.total_wait,
                    fixed.departed,
                    f"{fixed.departed_wait_total:.4f}",
                    f"{fixed.mean_departed_wait:.4f}",
                    int(fixed.switched),
                    ai.phase,
                    ai.ns_queue,
                    ai.ew_queue,
                    ai.total_wait,
                    ai.departed,
                    f"{ai.departed_wait_total:.4f}",
                    f"{ai.mean_departed_wait:.4f}",
                    int(ai.switched),
                ]
            )
    return path


def parse_emission_gases(raw_value: str) -> tuple[str, ...]:
    gases = []
    for item in raw_value.split(","):
        gas = item.strip().lower()
        if not gas:
            continue
        if gas not in EMISSION_GROUND_TRUTH:
            raise ValueError(
                f"Unsupported emission gas '{gas}'. Available gases: {', '.join(sorted(EMISSION_GROUND_TRUTH))}."
            )
        if gas not in gases:
            gases.append(gas)
    if not gases:
        raise ValueError("At least one emission gas must be provided.")
    return tuple(gases)


def _emission_feature_column(prefix: str, feature_key: str) -> str:
    return f"{prefix}_{feature_key}"


def _emission_total_column(prefix: str, gas: str) -> str:
    return f"{prefix}_total_{gas}"


def _snapshot_vehicle_bucket(snapshot: dict[str, object]) -> tuple[str, str, str]:
    vehicle_type_raw = str(snapshot.get("vehicle_type", "car"))
    vehicle_class = "motorcycle" if vehicle_type_raw == "motorcycle" else "car"
    speed = float(snapshot.get("speed", 0.0) or 0.0)
    motion_state = "stopped" if speed < HALTED_SPEED_THRESHOLD else "moving"
    feature_key = f"{vehicle_class}_{motion_state}_count"
    return vehicle_class, motion_state, feature_key


def _hidden_vehicle_detail(vehicle_id: str, vehicle_class: str) -> tuple[str, dict[str, float]]:
    rng = random.Random(f"detail::{vehicle_class}::{vehicle_id}")
    roll = rng.random()
    cumulative = 0.0
    detail_mix = HIDDEN_VEHICLE_DETAIL_MIX[vehicle_class]
    for detail_name, share, gas_multipliers in detail_mix:
        cumulative += share
        if roll <= cumulative:
            return detail_name, gas_multipliers
    detail_name, _, gas_multipliers = detail_mix[-1]
    return detail_name, gas_multipliers


def _hidden_weather_context(seed: int, controller: str, start_index: int, noise_seed: int) -> dict[str, float | str]:
    rng = random.Random(f"weather::{noise_seed}::{seed}::{controller}::{start_index}")
    base = dict(HIDDEN_WEATHER_REGIMES[int(rng.random() * len(HIDDEN_WEATHER_REGIMES))])
    base["temp_c"] = float(base["temp_c"]) + rng.gauss(0.0, 1.2)
    base["rain"] = min(1.0, max(0.0, float(base["rain"]) + rng.gauss(0.0, 0.05)))
    base["humidity"] = min(1.0, max(0.2, float(base["humidity"]) + rng.gauss(0.0, 0.04)))
    base["wind"] = min(1.0, max(0.0, float(base["wind"]) + rng.gauss(0.0, 0.03)))
    return base


def _vehicle_emission_multiplier(
    gas: str,
    snapshot: dict[str, object],
    weather: dict[str, float | str],
    previous_speed: float,
) -> float:
    vehicle_id = str(snapshot.get("id", ""))
    vehicle_class, motion_state, _ = _snapshot_vehicle_bucket(snapshot)
    _, gas_multipliers = _hidden_vehicle_detail(vehicle_id, vehicle_class)

    speed = float(snapshot.get("speed", 0.0) or 0.0)
    acceleration = speed - previous_speed
    speed_norm = min(1.8, max(0.0, speed / 13.9))
    accel_norm = max(-1.5, min(1.8, acceleration / 2.4))
    temp_c = float(weather["temp_c"])
    rain = float(weather["rain"])
    humidity = float(weather["humidity"])
    wind = float(weather["wind"])

    weather_multiplier = 1.0 + EMISSION_WEATHER_SENSITIVITY[gas] * (
        0.55 * rain + 0.22 * abs(temp_c - 28.0) / 10.0 + 0.12 * humidity + 0.06 * wind
    )

    if motion_state == "stopped":
        state_multiplier = 1.0 + 0.07 * rain + 0.03 * humidity + 0.02 * abs(temp_c - 28.0) / 10.0
    else:
        speed_multiplier = 0.84 + EMISSION_SPEED_SENSITIVITY[gas] * speed_norm + 0.12 * speed_norm * speed_norm
        accel_multiplier = 1.0 + EMISSION_ACCEL_SENSITIVITY[gas] * max(accel_norm, 0.0) + 0.08 * abs(min(accel_norm, 0.0))
        state_multiplier = speed_multiplier * accel_multiplier

    return float(gas_multipliers[gas]) * weather_multiplier * state_multiplier


def _window_ground_truth_totals(
    window_frames: list[TraceFrame],
    gas_names: tuple[str, ...],
    weather: dict[str, float | str],
) -> dict[str, float]:
    totals = {gas: 0.0 for gas in gas_names}
    previous_speed_by_vehicle: dict[str, float] = {}
    for frame in window_frames:
        snapshots = frame.vehicle_snapshots or []
        for snapshot in snapshots:
            vehicle_id = str(snapshot.get("id", ""))
            _, _, feature_key = _snapshot_vehicle_bucket(snapshot)
            previous_speed = previous_speed_by_vehicle.get(vehicle_id, float(snapshot.get("speed", 0.0) or 0.0))
            for gas in gas_names:
                base_rate = float(EMISSION_GROUND_TRUTH[gas]["rates"][feature_key])
                totals[gas] += base_rate * _vehicle_emission_multiplier(gas, snapshot, weather, previous_speed)
            previous_speed_by_vehicle[vehicle_id] = float(snapshot.get("speed", 0.0) or 0.0)
    return totals


def _empty_emission_counts() -> dict[str, int]:
    return {feature_key: 0 for feature_key in EMISSION_FEATURE_KEYS}


def _frame_emission_counts(frame: TraceFrame) -> dict[str, int]:
    snapshots = frame.vehicle_snapshots
    if snapshots is None:
        raise RuntimeError(
            "Emission fitting requires exact per-vehicle snapshots. Run with --backend sumo so the trace contains vehicle speed and type."
        )

    counts = _empty_emission_counts()
    for snapshot in snapshots:
        _, _, feature_key = _snapshot_vehicle_bucket(snapshot)
        counts[feature_key] += 1
    return counts


def _window_emission_total(feature_counts: dict[str, int], gas: str) -> float:
    rates = EMISSION_GROUND_TRUTH[gas]["rates"]
    return sum(float(feature_counts[feature_key]) * float(rates[feature_key]) for feature_key in EMISSION_FEATURE_KEYS)


def _apply_count_measurement_noise(
    feature_counts: dict[str, int],
    rng: random.Random,
    relative_std: float,
) -> dict[str, int]:
    if relative_std <= 0:
        return dict(feature_counts)

    noisy_counts = {}
    for feature_key, value in feature_counts.items():
        if value <= 0:
            noisy_counts[feature_key] = 0
            continue
        noisy_value = value * (1.0 + rng.gauss(0.0, relative_std))
        noisy_counts[feature_key] = max(0, int(round(noisy_value)))
    return noisy_counts


def _apply_total_measurement_noise(
    total_value: float,
    rng: random.Random,
    relative_std: float,
) -> float:
    if relative_std <= 0 or total_value <= 0:
        return float(total_value)
    gaussian_component = rng.gauss(0.0, relative_std)
    drift_component = rng.gauss(0.0, relative_std * 0.35)
    outlier_component = rng.gauss(0.0, relative_std * 1.2) if rng.random() < 0.08 else 0.0
    noisy_ratio = 1.0 + gaussian_component + drift_component + outlier_component
    return max(0.0, float(total_value) * noisy_ratio)


def build_emission_windows(
    frames: list[TraceFrame],
    gas_names: tuple[str, ...],
    window_size: int,
    controller: str,
    seed: int,
    count_noise_std: float = 0.0,
    target_noise_std: float = 0.0,
    noise_seed: int = 2026,
) -> list[dict[str, object]]:
    if window_size <= 0:
        raise ValueError("window_size must be positive.")
    if not frames:
        return []
    if not any(frame.vehicle_snapshots is not None for frame in frames):
        raise RuntimeError(
            "Emission fitting requires exact per-vehicle snapshots. Run with --backend sumo so the trace contains vehicle speed and type."
        )

    samples: list[dict[str, object]] = []
    for start_index in range(0, len(frames) - window_size + 1, window_size):
        window_frames = frames[start_index : start_index + window_size]
        feature_counts = _empty_emission_counts()
        for frame in window_frames:
            frame_counts = _frame_emission_counts(frame)
            for feature_key in EMISSION_FEATURE_KEYS:
                feature_counts[feature_key] += frame_counts[feature_key]

        weather = _hidden_weather_context(seed, controller, start_index, noise_seed)
        ground_truth_totals = _window_ground_truth_totals(window_frames, gas_names, weather)
        sample_rng = random.Random((noise_seed + 1) * 1_000_003 + (seed + 1) * 10_007 + start_index * 97 + (0 if controller == "fixed" else 1))
        observed_feature_counts = _apply_count_measurement_noise(feature_counts, sample_rng, count_noise_std)
        sample: dict[str, object] = {
            "controller": controller,
            "seed": seed,
            "window_size": window_size,
            "start_step": window_frames[0].step,
            "end_step": window_frames[-1].step,
            "count_noise_std": count_noise_std,
            "target_noise_std": target_noise_std,
            "hidden_weather_regime": str(weather["name"]),
            "hidden_weather_temp_c": float(weather["temp_c"]),
            "hidden_weather_rain": float(weather["rain"]),
            "hidden_weather_humidity": float(weather["humidity"]),
            "hidden_weather_wind": float(weather["wind"]),
        }
        for feature_key in EMISSION_FEATURE_KEYS:
            sample[_emission_feature_column("ground_truth", feature_key)] = feature_counts[feature_key]
            sample[_emission_feature_column("observed", feature_key)] = observed_feature_counts[feature_key]
        for gas in gas_names:
            ground_truth_total = ground_truth_totals[gas]
            observed_total = _apply_total_measurement_noise(ground_truth_total, sample_rng, target_noise_std)
            sample[_emission_total_column("ground_truth", gas)] = ground_truth_total
            sample[_emission_total_column("observed", gas)] = observed_total
            sample[f"measurement_error_{gas}"] = observed_total - ground_truth_total
        samples.append(sample)
    return samples


def collect_emission_dataset(
    env: IntersectionEnv | SumoIntersectionEnv,
    agent: QLearningAgent,
    steps: int,
    seeds: int,
    fixed_cycle: int,
    gas_names: tuple[str, ...],
    window_size: int,
    controllers: tuple[str, ...],
    count_noise_std: float,
    target_noise_std: float,
    noise_seed: int,
) -> list[dict[str, object]]:
    if seeds <= 0:
        raise ValueError("seeds must be positive.")

    samples: list[dict[str, object]] = []
    for seed in range(seeds):
        for controller in controllers:
            frames = collect_trace(
                env,
                steps,
                seed,
                controller,
                agent=agent if controller == "ai" else None,
                fixed_cycle=fixed_cycle,
            )
            samples.extend(
                build_emission_windows(
                    frames,
                    gas_names,
                    window_size,
                    controller,
                    seed,
                    count_noise_std=count_noise_std,
                    target_noise_std=target_noise_std,
                    noise_seed=noise_seed,
                )
            )
    if len(samples) < 4:
        raise RuntimeError(
            f"Need at least 4 emission windows to fit 4 hidden rates, but only collected {len(samples)} window(s)."
        )
    return samples


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(matrix)
    augmented = [row[:] + [vector[index]] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot_row = max(range(column, size), key=lambda row_index: abs(augmented[row_index][column]))
        pivot_value = augmented[pivot_row][column]
        if abs(pivot_value) < 1e-12:
            raise RuntimeError("The emission regression matrix is singular; collect more varied samples.")
        if pivot_row != column:
            augmented[column], augmented[pivot_row] = augmented[pivot_row], augmented[column]

        pivot_scale = augmented[column][column]
        for value_index in range(column, size + 1):
            augmented[column][value_index] /= pivot_scale

        for row_index in range(size):
            if row_index == column:
                continue
            factor = augmented[row_index][column]
            if abs(factor) < 1e-12:
                continue
            for value_index in range(column, size + 1):
                augmented[row_index][value_index] -= factor * augmented[column][value_index]

    return [augmented[row_index][size] for row_index in range(size)]


def fit_hidden_emission_rates(
    samples: list[dict[str, object]],
    gas: str,
    ridge_lambda: float = 1e-8,
    feature_prefix: str = "observed",
    target_prefix: str = "observed",
) -> dict[str, float]:
    matrix = [[0.0 for _ in EMISSION_FEATURE_KEYS] for _ in EMISSION_FEATURE_KEYS]
    vector = [0.0 for _ in EMISSION_FEATURE_KEYS]
    target_key = _emission_total_column(target_prefix, gas)

    for sample in samples:
        features = [float(sample[_emission_feature_column(feature_prefix, feature_key)]) for feature_key in EMISSION_FEATURE_KEYS]
        target = float(sample[target_key])
        for row_index, row_value in enumerate(features):
            vector[row_index] += row_value * target
            for column_index, column_value in enumerate(features):
                matrix[row_index][column_index] += row_value * column_value

    for diagonal_index in range(len(matrix)):
        matrix[diagonal_index][diagonal_index] += ridge_lambda

    coefficients = _solve_linear_system(matrix, vector)
    return {
        feature_key: coefficient
        for feature_key, coefficient in zip(EMISSION_FEATURE_KEYS, coefficients)
    }


def _predict_window_total(sample: dict[str, object], coefficients: dict[str, float]) -> float:
    return _predict_window_total_with_prefix(sample, coefficients, feature_prefix="observed")


def _predict_window_total_with_prefix(
    sample: dict[str, object],
    coefficients: dict[str, float],
    feature_prefix: str,
) -> float:
    return sum(
        float(sample[_emission_feature_column(feature_prefix, feature_key)]) * float(coefficients[feature_key])
        for feature_key in EMISSION_FEATURE_KEYS
    )


def _regression_metrics(
    samples: list[dict[str, object]],
    gas: str,
    coefficients: dict[str, float],
    feature_prefix: str = "observed",
    target_prefix: str = "observed",
) -> dict[str, float]:
    target_key = _emission_total_column(target_prefix, gas)
    actual_values = [float(sample[target_key]) for sample in samples]
    predicted_values = [
        _predict_window_total_with_prefix(sample, coefficients, feature_prefix=feature_prefix)
        for sample in samples
    ]
    count = len(actual_values)
    if count == 0:
        return {"mae": 0.0, "rmse": 0.0, "r2": 0.0}

    mae = sum(abs(predicted - actual) for predicted, actual in zip(predicted_values, actual_values)) / count
    rmse = (
        sum((predicted - actual) ** 2 for predicted, actual in zip(predicted_values, actual_values)) / count
    ) ** 0.5
    mean_actual = sum(actual_values) / count
    ss_tot = sum((actual - mean_actual) ** 2 for actual in actual_values)
    ss_res = sum((predicted - actual) ** 2 for predicted, actual in zip(predicted_values, actual_values))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-12 else 1.0
    return {"mae": mae, "rmse": rmse, "r2": r2}


def split_emission_samples(
    samples: list[dict[str, object]],
    test_ratio: float = 0.25,
    seed: int = 2026,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    shuffled = list(samples)
    random.Random(seed).shuffle(shuffled)
    if len(shuffled) < 2:
        raise RuntimeError("Need at least 2 emission windows to create a train/test split.")

    test_count = max(1, int(round(len(shuffled) * test_ratio)))
    test_count = min(test_count, len(shuffled) - 1)
    train_samples = shuffled[:-test_count]
    test_samples = shuffled[-test_count:]
    return train_samples, test_samples


def fit_emission_benchmark(
    samples: list[dict[str, object]],
    gas_names: tuple[str, ...],
    window_size: int,
    controllers: tuple[str, ...],
    seeds: int,
    count_noise_std: float,
    target_noise_std: float,
    noise_seed: int,
) -> dict[str, object]:
    train_samples, test_samples = split_emission_samples(samples)
    gases_report: dict[str, object] = {}

    for gas in gas_names:
        ground_truth_rates = {
            feature_key: float(EMISSION_GROUND_TRUTH[gas]["rates"][feature_key])
            for feature_key in EMISSION_FEATURE_KEYS
        }
        predicted_rates = fit_hidden_emission_rates(
            train_samples,
            gas,
            feature_prefix="observed",
            target_prefix="observed",
        )
        rate_errors = {}
        for feature_key in EMISSION_FEATURE_KEYS:
            ground_truth = ground_truth_rates[feature_key]
            predicted = predicted_rates[feature_key]
            absolute_error = abs(predicted - ground_truth)
            relative_error_percent = (absolute_error / ground_truth * 100.0) if ground_truth else 0.0
            rate_errors[feature_key] = {
                "ground_truth": ground_truth,
                "predicted": predicted,
                "absolute_error": absolute_error,
                "relative_error_percent": relative_error_percent,
            }

        gases_report[gas] = {
            "unit": str(EMISSION_GROUND_TRUTH[gas]["unit"]),
            "ground_truth_rates": ground_truth_rates,
            "predicted_rates": predicted_rates,
            "rate_errors": rate_errors,
            "train_metrics_observed": _regression_metrics(
                train_samples,
                gas,
                predicted_rates,
                feature_prefix="observed",
                target_prefix="observed",
            ),
            "test_metrics_observed": _regression_metrics(
                test_samples,
                gas,
                predicted_rates,
                feature_prefix="observed",
                target_prefix="observed",
            ),
            "train_metrics_ground_truth": _regression_metrics(
                train_samples,
                gas,
                predicted_rates,
                feature_prefix="ground_truth",
                target_prefix="ground_truth",
            ),
            "test_metrics_ground_truth": _regression_metrics(
                test_samples,
                gas,
                predicted_rates,
                feature_prefix="ground_truth",
                target_prefix="ground_truth",
            ),
        }

    return {
        "window_size": window_size,
        "samples": len(samples),
        "train_samples": len(train_samples),
        "test_samples": len(test_samples),
        "controllers": list(controllers),
        "seeds": seeds,
        "features": list(EMISSION_FEATURE_KEYS),
        "ground_truth_model": {
            "nonlinear": True,
            "hidden_variables": [
                "per-vehicle detailed subtype",
                "per-vehicle speed",
                "per-vehicle acceleration",
                "window-level weather",
            ],
            "observed_features": [
                "observed motorcycle stopped count",
                "observed motorcycle moving count",
                "observed car stopped count",
                "observed car moving count",
            ],
        },
        "measurement_noise": {
            "count_noise_std": count_noise_std,
            "target_noise_std": target_noise_std,
            "noise_seed": noise_seed,
        },
        "gases": gases_report,
    }


def export_emission_dataset_csv(
    samples: list[dict[str, object]],
    gas_names: tuple[str, ...],
    output_path: str,
) -> Path:
    path = Path(output_path)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        header = [
            "controller",
            "seed",
            "window_size",
            "start_step",
            "end_step",
            "count_noise_std",
            "target_noise_std",
            "hidden_weather_regime",
            "hidden_weather_temp_c",
            "hidden_weather_rain",
            "hidden_weather_humidity",
            "hidden_weather_wind",
            *[_emission_feature_column("ground_truth", feature_key) for feature_key in EMISSION_FEATURE_KEYS],
            *[_emission_feature_column("observed", feature_key) for feature_key in EMISSION_FEATURE_KEYS],
            *[_emission_total_column("ground_truth", gas) for gas in gas_names],
            *[_emission_total_column("observed", gas) for gas in gas_names],
            *[f"measurement_error_{gas}" for gas in gas_names],
        ]
        writer.writerow(header)
        for sample in samples:
            writer.writerow(
                [
                    sample["controller"],
                    sample["seed"],
                    sample["window_size"],
                    sample["start_step"],
                    sample["end_step"],
                    f"{float(sample['count_noise_std']):.6f}",
                    f"{float(sample['target_noise_std']):.6f}",
                    sample["hidden_weather_regime"],
                    f"{float(sample['hidden_weather_temp_c']):.6f}",
                    f"{float(sample['hidden_weather_rain']):.6f}",
                    f"{float(sample['hidden_weather_humidity']):.6f}",
                    f"{float(sample['hidden_weather_wind']):.6f}",
                    *[sample[_emission_feature_column("ground_truth", feature_key)] for feature_key in EMISSION_FEATURE_KEYS],
                    *[sample[_emission_feature_column("observed", feature_key)] for feature_key in EMISSION_FEATURE_KEYS],
                    *[f"{float(sample[_emission_total_column('ground_truth', gas)]):.6f}" for gas in gas_names],
                    *[f"{float(sample[_emission_total_column('observed', gas)]):.6f}" for gas in gas_names],
                    *[f"{float(sample[f'measurement_error_{gas}']):.6f}" for gas in gas_names],
                ]
            )
    return path


def export_emission_report_json(report: dict[str, object], output_path: str) -> Path:
    path = Path(output_path)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def print_emission_report(report: dict[str, object]) -> None:
    print("\n=== Emission Benchmark ===")
    print(f"Window size                    : {report['window_size']} frame(s)")
    print(f"Samples                        : {report['samples']} window(s)")
    print(f"Train / test                   : {report['train_samples']} / {report['test_samples']}")
    print(f"Controllers                    : {', '.join(report['controllers'])}")
    print(f"Feature vector                 : {', '.join(report['features'])}")
    hidden_model = report.get("ground_truth_model", {})
    if hidden_model:
        print(f"Nonlinear ground truth         : {'yes' if hidden_model.get('nonlinear') else 'no'}")
        print(f"Hidden variables               : {', '.join(hidden_model.get('hidden_variables', []))}")
    noise = report.get("measurement_noise", {})
    print(f"Count noise std                : {float(noise.get('count_noise_std', 0.0)):.4f}")
    print(f"Target noise std               : {float(noise.get('target_noise_std', 0.0)):.4f}")

    gases_report = report.get("gases", {})
    for gas, gas_report in gases_report.items():
        observed_test_metrics = gas_report["test_metrics_observed"]
        clean_test_metrics = gas_report["test_metrics_ground_truth"]
        print(f"\nGas                            : {gas.upper()} ({gas_report['unit']})")
        print(f"Observed test MAE              : {observed_test_metrics['mae']:.4f}")
        print(f"Observed test RMSE             : {observed_test_metrics['rmse']:.4f}")
        print(f"Observed test R^2              : {observed_test_metrics['r2']:.6f}")
        print(f"Ground-truth test MAE          : {clean_test_metrics['mae']:.4f}")
        print(f"Ground-truth test RMSE         : {clean_test_metrics['rmse']:.4f}")
        print(f"Ground-truth test R^2          : {clean_test_metrics['r2']:.6f}")
        for feature_key in EMISSION_FEATURE_KEYS:
            rate_report = gas_report["rate_errors"][feature_key]
            print(
                f"{feature_key:<30} gt={rate_report['ground_truth']:.4f} "
                f"pred={rate_report['predicted']:.4f} "
                f"abs_err={rate_report['absolute_error']:.4f} "
                f"rel_err={rate_report['relative_error_percent']:.2f}%"
            )

    co2_report = gases_report.get("co2")
    if co2_report and float(co2_report["test_metrics_ground_truth"]["r2"]) >= 0.995:
        print(
            "\nCO2 fit is strong enough to extend later to more gases. "
            "The code already supports `co` and `nox` via --emission-gases co2,co,nox."
        )


def _load_font(size: int):
    from PIL import ImageFont

    candidates = [
        "DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_rounded_rectangle(draw, box, radius, fill, outline=None, width=1) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _panel_signal_state(frame: TraceFrame, axis: str) -> str:
    if frame.countdown_mode == "clear":
        if frame.switched:
            previous_phase = "EW" if frame.phase == "NS" else "NS"
            return "yellow" if axis == previous_phase else "red"
        return "red"
    return "green" if frame.phase == axis else "red"


def _panel_source_color(source: str, fallback: str) -> str:
    return {
        "north": "#2563eb",
        "south": "#dc2626",
        "west": "#ca8a04",
        "east": "#7c3aed",
    }.get(source, fallback)


def _draw_signal_fixture(draw, px: float, py: float, state: str) -> None:
    draw.rounded_rectangle((px - 10, py - 20, px + 10, py + 20), radius=6, fill="#111827")
    top_fill = "#ef4444" if state == "red" else "#facc15" if state == "yellow" else "#7f1d1d"
    bottom_fill = "#22c55e" if state == "green" else "#19351f"
    draw.ellipse((px - 6, py - 15, px + 6, py - 3), fill=top_fill)
    draw.ellipse((px - 6, py + 2, px + 6, py + 14), fill=bottom_fill)


def _draw_panel_chrome(draw, frame: TraceFrame, panel_box: tuple[int, int, int, int], theme: str, title: str) -> None:
    x0, y0, x1, y1 = panel_box
    width = x1 - x0
    title_font = _load_font(26)
    label_font = _load_font(18)
    value_font = _load_font(30)
    small_font = _load_font(16)

    _draw_rounded_rectangle(draw, panel_box, radius=24, fill="#fffaf0", outline="#d8d2c4", width=2)
    draw.text((x0 + 24, y0 + 18), title, font=title_font, fill=theme)

    stat_y = y1 - 98
    stat_boxes = [
        (x0 + 24, stat_y, x0 + 168, y1 - 24),
        (x0 + 182, stat_y, x0 + 326, y1 - 24),
        (x0 + 340, stat_y, x0 + 484, y1 - 24),
    ]
    stat_labels = [
        ("Phase", frame.phase),
        ("Queue", str(frame.total_wait)),
        ("Departed", str(frame.departed)),
    ]
    for box, (label, value) in zip(stat_boxes, stat_labels):
        _draw_rounded_rectangle(draw, box, radius=14, fill="#ffffff", outline="#d8d2c4", width=1)
        draw.text((box[0] + 14, box[1] + 10), label, font=label_font, fill="#52606d")
        draw.text((box[0] + 14, box[1] + 36), value, font=value_font, fill="#1f2933")

    badge_box = (x0 + width - 170, y0 + 18, x0 + width - 24, y0 + 76)
    _draw_rounded_rectangle(draw, badge_box, radius=16, fill="#f7f2e8", outline="#d8d2c4", width=1)
    draw.text((badge_box[0] + 12, badge_box[1] + 10), f"Action: {frame.action}", font=small_font, fill="#1f2933")
    draw.text(
        (badge_box[0] + 12, badge_box[1] + 30),
        f"Switched: {'yes' if frame.switched else 'no'}",
        font=small_font,
        fill="#1f2933",
    )


def _draw_vertical_dashes(draw, x: float, y0: float, y1: float, dash: float, gap: float, fill: str, width: int) -> None:
    pos = y0
    while pos < y1:
        draw.line((x, pos, x, min(y1, pos + dash)), fill=fill, width=width)
        pos += dash + gap


def _draw_horizontal_dashes(draw, x0: float, x1: float, y: float, dash: float, gap: float, fill: str, width: int) -> None:
    pos = x0
    while pos < x1:
        draw.line((pos, y, min(x1, pos + dash), y), fill=fill, width=width)
        pos += dash + gap


def _build_exact_projection(panel_box: tuple[int, int, int, int]) -> dict[str, float]:
    x0, y0, x1, y1 = panel_box
    width = x1 - x0
    height = y1 - y0
    cx = x0 + width / 2.0
    cy = y0 + height / 2.0
    road = min(width, height) * 0.31
    road_half = road / 2.0
    viewport_x = x0 + max(18.0, width * 0.055)
    viewport_y = y0 + max(18.0, height * 0.055)
    approach_min = 86.4
    approach_max = 113.6
    junction_min = 86.4
    junction_max = 113.6
    approach_scale_x = max(1.0, (cx - road_half - viewport_x) / approach_min)
    approach_scale_y = max(1.0, (cy - road_half - viewport_y) / approach_min)
    vehicle_scale = math.sqrt(approach_scale_x * approach_scale_y)

    def remap(value: float, in_start: float, in_end: float, out_start: float, out_end: float) -> float:
        if abs(in_end - in_start) < 1e-6:
            return out_start
        return out_start + ((value - in_start) / (in_end - in_start)) * (out_end - out_start)

    def map_x(value: float) -> float:
        if value <= approach_min:
            return remap(value, 0.0, approach_min, viewport_x, cx - road_half)
        if value >= approach_max:
            return remap(value, approach_max, 200.0, cx + road_half, x1 - (viewport_x - x0))
        return remap(value, approach_min, approach_max, cx - road_half, cx + road_half)

    def map_y(value: float) -> float:
        if value >= approach_max:
            return remap(value, 200.0, approach_max, viewport_y, cy - road_half)
        if value <= approach_min:
            return remap(value, approach_min, 0.0, cy + road_half, y1 - (viewport_y - y0))
        return remap(value, approach_max, approach_min, cy - road_half, cy + road_half)

    viewport_right = x1 - (viewport_x - x0)
    viewport_bottom = y1 - (viewport_y - y0)
    return {
        "cx": cx,
        "cy": cy,
        "road": road,
        "road_half": road_half,
        "vehicle_scale": vehicle_scale,
        "viewport_left": viewport_x,
        "viewport_right": viewport_right,
        "viewport_top": viewport_y,
        "viewport_bottom": viewport_bottom,
        "road_left": cx - road_half,
        "road_right": cx + road_half,
        "road_top": cy - road_half,
        "road_bottom": cy + road_half,
        "junction_left": map_x(junction_min),
        "junction_right": map_x(junction_max),
        "junction_top": map_y(junction_max),
        "junction_bottom": map_y(junction_min),
        "lane_divider_west_outer": map_x(93.6),
        "lane_divider_west_inner": map_x(96.8),
        "lane_divider_center_x": map_x(100.0),
        "lane_divider_east_inner": map_x(103.2),
        "lane_divider_east_outer": map_x(106.4),
        "lane_divider_north_outer": map_y(106.4),
        "lane_divider_north_inner": map_y(103.2),
        "lane_divider_center_y": map_y(100.0),
        "lane_divider_south_inner": map_y(96.8),
        "lane_divider_south_outer": map_y(93.6),
        "north_stop_y": map_y(113.6),
        "south_stop_y": map_y(86.4),
        "west_stop_x": map_x(86.4),
        "east_stop_x": map_x(113.6),
        "map_x": map_x,
        "map_y": map_y,
    }


def _draw_exact_road_markings(draw, projection: dict[str, float]) -> None:
    draw.rectangle(
        (
            projection["viewport_left"],
            projection["viewport_top"],
            projection["viewport_right"],
            projection["viewport_bottom"],
        ),
        fill="#dde5d3",
    )
    draw.rectangle(
        (
            projection["road_left"],
            projection["viewport_top"],
            projection["road_right"],
            projection["viewport_bottom"],
        ),
        fill="#32363f",
    )
    draw.rectangle(
        (
            projection["viewport_left"],
            projection["road_top"],
            projection["viewport_right"],
            projection["road_bottom"],
        ),
        fill="#32363f",
    )
    draw.rectangle(
        (
            projection["junction_left"],
            projection["junction_top"],
            projection["junction_right"],
            projection["junction_bottom"],
        ),
        fill="#32363f",
    )

    dash_fill = (255, 255, 255, 128)
    _draw_vertical_dashes(
        draw,
        projection["lane_divider_center_x"],
        projection["viewport_top"],
        projection["north_stop_y"],
        14,
        12,
        dash_fill,
        3,
    )
    _draw_vertical_dashes(
        draw,
        projection["lane_divider_center_x"],
        projection["south_stop_y"],
        projection["viewport_bottom"],
        14,
        12,
        dash_fill,
        3,
    )
    _draw_horizontal_dashes(
        draw,
        projection["viewport_left"],
        projection["west_stop_x"],
        projection["lane_divider_center_y"],
        14,
        12,
        dash_fill,
        3,
    )
    _draw_horizontal_dashes(
        draw,
        projection["east_stop_x"],
        projection["viewport_right"],
        projection["lane_divider_center_y"],
        14,
        12,
        dash_fill,
        3,
    )

    divider_fill = (255, 255, 255, 66)
    for x in (projection["lane_divider_west_outer"], projection["lane_divider_west_inner"]):
        draw.line((x, projection["viewport_top"], x, projection["north_stop_y"]), fill=divider_fill, width=2)
    for x in (projection["lane_divider_east_inner"], projection["lane_divider_east_outer"]):
        draw.line((x, projection["south_stop_y"], x, projection["viewport_bottom"]), fill=divider_fill, width=2)
    for y in (projection["lane_divider_south_inner"], projection["lane_divider_south_outer"]):
        draw.line((projection["viewport_left"], y, projection["west_stop_x"], y), fill=divider_fill, width=2)
    for y in (projection["lane_divider_north_outer"], projection["lane_divider_north_inner"]):
        draw.line((projection["east_stop_x"], y, projection["viewport_right"], y), fill=divider_fill, width=2)


def _draw_exact_vehicle(image, px: float, py: float, width: float, height: float, angle_rad: float, color: str, halted: bool) -> None:
    from PIL import Image, ImageColor, ImageDraw

    body_w = max(8, int(round(width)))
    body_h = max(6, int(round(height)))
    padding = max(8, int(max(body_w, body_h) * 1.2))
    sprite_w = body_w + padding * 2
    sprite_h = body_h + padding * 2
    sprite = Image.new("RGBA", (sprite_w, sprite_h), (0, 0, 0, 0))
    sprite_draw = ImageDraw.Draw(sprite)
    body_box = (
        padding,
        padding,
        padding + body_w,
        padding + body_h,
    )
    body_color = ImageColor.getrgb(color)
    sprite_draw.rounded_rectangle(body_box, radius=max(3, min(body_w, body_h) // 4), fill=body_color)
    sprite_draw.rounded_rectangle(
        (body_box[0] + 2, body_box[1] + 2, body_box[2] - 2, body_box[1] + max(5, body_h // 3)),
        radius=max(2, min(body_w, body_h) // 6),
        fill=(255, 255, 255, 120),
    )
    if halted:
        sprite_draw.rectangle((body_box[0] + 2, body_box[3] - 3, body_box[2] - 2, body_box[3] - 1), fill=(255, 87, 87, 150))

    rotated = sprite.rotate(-math.degrees(angle_rad), resample=Image.Resampling.BICUBIC, expand=True)
    paste_x = int(round(px - rotated.width / 2))
    paste_y = int(round(py - rotated.height / 2))
    image.paste(rotated, (paste_x, paste_y), rotated)


def _draw_exact_intersection_panel(image, frame: TraceFrame, panel_box: tuple[int, int, int, int], theme: str, title: str) -> None:
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)
    _draw_panel_chrome(draw, frame, panel_box, theme, title)

    x0, y0, x1, y1 = panel_box
    width = x1 - x0
    height = y1 - y0
    chrome_bottom = y1 - 110
    road_box = (x0 + 24, y0 + 70, x1 - 24, chrome_bottom)
    projection = _build_exact_projection(road_box)
    _draw_exact_road_markings(draw, projection)

    cx = projection["cx"]
    cy = projection["cy"]
    road_half = projection["road_half"]
    _draw_signal_fixture(draw, cx - 26, cy - road_half, _panel_signal_state(frame, "NS"))
    _draw_signal_fixture(draw, cx + 26, cy + road_half, _panel_signal_state(frame, "NS"))
    _draw_signal_fixture(draw, cx + road_half, cy - 26, _panel_signal_state(frame, "EW"))
    _draw_signal_fixture(draw, cx - road_half, cy + 26, _panel_signal_state(frame, "EW"))

    snapshots = frame.vehicle_snapshots or []
    map_x = projection["map_x"]
    map_y = projection["map_y"]
    vehicle_scale = projection["vehicle_scale"]
    for snapshot in snapshots:
        is_motorcycle = snapshot.get("vehicle_type") == "motorcycle"
        vehicle_width = max(10 if is_motorcycle else 16, float(snapshot.get("length", 4.5)) * vehicle_scale * 1.02)
        vehicle_height = max(6 if is_motorcycle else 8, float(snapshot.get("width", 1.8)) * vehicle_scale * 1.15)
        px = map_x(float(snapshot.get("x", 0.0)))
        py = map_y(float(snapshot.get("y", 0.0)))
        angle = math.radians(90.0 - float(snapshot.get("angle", 0.0)))
        halted = float(snapshot.get("speed", 0.0) or 0.0) < 0.1
        color = _panel_source_color(str(snapshot.get("source", "")), theme)
        _draw_exact_vehicle(image, px, py, vehicle_width, vehicle_height, angle, color, halted)

    small_font = _load_font(16)
    timer_label = (
        f"Clear {frame.countdown}s"
        if frame.countdown_mode == "clear"
        else f"Swap {frame.countdown}s"
        if frame.countdown_mode == "switch"
        else f"Ready {frame.countdown}s"
    )
    draw.text((x0 + 24, chrome_bottom - 30), timer_label, font=small_font, fill="#1f2933")
    draw.text((x1 - 155, chrome_bottom - 30), f"Objects: {len(snapshots)}", font=small_font, fill="#1f2933")


def _draw_intersection_panel(draw, frame: TraceFrame, panel_box: tuple[int, int, int, int], theme: str, title: str) -> None:
    x0, y0, x1, y1 = panel_box
    width = x1 - x0
    height = y1 - y0
    cx = x0 + width // 2
    cy = y0 + height // 2 + 18
    road = 120
    title_font = _load_font(26)
    label_font = _load_font(18)
    value_font = _load_font(30)
    small_font = _load_font(16)

    _draw_panel_chrome(draw, frame, panel_box, theme, title)

    draw.rectangle((cx - road // 2, y0 + 70, cx + road // 2, y1 - 24), fill="#32363f")
    draw.rectangle((x0 + 24, cy - road // 2, x1 - 24, cy + road // 2), fill="#32363f")

    dash_color = "#cfd4db"
    for offset in range(0, 170, 24):
        draw.line((cx, y0 + 82 + offset, cx, y0 + 94 + offset), fill=dash_color, width=3)
        draw.line((x0 + 36 + offset, cy, x0 + 48 + offset, cy), fill=dash_color, width=3)
        draw.line((cx, y1 - 36 - offset, cx, y1 - 24 - offset), fill=dash_color, width=3)
        draw.line((x1 - 36 - offset, cy, x1 - 24 - offset, cy), fill=dash_color, width=3)

    _draw_signal_fixture(draw, cx - 26, cy - 92, _panel_signal_state(frame, "NS"))
    _draw_signal_fixture(draw, cx + 26, cy + 92, _panel_signal_state(frame, "NS"))
    _draw_signal_fixture(draw, cx + 92, cy - 26, _panel_signal_state(frame, "EW"))
    _draw_signal_fixture(draw, cx - 92, cy + 26, _panel_signal_state(frame, "EW"))

    def draw_car(box: tuple[int, int, int, int]) -> None:
        _draw_rounded_rectangle(draw, box, radius=6, fill=theme)
        x2, y2, x3, y3 = box
        draw.rectangle((x2 + 3, y2 + 3, x3 - 3, y2 + max(6, (y3 - y2) // 3)), fill="#ffffffaa")

    shown_ns = min(frame.ns_queue, 10)
    shown_ew = min(frame.ew_queue, 10)
    for i in range(shown_ns):
        top_y = cy - 126 - i * 24
        bottom_y = cy + 108 + i * 24
        draw_car((cx - 46, top_y, cx - 24, top_y + 18))
        draw_car((cx + 24, bottom_y, cx + 46, bottom_y + 18))
    for i in range(shown_ew):
        right_x = cx + 108 + i * 24
        left_x = cx - 126 - i * 24
        draw_car((right_x, cy - 44, right_x + 18, cy - 22))
        draw_car((left_x, cy + 22, left_x + 18, cy + 44))

    if frame.ns_queue > shown_ns:
        draw.text((cx + 56, cy + 118), f"+{frame.ns_queue - shown_ns}", font=small_font, fill="#1f2933")
    if frame.ew_queue > shown_ew:
        draw.text((cx + 116, cy + 54), f"+{frame.ew_queue - shown_ew}", font=small_font, fill="#1f2933")

def export_video(
    fixed_frames: list[TraceFrame],
    ai_frames: list[TraceFrame],
    results: dict[str, dict[str, float]],
    output_path: str,
    fps: int,
) -> Path:
    try:
        import imageio.v2 as imageio
        import numpy as np
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise RuntimeError(
            "Video export requires Pillow, imageio, and imageio-ffmpeg. "
            "Run with ./.venv-video/bin/python or install those packages."
        ) from exc

    path = Path(output_path)
    width = 1280
    height = 720
    header_font = _load_font(34)
    sub_font = _load_font(20)
    metric_font = _load_font(18)
    total_frames = max(len(fixed_frames), len(ai_frames))
    fixed_queue = results["fixed"].get("avg_queue", results["fixed"]["avg_wait"])
    ai_queue = results["ai"].get("avg_queue", results["ai"]["avg_wait"])
    fixed_delay = results["fixed"].get("avg_delay", 0.0)
    ai_delay = results["ai"].get("avg_delay", 0.0)
    improvement = ((fixed_delay - ai_delay) / fixed_delay * 100.0) if fixed_delay else 0.0

    writer = imageio.get_writer(
        str(path),
        fps=fps,
        codec="libx264",
        pixelformat="yuv420p",
        macro_block_size=1,
    )
    try:
        for index in range(total_frames):
            fixed = fixed_frames[index] if index < len(fixed_frames) else fixed_frames[-1]
            ai = ai_frames[index] if index < len(ai_frames) else ai_frames[-1]

            image = Image.new("RGB", (width, height), "#f2ede1")
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, width, height), fill="#f2ede1")

            draw.text((36, 24), "AI Traffic Light Simulation", font=header_font, fill="#1f2933")
            draw.text(
                (36, 68),
                f"Replay at {fps} fps. Fixed-time vs Q-learning on identical traffic arrivals.",
                font=sub_font,
                fill="#52606d",
            )
            draw.text(
                (36, 102),
                f"Avg queue: fixed {fixed_queue:.2f} | AI {ai_queue:.2f} | Avg delay: {fixed_delay:.2f}s -> {ai_delay:.2f}s ({improvement:.2f}%)",
                font=metric_font,
                fill="#52606d",
            )
            draw.text(
                (1088, 34),
                f"Step {index + 1}/{total_frames}",
                font=_load_font(22),
                fill="#1f2933",
            )

            fixed_panel = (36, 140, 620, 676)
            ai_panel = (660, 140, 1244, 676)
            if fixed.vehicle_snapshots:
                _draw_exact_intersection_panel(image, fixed, fixed_panel, "#b45309", "Fixed-Time Controller")
            else:
                _draw_intersection_panel(draw, fixed, fixed_panel, "#b45309", "Fixed-Time Controller")
            if ai.vehicle_snapshots:
                _draw_exact_intersection_panel(image, ai, ai_panel, "#0f766e", "Q-Learning Controller")
            else:
                _draw_intersection_panel(draw, ai, ai_panel, "#0f766e", "Q-Learning Controller")

            writer.append_data(np.asarray(image))
    finally:
        writer.close()
    return path


def run_sumo_gui_replay(
    args: argparse.Namespace,
    controller: str,
    agent: QLearningAgent | None = None,
) -> None:
    env = SumoIntersectionEnv(
        sumo_home=args.sumo_home,
        assets_dir=args.sumo_assets,
        steps=args.steps,
        connection_label="sumo_gui",
        use_gui=True,
        gui_delay_ms=args.sumo_gui_delay,
        ns_arrival_rate=args.ns_rate,
        ew_arrival_rate=args.ew_rate,
        min_green=args.min_green,
        switch_penalty_steps=args.switch_penalty,
        left_rate=args.left_rate,
        right_rate=args.right_rate,
        motorcycle_rate=args.motorcycle_rate,
    )
    try:
        state = env.reset(args.trace_seed)
        for step_index in range(args.steps):
            action = choose_action(controller, env, step_index, state, args.fixed_cycle, agent)
            state, _, _ = env.step(action)
    finally:
        close_fn = getattr(env, "_close_connection", None)
        if callable(close_fn):
            close_fn()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a minimal AI traffic light optimization demo.")
    parser.add_argument(
        "--backend",
        choices=("toy", "sumo"),
        default="sumo",
        help="Simulation backend: local SUMO intersection by default, or the lighter in-memory toy model.",
    )
    parser.add_argument("--train-episodes", type=int, default=800, help="Number of training episodes.")
    parser.add_argument("--eval-episodes", type=int, default=100, help="Number of evaluation episodes.")
    parser.add_argument("--steps", type=int, default=200, help="Simulation steps per episode.")
    parser.add_argument(
        "--fixed-cycle",
        type=int,
        default=30,
        help="Target green duration for the fixed controller before it requests a switch.",
    )
    parser.add_argument("--ns-rate", type=float, default=0.65, help="Arrival rate for north-south traffic.")
    parser.add_argument("--ew-rate", type=float, default=0.45, help="Arrival rate for east-west traffic.")
    parser.add_argument("--min-green", type=int, default=15, help="Minimum green time before switching.")
    parser.add_argument("--switch-penalty", type=int, default=2, help="All-red penalty steps after switching.")
    parser.add_argument("--left-rate", type=float, default=0.2, help="Share of departing vehicles turning left.")
    parser.add_argument("--right-rate", type=float, default=0.25, help="Share of departing vehicles turning right.")
    parser.add_argument(
        "--motorcycle-rate",
        type=float,
        default=0.35,
        help="Share of arriving vehicles that are motorcycles using the curb bike lane and the main lane.",
    )
    parser.add_argument(
        "--sumo-home",
        default="vendor/sumo-official",
        help="Path to the local SUMO distribution used when --backend sumo.",
    )
    parser.add_argument(
        "--sumo-assets",
        default="sumo_minimal",
        help="Directory for the generated minimal SUMO network and routes.",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Export an interactive HTML replay for the selected backend.",
    )
    parser.add_argument(
        "--visualize-output",
        default="traffic_ai_visualization.html",
        help="Path to the generated HTML visualization file.",
    )
    parser.add_argument(
        "--trace-seed",
        type=int,
        default=7,
        help="Seed used for the single replay trace shown in the visualization.",
    )
    parser.add_argument(
        "--sumo-visualize-controller",
        choices=("fixed", "ai"),
        default="ai",
        help="Which controller to replay in SUMO GUI when using --backend sumo --sumo-gui.",
    )
    parser.add_argument(
        "--sumo-gui-delay",
        type=int,
        default=120,
        help="Delay in milliseconds between SUMO GUI steps for visual playback.",
    )
    parser.add_argument(
        "--sumo-gui",
        action="store_true",
        help="Launch a live SUMO GUI replay in addition to any HTML export.",
    )
    parser.add_argument(
        "--export-json",
        default="",
        help="Optional path to write summary metrics as JSON.",
    )
    parser.add_argument(
        "--export-csv",
        default="",
        help="Optional path to write step-by-step traces as CSV.",
    )
    parser.add_argument(
        "--fit-emissions",
        action="store_true",
        help="Build a 10-frame vehicle-emission dataset and fit a linear ML model to recover hidden per-state emission rates.",
    )
    parser.add_argument(
        "--emission-gases",
        default="co2",
        help="Comma-separated gases to fit. Start with co2; the code can also fit co and nox.",
    )
    parser.add_argument(
        "--emissions-window",
        type=int,
        default=10,
        help="Number of frames per emission sample window.",
    )
    parser.add_argument(
        "--emissions-episodes",
        type=int,
        default=6,
        help="How many trace seeds to collect for the emission dataset.",
    )
    parser.add_argument(
        "--emissions-controllers",
        choices=("fixed", "ai", "both"),
        default="both",
        help="Which controller traces to include when fitting hidden emission rates.",
    )
    parser.add_argument(
        "--emissions-count-noise-std",
        type=float,
        default=0.03,
        help="Relative Gaussian measurement noise applied to vehicle-count features in each emission window.",
    )
    parser.add_argument(
        "--emissions-target-noise-std",
        type=float,
        default=0.05,
        help="Relative Gaussian measurement noise applied to total gas per emission window.",
    )
    parser.add_argument(
        "--emissions-noise-seed",
        type=int,
        default=2026,
        help="Seed for deterministic emission measurement noise.",
    )
    parser.add_argument(
        "--export-emissions-dataset",
        default="emissions_dataset.csv",
        help="Path for the emission dataset CSV written when --fit-emissions is enabled.",
    )
    parser.add_argument(
        "--export-emissions-report",
        default="emissions_report.json",
        help="Path for the emission benchmark JSON report written when --fit-emissions is enabled.",
    )
    parser.add_argument(
        "--export-video",
        default="",
        help="Optional path to write a silent MP4 replay of the simulation.",
    )
    parser.add_argument(
        "--video-fps",
        type=int,
        default=10,
        help="Frames per second for exported video.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    emission_gases = parse_emission_gases(args.emission_gases)
    if args.fit_emissions and args.backend != "sumo":
        raise RuntimeError(
            "Emission fitting currently requires --backend sumo because it depends on exact per-vehicle speed and type snapshots."
        )
    if args.fit_emissions and (args.emissions_count_noise_std < 0 or args.emissions_target_noise_std < 0):
        raise RuntimeError("Emission noise standard deviations must be non-negative.")

    if args.backend == "toy":
        env = IntersectionEnv(
            ns_arrival_rate=args.ns_rate,
            ew_arrival_rate=args.ew_rate,
            min_green=args.min_green,
            switch_penalty_steps=args.switch_penalty,
            left_rate=args.left_rate,
            right_rate=args.right_rate,
            motorcycle_rate=args.motorcycle_rate,
        )
    else:
        env = SumoIntersectionEnv(
            sumo_home=args.sumo_home,
            assets_dir=args.sumo_assets,
            steps=args.steps,
            ns_arrival_rate=args.ns_rate,
            ew_arrival_rate=args.ew_rate,
            min_green=args.min_green,
            switch_penalty_steps=args.switch_penalty,
            left_rate=args.left_rate,
            right_rate=args.right_rate,
            motorcycle_rate=args.motorcycle_rate,
        )

    try:
        agent = train_agent(env, episodes=args.train_episodes, steps=args.steps)
        results = evaluate(
            env,
            agent,
            episodes=args.eval_episodes,
            steps=args.steps,
            fixed_cycle=args.fixed_cycle,
        )
        print_report(results)
        if args.backend == "sumo":
            print(f"SUMO home                     : {Path(args.sumo_home).resolve()}")
            print(f"SUMO assets                   : {Path(args.sumo_assets).resolve()}")
        fixed_frames = []
        ai_frames = []
        if args.backend == "sumo" and args.export_video:
            raise RuntimeError("Video export is currently only supported for --backend toy.")
        if args.visualize or args.export_csv or args.export_video:
            fixed_frames = collect_trace(env, args.steps, args.trace_seed, "fixed", fixed_cycle=args.fixed_cycle)
            ai_frames = collect_trace(env, args.steps, args.trace_seed, "ai", agent=agent, fixed_cycle=args.fixed_cycle)
        if args.visualize:
            payload = {
                "fixed_frames": [frame.__dict__ for frame in fixed_frames],
                "ai_frames": [frame.__dict__ for frame in ai_frames],
                "metrics": results,
                "seed": args.trace_seed,
                "steps": args.steps,
            }
            html = _build_visualization_html(payload)
            html_path = Path(args.visualize_output)
            html_path.write_text(html, encoding="utf-8")
            print(f"\nVisualization written to: {html_path.resolve()}")
        if args.backend == "sumo" and args.sumo_gui:
            print(
                f"Launching SUMO GUI replay for controller '{args.sumo_visualize_controller}' "
                f"with delay {args.sumo_gui_delay} ms ..."
            )
            replay_agent = agent if args.sumo_visualize_controller == "ai" else None
            run_sumo_gui_replay(args, args.sumo_visualize_controller, replay_agent)
        if args.export_json:
            json_path = export_summary_json(results, args.export_json)
            print(f"Summary JSON written to: {json_path.resolve()}")
        if args.export_csv:
            csv_path = export_trace_csv(fixed_frames, ai_frames, args.export_csv)
            print(f"Trace CSV written to: {csv_path.resolve()}")
        if args.fit_emissions:
            emission_controllers = ("fixed", "ai") if args.emissions_controllers == "both" else (args.emissions_controllers,)
            emission_samples = collect_emission_dataset(
                env,
                agent,
                steps=args.steps,
                seeds=args.emissions_episodes,
                fixed_cycle=args.fixed_cycle,
                gas_names=emission_gases,
                window_size=args.emissions_window,
                controllers=emission_controllers,
                count_noise_std=args.emissions_count_noise_std,
                target_noise_std=args.emissions_target_noise_std,
                noise_seed=args.emissions_noise_seed,
            )
            emission_report = fit_emission_benchmark(
                emission_samples,
                emission_gases,
                window_size=args.emissions_window,
                controllers=emission_controllers,
                seeds=args.emissions_episodes,
                count_noise_std=args.emissions_count_noise_std,
                target_noise_std=args.emissions_target_noise_std,
                noise_seed=args.emissions_noise_seed,
            )
            print_emission_report(emission_report)
            if args.export_emissions_dataset:
                emission_dataset_path = export_emission_dataset_csv(
                    emission_samples,
                    emission_gases,
                    args.export_emissions_dataset,
                )
                print(f"Emission dataset written to: {emission_dataset_path.resolve()}")
            if args.export_emissions_report:
                emission_report_path = export_emission_report_json(
                    emission_report,
                    args.export_emissions_report,
                )
                print(f"Emission report written to: {emission_report_path.resolve()}")
        if args.export_video:
            video_path = export_video(fixed_frames, ai_frames, results, args.export_video, args.video_fps)
            print(f"Video written to: {video_path.resolve()}")
    finally:
        close_fn = getattr(env, "_close_connection", None)
        if callable(close_fn):
            close_fn()


if __name__ == "__main__":
    main()
