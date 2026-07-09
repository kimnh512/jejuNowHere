"""위경도 -> 기상청 5km 격자(nx, ny) 변환.

기상청 단기예보 안내서의 Lambert Conformal Conic 변환 공식 그대로 구현.
"""
import math

RE = 6371.00877   # 지구 반경 (km)
GRID = 5.0        # 격자 간격 (km)
SLAT1 = 30.0      # 표준 위도 1
SLAT2 = 60.0      # 표준 위도 2
OLON = 126.0      # 기준점 경도
OLAT = 38.0       # 기준점 위도
XO = 43           # 기준점 X 좌표
YO = 136          # 기준점 Y 좌표


def latlon_to_grid(lat: float, lon: float) -> tuple[int, int]:
    degrad = math.pi / 180.0
    re = RE / GRID
    slat1 = SLAT1 * degrad
    slat2 = SLAT2 * degrad
    olon = OLON * degrad
    olat = OLAT * degrad

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = sf ** sn * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / (ro ** sn)

    ra = math.tan(math.pi * 0.25 + lat * degrad * 0.5)
    ra = re * sf / (ra ** sn)
    theta = lon * degrad - olon
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn

    nx = int(ra * math.sin(theta) + XO + 0.5)
    ny = int(ro - ra * math.cos(theta) + YO + 0.5)
    return nx, ny


if __name__ == "__main__":
    # 검증: 제주시(33.499, 126.531) -> 대략 (53, 38)
    print(latlon_to_grid(33.499, 126.531))
