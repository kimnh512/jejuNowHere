"""사용자 위치 결정: GPS/위치서비스 → IP → 수동 선택 3단계 폴백.

PC 터미널에는 GPS 칩이 없으므로:
  1) Windows 위치 서비스 (WiFi 기반 — 노트북에서 수백 m 정확도)
  2) IP 지오로케이션 (통신사 기준이라 시 단위 정확도, 오차 큼)
  3) 읍면 직접 선택
좌표가 정해지면 하버사인 거리로 최근접 읍면에 매핑합니다.
나중에 모바일 앱으로 가면 1·2번만 클라이언트 GPS로 교체하면 됩니다.
"""
import json
import math
import subprocess

import requests

JEJU = {"lat": (33.10, 34.10), "lon": (126.08, 127.05)}  # 추자·우도 포함

_PS_SCRIPT = (
    "Add-Type -AssemblyName System.Device; "
    "$w = New-Object System.Device.Location.GeoCoordinateWatcher; "
    "$w.Start(); $i = 0; "
    "while (($w.Status -ne 'Ready') -and ($i -lt 60)) { Start-Sleep -Milliseconds 100; $i++ }; "
    "$c = $w.Position.Location; $w.Stop(); "
    "if (-not $c.IsUnknown) { Write-Output ('{0},{1}' -f $c.Latitude, $c.Longitude) }"
)


def windows_location(timeout: float = 10) -> tuple[float, float] | None:
    """Windows 위치 서비스 (설정 > 개인정보 > 위치 켜져 있어야 함)."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", _PS_SCRIPT],
            capture_output=True, text=True, timeout=timeout,
        )
        line = (r.stdout or "").strip().splitlines()
        if line and "," in line[-1]:
            lat, lon = (float(x) for x in line[-1].split(","))
            return lat, lon
    except Exception:
        pass
    return None


def ip_location(timeout: float = 5) -> tuple[float, float, str] | None:
    try:
        r = requests.get("http://ip-api.com/json/?fields=status,lat,lon,city",
                         timeout=timeout)
        d = r.json()
        if d.get("status") == "success":
            return d["lat"], d["lon"], d.get("city", "?")
    except Exception:
        pass
    return None


def in_jeju(lat: float, lon: float) -> bool:
    return JEJU["lat"][0] <= lat <= JEJU["lat"][1] and JEJU["lon"][0] <= lon <= JEJU["lon"][1]


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    rad = math.radians
    dlat, dlon = rad(lat2 - lat1), rad(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(rad(lat1)) * math.cos(rad(lat2)) * math.sin(dlon / 2) ** 2)
    return 6371 * 2 * math.asin(math.sqrt(a))


def nearest_region(lat: float, lon: float, regions: list[dict]) -> tuple[dict, float]:
    best, dist = None, 1e9
    for r in regions:
        d = haversine_km(lat, lon, r["lat"], r["lon"])
        if d < dist:
            best, dist = r, d
    return best, round(dist, 1)


def pick_region(regions: list[dict]) -> dict:
    print("\n읍면을 선택하세요:")
    for i, r in enumerate(regions, 1):
        print(f"  {i:2d}. {r['name']} ({r['city']})")
    while True:
        raw = input("번호 입력 > ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(regions):
            return regions[int(raw) - 1]
        print("다시 입력해주세요.")


def resolve(regions: list[dict], region_name: str | None = None,
            lat: float | None = None, lon: float | None = None) -> tuple[dict, str]:
    """(선택된 지역, 위치 출처 설명) 반환."""
    if region_name:
        for r in regions:
            if r["name"] == region_name:
                return r, "지역 직접 지정"
        raise SystemExit(f"'{region_name}' 은 등록된 읍면이 아닙니다: "
                         + ", ".join(r["name"] for r in regions))
    if lat is not None and lon is not None:
        r, d = nearest_region(lat, lon, regions)
        return r, f"입력 좌표 기준 최근접 ({d}km)"

    loc = windows_location()
    if loc and in_jeju(*loc):
        r, d = nearest_region(*loc, regions)
        return r, f"Windows 위치서비스 ({d}km 이내)"

    ip = ip_location()
    if ip and in_jeju(ip[0], ip[1]):
        r, d = nearest_region(ip[0], ip[1], regions)
        return r, f"IP 위치 추정 — {ip[2]} 부근 (오차 큼, ±수 km)"

    if loc or ip:
        print("현재 위치가 제주도 밖으로 잡혔습니다. 지역을 직접 선택해주세요.")
    else:
        print("자동 위치 확인 실패 (Windows 위치서비스 꺼짐 + IP 조회 실패).")
    return pick_region(regions), "수동 선택"
