"""
Simulasi in-memory untuk memvalidasi algoritma Hirschberg-Sinclair.
Tidak butuh jaringan/Docker. Membuktikan node ber-ID tertinggi terpilih
sebagai leader pada berbagai ukuran & urutan ring.
"""
import sys, os, collections, itertools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scheduler-service"))

from election import HSElection, CW, CCW  # noqa


class RingSimulator:
    def __init__(self, node_ids):
        # urutan posisi di ring = urutan list (BUKAN urutan id)
        self.ring = list(node_ids)
        self.n = len(self.ring)
        self.pos = {nid: i for i, nid in enumerate(self.ring)}
        self.queue = collections.deque()       # (target_node_id, msg)
        self.nodes = {}
        self.leaders = {}                       # node_id -> leader yang dia kenal

        for nid in self.ring:
            node = HSElection(
                node_id=nid,
                send_fn=self._make_send(nid),
                on_leader=self._make_on_leader(nid),
                log_fn=lambda m: None,          # senyap saat test
            )
            self.nodes[nid] = node

    def _neighbor(self, nid, direction):
        i = self.pos[nid]
        j = (i + 1) % self.n if direction == CW else (i - 1) % self.n
        return self.ring[j]

    def _make_send(self, nid):
        def send(direction, msg):
            target = self._neighbor(nid, direction)
            self.queue.append((target, msg))
        return send

    def _make_on_leader(self, nid):
        def on_leader(leader_id):
            self.leaders[nid] = leader_id
        return on_leader

    def run(self, starters=None):
        starters = starters or self.ring
        for nid in starters:
            self.nodes[nid].start()
        steps = 0
        while self.queue:
            target, msg = self.queue.popleft()
            self.nodes[target].handle(msg)
            steps += 1
            if steps > 100000:
                raise RuntimeError("tidak konvergen (kemungkinan loop)")
        return steps


def check(node_ids, ring_order):
    sim = RingSimulator(ring_order)
    steps = sim.run()
    expected = max(node_ids)
    # semua node harus sepakat leader = id tertinggi
    agreed = all(sim.leaders.get(nid) == expected for nid in ring_order)
    elected = sim.nodes[expected].is_leader
    ok = agreed and elected
    print(f"ring={str(ring_order):<28} leader_terpilih={expected} "
          f"sepakat={agreed} steps={steps} -> {'OK' if ok else 'GAGAL'}")
    assert ok, f"GAGAL untuk ring {ring_order}: {sim.leaders}"
    return ok


if __name__ == "__main__":
    print("=== Uji Hirschberg-Sinclair ===\n")

    # 1) Kasus utama project: 3 node, semua urutan ring
    print("[3 node] semua permutasi urutan ring:")
    for perm in itertools.permutations([1, 2, 3]):
        check([1, 2, 3], list(perm))

    # 2) ID tidak berurutan
    print("\n[ID acak]:")
    check([5, 2, 9], [5, 2, 9])
    check([10, 40, 20, 30], [10, 40, 20, 30])

    # 3) Ukuran ring lebih besar (uji skalabilitas O(n log n))
    print("\n[ring besar]:")
    check(list(range(1, 6)), [3, 1, 5, 2, 4])
    check(list(range(1, 9)), [7, 3, 8, 1, 6, 2, 5, 4])

    print("\nSEMUA TES LULUS. Algoritma HS valid.")
