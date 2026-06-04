-- Skema database untuk sistem Appointment Booking + Notification
-- Dijalankan otomatis oleh container Postgres saat pertama kali start.

CREATE TABLE IF NOT EXISTS slots (
    id          SERIAL PRIMARY KEY,
    service_id  VARCHAR(64)  NOT NULL,
    slot_time   VARCHAR(32)  NOT NULL,
    is_booked   BOOLEAN      NOT NULL DEFAULT FALSE,
    booked_by   VARCHAR(64),
    -- satu slot_time per service hanya boleh ada satu: kunci anti double-booking
    UNIQUE (service_id, slot_time)
);

CREATE TABLE IF NOT EXISTS appointments (
    id            VARCHAR(64) PRIMARY KEY,
    customer_name VARCHAR(128) NOT NULL,
    service_id    VARCHAR(64)  NOT NULL,
    slot_time     VARCHAR(32)  NOT NULL,
    status        VARCHAR(32)  NOT NULL DEFAULT 'PENDING',  -- PENDING|CONFIRMED|REJECTED
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notifications (
    id             SERIAL PRIMARY KEY,
    appointment_id VARCHAR(64) NOT NULL,
    channel        VARCHAR(32) NOT NULL,        -- WHATSAPP|EMAIL
    status         VARCHAR(32) NOT NULL,        -- SENT|FAILED
    detail         TEXT,
    sent_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Seed beberapa slot contoh supaya demo langsung ada data.
INSERT INTO slots (service_id, slot_time) VALUES
    ('konsultasi-umum', '2026-06-10T09:00'),
    ('konsultasi-umum', '2026-06-10T10:00'),
    ('konsultasi-umum', '2026-06-10T11:00'),
    ('konsultasi-gigi', '2026-06-10T09:00'),
    ('konsultasi-gigi', '2026-06-10T10:00')
ON CONFLICT (service_id, slot_time) DO NOTHING;
