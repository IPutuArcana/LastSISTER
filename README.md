# Distributed Appointment Booking System

Proyek UAS Sistem Terdistribusi. Ekstensi dari demo `goshlive/dist-system`
dengan domain **Appointment Booking + Notification**.

Sistem terdiri dari beberapa service yang berkomunikasi via REST, gRPC, dan
RabbitMQ, dengan cluster scheduler yang memilih leader memakai algoritma
**Hirschberg-Sinclair**. Semua dijalankan lewat Docker Compose.

---

## Pemetaan Rubrik

| Item | Implementasi |
|---|---|
| REST-API | Booking Service (FastAPI): `/appointments`, `/notifications`, `/cluster/leader` |
| Service-to-Service RPC (stub) | gRPC: Booking Service -> Scheduler cluster (`scheduler.proto`) |
| RabbitMQ async workflow | Event `appointment_confirmed` -> Notification Worker |
| Persistent Storage (DB) | PostgreSQL (appointments, slots, notifications) |
| Case study domain | Appointment booking + notification |
| Leader Election | Hirschberg-Sinclair (`scheduler-service/election.py`) |
| API Load Balancing | nginx round-robin ke 2 replika Booking Service |
| Docker | `docker-compose.yml` (semua service) |
| GUI | Dashboard web (`dashboard/index.html`) |

---

## Arsitektur

```
            [ Dashboard GUI ]
                   |
                   v  REST /api/*
            [ nginx :8080 ]  (load balancer)
              /          \
      [ booking-1 ]   [ booking-2 ]   REST-API publik (FastAPI)
              \          /
               | gRPC (stub) round-robin + retry ke leader
               v
   [ scheduler-1 ] [ scheduler-2 ] [ scheduler-3 ]
     Hirschberg-Sinclair leader election (ring)
     LEADER = otoritas tunggal commit slot (anti double-booking)
               |
               | publish "appointment_confirmed"
               v
          [ RabbitMQ ]
               |
        +------+------+
        v             v
 [ notif-worker-1 ] [ notif-worker-2 ]   konsumsi async -> simulasi kirim
        \             /
               v
        [ PostgreSQL ]   appointments | slots | notifications
```

### Kenapa butuh leader election?

Alokasi slot harus diserialisasi supaya dua request berbeda tidak memesan
slot yang sama (double-booking). Hanya node **leader** yang boleh meng-commit
slot ke database. Kalau leader mati, cluster otomatis memilih leader baru
sehingga sistem tetap berjalan.

### Hirschberg-Sinclair (singkat)

Node bekerja dalam fase k = 0,1,2,... Pada tiap fase, node mengirim PROBE
berisi ID-nya ke dua arah sejauh 2^k hop. Probe dari ID lebih besar diteruskan,
dari ID lebih kecil ditelan. Node yang menerima dua REPLY pada fase tertentu
lanjut ke fase berikutnya. Node yang menerima PROBE-nya sendiri kembali berarti
sudah keliling ring penuh -> jadi leader, lalu broadcast LEADER. Node ber-ID
tertinggi yang menang. Kompleksitas pesan O(n log n).

---

## Cara Menjalankan

Syarat: Docker + Docker Compose.

```bash
docker compose up --build
```

Tunggu beberapa detik sampai election selesai, lalu buka:

- Dashboard: http://localhost:8080
- RabbitMQ UI: http://localhost:15672 (guest / guest)

Hentikan:

```bash
docker compose down          # tetap simpan data
docker compose down -v       # hapus data Postgres juga
```

---

## Skenario Demo (untuk presentasi)

### 1. Booking normal
Buka dashboard, isi form, klik **RESERVE SLOT**. Status jadi `CONFIRMED`,
muncul notifikasi async di feed (diproses worker via RabbitMQ).

### 2. Anti double-booking
Booking slot yang sama dua kali (service + waktu sama). Yang kedua jadi
`SLOT_TAKEN`. Dijamin oleh operasi atomik di leader + constraint UNIQUE di DB.

### 3. Failover leader (paling penting)
Lihat node leader di dashboard (default node dengan ID tertinggi = scheduler-3).
Matikan leader:

```bash
docker compose stop scheduler-3
```

Dalam beberapa detik dashboard menunjukkan leader baru (scheduler-2). Coba
booking lagi: tetap berhasil. Hidupkan lagi:

```bash
docker compose start scheduler-3
```

scheduler-3 memicu election dan merebut kembali posisi leader.

### 4. Load balancing
Hasil booking menampilkan field `via` yang menyebut `booking-1` atau
`booking-2` bergantian, bukti request tersebar oleh nginx.

---

## Tes Tanpa Docker

Logika inti bisa diuji langsung tanpa Docker:

```bash
pip install grpcio grpcio-tools

# 1) Validasi algoritma HS (simulasi banyak ukuran ring)
python3 tests/test_election_sim.py

# 2) Election + failover via gRPC nyata (3 proses, DB in-memory)
python3 tests/test_grpc_election.py
```

---

## Struktur Folder

```
proto/scheduler.proto         definisi gRPC
scheduler-service/            cluster node: election.py (HS) + server.py (gRPC)
booking-service/              REST-API (FastAPI) + gRPC client + publisher MQ
notification-worker/          consumer RabbitMQ
dashboard/index.html          GUI
nginx/nginx.conf              load balancer + serve dashboard
db/init.sql                   skema PostgreSQL + seed
docker-compose.yml            orkestrasi semua service
tests/                        uji algoritma & integrasi
gen_proto.sh                  regenerate stub gRPC
```

## Regenerate Stub gRPC (jika proto diubah)

```bash
./gen_proto.sh
```

---

## Endpoint REST (Booking Service, via nginx prefix `/api`)

| Method | Path | Fungsi |
|---|---|---|
| POST | `/api/appointments` | buat appointment + reserve slot |
| GET | `/api/appointments` | daftar appointment |
| GET | `/api/appointments/{id}` | detail appointment |
| GET | `/api/notifications` | daftar notifikasi |
| GET | `/api/cluster/leader` | status leader tiap node (dipakai dashboard) |
