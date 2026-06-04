# Naskah Presentasi — Mini Proyek Akhir Semester
## Distributed Appointment Booking System
### Distributed System: Messaging, Replication & Leader Election

---

> **Durasi total:** ≤ 10 menit
> **Pembagian:**
> - **Anggota 1** — Pembukaan, jalankan aplikasi, tunjukkan arsitektur hidup *(~2,5 menit)*
> - **Anggota 2** — Demo REST API, gRPC, RabbitMQ, Database *(~3,5 menit)*
> - **Anggota 3** — Demo Leader Election HS, Load Balancing, Fault Tolerance, Penutup *(~4 menit)*
>
> **Legenda:**
> ```
> ⌨️  KETIK     → perintah yang diketik di terminal
> 🖱️  KLIK      → aksi di browser atau GUI
> 👁️  TUNJUK    → arahkan perhatian audiens ke bagian ini
> 🗣️  UCAPKAN   → kata-kata yang diucapkan presenter
> ✅  BUKTI      → apa yang membuktikan fitur ini bekerja
> 💡  JELASKAN  → kenapa dan bagaimana fitur ini bekerja
> ```

---

---

## ═══ PERSIAPAN SEBELUM PRESENTASI ═══
### *Lakukan ini 5 menit sebelum mulai — jangan tunggu saat presentasi*

---

### Langkah 1 — Jalankan Aplikasi

Buka terminal (PowerShell atau Command Prompt), lalu ketik:

```
⌨️  cd "C:\Users\Arcana\Documents\SISTER\dist-booking-system\dist-booking-system"
⌨️  docker compose up --build
```

Tunggu sampai semua container menampilkan log seperti ini di terminal:

```
scheduler-1  | [scheduler-1 id=1] scheduler gRPC listening on :50051
scheduler-2  | [scheduler-2 id=2] scheduler gRPC listening on :50051
scheduler-3  | [scheduler-3 id=3] scheduler gRPC listening on :50051
scheduler-3  | [scheduler-3 id=3] ELECTION start (Hirschberg-Sinclair) by node 3
scheduler-3  | [scheduler-3 id=3] node 3 -> LEADER, broadcast ke ring
notif-worker-1 | [notif-worker-1] menunggu event di queue 'appointment_confirmed'...
```

> **Tandanya siap:** Muncul baris `LEADER` di log dan tidak ada error merah.
> Proses ini memakan waktu ±30–60 detik pertama kali (build Docker image).

---

### Langkah 2 — Siapkan Jendela-Jendela Ini Sebelum Presentasi

Buka semuanya sekarang, jangan saat presentasi sedang berjalan:

| Jendela | URL / Lokasi | Untuk demo |
|---|---|---|
| **Terminal** | Layar docker compose up | Log election & notifikasi |
| **Browser Tab 1** | `http://localhost:8080` | Dashboard utama |
| **Browser Tab 2** | `http://localhost:8080/api/cluster/leader` | JSON status cluster |
| **Browser Tab 3** | `http://localhost:8080/api/appointments` | JSON daftar booking |
| **Browser Tab 4** | `http://localhost:15672` (guest/guest) | RabbitMQ Management UI |
| **VS Code** | File `election.py` sudah terbuka | Tunjuk kode jika ditanya |

> **Tips:** Zoom browser ke 125% (Ctrl+=) agar teks dashboard terbaca dari proyektor.

---

---

## ═══ BAGIAN 1 — ANGGOTA 1 ═══
### *Pembukaan + Tunjukkan Semua Komponen Hidup*

---

### [1.1 — Pembukaan]

🗣️ *"Selamat pagi/siang, Bapak/Ibu dosen dan teman-teman sekalian. Kelompok kami mempresentasikan Mini Proyek Akhir Semester: Distributed Appointment Booking System — sebuah sistem booking janji temu yang mengimplementasikan Messaging, Replication, dan Leader Election. Saya [Nama], bersama [Nama] dan [Nama]."*

---

### [1.2 — Tunjukkan Semua Container Hidup]

> **Tujuan:** Buktikan bahwa seluruh sistem sudah berjalan di Docker.

```
⌨️  Buka terminal baru (jangan tutup yang docker compose up)
⌨️  docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Output yang akan muncul di terminal:

```
NAMES            STATUS                    PORTS
nginx            Up 2 minutes              0.0.0.0:8080->80/tcp
booking-1        Up 2 minutes              8000/tcp
booking-2        Up 2 minutes              8000/tcp
scheduler-1      Up 2 minutes              50051/tcp
scheduler-2      Up 2 minutes              50051/tcp
scheduler-3      Up 2 minutes              50051/tcp
notif-worker-1   Up 2 minutes
notif-worker-2   Up 2 minutes
rabbitmq         Up 2 minutes              5672/tcp, 15672/tcp
postgres         Up 2 minutes (healthy)    5432/tcp
```

👁️ *Tunjuk output terminal ke audiens.*

✅ **Bukti:** 10 container berstatus `Up` — semua komponen sistem berjalan.

🗣️ *"Ini adalah bukti nyata bahwa seluruh sistem kami sudah berjalan. Ada 10 container Docker: Nginx sebagai pintu masuk, 2 replika Booking Service, 3 node Scheduler yang membentuk ring, 2 Notification Worker, RabbitMQ, dan PostgreSQL. Semua dijalankan dengan satu perintah* `docker compose up`*."*

💡 **Jelaskan:** *"Mengapa Docker? Karena setiap komponen punya environment yang terisolasi. Scheduler-1, 2, dan 3 adalah proses yang sama persis tapi berjalan sebagai tiga 'mesin' terpisah — persis seperti distributed system di dunia nyata."*

---

### [1.3 — Tunjukkan Dashboard Hidup]

```
🖱️  Buka Browser Tab 1 → http://localhost:8080
```

👁️ *Tunjuk ke layar browser. Dashboard menampilkan:*
- *Header: "BOOKING CLUSTER CONSOLE" dengan jam real-time*
- *Panel Scheduler Cluster: tiga kotak node, salah satu ber-mahkota ♛*
- *Panel form booking di kiri*
- *Panel daftar appointments dan notifikasi di kanan*

🗣️ *"Ini adalah dashboard GUI kami — dibangun dengan HTML, CSS, dan JavaScript murni tanpa framework, disajikan oleh Nginx. Dashboard ini auto-refresh setiap 2 detik sehingga semua perubahan terlihat secara real-time."*

🗣️ *"Perhatikan panel Scheduler Cluster di bagian atas. Tiga node scheduler sudah hidup. Salah satunya bertanda mahkota — itulah leader saat ini. Bagaimana leader ini dipilih, akan dijelaskan oleh [Nama Anggota 3] nanti."*

🗣️ *"Untuk detail teknis setiap fitur, saya serahkan kepada [Nama Anggota 2]."*

---

---

## ═══ BAGIAN 2 — ANGGOTA 2 ═══
### *Demo REST API, gRPC, RabbitMQ, Database*

---

### [2.1 — Demo REST API: Buat Booking]

> **Tujuan:** Tunjukkan REST API bekerja menerima request dari pengguna.

🗣️ *"Saya [Nama Anggota 2]. Mari kita mulai dengan fitur pertama — REST API."*

```
🖱️  Masih di Browser Tab 1 (http://localhost:8080)
🖱️  Di panel "Buat Appointment", isi:
     - Nama Customer  : Budi Santoso
     - Layanan        : konsultasi-umum
     - Waktu Slot     : 2026-06-10T09:00
     - Channel        : WHATSAPP
🖱️  Klik tombol hijau "RESERVE SLOT"
```

👁️ *Response muncul di bawah tombol dalam 1–2 detik:*

```
CONFIRMED ✓
slot_id=abc12345  leader=node 3
via scheduler-2 (served by booking-1)
```

✅ **Bukti REST API bekerja:** Sistem menerima request HTTP POST dan mengembalikan response JSON yang diformat menjadi teks di dashboard.

💡 **Jelaskan:** *"REST API kami dibangun dengan FastAPI di Python. Saat tombol ditekan, browser mengirim* `POST /api/appointments` *ke Nginx. Nginx meneruskannya ke salah satu Booking Service. Booking Service memvalidasi data menggunakan Pydantic — kalau ada field yang kosong atau tipe datanya salah, langsung ditolak sebelum masuk ke database. Ini adalah boundary validation yang benar."*

---

### [2.2 — Demo REST API: Lihat Data via JSON]

> **Tujuan:** Tunjukkan endpoint GET mengembalikan data dari database.

```
🖱️  Buka Browser Tab 3 → http://localhost:8080/api/appointments
```

👁️ *Browser menampilkan JSON:*

```json
{
  "appointments": [
    {
      "id": "abc12345",
      "customer_name": "Budi Santoso",
      "service_id": "konsultasi-umum",
      "slot_time": "2026-06-10T09:00",
      "status": "CONFIRMED",
      "created_at": "2026-06-04T..."
    }
  ]
}
```

✅ **Bukti:** Data appointment tersimpan di PostgreSQL dan bisa diambil via GET endpoint.

🗣️ *"Ini adalah raw JSON yang dikembalikan endpoint* `GET /appointments`*. Status sudah* `CONFIRMED` *— artinya data sudah tersimpan persisten di PostgreSQL."*

---

### [2.3 — Demo gRPC: Buktikan Komunikasi Antar-Service]

> **Tujuan:** Tunjukkan Booking Service berkomunikasi ke Scheduler cluster via gRPC.

```
🖱️  Buka Browser Tab 2 → http://localhost:8080/api/cluster/leader
```

👁️ *Browser menampilkan JSON seperti ini:*

```json
{
  "nodes": [
    {"addr": "scheduler-1:50051", "leader_id": 3, "i_am_leader": false, "alive": true},
    {"addr": "scheduler-2:50051", "leader_id": 3, "i_am_leader": false, "alive": true},
    {"addr": "scheduler-3:50051", "leader_id": 3, "i_am_leader": true,  "alive": true}
  ]
}
```

✅ **Bukti gRPC bekerja:** Endpoint ini memanggil `WhoIsLeader` via gRPC ke ketiga node dan mengumpulkan hasilnya. Kalau gRPC tidak bekerja, semua node akan `alive: false`.

💡 **Jelaskan:** *"Booking Service tidak tahu secara langsung siapa leader. Ia mengirim request via gRPC ke salah satu node menggunakan round-robin. Kalau node yang dipilih bukan leader, node itu membalas dengan status* `NOT_LEADER` *dan memberitahu alamat leader yang sebenarnya. Booking Service otomatis retry ke leader tersebut. Inilah yang menyebabkan di response booking tadi tertulis 'via scheduler-2 served by booking-1' — scheduler-2 bukan leader, dia mengarahkan request ke scheduler-3 yang leader."*

🗣️ *"Lihat field* `i_am_leader: true` *hanya ada di scheduler-3. Semua node tahu siapa leader-nya karena algoritma leader election sudah selesai saat startup."*

---

### [2.4 — Demo RabbitMQ: Asynchronous Notification]

> **Tujuan:** Buktikan notifikasi dikirim TANPA memblok response booking, diproses di belakang layar.

```
🖱️  Kembali ke Browser Tab 1 (http://localhost:8080)
👁️  Perhatikan panel "Notifikasi (async via RabbitMQ)" di kanan bawah
```

👁️ *Panel notifikasi sudah menampilkan entri dari booking sebelumnya:*

```
[WHATSAPP] SENT · appt abc12345
Halo Budi Santoso, janji konsultasi-umum pada 2026-06-10T09:00 dikonfirmasi.
```

✅ **Bukti RabbitMQ bekerja:** Notifikasi muncul beberapa detik SETELAH response booking diterima — bukan bersamaan. Ini membuktikan proses async.

💡 **Jelaskan:** *"Saat booking CONFIRMED, Booking Service tidak menunggu notifikasi selesai dikirim. Ia langsung mempublikasikan sebuah pesan ke RabbitMQ — ke queue bernama* `appointment_confirmed` *— lalu langsung mengembalikan response ke pengguna. Notification Worker yang sedang berjalan di latar belakang kemudian mengambil pesan dari queue itu, memproses simulasi pengiriman, dan mencatat hasilnya ke database. Jeda waktu beberapa detik itulah yang membuktikan ini benar-benar asynchronous."*

Sekarang tunjukkan RabbitMQ Management UI:

```
🖱️  Buka Browser Tab 4 → http://localhost:15672
🖱️  Login: username = guest, password = guest
🖱️  Klik menu "Queues and Streams"
🖱️  Klik nama queue "appointment_confirmed"
```

👁️ *Halaman queue menampilkan:*
- *Consumers: 2 (dua worker aktif mendengarkan)*
- *Message rates: grafik spike kecil saat tadi ada booking*
- *Total messages: 0 (semua sudah diproses)*

✅ **Bukti tambahan:** 2 consumer aktif = 2 Notification Worker berjalan dan siap memproses pesan.

---

### [2.5 — Demo Database: Persistent Storage & Anti Double-Booking]

> **Tujuan:** Buktikan database menyimpan data dan mencegah double booking.

**Tes 1 — Data persisten:**

👁️ *Data booking yang dibuat tadi masih terlihat di panel Appointments di dashboard.*

🗣️ *"Data ini disimpan di PostgreSQL dan akan tetap ada meskipun Booking Service di-restart. Bukan data in-memory."*

**Tes 2 — Anti double-booking (coba pesan slot yang sama):**

```
🖱️  Di panel "Buat Appointment", isi dengan slot yang SAMA persis:
     - Nama Customer  : Siti Rahayu   (nama beda tidak masalah)
     - Layanan        : konsultasi-umum
     - Waktu Slot     : 2026-06-10T09:00   ← SAMA dengan sebelumnya
     - Channel        : EMAIL
🖱️  Klik "RESERVE SLOT"
```

👁️ *Response muncul berwarna kuning/oranye:*

```
SLOT_TAKEN — slot ini sudah dipesan (anti double-booking).
```

✅ **Bukti database bekerja:** Sistem menolak booking kedua untuk slot yang sama.

💡 **Jelaskan:** *"Di database, tabel* `slots` *di Scheduler Service memiliki* `PRIMARY KEY` *gabungan antara service_id dan slot_time. Ketika Leader mencoba menyimpan slot yang sama, PostgreSQL menjalankan* `INSERT ... ON CONFLICT DO NOTHING`*. Query ini atomik — tidak bisa terjadi dua insert bersamaan untuk key yang sama karena PostgreSQL menggunakan row-level locking. Hasilnya: jika slot sudah ada, insert gagal dengan elegan, dan sistem mengembalikan status* `SLOT_TAKEN`*."*

🗣️ *"Untuk fitur Leader Election dan Load Balancing, saya serahkan kepada [Nama Anggota 3]."*

---

---

## ═══ BAGIAN 3 — ANGGOTA 3 ═══
### *Demo Leader Election HS, Load Balancing, Fault Tolerance*

---

### [3.1 — Tunjukkan Leader Election di Dashboard]

🗣️ *"Terima kasih. Saya [Nama Anggota 3]. Fitur yang paling kompleks di proyek ini adalah Leader Election menggunakan algoritma Hirschberg-Sinclair."*

```
🖱️  Kembali ke Browser Tab 1 (http://localhost:8080)
👁️  Fokus ke panel "Scheduler Cluster" di bagian atas
```

👁️ *Panel menampilkan tiga kotak node:*
```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  scheduler-1 │  │  scheduler-2 │  │  scheduler-3 │
│   follower   │  │   follower   │  │  ♛ LEADER    │
│ ● ALIVE      │  │ ● ALIVE      │  │ ● ALIVE      │
└──────────────┘  └──────────────┘  └──────────────┘
```

✅ **Bukti leader election bekerja:** Hanya satu node bertanda mahkota. Semua node setuju siapa leader-nya (terbukti dari endpoint `/cluster/leader` yang tadi menunjukkan `i_am_leader: true` hanya di satu node).

💡 **Jelaskan cara kerja HS:**

🗣️ *"Algoritma Hirschberg-Sinclair bekerja di atas topologi ring. Tiga node scheduler ini membentuk lingkaran: scheduler-1 terhubung ke scheduler-2 dan scheduler-3, begitu seterusnya.*

*Saat sistem startup, setiap node menjalankan election secara bersamaan. Setiap node mengirim dua pesan PROBE — satu searah jarum jam (CW) dan satu berlawanan (CCW). PROBE membawa ID pengirimnya.*

*Aturannya sederhana: kalau sebuah node menerima PROBE dengan ID lebih kecil dari ID-nya sendiri, probe itu ditelan — pengirimnya gugur. Kalau ID probe lebih besar, probe diteruskan. Kalau ID probe sama dengan ID node itu sendiri, artinya probe sudah berhasil mengelilingi ring penuh tanpa dihentikan siapapun — node itu mendeklarasikan diri sebagai LEADER.*

*Di sistem kita, node-3 punya ID tertinggi, jadi probe-nya tidak pernah ditelan. Hasilnya: node-3 selalu menjadi leader."*

---

### [3.2 — Tunjukkan Log Election di Terminal]

> **Tujuan:** Lihat proses election secara langsung dari dalam sistem.

```
🖱️  Buka terminal yang menjalankan docker compose up
👁️  Scroll ke atas sedikit, cari baris-baris dari waktu startup
```

👁️ *Log election saat startup akan terlihat seperti ini:*

```
scheduler-1  | [scheduler-1 id=1] ELECTION start (Hirschberg-Sinclair) by node 1
scheduler-2  | [scheduler-2 id=2] ELECTION start (Hirschberg-Sinclair) by node 2
scheduler-3  | [scheduler-3 id=3] ELECTION start (Hirschberg-Sinclair) by node 3
scheduler-1  | [scheduler-1 id=1] leader diketahui: id=3 addr=scheduler-3:50051
scheduler-2  | [scheduler-2 id=2] leader diketahui: id=3 addr=scheduler-3:50051
scheduler-3  | [scheduler-3 id=3] node 3 -> LEADER, broadcast ke ring
```

✅ **Bukti proses election:** Ketiga node memulai election bersamaan. Node-3 mendeklarasikan diri sebagai leader dan melakukan broadcast. Node-1 dan node-2 menerima broadcast dan mengakui node-3 sebagai leader.

💡 **Jelaskan:**  *"Log ini menunjukkan proses election yang sebenarnya terjadi di dalam container. Perhatikan urutan waktunya: ketiga node mulai hampir bersamaan, kemudian node-3 yang paling pertama mengumumkan diri sebagai leader karena probe-nya berhasil keliling ring. Sementara probe node-1 dan node-2 ditelan oleh node-3 di tengah jalan."*

---

### [3.3 — Demo Fault Tolerance: Matikan Leader, Lihat Election Baru]

> **Tujuan:** Buktikan sistem otomatis pulih ketika leader mati.
> *Ini adalah demo paling dramatis — lakukan dengan tenang.*

**Langkah 1 — Catat siapa leader sekarang:**

```
🖱️  Lihat dashboard — node mana yang bertanda mahkota? Ingat namanya.
     (kemungkinan besar scheduler-3)
```

**Langkah 2 — Matikan leader:**

```
⌨️  Buka terminal BARU (jangan tutup yang docker compose up)
⌨️  docker stop dist-booking-system-scheduler-3-1
```

> Nama container bisa sedikit berbeda. Gunakan `docker ps` untuk melihat nama pastinya,
> lalu ganti `scheduler-3` dengan nama yang tepat.

**Langkah 3 — Amati dashboard dan terminal dalam 6–8 detik:**

```
👁️  Amati Browser Tab 1 (dashboard) — panel Scheduler Cluster
👁️  Amati terminal docker compose up secara bersamaan
```

👁️ *Yang akan terjadi di dashboard (dalam ~6 detik):*
```
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│  scheduler-1 │  │  scheduler-2 │  │   scheduler-3    │
│  ♛ LEADER   │  │   follower   │  │ (opacity redup)  │
│ ● ALIVE      │  │ ● ALIVE      │  │ ● DOWN           │
└──────────────┘  └──────────────┘  └──────────────────┘
```

👁️ *Yang akan muncul di log terminal:*
```
scheduler-1  | [scheduler-1 id=1] leader sunyi 6.1s -> mulai election ulang
scheduler-2  | [scheduler-2 id=2] leader sunyi 6.2s -> mulai election ulang
scheduler-1  | [scheduler-1 id=1] ELECTION start (Hirschberg-Sinclair) by node 1
scheduler-2  | [scheduler-2 id=2] ELECTION start (Hirschberg-Sinclair) by node 2
scheduler-2  | [scheduler-2 id=2] node 2 -> LEADER, broadcast ke ring
scheduler-1  | [scheduler-1 id=1] leader diketahui: id=2 addr=scheduler-2:50051
```

✅ **Bukti fault tolerance:** Tanpa intervensi manusia, sistem mendeteksi leader mati dan memilih leader baru dalam waktu ~6 detik. Tidak ada downtime permanen.

💡 **Jelaskan:**
🗣️ *"Inilah fault tolerance yang kami implementasikan. Setiap follower menjalankan sebuah loop yang memantau heartbeat dari leader. Leader mengirim heartbeat setiap 2 detik. Jika dalam 6 detik tidak ada heartbeat — karena leader mati — follower memulai election baru secara otomatis.*

*Sekarang node-2 menjadi leader karena ia node dengan ID tertinggi yang masih hidup. Booking tetap bisa dilakukan — sistem tidak berhenti sama sekali."*

**Langkah 4 — Coba booking saat leader mati digantikan leader baru:**

```
🖱️  Di dashboard, buat booking baru:
     - Nama: Dewi Lestari
     - Layanan: konsultasi-gigi
     - Slot: 2026-06-10T10:00
🖱️  Klik RESERVE SLOT
```

✅ **Bukti sistem tetap berjalan:** Booking berhasil CONFIRMED meskipun satu node mati. Response sekarang menunjukkan `leader=node 2`.

**Langkah 5 — Hidupkan kembali node yang dimatikan:**

```
⌨️  docker start dist-booking-system-scheduler-3-1
```

👁️ *Dalam beberapa detik, node-3 muncul kembali di dashboard dengan badge ALIVE. Election terjadi lagi dan node-3 kembali menjadi leader karena ID-nya tertinggi.*

---

### [3.4 — Demo Load Balancing: Nginx Round-Robin]

> **Tujuan:** Buktikan request tersebar ke dua Booking Service secara bergantian.

🗣️ *"Sekarang saya tunjukkan Load Balancing."*

**Buat 4 booking berturut-turut dengan slot waktu yang berbeda:**

```
🖱️  Booking 1: Nama = A, slot = 2026-06-11T08:00, klik RESERVE SLOT
🖱️  Booking 2: Nama = B, slot = 2026-06-11T09:00, klik RESERVE SLOT
🖱️  Booking 3: Nama = C, slot = 2026-06-11T10:00, klik RESERVE SLOT
🖱️  Booking 4: Nama = D, slot = 2026-06-11T11:00, klik RESERVE SLOT
```

👁️ *Perhatikan bagian bawah setiap response — baris `via ...`:*

```
Booking 1 → via scheduler-X (served by booking-1)
Booking 2 → via scheduler-X (served by booking-2)
Booking 3 → via scheduler-X (served by booking-1)
Booking 4 → via scheduler-X (served by booking-2)
```

✅ **Bukti load balancing:** Kata `served by booking-1` dan `served by booking-2` bergantian — membuktikan Nginx mendistribusikan request secara round-robin ke dua replika.

💡 **Jelaskan:**
🗣️ *"Nginx dikonfigurasi sebagai reverse proxy dengan blok* `upstream` *yang berisi dua server: booking-1 dan booking-2. Algoritma default Nginx adalah round-robin — request pertama ke booking-1, berikutnya ke booking-2, bergantian terus. Nginx juga menambahkan header* `X-Served-By` *pada setiap response sehingga kita bisa melacak replika mana yang merespons. Inilah bukti API Load Balancing berjalan."*

---

### [3.5 — Rekap Semua Fitur yang Sudah Didemonstrasikan]

🗣️ *"Baik, mari kita rekap apa yang sudah kami demonstrasikan:"*

| Fitur | Bukti yang Sudah Dilihat |
|---|---|
| ✅ **REST API (15%)** | Form booking → response JSON CONFIRMED |
| ✅ **gRPC Service-to-Service (20%)** | `/cluster/leader` → JSON dari 3 node via gRPC |
| ✅ **RabbitMQ Async (20%)** | Notifikasi muncul setelah response, bukan bersamaan |
| ✅ **Database Persistent (10%)** | Data tersimpan; SLOT_TAKEN saat double-booking |
| ✅ **Domain Booking + Notif (10%)** | Form booking + panel notifikasi |
| ✅ **Leader Election HS (20%)** | Mahkota berpindah otomatis saat leader dimatikan |
| ✅ **API Load Balancing (5%)** | "served by booking-1/2" bergantian |
| ✅ **Docker (15%)** | `docker ps` = 10 container aktif |
| ✅ **GUI (5%)** | Dashboard real-time di browser |

---

### [3.6 — Penutup]

🗣️ *"Kami berhasil membangun sistem distributed yang nyata — bukan simulasi. Setiap komponen berjalan sebagai proses terpisah di container berbeda, berkomunikasi lewat jaringan, dan bisa gagal secara independen. Sistem ini pulih sendiri ketika node mati, mendistribusikan beban secara merata, dan memproses notifikasi tanpa memblok pengguna."*

🗣️ *"Yang paling kami banggakan adalah implementasi Hirschberg-Sinclair — algoritma dengan kompleksitas O(n log n) yang kami implementasikan dari nol, dan tadi sudah kami buktikan bekerja secara live ketika node dimatikan dan election baru terjadi otomatis."*

🗣️ *"Demikian presentasi kami. Kami siap menjawab pertanyaan. Terima kasih."*

---

---

## ═══ PANDUAN TANYA JAWAB ═══
*(Jawaban siap pakai untuk pertanyaan umum dosen)*

---

**Q: Kenapa pilih Hirschberg-Sinclair bukan Bully atau Ring biasa?**

> HS punya kompleksitas O(n log n) — lebih efisien dari Ring O(n²). Alasan utama lainnya: rubrik memberi bobot 20% untuk HS vs Ring 10% dan Bully 5%. Secara teknis, HS juga lebih menarik karena bekerja di ring bidireksional — probe dikirim ke dua arah sehingga konvergensi lebih cepat dan lebih tahan terhadap kegagalan satu arah.

---

**Q: Bagaimana kalau dua node mengklaim diri sebagai leader sekaligus?**

> Tidak mungkin terjadi di HS. Hanya node yang probe-nya kembali ke dirinya sendiri yang bisa menjadi leader — itu hanya bisa terjadi kalau probe sudah keliling ring penuh tanpa ditelan siapapun. Kalau ada node lain dengan ID lebih tinggi, probe itu pasti sudah ditelan sebelum bisa balik. Jadi secara matematis hanya satu node yang bisa mencapai kondisi itu.

---

**Q: Apa bedanya gRPC dengan REST biasa untuk komunikasi antar-service?**

> REST mengirim data sebagai JSON teks — mudah dibaca manusia tapi lebih besar dan lebih lambat di-parse. gRPC mengirim data sebagai binary Protobuf — lebih kecil dan lebih cepat. Yang lebih penting: gRPC menggunakan file `.proto` sebagai kontrak ketat antara client dan server. Kalau kontrak berubah, kompilasi gagal — tidak bisa terjadi mismatch diam-diam seperti di REST. Untuk komunikasi scheduler-to-scheduler yang frekuensinya tinggi (heartbeat tiap 2 detik), efisiensi ini sangat penting.

---

**Q: Kenapa RabbitMQ perlu prefetch_count=1?**

> Tanpa itu, RabbitMQ akan mendorong semua pesan yang ada di queue ke satu worker sekaligus. Worker-1 bisa mendapat 100 pesan sementara worker-2 menganggur. Dengan `prefetch_count=1`, setiap worker hanya mengambil satu pesan, memprosesnya, mengirim ACK, baru mengambil pesan berikutnya. Hasilnya: beban terdistribusi merata antara dua worker.

---

**Q: Bagaimana cara menjalankan proyeknya dari awal?**

> ```
> cd "C:\Users\Arcana\Documents\SISTER\dist-booking-system\dist-booking-system"
> docker compose up --build
> ```
> Buka browser ke `http://localhost:8080`. Selesai. Satu perintah untuk seluruh sistem.

---

*Naskah presentasi Mini Proyek Akhir Semester — Distributed System*
