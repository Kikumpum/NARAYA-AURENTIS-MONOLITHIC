# AGENTS.md — Panduan pengembangan NAM DMS untuk Codex

## Mandat

Bangun **Naraya Aurentis Monolithic Dental Management System** sebagai sistem multi-divisi aman, mobile-friendly, terintegrasi penuh antara Klinik internal, Lab internal, Klinik mitra eksternal, Finance/FAT, QC dan divisi lainnya. Gunakan Bahasa Indonesia untuk antarmuka bisnis. Proyek saat ini adalah **demo lokal saja**.

## Non-negotiable safety rules

1. **JANGAN** menganggap aplikasi ini siap production atau memasukkan data pasien asli.
2. JANGAN mengizinkan resepsionis mengubah diagnosis/instruksi klinis dokter, meloloskan QC, memverifikasi penerimaan uangnya sendiri, atau menyetujui penghapusan piutang.
3. JANGAN mengizinkan IT admin otomatis membaca data medis; semua akses pasien berbasis kebutuhan minimum dan tenant organisasi.
4. Untuk setiap fitur baru, periksa role, scope organisasi, hubungan dengan order dan status workflow **pada backend**, bukan sekadar menyembunyikan tombol.
5. Untuk order internal, komunikasi progres dan delay adalah tanggung jawab Lab sesudah serah terima; tindakan klinis tetap tanggung jawab dokter gigi yang sah.
6. Untuk order eksternal, klinik mitra menjadi penerima utama; komunikasi langsung ke pasien baru diaktifkan setelah kontrak, otorisasi klinik mitra, verifikasi kontak, izin dan aturan privasi tervalidasi.
7. Jangan menandai pembayaran QRIS/transfer/kartu sukses hanya karena screenshot. Dalam demo, FAT boleh memverifikasi **simulasi manual**, tetapi fitur ini harus diblokir/diganti sebelum go-live.
8. Jika tanggal yang dijanjikan berubah, simpan tanggal semula dan usulan; tidak boleh menganggap pesan dibaca sebagai persetujuan.
9. Log kejadian penting dan alasan perubahan; jangan menghapus riwayat pembayaran, penerimaan order, penolakan, revisi ETA, persetujuan.
10. Pilihan frekuensi notifikasi pasien (minimal/standar/detail) tidak menghapus kewajiban komunikasi layanan yang sah.
11. Setiap penambahan modul wajib disertai test RBAC/tenant leakage, workflow state, idempotency dan audit.
12. Bekerja secara inkremental. Jangan melemahkan kontrol hanya agar demo berhasil.

## Codebase

- FastAPI + SQLAlchemy + SQLite saat demo; target modular monolith + PostgreSQL + Alembic di enterprise.
- `backend/app.py` monolit awal sengaja disediakan agar runnable. Refactor ke package modules (`auth`, `clinic`, `lab`, `finance`, `communication`, `operations`, `audit`) terlebih dahulu **tanpa mengubah perilaku**, lalu tambahkan migrasi.
- Frontend HTML/CSS/JS tanpa build step; untuk produk riil boleh dipertimbangkan Next.js/React apabila ada alasan UX dan biaya maintain yang jelas.
- Source of truth bisnis: `docs/REFERENCE_SPEC_v0.17.md`, percakapan user tahap berikutnya, `docs/DECISIONS.md`.

## Definition of Done untuk fitur

- API dan UI berjalan pada HP/laptop.
- Data valid dan hanya tersimpan pada tenant berwenang.
- Pemeriksaan backend role + object scope + transisi state.
- Pencatatan audit untuk aksi sensitif.
- Test otomatis positif dan negatif; `python -m pytest -q backend/tests` lulus.
- Dokumentasi dan diagram diperbarui.
- Tidak menggunakan layanan pihak ketiga sungguhan tanpa kredensial yang diberikan secara aman dan persetujuan user.
- Keterbatasan secara jelas diberi label demo/beta/siap produksi, berdasarkan bukti verifikasi.

## Cara menjalankan

Ikuti `README.md`. Gunakan `python -m pytest -q backend/tests` untuk tes. Lihat `CODEX_START_HERE.md` untuk daftar tugas prioritas.
