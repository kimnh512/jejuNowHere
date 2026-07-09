"""locations 테이블 시드: 위경도 -> 격자 변환 + 측정소/지점코드 매핑 적재.

사용법: python seed_locations.py
"""
import config
import db
from grid_converter import latlon_to_grid

SQL = """
INSERT INTO locations (name, city, lat, lon, nx, ny, air_station, area_no)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (name) DO UPDATE SET
    city = EXCLUDED.city, lat = EXCLUDED.lat, lon = EXCLUDED.lon,
    nx = EXCLUDED.nx, ny = EXCLUDED.ny,
    air_station = EXCLUDED.air_station, area_no = EXCLUDED.area_no
"""


def main():
    rows = []
    for r in config.REGIONS:
        nx, ny = latlon_to_grid(r["lat"], r["lon"])
        rows.append((
            r["name"], r["city"], r["lat"], r["lon"], nx, ny,
            r.get("air"), config.AREA_NO[r["city"]],
        ))
        print(f"{r['name']:6s} -> nx={nx}, ny={ny}, 측정소={r.get('air')}")
    n = db.executemany(SQL, rows)
    print(f"{n}개 지역 적재 완료")


if __name__ == "__main__":
    main()
