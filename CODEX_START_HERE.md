# Instruksi awal kepada Codex

**Tujuan:** lanjutkan implementasi NAM DMS dari prototipe demo menjadi produk enterprise terintegrasi yang dapat dievaluasi secara aman, bukan langsung di-deploy dengan data nyata.

**Prompt untuk Codex (salin):**

> Baca README.md, AGENTS.md, docs/DECISIONS.md, docs/SECURITY_GATES.md, docs/ROADMAP.md, dan docs/REFERENCE_SPEC_v0.17.md sebelum mengubah kode. Jadikan proyek NAM DMS sebagai modular monolith yang scalable. Jalankan pengujian awal, inventarisasi gap antara kode demo dan spesifikasi, kemudian kerjakan milestone P0 dari ROADMAP bertahap: refactor struktur modul tanpa mengubah fungsionalitas, PostgreSQL dan Alembic migrations, central authorization RBAC + tenant-scope + tests, manajemen sesi dan MFA, audit trail yang lebih kuat, consent dan contact verification nyata, transaksi keuangan dan sistem notifikasi dengan outbox yang handal (tetap gunakan provider mock dulu), lalu implementasi klinik/lab/finance/HR/gudang per milestone. Gunakan data sintetis dan jangan mengklaim siap produksi sebelum SECURITY_GATES.md lulus. Kerjakan satu milestone per perubahan teruji, catat alasan keputusan dan uji regresi. Berikan daftar kebutuhan yang benar-benar memerlukan persetujuan direktur, jangan menanyakan hal teknis standar.

## Prioritas pertama yang aman

1. Jalankan `python -m pytest -q backend/tests` (seluruh tes harus lulus).
2. Jalankan server lokal, cek login setiap role, tes tidak ada akses silang klinik mitra.
3. Ekstrak API/model/service ke modul sesuai domain sambil mempertahankan semua tests.
4. Perluas test keamanan: role matrix penuh, IDOR pada semua endpoint, CSRF/session, multitenant, concurrency, malicious input.
5. Migrasikan ke PostgreSQL + Alembic; pindahkan seed demo ke command eksplisit, bukan startup otomatis.
6. Bentuk design system mobile-first: antrean role-specific, cari order, detail order dengan activity log dan due-date impact.
7. Implementasikan semua milestone berikutnya di `docs/ROADMAP.md`.

## Hal yang tidak boleh diputuskan sendiri sebelum go-live

- Identitas badan hukum dan cabang yang memegang rekam medis/transaksi.
- Kebijakan batas kredit/cicilan, penghapusan piutang, refund, pajak dan otorisasi nominal.
- Sumber pembuktian verifikasi penerimaan uang (bank/gateway provider asli).
- Penggunaan kanal pesan pihak ketiga, kontrak, pengolahan data pribadi, masa retensi dan izin pasien.
- Finalisasi kebijakan klinis oleh dokter gigi penanggung jawab dan review kepatuhan.

Semua item lain dapat diterapkan berdasarkan rekomendasi profesional, ditandai sebagai **asumsi sementara** dan diuji sebelum rilis.
