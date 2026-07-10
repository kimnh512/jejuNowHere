"""DB 연결 및 공용 헬퍼."""
import contextlib

import psycopg2
import psycopg2.extras

import config


@contextlib.contextmanager
def get_conn():
    conn = psycopg2.connect(config.DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def executemany(sql: str, rows: list[tuple]) -> int:
    """배치 upsert. 적재한 행 수 반환."""
    if not rows:
        return 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, sql, rows, page_size=500)
    return len(rows)


def fetch_regions() -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM locations ORDER BY region_id")
            return [dict(r) for r in cur.fetchall()]


def purge_future(horizon_hours: int) -> None:
    """+horizon 이후의 예보 행 삭제 (실시간 중심 정책).

    ※ DB의 now()는 서버 시간대(클라우드는 UTC)라 KST로 저장된 예보가
      전부 지워질 수 있음 → 반드시 파이썬(수집기와 같은 TZ) 기준으로 비교.
    """
    from datetime import datetime, timedelta
    cutoff = datetime.now() + timedelta(hours=horizon_hours)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM village_forecast WHERE fcst_at > %s", (cutoff,))
            cur.execute("DELETE FROM ultra_forecast WHERE fcst_at > %s", (cutoff,))


def log_run(source: str, started_at, finished_at, status: str, rows: int, error: str | None = None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO collect_log (source, started_at, finished_at, status, rows_upserted, error)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (source, started_at, finished_at, status, rows, error),
            )
