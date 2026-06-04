"""
Booking Service (REST-API publik)
=================================

- Menyediakan REST-API untuk membuat & melihat appointment.
- Memanggil Scheduler cluster via gRPC (service-to-service RPC, stub-based).
  Pemilihan node memakai round-robin (load balancing tingkat aplikasi).
  Jika node yang dipilih bukan leader, otomatis retry ke leader.
- Saat appointment CONFIRMED, mem-publish event ke RabbitMQ untuk diproses
  Notification Worker secara asynchronous.
"""
import os
import uuid
import itertools

import grpc
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import scheduler_pb2 as pb
import scheduler_pb2_grpc as pb_grpc

import db
import mq

SCHEDULER_NODES = [x.strip() for x in os.getenv(
    "SCHEDULER_NODES",
    "scheduler-1:50051,scheduler-2:50051,scheduler-3:50051",
).split(",") if x.strip()]

INSTANCE = os.getenv("INSTANCE_NAME", "booking")

app = FastAPI(title="Appointment Booking Service")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

_rr = itertools.cycle(SCHEDULER_NODES)
_stubs = {}


def stub_for(addr):
    if addr not in _stubs:
        _stubs[addr] = pb_grpc.SchedulerStub(grpc.insecure_channel(addr))
    return _stubs[addr]


def pick_node():
    return next(_rr)


def find_leader_addr():
    """Tanya semua node siapa leader-nya (fallback bila NOT_LEADER tanpa info)."""
    for addr in SCHEDULER_NODES:
        try:
            info = stub_for(addr).WhoIsLeader(pb.Empty(), timeout=1.0)
            if info.leader_addr:
                return info.leader_addr
        except Exception:
            continue
    return None


def reserve_via_cluster(appt_id, customer_name, service_id, slot_time):
    """Reservasi slot ke cluster: round-robin lalu retry ke leader bila perlu."""
    req = pb.ReserveRequest(
        appointment_id=appt_id, customer_name=customer_name,
        service_id=service_id, slot_time=slot_time,
    )

    chosen = pick_node()
    try:
        resp = stub_for(chosen).ReserveSlot(req, timeout=3.0)
    except Exception as e:
        return {"status": "ERROR", "message": f"node {chosen} unreachable: {e}"}

    # Bila node yang dipilih bukan leader, retry ke leader.
    if resp.status in ("NOT_LEADER", "NO_LEADER"):
        leader_addr = resp.leader_addr or find_leader_addr()
        if not leader_addr:
            return {"status": "NO_LEADER",
                    "message": "leader belum terpilih, coba lagi sebentar"}
        try:
            resp = stub_for(leader_addr).ReserveSlot(req, timeout=3.0)
        except Exception as e:
            return {"status": "ERROR", "message": f"leader unreachable: {e}"}

    return {
        "status": resp.status,
        "slot_id": resp.slot_id,
        "leader_id": resp.leader_id,
        "via": f"{chosen} (served by {INSTANCE})",
    }


# ---- Schema request ----------------------------------------------------
class BookingIn(BaseModel):
    customer_name: str
    service_id: str
    slot_time: str
    channel: str = "WHATSAPP"


# ---- Endpoint REST -----------------------------------------------------
@app.get("/")
def root():
    return {"service": "booking", "instance": INSTANCE,
            "scheduler_nodes": SCHEDULER_NODES}


@app.get("/cluster/leader")
def cluster_leader():
    out = []
    for addr in SCHEDULER_NODES:
        try:
            info = stub_for(addr).WhoIsLeader(pb.Empty(), timeout=1.0)
            out.append({"addr": addr, "leader_id": info.leader_id,
                        "i_am_leader": info.i_am_leader, "alive": True})
        except Exception:
            out.append({"addr": addr, "alive": False})
    return {"nodes": out}


@app.post("/appointments")
def create_appointment(body: BookingIn):
    appt_id = str(uuid.uuid4())[:8]
    db.create_appointment(appt_id, body.customer_name, body.service_id,
                          body.slot_time)

    result = reserve_via_cluster(appt_id, body.customer_name,
                                 body.service_id, body.slot_time)

    if result["status"] == "CONFIRMED":
        # Publish event async untuk notifikasi (tidak blok response).
        try:
            mq.publish_confirmed({
                "appointment_id": appt_id,
                "customer_name": body.customer_name,
                "service_id": body.service_id,
                "slot_time": body.slot_time,
                "channel": body.channel,
            })
        except Exception as e:  # noqa
            result["notify_warning"] = f"gagal publish event: {e}"

    appt = db.get_appointment(appt_id)
    return {"appointment": appt, "reservation": result}


@app.get("/appointments")
def list_appointments():
    return {"appointments": db.list_appointments()}


@app.get("/appointments/{appt_id}")
def get_appointment(appt_id: str):
    appt = db.get_appointment(appt_id)
    if not appt:
        return {"error": "not found"}
    return appt


@app.get("/notifications")
def list_notifications():
    return {"notifications": db.list_notifications()}
