# NAM DMS 0.3 — Struktur, SOP dan laporan berbukti

20 Oktober 2026. Demo lokal dengan data fiktif. Pengguna mengizinkan penyesuaian bagan dan meminta draf lengkap karena belum ada SOP resmi.

## Yang tersedia

- 31 jabatan: jenjang Komisaris, Direktur Utama, Direktur, Operation, kepala unit dan fungsi pendukung. Nama pribadi tidak ditranskripsi dari gambar kecil. Akun lama dipetakan sebagai **akun latihan**, bukan penetapan pegawai. Tidak ada akun baru otomatis untuk posisi kosong.
- Direktur/HR dapat memetakan akun aktif ke jabatan dengan peran yang kompatibel. Alasan, pemeriksaan versi dan audit wajib. Jabatan tidak menaikkan izin aplikasi.
- 32 draf SOP, 192 item pemeriksaan. Mencakup pengawasan/direksi, operasional/cabang, bisnis/corporate, HR, GA/housekeeping, IT, FO, Klinik/Perawat, penerimaan Lab, produksi, CAD/CAM, QC, ETA, serah terima, FAT/rekonsiliasi/pengecualian, Insurance, Procurement, Gudang, CS, komunikasi, keluhan, pemasaran/editor/sales dan insiden.
- Hasil checklist: belum diperiksa, sesuai, ada temuan, atau tidak relevan jika SOP mengizinkan. Temuan membutuhkan uraian, tindakan, penanggung jawab dan tenggat. N/A memerlukan alasan.
- Bukti PDF/PNG/JPG/TXT dikaitkan dengan item. Maksimal 3 MB per berkas, 8 berkas / 15 MB aktif per laporan. Isi dasar dan nama berkas diperiksa. Berkas disimpan privat dalam DB demo, bukan pada direktori static. Unduhan selalu attachment, nosniff dan sandbox.
- Alur draf → diajukan → ditinjau / perlu perbaikan. Peninjau harus orang berbeda dan mempunyai peran peninjauan SOP. Jika petugas sah belum tersedia, laporan tetap menunggu; tidak ada persetujuan otomatis atau pengganti kewenangan.
- Snapshot SOP, pengajuan, peninjauan serta daftar hash bukti dipertahankan. Lampiran yang dilepas dari revisi berikutnya tetap dapat diunduh oleh petugas berwenang jika pernah menjadi bukti pengajuan.
- Ekspor HTML untuk cetak dan ZIP berisi laporan.html, lampiran, riwayat.json, petunjuk. Batas arsip riwayat 30 MB. Laporan lama tetap tersedia pada bagian catatan sebelumnya.
- Katalog SOP dapat diunduh dari menu. Paket template kosong di `output/NAM_Draf_SOP_Checklist_dan_Lampiran_1.0.zip`; regenerasi dengan `python scripts/build_sop_package.py`.

## Akses dan workflow

Backend memeriksa peran, tenant dan pemilik/pemeriksa pada **daftar, detail, perubahan, lampiran, riwayat dan ekspor**. Order terkait harus masuk lingkup tugas; Supervisor harus PJ, Teknisi harus teknisi yang ditugaskan, QC tidak boleh menjadi teknisi pembuat. Tahap order diperiksa saat pembuatan dan pengajuan. Hilangnya penugasan mencabut akses ke isi dan lampiran laporan terkait.

Draf hanya milik penyusun. Setelah pengajuan, peninjau sesuai SOP dapat membaca isi jika lingkup order juga mengizinkan. Manajemen yang tidak memiliki izin isi menerima metadata status tanpa ringkasan, identitas pasien, order, hasil checklist atau bukti. IT tidak mendapat akses laporan medis atau transkrip karena posisinya.

Kunci idempotensi disimpan bersama hasil transaksi. Kunci sama untuk isi berbeda ditolak. Versi laporan/pemetaan diperiksa secara atomik agar penyimpanan dari form lama tidak menimpa versi baru. Audit mencatat perubahan, peninjauan, akses detail, unduhan, dan ekspor tanpa menyalin isi bukti ke log.

## Draf yang perlu ditelaah

Garis pelaporan Auditor, label IC/GA dan Branch Head serta dukungan bersama merupakan pemetaan sementara. Satu kotak penasihat pada gambar belum terbaca. Lihat catatan pada menu Struktur organisasi. Tidak ada nama pribadi yang ditebak.

SOP di sini adalah prosedur **pencatatan dan pemeriksaan operasional**, bukan protokol diagnosis, terapi, sterilisasi, kriteria teknis medis final atau pengesahan regulasi. Pemilik proses dan penanggung jawab klinis/FAT perlu menelaah dan mengesahkan sebelum penggunaan nyata. Peninjauan laporan tidak meluluskan QC, memverifikasi pembayaran, memberi kredit/refund, menghapus piutang, menandatangani surat klinis atau menyetujui perubahan janji.

Modul HR, CAD/CAM, Gudang, Procurement, Marketing, fasilitas dan Insurance kini memiliki checklist laporan, tetapi transaksi operasional khususnya (stok/PO/payroll/klaim/dll.) belum menjadi modul lengkap. Chat tetap asisten mock lokal. Verifikasi bank dan kanal pesan eksternal tetap belum aktif.

## Penyimpanan dan migrasi

Alembic 0003 menambah tabel jabatan, pemetaan akun, laporan SOP, snapshot, bukti privat dan tanda terima idempotensi. Data order, pengguna, pembayaran, chat serta laporan lama tidak dihapus. Demo tetap SQLite; bukti belum terenkripsi, pemindaian malware menyeluruh belum tersedia, audit belum immutable. Tidak untuk data pasien atau transaksi nyata.

## Verifikasi

- Regresi awal: 52 tes lulus.
- Tes baru: 38 tes lulus.
- Seluruh suite: 90 tes lulus, 1 peringatan deprecation Starlette/httpx yang sudah ada.
- Cakupan: RBAC semua akun internal, tenant palsu, order/penugasan/tahap, draf privat, metadata manajemen, peninjau berbeda, field palsu, bukti wajib, ukuran/format/nama berkas, unduh privat, idempotensi mutasi, konflik edit bersamaan, snapshot dan bukti versi lama, audit dan ekspor HTML/ZIP.

Diagram: `ORGANIZATION_DRAFT.mmd`, `SOP_REPORT_FLOW.mmd`. Katalog sumber: `backend/sop_catalog.py`.

Uji browser: ukuran laptop 1440×1000 dan HP 390×844. Daftar laporan, form checklist, menu HP dan struktur tidak memiliki overflow halaman. Laporan SOP-00001 disusun IT Demo, memakai satu item temuan dengan PJ/tenggat, satu N/A beralasan, bukti TXT sintetis, kemudian diajukan dan ditinjau Direktur Demo. Temuan restore tetap terbuka; peninjauan hanya atas laporannya. ZIP hasil unduhan tersedia di `output/Contoh_Laporan_SOP_00001_dan_Bukti.zip`.
