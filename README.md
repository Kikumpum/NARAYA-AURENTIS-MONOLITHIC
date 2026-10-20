# NAM DMS — Naraya Aurentis Monolithic

**Prototipe fungsional untuk dibuka dan dikembangkan lewat OpenAI Codex.**

Integrasi awal Dental Clinic, Dental Lab (internal + eksternal), surat kerja Dokter Klinik, penugasan Supervisor Lab, estimasi, produksi, QC, portal pasien, peran Klinik Mitra, invoice, kontrol FAT, dan Daily Report. Antarmuka responsif untuk HP dan laptop.

> **PERINGATAN: HANYA DEMO LOKAL DENGAN DATA FIKTIF. BUKAN SOFTWARE PRODUKSI, BELUM LAYAK MENYIMPAN DATA PASIEN ASLI ATAU MEMPROSES PEMBAYARAN NYATA.** Security checklist masih memiliki blocking items, lihat `docs/SECURITY_GATES.md`.

## Jalankan di Codex / komputer developer

**Syarat:** Python 3.11+; koneksi untuk memasang dependencies (atau dependency telah terpasang).

```bash
# Dari root folder proyek
python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

Buka **http://127.0.0.1:8000**. API demo: **http://127.0.0.1:8000/api/docs** (perlu akses CDN untuk interaktif Swagger bawaan; endpoint tetap bekerja tanpa CDN).

**Akun login DEMO** menggunakan kata sandi sama: `DemoNAM2026!`

| Login | Divisi | Login | Divisi |
| --- | --- | --- | --- |
| `resepsionis` | Front Office | `dokter` | Dokter Klinik |
| `lab` | Supervisor Lab | `teknisi` | Teknisi produksi |
| `qc` | Quality Control | `fat` | Finance/FAT |
| `direktur` | Manajemen | `mitra` | Klinik eksternal |
| `pasien` | Portal pasien | `it` | IT (tidak melihat data klinis) |
| `dokter2` | Dokter kedua | `lab2` | Supervisor Lab kedua |
| `perawat` | Perawat | `cadcam` | CAD/CAM (laporan harian) |
| `cs` | Customer Service | `gudang` | Inventaris (laporan harian) |
| `purchasing` | Pembelian | `hr` | HRD |
| `marketing` | Marketing | | |

Akun awal, pasien dan order adalah **simulasi**. Data tersimpan ke `nam_demo.db` di direktori tempat server dijalankan. Hapus file `.db` setelah server dihentikan untuk reset demo.

## Pengujian

```bash
python -m pip install pytest httpx
python -m pytest -q backend/tests
node --check frontend/app.js  # jika Node.js tersedia
```

## Skenario penggunaan antar-divisi

1. Masuk sebagai `resepsionis` → Order Dental Lab → tugaskan `LAB-DEMO-001` kepada Supervisor Lab.
2. Masuk sebagai `lab` → terima order → tentukan teknisi, validasi ETA.
3. Masuk sebagai `teknisi` → ubah tahap ke `qc_pending`.
4. Masuk sebagai `qc` → lakukan pemeriksaan → order `ready`.
5. Masuk sebagai `pasien` → baca notifikasi di outbox portal. **Tidak ada pengiriman pesan eksternal nyata.**
6. Masuk sebagai `resepsionis` → buat invoice dan catat pembayaran.
7. Masuk sebagai `fat` → lakukan verifikasi *manual demo* → status invoice terhitung lunas.
8. Masuk sebagai `direktur` → lihat dashboard, report lintas divisi, audit event.
9. Masuk sebagai `mitra` → lihat hanya order mitra; bisa membuat referensi kasus anonim dan membuat order eksternal.

Tambahan: Resepsionis mengusulkan dokter pengganti pada appointment, pasien harus menyetujui. Supervisor Lab dapat mengusulkan keterlambatan, pasien internal atau klinik mitra eksternal yang berwenang harus menyetujuinya.

## Yang SUDAH berfungsi di demo

- Login lokal per pengguna, sesi cookie HTTP-only, CSRF token (in-memory JS), pemeriksaan RBAC + pembatasan tenant pada order.
- Alur klinik → surat kerja → lab intake → supervisor accept/reject → penugasan teknisi + ETA sederhana → tahapan produksi → QC + rework.
- Order dari klinik eksternal terpisah berdasar organisasi; hanya pseudonim kasus, tanpa kontak pasien eksternal.
- Perubahan janji waktu memerlukan respons pihak berwenang; tanggal lama tetap ada sebelum disetujui.
- Appointment klinik, penggantian dokter perlu respons pasien.
- Registrasi pasien internal + preferensi kanal dan frekuensi (verifikasi/consent masih berupa checkbox **simulasi**, tidak boleh digunakan nyata).
- Notifikasi pasien dan mitra via **outbox demo**, bukan WhatsApp/SMS/email live.
- Invoice per order; multi-pembayaran; transaksi yang belum diverifikasi tidak dihitung lunas; pemisahan resepsionis dan FAT.
- Daily Report untuk seluruh divisi awal, dashboard agregat dan audit peristiwa dasar.
- Halaman akses sesuai divisi, navigasi ramah layar kecil.

## Yang BELUM selesai — wajib dikerjakan sebelum implementasi nyata

- **Autentikasi enterprise:** MFA, SSO opsional, pemulihan akun, OTP kontak asli, manajemen session lanjutan, rate limiter terdistribusi.
- **Keamanan data medis:** pemodelan rekam medis lengkap, consent yang sah beserta buktinya, enkripsi dengan key management, audit tahan manipulasi, pemisahan tenant pada tingkat DB, review ancaman dan uji penetrasi.
- **Keuangan:** verifikasi langsung bank/payment gateway/QRIS/EDC; settlement, cash-shift, rekonsiliasi yang dibuktikan, klaim asuransi, skema cicilan dan approval, refund dan pajak.
- **Notifikasi nyata:** koneksi WhatsApp Business API, SMS, email, antrean pesan tahan gangguan, kontrol template, retry, SLA, anti-spam.
- **Estimasi produksi:** saat ini HEURISTIK DEMO, belum pengukuran kapasitas per mesin/teknisi/jenis kasus atau jadwal QC aktual.
- **Integrasi lengkap 12 divisi:** modul CAD/CAM mendalam, HR, pengadaan, gudang, marketing/CS dan operasional klinik lengkap masih roadmap. Setiap divisi tetap dapat login demo dan mengirim Daily Report.
- **Ketahanan sistem:** PostgreSQL, Alembic migrations, test integrasi/beban, worker jobs, observability, disaster recovery, CI/CD, kontrol backup.
- **Kesiapan hukum/klinis Indonesia:** penilaian kepatuhan dan kontrak oleh tenaga profesional dan pihak terkait sebelum go-live.

## Struktur proyek

**Pembaruan 0.2:** tampilan mengikuti logo Naraya, pencarian/filter dan detail order, pemulihan sesi, serta Bantuan dengan asisten mock lalu petugas CS. Backend telah dipisah ke modul domain. Skema menggunakan Alembic dan migrasi demo dijalankan saat startup. Lihat [catatan pembaruan](docs/WORKSPACE_DEMO_0.2.md) dan [alur chat](docs/CHAT_FLOW.mmd).

**Pembaruan 0.3:** struktur 31 jabatan dari bagan, pemetaan akun sesuai fungsi, 32 draf SOP dengan 192 item checklist, lampiran bukti privat, pengajuan/peninjauan oleh orang berbeda, serta unduhan laporan HTML/ZIP dengan bukti dan riwayat. Menu baru: **Struktur organisasi**, **SOP & checklist**, **Laporan & bukti**. Posisi kosong tidak dibuatkan akun otomatis. Lihat [panduan 0.3](docs/WORKSPACE_DEMO_0.3.md), [draf seluruh SOP](docs/SOP_OPERASIONAL_DRAF_1.0.md), [bagan organisasi](docs/ORGANIZATION_DRAFT.mmd), dan [alur laporan](docs/SOP_REPORT_FLOW.mmd).

Untuk mencoba: masuk `it` → SOP & checklist → IT-01 → Buat laporan → isi hasil setiap item → unggah TXT/PDF/foto **fiktif** pada item bukti wajib → Ajukan. Masuk `direktur` → Laporan & bukti → buka laporan → tinjau atau minta perbaikan. Klik **Unduh laporan + bukti** untuk ZIP, ekstrak lalu buka `laporan.html`. Pemeriksa laporan klinis tetap perlu izin order yang sesuai; jabatan atasan tidak menggantikannya. Seluruh SOP masih draf untuk ditelaah pemilik proses.

Paket template kosong: `output/NAM_Draf_SOP_Checklist_dan_Lampiran_1.0.zip`; baca `Panduan_SOP_dan_Lampiran.html` untuk panduan cetak serta lampiran A–D. Regenerasi dengan `python scripts/build_sop_package.py`. Bukti demo belum dienkripsi atau dipindai malware secara menyeluruh; tidak untuk dokumen pasien asli.

Untuk mencoba handoff: masuk sebagai `pasien` → Bantuan → Mulai percakapan → Hubungi petugas. Pada browser/profil lain, masuk sebagai `cs` → Layanan chat → Ambil percakapan → balas. Dua akun yang berbeda perlu browser/profil terpisah agar cookie tidak saling menggantikan. Asisten adalah simulasi lokal, belum model AI eksternal.

```text
backend/app.py                  Perakitan aplikasi, middleware, frontend
backend/models.py              Model data demo
backend/security.py            Autentikasi, otorisasi objek, CSRF
backend/modules/               Router domain, chat, organization, sop_reports
backend/sop_catalog.py         Draf SOP dan aturan checklist berversi
backend/organization_catalog.py Draf jabatan dari bagan
backend/migrations/            Migrasi Alembic 0001–0004
backend/tests/                 Pengujian bisnis, akses, sesi, chat, dan migrasi
frontend/index.html            Shell UI
frontend/app.js                Dashboard antardivisi
frontend/views.js              Halaman ruang kerja
frontend/actions.js            Form dan tindakan workflow
frontend/chat.js               Asisten mock dan layanan CS
frontend/sop.js                Struktur, katalog SOP, laporan dan lampiran
frontend/styles.css            Desain responsive
AGENTS.md                      Aturan kerja untuk Codex
CODEX_START_HERE.md            Instruksi kerja Codex tahap lanjut
docs/FLOWCHART.mmd              Flowchart operasi editabel Mermaid
docs/NAM_DMS_Flowchart.png      Flowchart siap dilihat
docs/NAM_DMS_Flowchart.svg      Flowchart vektor
docs/SECURITY_FLOW.mmd          Flow keamanan role + audit
docs/ERD.mmd                    Relasi data inti
docs/NAM_DMS_Architecture.png   Target arsitektur modular monolith
docs/REFERENCE_SPEC_v0.17.md  Dokumen keputusan Tahap 1–17 sebelumnya
docs/DECISIONS.md              Asumsi, keputusan, eskalasi penting
docs/ROADMAP.md                Daftar pengerjaan menjadi software enterprise
```

## Format proyek

Paket diberikan sebagai source code siap dijalankan, bukan file .exe/APK. Buka folder ini di Codex atau IDE; Codex dapat membaca `AGENTS.md`, menjalankan tes, dan mengembangkan modul sedikit demi sedikit dengan commit, migrasi, serta pengujian.

## Start cepat (tanpa mengetik perintah panjang)

- **Windows:** klik `START_WINDOWS.bat` (memerlukan Python dan koneksi memasang dependensi).
- **macOS/Linux:** jalankan `bash START_MAC_LINUX.sh`.
- Alternatif Docker lokal: `docker compose up --build` dan buka `http://127.0.0.1:8000`.

**Jangan arahkan port demo ke internet publik.** Kata sandi akun simulasi memang dibagikan di dalam proyek.

Portal pasien khusus tersedia di http://127.0.0.1:8000/pasien dengan akun fiktif DEMO-P-001 / DemoNAM2026!. Ruang pegawai di / memakai nama pengguna biasa tanpa daftar akun divisi. Lihat docs/WORKSPACE_DEMO_0.4.md untuk sesi terpisah, chat khusus pasien dan materi pegawai.

