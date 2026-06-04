"""
Notification Worker
====================

Consumer RabbitMQ. Memproses event 'appointment_confirmed' secara
asynchronous: mensimulasikan pengiriman notifikasi (WhatsApp/email) lalu
mencatat hasilnya ke tabel notifications. Bisa di-scale ke banyak worker
(prefetch_count=1 -> distribusi pesan merata).
"""
import os
import json
import time
import random

import pika
import psycopg2

RABBIT_HOST = os.getenv("RABBIT_HOST", "rabbitmq")
NOTIF_QUEUE = os.getenv("NOTIF_QUEUE", "appointment_confirmed")
WORKER_NAME = os.getenv("WORKER_NAME", "notif-worker")
DB_DSN = os.getenv(
    "DB_DSN",
    "host=postgres dbname=booking user=booking password=booking port=5432",
)


def db_conn(retries=10, delay=2):
    last = None
    for _ in range(retries):
        try:
            return psycopg2.connect(DB_DSN)
        except Exception as e:  # noqa
            last = e
            time.sleep(delay)
    raise last


def record_notification(appt_id, channel, status, detail):
    conn = db_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO notifications
                       (appointment_id, channel, status, detail)
                       VALUES (%s, %s, %s, %s)""",
                    (appt_id, channel, status, detail),
                )
    finally:
        conn.close()


def main():
    params = pika.ConnectionParameters(
        host=RABBIT_HOST, heartbeat=30,
        connection_attempts=15, retry_delay=3,
    )
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    ch.queue_declare(queue=NOTIF_QUEUE, durable=True)
    ch.basic_qos(prefetch_count=1)

    def on_message(ch, method, properties, body):
        evt = json.loads(body.decode("utf-8"))
        appt_id = evt.get("appointment_id")
        channel = evt.get("channel", "WHATSAPP")
        print(f"[{WORKER_NAME}] terima event appointment={appt_id} "
              f"channel={channel}", flush=True)

        # Simulasi latensi & hasil pengiriman notifikasi.
        time.sleep(random.uniform(0.3, 1.0))
        ok = random.random() > 0.1   # 90% sukses
        status = "SENT" if ok else "FAILED"
        detail = (f"Halo {evt.get('customer_name')}, janji {evt.get('service_id')} "
                  f"pada {evt.get('slot_time')} dikonfirmasi.")

        try:
            record_notification(appt_id, channel, status, detail)
            print(f"[{WORKER_NAME}] notifikasi {status} -> {appt_id}", flush=True)
        except Exception as e:  # noqa
            print(f"[{WORKER_NAME}] gagal tulis DB: {e}", flush=True)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    ch.basic_consume(queue=NOTIF_QUEUE, on_message_callback=on_message)
    print(f"[{WORKER_NAME}] menunggu event di queue '{NOTIF_QUEUE}'...", flush=True)
    ch.start_consuming()


if __name__ == "__main__":
    main()
