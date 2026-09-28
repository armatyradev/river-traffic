import numpy as np
from collision import evaluate_collision_risk

RIVER_PATH = [
    [43.9650, 56.3412],
    [43.9740, 56.3392],
    [43.9810, 56.3380],
    [43.9890, 56.3366],
    [43.9980, 56.3355],
    [44.0150, 56.3348],
    [44.0320, 56.3350],
    [44.0520, 56.3340],
]

BERTH_SPOTS = [
    {"name": "Причал 1 (Речной вокзал)", "coords": [43.9895, 56.3338], "type": "berth"},
    {"name": "Причал 1 (Речной вокзал)", "coords": [43.9910, 56.3335], "type": "berth"},
    {"name": "Причал 2 (Чкаловская лестница)", "coords": [44.0090, 56.3325], "type": "berth"},
    {"name": "Причал 2 (Чкаловская лестница)", "coords": [44.0110, 56.3322], "type": "berth"},
    {"name": "Грузовой терминал Восток", "coords": [44.0380, 56.3335], "type": "berth"},
    {"name": "Грузовой терминал Восток", "coords": [44.0400, 56.3332], "type": "berth"},
    {"name": "Рейд ожидания шлюза", "coords": [44.0480, 56.3360], "type": "lock_wait"},
    {"name": "Рейд ожидания шлюза", "coords": [44.0500, 56.3365], "type": "lock_wait"},
]

def get_position_along_river(progress: float, offset_lateral: float):
    total_segments = len(RIVER_PATH) - 1
    scaled = max(0.0, min(progress, 0.999)) * total_segments
    idx = int(scaled)
    t = scaled - idx

    p1 = np.array(RIVER_PATH[idx])
    p2 = np.array(RIVER_PATH[idx + 1])

    pos = p1 + (p2 - p1) * t
    delta = p2 - p1
    length = np.linalg.norm(delta)
    perp = np.array([-delta[1] / length, delta[0] / length])

    width_multiplier = 0.65 if progress < 0.45 else 2.2
    actual_offset = offset_lateral * width_multiplier

    res = pos + perp * actual_offset
    return [round(float(res[0]), 7), round(float(res[1]), 7)]

class TrafficSimulator:
    def __init__(self):
        self.emergency_mode = False
        self.cargo_consolidated = False
        self.features = []
        self._init_fleet()

    def _init_fleet(self):
        vessels = []
        counter = 1

        for idx, spot in enumerate(BERTH_SPOTS):
            vessels.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": spot["coords"]},
                "properties": {
                    "id": f"v-{counter}",
                    "name": f"Прогулочный катер #{idx + 1}" if idx < 4 else f"Баржа-Транзит {idx}",
                    "vessel_type": "cutter" if idx < 4 else "barge",
                    "status": "У причала" if spot["type"] == "berth" else "Ожидание шлюза",
                    "speed_kmh": 0.0,
                    "base_speed_kmh": 0.0,
                    "course_deg": 90.0,
                    "has_ais": idx in [0, 4],
                    "isStatic": True,
                    "in_danger": False,
                    "tcpa": None,
                    "cpa": None,
                    "target_conflict_id": None,
                    "resolution": None
                }
            })
            counter += 1

        moving_specs = [
            {"type": "steamer", "name": "Теплоход «Волга-1»", "speed": 18, "ais": True, "dir": 1, "prog": 0.20, "lane": -1.0},
            {"type": "steamer", "name": "Теплоход «Самара»", "speed": 20, "ais": True, "dir": -1, "prog": 0.82, "lane": 1.0},
            {"type": "barge", "name": "Баржа Б-101 (песок)", "speed": 13, "ais": True, "dir": 1, "prog": 0.45, "lane": -1.2},
            {"type": "barge", "name": "Баржа Б-102 (щебень)", "speed": 12, "ais": True, "dir": -1, "prog": 0.65, "lane": 1.2},
            {"type": "cutter", "name": "Катер-такси #1", "speed": 28, "ais": False, "dir": 1, "prog": 0.28, "lane": -0.6},
            {"type": "cutter", "name": "Катер-такси #2", "speed": 30, "ais": False, "dir": -1, "prog": 0.35, "lane": 0.6},
            {"type": "cutter", "name": "Катер-такси #3", "speed": 26, "ais": False, "dir": 1, "prog": 0.70, "lane": -0.7},
            {"type": "cutter", "name": "Катер «Азимут»", "speed": 32, "ais": False, "dir": -1, "prog": 0.52, "lane": 0.8},
            {"type": "boat", "name": "Моторная лодка «Казанка»", "speed": 22, "ais": False, "dir": 1, "prog": 0.08, "lane": -0.5},
            {"type": "boat", "name": "Моторная лодка «Прогресс»", "speed": 24, "ais": False, "dir": -1, "prog": 0.90, "lane": 0.5},
            {"type": "boat", "name": "Лодка патрульная", "speed": 25, "ais": True, "dir": 1, "prog": 0.60, "lane": -0.8},
            {"type": "boat", "name": "Моторная лодка #4", "speed": 21, "ais": False, "dir": -1, "prog": 0.15, "lane": 0.7},
            {"type": "jetski", "name": "Гидроцикл Sport-1", "speed": 42, "ais": False, "dir": 1, "prog": 0.24, "lane": 1.2},
            {"type": "jetski", "name": "Гидроцикл Sport-2", "speed": 38, "ais": False, "dir": -1, "prog": 0.40, "lane": 1.5},
            {"type": "jetski", "name": "Гидроцикл Wave-X", "speed": 45, "ais": False, "dir": 1, "prog": 0.55, "lane": 1.8},
            {"type": "cutter", "name": "Катер «Стрела»", "speed": 34, "ais": False, "dir": -1, "prog": 0.74, "lane": 0.6},
            {"type": "cutter", "name": "Катер «Ветерок»", "speed": 27, "ais": False, "dir": 1, "prog": 0.38, "lane": -0.9},
            {"type": "boat", "name": "Лодка РИБ-450", "speed": 25, "ais": False, "dir": -1, "prog": 0.12, "lane": 0.9},
            {"type": "boat", "name": "Лодка «Ока»", "speed": 19, "ais": False, "dir": 1, "prog": 0.88, "lane": -0.6},
            {"type": "cutter", "name": "Катер-такси #4", "speed": 29, "ais": False, "dir": -1, "prog": 0.62, "lane": 0.5},
            {"type": "cutter", "name": "Катер «Волна»", "speed": 31, "ais": False, "dir": 1, "prog": 0.93, "lane": -1.0},
            {"type": "cutter", "name": "Катер «Бриз»", "speed": 26, "ais": False, "dir": -1, "prog": 0.48, "lane": 0.7},
        ]

        for spec in moving_specs:
            base_offset = spec["lane"] * 0.00045
            coords = get_position_along_river(spec["prog"], base_offset)
            vessels.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": coords},
                "properties": {
                    "id": f"v-{counter}",
                    "name": spec["name"],
                    "vessel_type": spec["type"],
                    "status": "На судовом ходу",
                    "speed_kmh": float(spec["speed"]),
                    "base_speed_kmh": float(spec["speed"]),
                    "course_deg": 115.0 if spec["dir"] == 1 else 295.0,
                    "has_ais": spec["ais"],
                    "isStatic": False,
                    "in_danger": False,
                    "tcpa": None,
                    "cpa": None,
                    "target_conflict_id": None,
                    "resolution": None,
                    "_progress": spec["prog"],
                    "_direction": spec["dir"],
                    "_baseOffset": base_offset,
                    "_currentOffset": base_offset
                }
            })
            counter += 1

        self.features = vessels

    def step(self):
        """Один шаг симуляции (вызывается каждую секунду)"""
        n = len(self.features)

        # 1. Движение
        for f in self.features:
            p = f["properties"]
            if p["isStatic"]:
                continue

            # Срежиссированная коллизия гидроцикла (v-21) наперерез теплоходу (v-9)
            if self.emergency_mode and p["id"] == "v-21":
                target = next((x for x in self.features if x["properties"]["id"] == "v-9"), None)
                if target:
                    p["_progress"] = target["properties"]["_progress"] + 0.004
                    p["_currentOffset"] = target["properties"]["_currentOffset"] + 0.00012
                    p["course_deg"] = 205.0
                    p["speed_kmh"] = 45.0
                    f["geometry"]["coordinates"] = get_position_along_river(p["_progress"], p["_currentOffset"])
                    continue

            step = (0.0012 + (p["speed_kmh"] / 45.0) * 0.0016) * p["_direction"]
            p["_progress"] += step

            if p["_progress"] >= 0.97:
                p["_progress"] = 0.97
                p["_direction"] = -1
                p["_baseOffset"] = abs(p["_baseOffset"])
            elif p["_progress"] <= 0.03:
                p["_progress"] = 0.03
                p["_direction"] = 1
                p["_baseOffset"] = -abs(p["_baseOffset"])

            p["_currentOffset"] += (p["_baseOffset"] - p["_currentOffset"]) * 0.15
            p["speed_kmh"] += (p["base_speed_kmh"] - p["speed_kmh"]) * 0.1
            p["in_danger"] = False
            p["tcpa"] = None
            p["cpa"] = None
            p["target_conflict_id"] = None
            p["resolution"] = None

            f["geometry"]["coordinates"] = get_position_along_river(p["_progress"], p["_currentOffset"])
            p["course_deg"] = 115.0 if p["_direction"] == 1 else 295.0

        # 2. Векторный анализ сближений (CPA/TCPA)
        for i in range(n):
            f_a = self.features[i]
            p_a = f_a["properties"]
            if p_a["isStatic"]:
                continue

            for j in range(i + 1, n):
                f_b = self.features[j]
                p_b = f_b["properties"]
                if p_b["isStatic"]:
                    continue

                danger, cpa, tcpa, res = evaluate_collision_risk(f_a, f_b)
                if danger:
                    p_a["in_danger"] = True
                    p_b["in_danger"] = True
                    p_a["target_conflict_id"] = p_b["id"]
                    p_b["target_conflict_id"] = p_a["id"]
                    p_a["cpa"] = cpa
                    p_b["cpa"] = cpa
                    p_a["tcpa"] = tcpa
                    p_b["tcpa"] = tcpa
                    p_a["resolution"] = res
                    p_b["resolution"] = res

                    # Автоматическое замедление попутного судна
                    if p_a["_direction"] == p_b["_direction"] and not self.emergency_mode:
                        if (p_a["_progress"] * p_a["_direction"]) < (p_b["_progress"] * p_b["_direction"]):
                            p_a["speed_kmh"] = max(8.0, p_b["speed_kmh"] * 0.8)
                        else:
                            p_b["speed_kmh"] = max(8.0, p_a["speed_kmh"] * 0.8)

        return {"type": "FeatureCollection", "features": self.features}