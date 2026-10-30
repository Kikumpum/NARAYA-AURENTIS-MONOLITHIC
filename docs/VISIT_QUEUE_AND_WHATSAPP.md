# Perkiraan kunjungan dan persiapan WhatsApp

30 Oktober 2026. Demo dengan data fiktif, bukan sistem pelayanan produksi. Pengguna meminta perkiraan pasien pertama selesai agar pasien berikutnya bisa mengurangi waktu tunggu, memilih portal dan WhatsApp, lalu menyatakan belum memiliki API WhatsApp dan meminta integrasinya disiapkan dahulu.

## Perkiraan yang ditampilkan

Portal menampilkan jadwal semula, perkiraan mulai, perkiraan selesai, serta selisih mulai dari jadwal. Untuk kunjungan yang belum dimulai, asumsi demo adalah 30 menit. Dokter yang menangani mencatat mulai dan perkiraan durasi 5–180 menit, dapat memperbarui menit tersisa dengan alasan, dan mencatat selesai aktual. Perkiraan berikutnya dihitung dari pelayanan yang sedang berlangsung dan urutan jadwal dokter yang sama. Selesai lebih cepat tidak memajukan perkiraan pasien berikutnya sebelum jadwal semula.

Contoh: jadwal A pukul 09.00 dan B pukul 09.30. Jika dokter memperkirakan A selesai 09.45, B melihat perkiraan mulai 09.45 dan selesai 10.15. Jadwal B semula tetap 09.30; sistem tidak menganggap perkiraan, pesan dibaca atau notifikasi sebagai persetujuan perubahan janji.

Jika perkiraan pelayanan aktif sudah terlewati tanpa pembaruan dokter, waktu berikutnya ditampilkan sebagai perlu konfirmasi. Sistem tidak mengakhiri pelayanan atau membuat hitung mundur fiktif secara otomatis. Kunjungan lama yang belum dimulai perlu keputusan petugas; penandaan tidak hadir diperbolehkan setelah waktu jadwal, oleh resepsionis atau dokter terkait. Kunjungan yang sudah diproses tidak dapat dibatalkan mandiri atau dipindahkan dokternya.

Pasien hanya menerima perkiraan kunjungannya sendiri, tanpa nama, nomor antrean, tindakan, diagnosis, atau ID pasien sebelumnya. Pembaruan rutin portal mengikuti interval 30 detik dan tombol Perbarui yang sudah ada. Ini perkiraan berdasarkan jadwal dan pencatatan petugas; belum mencakup triase, prioritas darurat, waktu check-in, jeda dokter, atau model durasi per tindakan. Konfirmasi kedatangan tetap melalui petugas; tidak ada jaminan bebas menunggu.

## Kewenangan dan riwayat

Backend memeriksa audience/CSRF, organisasi, hubungan dokter dengan kunjungan, status janji dan tahap pelayanan. Hanya dokter yang menangani boleh memulai, mengubah perkiraan atau menyelesaikan. Resepsionis boleh mencatat tidak hadir, bukan mengisi waktu tindakan klinis. Peninjauan laporan SOP tidak menyelesaikan kunjungan. Row lock pasien/dokter dan receipt idempotensi melindungi aksi paralel. PostgreSQL memakai NO KEY UPDATE agar foreign key notifikasi tidak menyebabkan deadlock dengan penulis pasien lain.

Perubahan menyimpan alasan, waktu semula, perkiraan terakhir, waktu mulai/selesai aktual dan revisi melalui audit. Kabar layanan privat dibuat untuk kunjungan terkait yang perkiraannya berubah. Pesan tidak menyertakan alasan internal petugas atau informasi pasien lain. Kabar dari permintaan GET tidak menciptakan pengiriman eksternal.

## Laporan

Menu Pasien & jadwal mempunyai unduhan CSV per tanggal. Dokter hanya mengekspor penugasannya sendiri; resepsionis dan direktur sesuai organisasi. Kolom: ID kunjungan, jadwal UTC, mulai UTC, selesai UTC, selisih mulai dari jadwal, durasi aktual dan status. Durasi kosong jika kunjungan belum selesai. Selisih mulai dari jadwal bukan pengukuran waktu tunggu sejak kedatangan, karena check-in belum dicatat. Nama pasien tidak dimasukkan ke CSV. Ekspor dicatat audit.

## WhatsApp: disiapkan, belum mengirim

Nomor pengirim/API/provider belum ada. Tidak ada token yang diminta melalui chat, akun provider yang dibuat, biaya yang diaktifkan, atau panggilan jaringan WhatsApp. Integrasi tahap ini menyediakan outbox persisten yang terhubung ke kabar kunjungan, draf template, status konfigurasi, akses petugas dan deduplikasi. **Bukan implementasi pengiriman Cloud API yang sudah aktif.**

Outbox dibuat hanya untuk pasien internal yang memilih WhatsApp, kontak terverifikasi dan izin layanan tercatat. Preferensi minimal tidak menghapus kabar penting tentang waktu pelayanan. Pesan tetap tampil di portal. Outbox berstatus `awaiting_configuration`, dengan constraint database yang tidak mengizinkan penandaan terkirim. Klinik mitra tidak dilewati untuk menghubungi pasien eksternal. IT melihat kebutuhan konfigurasi tanpa membaca antrean pesan pasien. Resepsionis dapat melihat draf dari menu Persiapan notifikasi WhatsApp.

Draf template utilitas: `nam_visit_estimate_update`, bahasa Indonesia. Usulan teks untuk ditelaah dan diajukan ke provider:

> Informasi kunjungan Naraya Aurentis: perkiraan mulai {{1}}, perkiraan selesai {{2}}. Waktu dapat berubah. Silakan periksa portal atau hubungi klinik sebelum menyesuaikan kedatangan. Tidak perlu membalas dengan data medis.

Sebelum mengaktifkan pengiriman: pilih Meta Cloud API atau provider resmi, siapkan akun/nomor pengirim, template yang disetujui, secret environment, kontak uji dan izin penerima yang tervalidasi. Implementasikan adapter pengiriman, pemroses outbox, validasi ulang consent/kontak/tenant/status kunjungan sesaat sebelum kirim, supersession pesan lama, penanganan hasil ambigu tanpa retry buta, serta webhook autentik untuk sent/delivered/read/failed. Balasan diterima atau dibaca tidak menyetujui perubahan jadwal. Kesepakatan biaya dan pengujian nomor terotorisasi perlu diselesaikan sebelum aktivasi; status draft tidak boleh ditampilkan sebagai delivered.

Referensi primer: [WhatsApp Business Platform](https://whatsappbusiness.com/products/business-platform/) menjelaskan integrasi langsung/mitra, template yang disetujui dan notifikasi janji. Detail adapter belum dipilih sampai layanan tersedia.

## Migrasi dan verifikasi

Alembic 0006 menambahkan `visit_timings` dan `whatsapp_outbox`, tanpa mengubah jadwal lama. Migrasi memakai koneksi langsung demo yang sama, kueri aplikasi tetap pooled. Uji 0005→0006 dua kali, preservasi data, concurrency, receipt, laporan dan selesai aktual berhasil pada schema PostgreSQL terisolasi; schema uji dihapus, schema live tidak diubah oleh tes tersebut. Tes backend mencakup peran, tenant, status, privasi, prediksi terlambat/kedaluwarsa, idempotensi, benturan dokter, pembatalan/penggantian yang diblokir dan outbox tanpa kirim.
