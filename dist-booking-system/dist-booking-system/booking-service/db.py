"""Helper akses PostgreSQL untuk Booking Service."""
import os
import time
import psycopg2
import psycopg2.extras

DB_DSN = os.getenv(
    "DB_DSN",
    "host=postgres dbname=booking user=booking password=booking port=5432",
)


def get_conn(retries=10, delay=2):
    last = None
    for _ in range(retries):
        try:
            return psycopg2.connect(DB_DSN)
        except Exception as e:  # noqa
            last = e
            time.sleep(delay)
    raise last


def create_appointment(appt_id, customer_name, service_id, slot_time):
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO appointments
                       (id, customer_name, service_id, slot_time, status)
                       VALUES (%s, %s, %s, %s, 'PENDING')""",
                    (appt_id, customer_name, service_id, slot_time),
                )
    finally:
        conn.close()


def get_appointment(appt_id):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM appointments WHERE id=%s", (appt_id,))
            return cur.fetchone()
    finally:
        conn.close()


def list_appointments(limit=50):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM appointments ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            return cur.fetchall()
    finally:
        conn.close()


def list_notifications(limit=50):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM notifications ORDER BY sent_at DESC LIMIT %s",
                (limit,),
            )
            return cur.fetchall()
    finally:
        conn.close()
