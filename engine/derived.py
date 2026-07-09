"""파생 변수 계산 — 체감온도, 해안 상대풍향(오프쇼어) 등."""
import math

from . import boundaries


def feels_like(tmp: float | None, wsd: float | None, reh: float | None) -> float | None:
    """기상청 방식 체감온도.

    겨울(10℃ 이하 + 바람): wind chill 공식.
    여름(27℃ 이상): 습구온도(Stull) 기반 여름 체감온도 공식.
    그 외: 기온 그대로.
    """
    if tmp is None:
        return None
    if tmp <= 10 and wsd is not None and wsd >= 1.3:
        v = wsd * 3.6  # m/s -> km/h
        return round(
            13.12 + 0.6215 * tmp - 11.37 * v ** 0.16 + 0.3965 * tmp * v ** 0.16, 1
        )
    if tmp >= 27 and reh is not None:
        tw = (
            tmp * math.atan(0.151977 * math.sqrt(reh + 8.313659))
            + math.atan(tmp + reh)
            - math.atan(reh - 1.676331)
            + 0.00391838 * reh ** 1.5 * math.atan(0.023101 * reh)
            - 4.686035
        )
        return round(
            -0.2442 + 0.55399 * tw + 0.45535 * tmp
            - 0.0022 * tw ** 2 + 0.00278 * tw * tmp + 3.0, 1
        )
    return round(tmp, 1)


def _ang_diff(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return d if d <= 180 else 360 - d


def offshore_state(region_name: str, vec: float | None) -> str | None:
    """서핑용 해안 상대풍향: offshore(육→해) / cross / onshore(해→육).

    vec = 바람이 불어오는 방향(기상청 풍향).
    바다를 바라보는 방위각(facing) 반대쪽에서 불어오면 오프쇼어.
    """
    facing = boundaries.COAST_FACING.get(region_name)
    if facing is None or vec is None:
        return None
    d = _ang_diff(vec, (facing + 180) % 360)
    if d <= 45:
        return "offshore"
    if d <= 100:
        return "cross"
    return "onshore"


def clothing_for(feel: float | None) -> str | None:
    if feel is None:
        return None
    for limit, text in boundaries.CLOTHING:
        if feel >= limit:
            return text
    return None


def grade(value: float | None, table: list[tuple]) -> str | None:
    if value is None:
        return None
    for limit, name in table:
        if value <= limit:
            return name
    return None
