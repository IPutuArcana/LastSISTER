"""Helper akses PostgreSQL untuk Scheduler Service.

Catatan: bila DB_DSN diset "memory://", dipakai penyimpanan in-memory.
Mode ini HANYA untuk smoke-test lokal tanpa Postgres (lihat tests/).
Saat dijalankan via Docker, DB_DSN mengarah ke Postgres sungguhan.
"""
import os
import time
import threading

DB_DSN = os.getenv(
    "DB_DSN",
    "host=postgres dbname=booking user=booking password=booking port=5432",
)

_MEM = DB_DSN.startswith("memory")
_mem_slots = {}            # (service_id, slot_time) -> appointment_id
_mem_lock = threading.Lock()

if not _MEM:
    import psycopg2


def get_conn(retries=10, delay=2):
    """Koneksi ke Postgres dengan retry (Postgres mungkin belum siap saat start)."""
    last = None
    for _ in range(retries):
        try:
            return psycopg2.connect(DB_DSN)
        except Exception as e:  # noqa
            last = e
            time.sleep(delay)
    raise last


def reserve_slot(appointment_id, customer_name, service_id, slot_time):
    """Klaim slot secara atomik. Hanya boleh dipanggil oleh node LEADER.

    Mengembalikan (status, slot_id):
      - ("CONFIRMED", slot_id) jika slot berhasil diklaim.
      - ("SLOT_TAKEN", None)   jika slot sudah dipesan orang lain.

    Anti double-booking dijamin oleh UNIQUE(service_id, slot_time) +
    klausa WHERE is_booked=FALSE pada operasi atomik tunggal.
    """
    if _MEM:
        # Jalur in-memory (smoke-test lokal saja).
        key = (service_id, slot_time)
        with _mem_lock:
            if key in _mem_slots:
                return "SLOT_TAKEN", None
            _mem_slots[key] = appointment_id
            return "CONFIRMED", abs(hash(key)) % 100000

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO slots (service_id, slot_time, is_booked, booked_by)
                    VALUES (%s, %s, TRUE, %s)
                    ON CONFLICT (service_id, slot_time) DO UPDATE
                        SET is_booked = TRUE, booked_by = EXCLUDED.booked_by
                        WHERE slots.is_booked = FALSE
                    RETURNING id;
                    """,
                    (service_id, slot_time, appointment_id),
                )
                row = cur.fetchone()
                if row:
                    slot_id = row[0]
                    cur.execute(
                        "UPDATE appointments SET status='CONFIRMED' WHERE id=%s",
                        (appointment_id,),
                    )
                    return "CONFIRMED", slot_id
                else:
                    cur.execute(
                        "UPDATE appointments SET status='REJECTED' WHERE id=%s",
                        (appointment_id,),
                    )
                    return "SLOT_TAKEN", None
    finally:
        conn.close()
