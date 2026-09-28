import numpy as np

# Коэффициенты проекции градусов в метры для широты 56.33° (Волга, Нижний Новгород)
METERS_PER_DEG_LAT = 111320.0
METERS_PER_DEG_LON = 61800.0

def evaluate_collision_risk(vessel_a: dict, vessel_b: dict, min_cpa_meters: float = 40.0, max_tcpa_seconds: float = 60.0):
    """
    Расчет риска столкновения по стандартам ARPA/СУДС.
    Возвращает (is_danger: bool, cpa: float, tcpa: float, resolution: str)
    """
    coords_a = vessel_a["geometry"]["coordinates"]
    coords_b = vessel_b["geometry"]["coordinates"]
    prop_a = vessel_a["properties"]
    prop_b = vessel_b["properties"]

    # 1. Позиция в локальных метрах
    p_rel = np.array([
        (coords_b[0] - coords_a[0]) * METERS_PER_DEG_LON,
        (coords_b[1] - coords_a[1]) * METERS_PER_DEG_LAT
    ], dtype=np.float64)

    current_dist = float(np.linalg.norm(p_rel))

    # Если уже ближе порога экстренной зоны
    if current_dist < 40.0:
        return True, current_dist, 0.0, "ЭКСТРЕННАЯ ОСТАНОВКА: Дистанция менее 40м"

    # 2. Векторы скоростей (м/с) с учетом курса в радианах (0° = Север, 90° = Восток)
    def get_velocity_vector(speed_kmh, course_deg):
        speed_ms = speed_kmh / 3.6
        rad = np.radians(course_deg)
        # vx = sin(course), vy = cos(course)
        return np.array([speed_ms * np.sin(rad), speed_ms * np.cos(rad)], dtype=np.float64)

    v_a = get_velocity_vector(prop_a.get("speed_kmh", 0), prop_a.get("course_deg", 0))
    v_b = get_velocity_vector(prop_b.get("speed_kmh", 0), prop_b.get("course_deg", 0))
    v_rel = v_b - v_a

    v_rel_sq = float(np.dot(v_rel, v_rel))

    # Если относительная скорость нулевая (идут параллельно с равной скоростью)
    if v_rel_sq < 0.01:
        return False, current_dist, -1.0, None

    # 3. Расчет TCPA (секунды)
    tcpa = -float(np.dot(p_rel, v_rel)) / v_rel_sq

    if tcpa <= 0 or tcpa > max_tcpa_seconds:
        return False, current_dist, tcpa, None

    # 4. Расчет CPA (дистанция в метрах при t = TCPA)
    cpa_vector = p_rel + v_rel * tcpa
    cpa = float(np.linalg.norm(cpa_vector))

    if cpa < min_cpa_meters:
        # Регламентная логика по ППВП РФ
        if prop_a.get("vessel_type") == "jetski" or prop_b.get("vessel_type") == "jetski":
            resolution = "Правило 24 ППВП: Маломерное/скоростное судно уступает дорогу. Отворот вправо на 25°"
        else:
            resolution = "Правило 16 ППВП: Замедлить ход до 10 км/ч, разойтись левыми бортами"
        return True, round(cpa, 1), round(tcpa, 1), resolution

    return False, round(cpa, 1), round(tcpa, 1), None