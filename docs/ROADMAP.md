# ROADMAP — dari Prototipe menuju NAM DMS Enterprise

**Kriteria rilis: bukan sekadar tampilan bagus — hak akses, integritas workflow, kepatuhan dan keamanan harus dapat diuji.**

## Milestone 0 — Selesai sebagai prototipe lokal

- [x] FastAPI + SQLAlchemy API, web responsive, akun fiktif per role.
- [x] Order internal/eksternal, surat kerja, Lab queue, konfirmasi penugasan, ETA dasar, produksi, QC, rework.
- [x] Dokter pengganti perlu persetujuan pasien, revisi due date perlu persetujuan penerima yang sah.
- [x] Klinik mitra scoped per organisasi, informasi klinis minimal, portal pasien dasar.
- [x] Invoice & penerimaan yang menunggu FAT, Daily Report lintas divisi, audit event dasar.
- [x] Flowchart SVG/PNG/Mermaid dan acceptance test awal.

## Milestone 1 — Pondasi enterprise (P0)

Kemajuan demo 0.2: router domain sudah dipisahkan dari app utama, SQLite memakai migrasi Alembic 0001/0002, sesi pulih setelah refresh, dan chat memakai scope serta penugasan petugas. Suite saat ini memiliki 52 tes lulus. PostgreSQL, IAM enterprise, audit immutable dan security gates tetap belum selesai. Lihat `WORKSPACE_DEMO_0.2.md`.

- [ ] Modularisasi FastAPI (`modules/auth`, `clinic`, `lab`, `finance`, `inventory`, `hr`, `notification`, `audit`).
- [ ] PostgreSQL, migrations Alembic, transactions row locks + idempotency, typed repositories.
- [ ] IAM: roles/permissions yang tersimpan di DB, object-level grant, data ownership multi-tenant, secret management dan MFA.
- [ ] Keamanan consent, kontak, OTP, sesi, audit immutable, pengetesan semua endpoint dan review kepatuhan.
- [ ] CI/CD test lintas role + API lint + dependency scanning.

## Milestone 2 — Klinik dan pasien

- [ ] Registrasi/rekam medis sesuai peraturan relevan, appointment kapasitas slot, dokter/assistant/perawat, riwayat tindakan dan rujukan Lab.
- [ ] Form surat kerja digital tervalidasi dokter gigi, lampiran terbatas dan revision history.
- [ ] Portal pasien aktif dengan consent, konfirmasi dokter pengganti, persetujuan perubahan komitmen.
- [ ] Alur penyerahan hasil Lab ke klinik/pasien, pelacakan fitting dan remake.

## Milestone 3 — Dental Lab produksi lengkap

- [ ] Lead assignment dengan approval reassign Supervisor (saat ini belum lengkap).
- [ ] Workstation dan teknisi CAD/CAM, mesin, bahan, batch, dental shades, scan/assets per kasus, QC checklist.
- [ ] ETA engine berdasarkan jam kerja, waktu proses standar tiap produk, resource capacity, material/holiday, prioritas dan SLA.
- [ ] Prioritas kasus pasien dengan jadwal pemasangan; kategori keterlambatan normal/perhatian/kritis, eskalasi.
- [ ] Order mitra, kontrak, tarif B2B, portal dan notifikasi + izin komunikasi pasien jika disepakati.

## Milestone 4 — Finance/FAT enterprise

- [ ] Pricing, tarif, DP, split tenders, skema cicilan (approval kredit), rekonsiliasi cash shift, insurance claims, corporate billing, aging piutang.
- [ ] Gateway settlement dan webhooks idempotent, EDC/QRIS, refund reversal dengan 4-eyes approval, pajak dan laporan akuntansi.
- [ ] Pemisahan pendapatan eksternal vs alokasi biaya internal/antarentitas; anti double count.

## Milestone 5 — Seluruh divisi & laporan

Demo 0.3 menambahkan struktur jabatan, draf SOP/checklist lintas divisi, bukti privat dan laporan berversi dengan peninjauan serta ekspor. Ini belum menggantikan transaksi stok, PO, payroll, klaim, pengesahan SOP atau IAM enterprise. Bukti uji dan batas: `WORKSPACE_DEMO_0.3.md`.

- [ ] Gudang/inventaris, purchasing, approval PR/PO, expired stocks, traceability.
- [ ] HR/GA: absensi, shift, kapasitas, cuti, kompetensi teknisi/dokter, training.
- [ ] Marketing/CS: case-based ticketing, CRM dengan consent terpisah.
- [ ] Daily report otomatis per divisi plus formulir khusus, pengingat, supervisor approval, KPI historis.
- [x] Draf checklist SOP, lampiran per item, peninjau berbeda, snapshot pengajuan dan unduhan laporan/bukti pada demo lokal.
- [ ] Dashboard direktur multi-cabang; ekspor laporan sesuai kewenangan dan audit.

## Milestone 6 — Production readiness

- [ ] Gate keamanan `SECURITY_GATES.md` seluruhnya lulus dengan bukti.
- [ ] UAT tenaga klinis/lab/FAT, DR test, training semua divisi, SOP incident response.
- [ ] Rollout bertahap dengan data migrasi tervalidasi, audit dan pemantauan.
