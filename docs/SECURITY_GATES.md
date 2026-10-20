# SECURITY GATES — WAJIB LULUS SEBELUM PRODUKSI

> **Status keseluruhan: BLOCKED.** Prototipe ini tidak boleh menerima data kesehatan maupun transaksi sungguhan.

## Gate P0 — keamanan & privasi

- [ ] Nonaktifkan seed data dan akun demo, larang login dengan password bersama di deployment nyata.
- [ ] MFA untuk admin, FAT, direktur dan approver; kebijakan identitas pasien; login rate limiting terdistribusi.
- [ ] CSRF yang aman dengan sesi persisted frontend atau server-side session bootstrap; session rotation, revoke-all, secure HTTPS/TLS everywhere.
- [ ] Uji IDOR / RBAC / row-level tenant isolation pada **semua** endpoint termasuk export, audit, media dan background jobs.
- [ ] Enkripsi data sensitif at-rest + in-transit, key management, tokenisasi data yang memungkinkan, audit akses medis.
- [ ] Manajemen consent pasien sah, identitas, OTP/konfirmasi kontak asli, pengelolaan pencabutan izin.
- [ ] PostgreSQL RLS (atau enforcement terpercaya dan diuji), backup terenkripsi, restore drill, retention policy.
- [ ] Audit log append-only/tamper-evident pada storage terpisah dengan alert aktivitas mencurigakan.
- [ ] Penerapan security headers, CSP lengkap sesuai app nyata, secret vault, scanning dependency/SAST/DAST.
- [ ] Pentest independen dan threat model lintas peran/mitra, insiden respons, owner keamanan, SOP akses darurat.
- [ ] Peninjauan kewajiban data pribadi, kerahasiaan medis, penyelenggaraan layanan kesehatan dan rekam medis oleh profesional yang berwenang di Indonesia.

## Gate P0 — integritas klinis & keuangan

- [ ] Dokter berizin memvalidasi surat kerja/instruksi klinis, electronic signature sesuai kebutuhan kebijakan medis.
- [ ] QC teknis independen, rincian remake dan traceability material batch, complaint handling, recall workflow.
- [ ] Settlement QRIS/transfer/kartu hanya dari gateway/bank tepercaya; jangan dari screenshot atau tombol 'manual demo verification'.
- [ ] Closing kas per shift, bukti setoran, rekonsiliasi bank, piutang, insentif, pajak dan audit keuangan.
- [ ] Kebijakan DP/cicilan/refund/credit limit diputuskan bersama pengelola dan FAT.
- [ ] Transaksi idempotent, constraint DB, locking/concurrency pada slot dokter, stok, pembayaran, order dan ETA.
- [ ] Integrasi sender WA Business/SMS/email tersertifikasi, template minimal data, outbox dengan retries & delivery receipts yang benar.

## Known limitations PROTOTIPE saat ini

- Demo 0.3 memiliki jabatan/pemetaan akun dan SOP/laporan berbukti dengan scope, versi, audit, idempotensi dan peninjau berbeda. Struktur dan SOP tetap draf; persetujuan laporan tidak menjalankan persetujuan bisnis atau klinis.
- Lampiran disimpan sebagai blob DB privat dan hanya diunduh setelah otorisasi. Pembatasan format/ukuran serta fitur aktif dasar belum menggantikan antivirus, CDR, object storage terenkripsi, pengelolaan kunci dan retensi sebelum go-live.

- Backend telah dipisah ke modul domain dan memakai Alembic 0001–0004. Migrasi/seed otomatis saat startup masih khusus demo lokal.
- Demo 0.4 memisahkan sesi dan API pasien, meminimalkan serializer pasien termasuk API kompatibilitas, membatasi percakapan personal kepada pasien, serta menyediakan materi pegawai sesuai peran. Semua ini belum merupakan izin penggunaan data nyata.
- Demo SQLite; tidak ada row-level DB isolation atau proteksi untuk admin DB.
- Pemakaian checkbox sebagai pernyataan verifikasi/consent; **belum melakukan verifikasi sungguhan**.
- Satu kata sandi untuk semua akun fiktif; semua password hash menggunakan PBKDF2 pada demo.
- Sesi dapat dipulihkan setelah refresh melalui endpoint terautentikasi dan token CSRF per sesi. MFA, revoke-all, dan pengelolaan sesi enterprise tetap belum tersedia.
- ETA adalah heuristik kasar, belum kalkulasi jadwal produksi yang benar.
- Notifikasi **queue only**; tidak pernah dikirim kepada pasien.
- Manual demo verification untuk pembayaran belum memeriksa bank/settlement.
- Audit hanya tabel DB biasa (belum tahan manipulasi administrator database).
- Registrasi pasien internal masih menerima data dari resepsionis tanpa bukti OTP.
- CAD/CAM, perawat, HR, pengadaan, gudang dan marketing memiliki draf SOP/checklist serta laporan berbukti; transaksi khusus divisi belum lengkap. CS memiliki antrean chat dengan penugasan petugas.
- Asisten chat memakai mock lokal. Provider AI, batas pemrosesan data, retensi pesan dan evaluasi jawaban belum disahkan untuk penggunaan nyata.
- Semua tindakan bisnis kritis memerlukan uji threat modeling dan validasi alur riil.

## Bukti uji minimal

`python -m pytest -q backend/tests` dan test suite lanjutan + load tests + pentest report + sign-off legal/klinis/FAT.
