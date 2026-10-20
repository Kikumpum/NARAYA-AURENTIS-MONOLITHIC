# Portal pasien: jadwal dan pengerjaan terhubung

Pembaruan 20 Oktober 2026. Seluruh akun, jadwal, order dan pesan adalah data latihan. Tidak ada aktivasi layanan pasien nyata atau paket berbayar.

## Pengalaman pasien

Login utama tetap netral bagi pasien dan karyawan. Setelah masuk, pasien membuka portal tersendiri: logo transparan menyatu pada kepala halaman hijau, latar krem, kunjungan berikutnya, tahapan pengerjaan dan kotak pemberitahuan. Tidak ada daftar akun divisi atau navigasi pegawai.

Kategori contoh yang disetujui pemilik: Behel, Scaling, Perawatan Gigi Harian. Kartu katalog mengarahkan pasien ke konsultasi. Merek sponsor, produk komersial, harga dan klaim manfaat belum ditetapkan. Nama dokter yang tampil adalah identitas fiktif. Tidak dibuat identitas dokter Lab yang belum ditetapkan.

## Aturan jadwal

- Jadwal mandiri memakai asumsi demo: besok sampai 30 hari ke depan, pukul 09.00–17.00 WIB, slot 30 menit. Jam pelayanan riil belum ditetapkan.
- Waktu disimpan UTC dan ditampilkan WIB. Kunjungan lama dianggap berdurasi 30 menit untuk pemeriksaan benturan.
- Dokter harus aktif, berada dalam organisasi pasien dan mempunyai shift tersedia. Pasien maupun dokter tidak dapat memiliki dua kunjungan bertumpang tindih; calon pengganti yang menunggu persetujuan juga dicadangkan.
- Kunjungan terkait order hanya menerima order internal milik pasien dalam organisasi yang sama, bersama dokter klinik yang menangani order tersebut.
- Pemasangan hasil Lab membutuhkan status `ready`, setelah QC. Konsultasi dan kontrol dapat dibuat selama pengerjaan. Pasien tidak mengubah instruksi klinis, produksi atau QC.
- Pembatalan mandiri hanya untuk kunjungan mendatang milik pasien. Alasan dan audit disimpan, slot dibuka kembali. Pembatalan tidak menghapus order atau riwayat.
- Resepsionis dan pergantian dokter memakai pemeriksaan benturan yang sama. Grid/jam mandiri tidak dipaksakan pada kunjungan lama atau input resepsionis.
- PostgreSQL memakai row lock pasien dan dokter/shift; SQLite memakai transaksi penulis. Receipt mencegah duplikasi pengiriman ulang. Kesalahan kunci yang sama dengan isi berbeda ditolak.

## Progres dan pemberitahuan

Tahapan berasal dari order yang sama dengan ruang kerja klinik dan Lab: permintaan, diterima, desain, pengerjaan, penyelesaian, QC, siap diserahkan. Status perbaikan atau penolakan dijelaskan tanpa mengklaim persentase selesai. Dokter klinik menangani tindakan klinis, tim Lab menyampaikan progres setelah serah terima. Riwayat memakai label layanan yang diizinkan; instruksi medis, catatan internal, identitas teknisi dan audit mentah tidak dibuka.

Kotak pesan menggabungkan kabar layanan dan kunjungan. Filter: semua, belum dibaca, jadwal, pengerjaan dan perlu keputusan. Status dibaca per akun idempotent dan diaudit. Membaca pesan tidak menyetujui tanggal baru atau dokter pengganti; pasien harus memilih setuju/tolak secara eksplisit. Filter keputusan menautkan ke keadaan layanan terkini.

Kabar Lab memakai pemeriksaan persetujuan/kontak yang sudah ada. Preferensi minimal menekan kabar produksi rutin, bukan kabar penting. Order eksternal tetap mengirim kabar ke klinik mitra, bukan langsung ke pasien mitra. Kabar jadwal baru bersifat privat di portal, tanpa WhatsApp/SMS/email nyata. Chat asisten tetap simulasi lokal dan dapat diteruskan ke CS.

Beranda memperbarui data setiap 30 detik ketika terlihat dan tidak sedang mengisi dialog/chat. Rincian layanan dapat diperbarui melalui tombol Perbarui; formulir pemesanan dan draf chat tidak direset oleh penyegaran otomatis.

## Penyimpanan dan verifikasi

Migrasi `0005` menambah `patient_visit_details`, `patient_updates`, `patient_notice_reads`. Tabel kunjungan/pemberitahuan lama tidak diganti. Startup bersama memakai koneksi langsung `NAM_DEMO_DATABASE_URL_UNPOOLED` dengan TLS yang cocok dengan database/akun/host pooler khusus demo. Kueri aplikasi tetap melalui pooler; tidak ada URL operasional umum yang dibuka.

Seluruh 248 tes backend lulus. Cakupan baru: audience/CSRF, tenant/kepemilikan, shift/waktu, benturan termasuk resepsionis/pengganti, concurrency, idempotensi/audit, pembatalan, syarat QC dan read-state terpisah dari persetujuan. Migrasi 0004→0005, preservasi data, concurrency, pembatalan dan read-state juga berhasil pada schema PostgreSQL sementara yang kemudian dihapus. Pengujian migrasi tersebut tidak mengubah schema/data aplikasi online.

Diagram: [PATIENT_CARE_FLOW.mmd](PATIENT_CARE_FLOW.mmd).
