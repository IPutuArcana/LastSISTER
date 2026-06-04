"""
Scheduler Service (gRPC server)
================================

Setiap instance adalah satu node di cluster scheduler. Tanggung jawab:
  1. Leader election Hirschberg-Sinclair (lewat modul election.py).
  2. Heartbeat dari leader + deteksi kegagalan oleh follower.
  3. RPC ReserveSlot: hanya LEADER yang boleh commit slot ke DB
     (otoritas tunggal -> anti double-booking).

Topologi ring diambil dari env ALL_NODES, urutannya = urutan posisi ring.
  Format: "host:node_id:port,host:node_id:port,..."
Neighbor CW  = node berikutnya di daftar (wrap-around).
Neighbor CCW = node sebelumnya di daftar (wrap-around).
Jika neighbor langsung mati, send_fn "berjalan" ke node hidup berikutnya
pada arah yang sama (ring mengerut otomatis -> toleransi kegagalan).
"""
import os
import time
import threading
from concurrent import futures

import grpc
import scheduler_pb2 as pb
import scheduler_pb2_grpc as pb_grpc

from election import HSElection, CW, CCW
import db

# ---- Konfigurasi node dari environment --------------------------------
NODE_ID = int(os.getenv("NODE_ID", "1"))
NODE_NAME = os.getenv("NODE_NAME", f"scheduler-{NODE_ID}")
PORT = int(os.getenv("PORT", "50051"))
ALL_NODES_RAW = os.getenv(
    "ALL_NODES",
    "scheduler-1:1:50051,scheduler-2:2:50051,scheduler-3:3:50051",
)

HEARTBEAT_INTERVAL = 2.0    # detik, leader kirim heartbeat tiap segini
HEARTBEAT_TIMEOUT = 6.0     # detik tanpa heartbeat -> anggap leader mati

# Parse ring: list of dict {id, host, port, addr}, urut sesuai posisi ring.
RING = []
for item in [x.strip() for x in ALL_NODES_RAW.split(",") if x.strip()]:
    host, sid, port = item.split(":")
    RING.append({"id": int(sid), "host": host, "port": int(port),
                 "addr": f"{host}:{port}"})

POS = next(i for i, n in enumerate(RING) if n["id"] == NODE_ID)
SELF_ADDR = f"{NODE_NAME}:{PORT}"

# ---- State global ------------------------------------------------------
state_lock = threading.RLock()
leader_id = None
leader_addr = None
is_leader = False
last_heartbeat = time.time()
_channels = {}


def log(msg):
    print(f"[{NODE_NAME} id={NODE_ID}] {msg}", flush=True)


def stub_for(addr):
    """Channel/stub gRPC ke alamat node (di-cache)."""
    if addr not in _channels:
        _channels[addr] = pb_grpc.SchedulerStub(grpc.insecure_channel(addr))
    return _channels[addr]


def neighbor_index(direction):
    return (POS + 1) % len(RING) if direction == CW else (POS - 1) % len(RING)


# ---- send_fn untuk modul election -------------------------------------
def send_election(direction, msg):
    """Kirim pesan election ke neighbor hidup pertama pada arah tertentu.

    Dijalankan di thread terpisah agar tidak memblokir handler RPC dan
    meniru pengiriman pesan asynchronous.
    """
    def worker():
        step = 1 if direction == CW else -1
        idx = POS
        # coba neighbor berurutan sampai ketemu yang hidup (ring mengerut)
        for _ in range(len(RING) - 1):
            idx = (idx + step) % len(RING)
            target = RING[idx]
            try:
                stub_for(target["addr"]).Election(
                    pb.ElectionMessage(
                        type=msg["type"],
                        initiator_id=msg.get("initiator_id", 0),
                        phase=msg.get("phase", 0),
                        hops=msg.get("hops", 0),
                        direction=msg.get("direction", direction),
                        leader_id=msg.get("leader_id", 0),
                        origin_id=msg.get("origin_id", 0),
                    ),
                    timeout=2.0,
                )
                return  # berhasil terkirim ke node hidup
            except Exception:
                continue  # node mati, lanjut ke node berikutnya pada arah ini
    threading.Thread(target=worker, daemon=True).start()


def on_leader_known(lid):
    global leader_id, leader_addr, is_leader, last_heartbeat
    addr = next((n["addr"] for n in RING if n["id"] == lid), None)
    with state_lock:
        leader_id = lid
        leader_addr = addr
        is_leader = (lid == NODE_ID)
        last_heartbeat = time.time()
    log(f"leader diketahui: id={lid} addr={addr} (saya leader={is_leader})")


hs = HSElection(NODE_ID, send_election, on_leader_known, log_fn=log)


# ---- Implementasi service gRPC ----------------------------------------
class SchedulerServicer(pb_grpc.SchedulerServicer):

    def Election(self, request, context):
        msg = {
            "type": request.type,
            "initiator_id": request.initiator_id,
            "phase": request.phase,
            "hops": request.hops,
            "direction": request.direction,
            "leader_id": request.leader_id,
            "origin_id": request.origin_id,
        }
        hs.handle(msg)
        return pb.Ack(ok=True)

    def Heartbeat(self, request, context):
        global leader_id, leader_addr, is_leader, last_heartbeat
        with state_lock:
            leader_id = request.leader_id
            leader_addr = request.leader_addr
            is_leader = (leader_id == NODE_ID)
            last_heartbeat = time.time()
        return pb.Ack(ok=True)

    def WhoIsLeader(self, request, context):
        with state_lock:
            return pb.LeaderInfo(
                leader_id=leader_id or 0,
                leader_addr=leader_addr or "",
                i_am_leader=bool(is_leader),
            )

    def ReserveSlot(self, request, context):
        with state_lock:
            local_leader = is_leader
            l_id = leader_id or 0
            l_addr = leader_addr or ""

        if not local_leader:
            # Bukan leader -> arahkan caller ke leader yang diketahui.
            return pb.ReserveResponse(
                status="NO_LEADER" if not l_addr else "NOT_LEADER",
                leader_id=l_id, leader_addr=l_addr,
                message="node ini bukan leader",
            )

        # Node ini leader -> commit slot ke DB secara atomik.
        try:
            status, slot_id = db.reserve_slot(
                request.appointment_id, request.customer_name,
                request.service_id, request.slot_time,
            )
        except Exception as e:  # noqa
            log(f"DB error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return pb.ReserveResponse(status="ERROR", message=str(e))

        log(f"[LEADER] reserve {request.service_id}@{request.slot_time} "
            f"-> {status}")
        return pb.ReserveResponse(
            status=status,
            slot_id=str(slot_id or ""),
            leader_id=NODE_ID, leader_addr=SELF_ADDR,
            message="ok",
        )


# ---- Loop latar belakang ----------------------------------------------
def heartbeat_loop():
    """Leader mengirim heartbeat ke semua follower secara periodik."""
    while True:
        time.sleep(HEARTBEAT_INTERVAL)
        with state_lock:
            if not is_leader:
                continue
        for n in RING:
            if n["id"] == NODE_ID:
                continue
            try:
                stub_for(n["addr"]).Heartbeat(
                    pb.HeartbeatMsg(leader_id=NODE_ID, leader_addr=SELF_ADDR),
                    timeout=2.0,
                )
            except Exception:
                pass


def monitor_loop():
    """Follower memantau heartbeat; jika leader mati, mulai election baru."""
    while True:
        time.sleep(1.0)
        with state_lock:
            if is_leader:
                continue
            silent = time.time() - last_heartbeat
        if silent > HEARTBEAT_TIMEOUT:
            log(f"leader sunyi {silent:.1f}s -> mulai election ulang")
            hs.start()


def bootstrap():
    """Saat start, tunggu sebentar lalu mulai election.

    Karena setiap node yang start memicu election, node ber-ID tinggi yang
    baru kembali hidup otomatis merebut kembali posisi leader.
    """
    time.sleep(3.0 + 0.3 * NODE_ID)  # beri waktu node lain & DB siap
    hs.start()


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=16))
    pb_grpc.add_SchedulerServicer_to_server(SchedulerServicer(), server)
    server.add_insecure_port(f"0.0.0.0:{PORT}")
    server.start()
    log(f"scheduler gRPC listening on :{PORT}  ring={[n['id'] for n in RING]}")

    threading.Thread(target=heartbeat_loop, daemon=True).start()
    threading.Thread(target=monitor_loop, daemon=True).start()
    threading.Thread(target=bootstrap, daemon=True).start()

    server.wait_for_termination()


if __name__ == "__main__":
    serve()
