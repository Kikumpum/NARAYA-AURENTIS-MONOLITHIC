# NAM DMS — Decision Register (konsolidasi sampai Tahap 17)

| Tema | Status | Kebijakan kerja |
|---|---|---|
| Struktur organisasi | Draf mengikuti bagan pengguna, 20 Oktober 2026 | Jabatan, akun dan peran dipisahkan; beberapa label/garis belum jelas. Tidak menebak nama pribadi atau membuat login untuk jabatan kosong. |
| Resepsionis menerima pembayaran | Disepakati | Tidak boleh menyetujui penghapusan uang/refund atau merekonsiliasi pembayaran sendiri |
| Metode pembayaran | Disepakati | Cash, QRIS, transfer, debit/EDC, kredit, asuransi/corporate, cicilan (cicilan skema piutang, bukan metode settlement) |
| Split payment | **Rekomendasi teknis**, belum kebijakan final | Invoice 1:N pembayaran, pembayaran aktual satu metode, tetap menunggu verifikasi |
| Approval kredit/DP | **Belum disahkan** | Default aman: approval FAT/manajer sesuai limit, direktur untuk pengecualian |
| Dokter Klinik vs 'Dokter Lab' | Disepakati | 'Dokter Lab' merupakan sebutan internal teknisi/PJ produksi, bukan dokter gigi berizin |
| Penugasan | Disepakati | Semi-otomatis: sistem rekomendasi, resepsionis pilih, PJ Lab konfirmasi |
| Order ditolak | Disepakati | Resepsionis ajukan pengganti, Supervisor Lab approve (implementasi approval reasignment lanjutan) |
| Pergantian Dokter Klinik | Disepakati | Pasien menerima/menolak dokter pengganti sebelum perubahan final |
| ETA Lab | Disepakati | Sistem rekomendasikan berdasarkan beban, Supervisor validasi, resepsionis/CS menginformasikan |
| Keterlambatan | Disepakati | Dampak pada jadwal pasien dan komitmen; notifikasi wajib, perubahan janji perlu approval sah |
| Tanggung jawab setelah surat kerja | Disepakati | Lab tanggung jawab produksi, QC dan komunikasi, bukan diagnosis / keputusan klinis |
| Kontak pasien internal | Disepakati | Front Office verifikasi dan catat izin; sistem Lab komunikasi langsung sesuai preferensi |
| Kanal & frekuensi | Disepakati | Pasien memilih WhatsApp/SMS/email/portal dan tingkat minimal/standar/detail |
| Order Lab | Disepakati | Internal Naraya + eksternal klinik/dokter mitra |
| Komunikasi kasus eksternal | **Asumsi rekomendasi**, user mendelegasikan keputusan standar | Klinik mitra sebagai penerima utama; pasien eksternal hanya setelah otorisasi tertulis & verifikasi sah |
| Struktur teknologi | Rekomendasi engineering | Modular monolith, PostgreSQL, job queues, RBAC multi-tenant, audit log |

## Keputusan penting yang WAJIB diangkat sebelum produksi

1. Struktur badan hukum, cabang/tenant, otoritas data, penanggung jawab klinis dan kontrak pihak mitra.
2. Kebijakan persetujuan DP/cicilan, limit kredit, refund, dan kewenangan FAT/direktur.
3. Pilihan vendor pembayaran dan pesan, verifikasi identitas, dasar hukum/izin komunikasi, retensi data, serta pemeriksaan kepatuhan.

Belum diputuskan ≠ izin untuk mengaktifkan proses produksi. Tetap gunakan demo/sandbox hingga ada keputusan sah.

## Pembaruan demo 0.2 — 19 Oktober 2026

Pengguna meminta tampilan mengikuti logo Naraya, aplikasi yang dikerjakan dengan baik, dan chat yang dilayani asisten terlebih dahulu lalu petugas. Implementasi demo memakai logo transparan, ruang kerja per divisi, dan routing chat ke CS Naraya. Asisten saat ini mock lokal, tanpa koneksi AI eksternal atau pengiriman data pihak ketiga. Petugas harus mengambil percakapan sebelum membaca transkrip. Rincian, bukti uji, dan batasnya ada di `WORKSPACE_DEMO_0.2.md` serta `CHAT_FLOW.mmd`.

Refactor modul mendahului perubahan fungsi dan melewati sembilan tes lama. Skema selanjutnya memakai migrasi Alembic 0001/0002. Tidak ada keputusan go-live, kebijakan komersial, atau izin integrasi provider nyata yang diasumsikan.

## Pembaruan demo 0.3 — 20 Oktober 2026

Pengguna meminta penyesuaian struktur serta seluruh SOP dengan checklist dan lampiran laporan, kemudian mengonfirmasi belum ada SOP resmi dan mengizinkan draf lengkap. Diterapkan 31 jabatan, pemetaan akun sesuai peran, 32 draf SOP / 192 item, bukti privat per item, peninjau berbeda, riwayat pengajuan, dan ekspor laporan berikut lampirannya. Tidak ada nama pribadi yang ditebak. Garis/label yang kurang terbaca ditandai usulan pada struktur.

SOP adalah draf pencatatan operasional untuk ditelaah pemilik proses. Tidak mengesahkan protokol klinis atau kebijakan finansial. Peninjauan laporan tidak menjalankan QC, settlement pembayaran, penghapusan piutang, refund, maupun persetujuan pasien. Hak akses tidak diwariskan dari atasan. Petugas berwenang yang belum tersedia tidak diganti dengan persetujuan otomatis. Rincian: `WORKSPACE_DEMO_0.3.md`.

## Pembaruan demo 0.4 — 20 Oktober 2026

Pengguna meminta portal pasien sepenuhnya terpisah dari akun divisi, lalu membatasi live chat untuk pasien dan meminta materi belajar bagi pegawai. Portal `/pasien` kini memakai bundle, form masuk, sesi audience dan API khusus. Daftar akun di login pegawai dihapus. Live chat personal pegawai/mitra ditolak backend; CS tetap melayani antrean pasien. Materi pegawai berasal dari draf SOP sesuai peran, dengan ringkasan tujuan divisi lain. Tidak ada klaim kelulusan pelatihan atau kewenangan baru. Rincian dan batas kompatibilitas API lama: `WORKSPACE_DEMO_0.4.md`.

## Uji online sementara - 20 Oktober 2026

Pengguna mengoreksi pilihan halaman presentasi: presentasi/PPT tetap lokal, aplikasi ingin diakses online sementara sebelum mempertimbangkan hosting berbayar. Disediakan entrypoint Vercel dan mode demo sementara yang memerlukan kunci akses privat serta masa berlaku. Login pasien/pegawai, RBAC, organisasi, state, CSRF dan audit tidak dilewati. SQLite online hanya scratch per instance; data/sesi dapat ter-reset atau berbeda antar-instance dan tidak menjanjikan demo multiuser yang konsisten. Database lokal maupun DATABASE_URL eksternal tidak dipakai oleh mode ini. Mode produksi dan data nyata tetap diblokir. Rincian: `TEMPORARY_ONLINE_DEMO.md`.

Pengguna kemudian meminta halaman online mempertahankan desain login lokal dan menunjukkan foto desain tersebut. Halaman gerbang putih diganti dengan halaman login asli yang tampil langsung. Kunci demo diminta melalui dialog saat masuk dan ditukar menjadi cookie gerbang bertanda tangan, terpisah dari sesi akun. Allowlist hanya membuka UI login dan aset presentasi; API data serta tindakan bisnis tetap memerlukan gerbang, akun, scope dan state yang sah. Nama akun/divisi tetap tidak ditampilkan pada portal pasien.
