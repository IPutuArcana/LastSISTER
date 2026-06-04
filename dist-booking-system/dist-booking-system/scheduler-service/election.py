"""
Hirschberg-Sinclair (HS) Leader Election
=========================================

Implementasi algoritma leader election Hirschberg-Sinclair untuk ring
bidirectional. Algoritma ini dipilih (bukan Bully/Ring sederhana) karena
kompleksitas pesannya O(n log n) dan jadi tantangan rubrik dengan bobot
tertinggi.

Cara kerja singkat:
- Setiap node bekerja dalam fase k = 0, 1, 2, ...
- Pada fase k, node mengirim PROBE berisi ID-nya ke DUA arah (cw & ccw)
  sejauh 2^k hop.
- Node penerima PROBE:
    * jika id_probe > id_sendiri  -> teruskan probe (kurangi hop). Kalau hop
      habis, kirim REPLY balik ke pengirim.
    * jika id_probe < id_sendiri  -> telan probe (node ini lebih kuat).
    * jika id_probe == id_sendiri -> probe sudah keliling ring penuh -> node
      ini LEADER.
- Node yang menerima KEDUA reply (cw & ccw) di fase k akan lanjut ke fase k+1.
- Node dengan ID tertinggi pada akhirnya jadi leader, lalu broadcast LEADER.

Modul ini SENGAJA tidak tahu soal jaringan. Ia memanggil callback `send_fn`
untuk mengirim pesan, sehingga bisa diuji dengan simulasi in-memory maupun
dijalankan di atas gRPC tanpa mengubah logika inti.
"""

import threading
import time

# Tipe pesan election
PROBE = "PROBE"
REPLY = "REPLY"
LEADER = "LEADER"

# Arah keliling ring
CW = "CW"    # clockwise  (ke neighbor kanan)
CCW = "CCW"  # counter-clockwise (ke neighbor kiri)


def opposite(direction):
    return CCW if direction == CW else CW


class HSElection:
    """State machine Hirschberg-Sinclair untuk satu node.

    Parameter:
      node_id   : int unik untuk node ini (ID tertinggi menang).
      send_fn   : callable(target_dir, message_dict) -> None
                  mengirim pesan ke neighbor pada arah target_dir (CW/CCW).
      on_leader : callable(leader_id) -> None
                  dipanggil saat node ini tahu siapa leader final.
    """

    def __init__(self, node_id, send_fn, on_leader=None, log_fn=print):
        self.node_id = node_id
        self.send_fn = send_fn
        self.on_leader = on_leader or (lambda lid: None)
        self.log = log_fn

        self.lock = threading.RLock()
        self.reset()

    def reset(self):
        with self.lock:
            self.phase = 0
            self.replies_this_phase = 0
            self.active = False        # sedang ikut election atau sudah kalah
            self.leader_id = None
            self.is_leader = False

    # ---- API utama ----------------------------------------------------

    def start(self):
        """Mulai election dari fase 0."""
        with self.lock:
            self.phase = 0
            self.replies_this_phase = 0
            self.active = True
            self.leader_id = None
            self.is_leader = False
        self.log(f"ELECTION start (Hirschberg-Sinclair) by node {self.node_id}")
        self._send_probes()

    def handle(self, msg):
        """Proses satu pesan election yang masuk."""
        mtype = msg["type"]
        if mtype == PROBE:
            self._on_probe(msg)
        elif mtype == REPLY:
            self._on_reply(msg)
        elif mtype == LEADER:
            self._on_leader(msg)

    # ---- internal -----------------------------------------------------

    def _send_probes(self):
        """Kirim probe ke dua arah sejauh 2^phase hop."""
        hops = 2 ** self.phase
        for direction in (CW, CCW):
            self.send_fn(direction, {
                "type": PROBE,
                "initiator_id": self.node_id,
                "phase": self.phase,
                "hops": hops,
                "direction": direction,   # arah perjalanan probe
            })

    def _on_probe(self, msg):
        initiator = msg["initiator_id"]
        phase = msg["phase"]
        hops = msg["hops"]
        direction = msg["direction"]

        if initiator == self.node_id:
            # Probe kembali ke pengirim asal -> sudah keliling ring penuh.
            # Node ini punya ID tertinggi -> jadi leader.
            self._declare_leader()
            return

        if initiator < self.node_id:
            # Node ini lebih kuat -> telan probe, jangan diteruskan.
            return

        # initiator > node_id: node ini kalah di ronde ini, layani probe.
        hops -= 1
        if hops <= 0:
            # Hop habis -> kirim REPLY balik ke arah berlawanan.
            self.send_fn(opposite(direction), {
                "type": REPLY,
                "initiator_id": initiator,
                "phase": phase,
                "direction": opposite(direction),
            })
        else:
            # Teruskan probe pada arah yang sama.
            self.send_fn(direction, {
                "type": PROBE,
                "initiator_id": initiator,
                "phase": phase,
                "hops": hops,
                "direction": direction,
            })

    def _on_reply(self, msg):
        initiator = msg["initiator_id"]
        direction = msg["direction"]

        if initiator != self.node_id:
            # Bukan reply untuk node ini -> teruskan ke tujuan.
            self.send_fn(direction, msg)
            return

        # Reply untuk node ini.
        with self.lock:
            if not self.active:
                return
            self.replies_this_phase += 1
            got_both = self.replies_this_phase >= 2

        if got_both:
            # Lolos fase ini -> naik ke fase berikutnya.
            with self.lock:
                self.phase += 1
                self.replies_this_phase = 0
                next_phase = self.phase
            self.log(f"node {self.node_id} survived, masuk fase {next_phase}")
            self._send_probes()

    def _declare_leader(self):
        with self.lock:
            if self.is_leader:
                return
            self.is_leader = True
            self.leader_id = self.node_id
            self.active = False
        self.log(f"node {self.node_id} -> LEADER, broadcast ke ring")
        # Sebarkan pengumuman leader keliling ring (cukup satu arah).
        self.send_fn(CW, {
            "type": LEADER,
            "leader_id": self.node_id,
            "origin_id": self.node_id,
        })
        self.on_leader(self.node_id)

    def _on_leader(self, msg):
        leader_id = msg["leader_id"]
        origin = msg["origin_id"]
        with self.lock:
            already = (self.leader_id == leader_id)
            self.leader_id = leader_id
            self.is_leader = (leader_id == self.node_id)
            self.active = False
        if not already:
            self.on_leader(leader_id)
        # Teruskan ke node berikutnya selama belum kembali ke origin.
        if self.node_id != origin:
            self.send_fn(CW, msg)
