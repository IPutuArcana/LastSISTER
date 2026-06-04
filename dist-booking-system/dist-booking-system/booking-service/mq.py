"""Publisher RabbitMQ untuk Booking Service.

Mempublikasikan event 'appointment_confirmed' ke queue agar diproses
secara asynchronous oleh Notification Worker. Koneksi dibuat per-publish
agar sederhana dan tahan terhadap koneksi yang putus.
"""
import os
import json
import pika

RABBIT_HOST = os.getenv("RABBIT_HOST", "rabbitmq")
NOTIF_QUEUE = os.getenv("NOTIF_QUEUE", "appointment_confirmed")


def publish_confirmed(payload: dict):
    params = pika.ConnectionParameters(
        host=RABBIT_HOST,
        heartbeat=30,
        connection_attempts=5,
        retry_delay=3,
    )
    conn = pika.BlockingConnection(params)
    try:
        ch = conn.channel()
        ch.queue_declare(queue=NOTIF_QUEUE, durable=True)
        ch.basic_publish(
            exchange="",
            routing_key=NOTIF_QUEUE,
            body=json.dumps(payload).encode("utf-8"),
            properties=pika.BasicProperties(delivery_mode=2),  # persistent
        )
    finally:
        conn.close()
