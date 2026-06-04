"""
Integration test: menjalankan 3 node scheduler SUNGGUHAN (server.py) sebagai
proses terpisah di localhost, lalu memverifikasi:
  1. Election via gRPC -> semua node sepakat leader = ID tertinggi (3).
  2. ReserveSlot ke leader -> CONFIRMED, dan duplikat -> SLOT_TAKEN.
  3. Failover: leader dimatikan -> node tersisa memilih leader baru (2).

Pakai DB in-memory (DB_DSN=memory://) jadi TIDAK butuh Postgres/Docker.
Jalankan: python3 tests/test_grpc_election.py
"""
import os
import sys
import time
import subprocess
import signal

import grpc

HERE = os.path.dirname(__file__)
SVC = os.path.join(HERE, "..", "scheduler-service")
sys.path.insert(0, SVC)
import scheduler_pb2 as pb          # noqa
import scheduler_pb2_grpc as pbg    # noqa

RING = "127.0.0.1:1:50051,127.0.0.1:2:50052,127.0.0.1:3:50053"
PORTS = {1: 50051, 2: 50052, 3: 50053}
procs = {}


def start_node(nid):
    env = dict(os.environ)
    env.update({
        "NODE_ID": str(nid),
        "NODE_NAME": "127.0.0.1",
        "PORT": str(PORTS[nid]),
        "ALL_NODES": RING,
        "DB_DSN": "memory://",
        "PYTHONUNBUFFERED": "1",
    })
    log = open(os.path.join(HERE, f"node{nid}.log"), "w")
    p = subprocess.Popen([sys.executable, "server.py"], cwd=SVC, env=env,
                         stdout=log, stderr=subprocess.STDOUT)
    procs[nid] = p


def stub(nid):
    return pbg.SchedulerStub(grpc.insecure_channel(f"127.0.0.1:{PORTS[nid]}"))


def who_is_leader(nid):
    try:
        info = stub(nid).WhoIsLeader(pb.Empty(), timeout=1.0)
        return info.leader_id, info.i_am_leader
    except Exception as e:
        return None, f"down ({e.__class__.__name__})"


def cleanup():
    for p in procs.values():
        try:
            p.send_signal(signal.SIGTERM)
        except Exception:
            pass
    time.sleep(0.5)
    for p in procs.values():
        try:
            p.kill()
        except Exception:
            pass


def main():
    print("=== Integration test: HS election via gRPC (3 node nyata) ===\n")
    for nid in (1, 2, 3):
        start_node(nid)
    print("3 node dijalankan, menunggu election...")
    time.sleep(8)

    print("\n[1] Cek kesepakatan leader:")
    leaders = {}
    for nid in (1, 2, 3):
        lid, mine = who_is_leader(nid)
        leaders[nid] = lid
        print(f"    node{nid} bilang leader = {lid} (i_am_leader={mine})")
    assert all(v == 3 for v in leaders.values()), f"tidak sepakat: {leaders}"
    print("    OK semua sepakat leader = 3 (ID tertinggi)")

    print("\n[2] ReserveSlot via leader:")
    req = pb.ReserveRequest(appointment_id="appt-A", customer_name="Budi",
                            service_id="gigi", slot_time="2026-06-10T09:00")
    r1 = stub(3).ReserveSlot(req, timeout=3.0)
    print(f"    booking pertama  -> {r1.status}")
    assert r1.status == "CONFIRMED"
    req2 = pb.ReserveRequest(appointment_id="appt-B", customer_name="Sari",
                             service_id="gigi", slot_time="2026-06-10T09:00")
    r2 = stub(3).ReserveSlot(req2, timeout=3.0)
    print(f"    booking duplikat -> {r2.status}")
    assert r2.status == "SLOT_TAKEN"
    print("    OK anti double-booking jalan")

    print("\n[3] Cek follower menolak commit (NOT_LEADER):")
    r3 = stub(1).ReserveSlot(req, timeout=3.0)
    print(f"    reserve ke node1 (follower) -> {r3.status}, "
          f"diarahkan ke leader_id={r3.leader_id}")
    assert r3.status == "NOT_LEADER"
    print("    OK follower mengarahkan ke leader")

    print("\n[4] FAILOVER: matikan leader (node3)...")
    procs[3].send_signal(signal.SIGTERM)
    procs[3].wait(timeout=5)
    del procs[3]
    print("    node3 mati, menunggu deteksi + election ulang...")
    time.sleep(12)

    new_leaders = {}
    for nid in (1, 2):
        lid, mine = who_is_leader(nid)
        new_leaders[nid] = lid
        print(f"    node{nid} bilang leader = {lid} (i_am_leader={mine})")
    assert all(v == 2 for v in new_leaders.values()), \
        f"failover gagal: {new_leaders}"
    print("    OK leader baru = 2 (tertinggi di antara node hidup)")

    print("\n[5] Booking masih jalan via leader baru:")
    req4 = pb.ReserveRequest(appointment_id="appt-C", customer_name="Joni",
                             service_id="umum", slot_time="2026-06-11T08:00")
    r5 = stub(2).ReserveSlot(req4, timeout=3.0)
    print(f"    booking via leader baru -> {r5.status}")
    assert r5.status == "CONFIRMED"

    print("\nSEMUA INTEGRATION TEST LULUS.")


if __name__ == "__main__":
    try:
        main()
    finally:
        cleanup()
