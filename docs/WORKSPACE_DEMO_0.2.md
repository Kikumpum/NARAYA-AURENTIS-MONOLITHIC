# NAM DMS 0.2 — ruang kerja dan bantuan layanan

Tanggal: 19 Oktober 2026. Seluruh contoh memakai data fiktif. Status tetap demo lokal.

## Tampilan dan pemakaian

- Logo asli pengguna tersimpan di `frontend/assets/naraya-aurentis-logo.png`. Adaptasi transparan di `naraya-aurentis-transparent.png` mempertahankan susunan identitas dan menghilangkan latar kotak. Warna aplikasi mengikuti hijau gelap, arang, dan emas logo.
- Dashboard menampilkan angka dari API sesuai peran. Tidak ada tren atau persentase rekaan.
- Daftar order mendukung pencarian lokal pada data yang sudah lolos otorisasi server, filter sumber/status, dan urutan komitmen terdekat.
- Detail order memisahkan komitmen, estimasi, instruksi yang boleh dibaca, serta riwayat layanan. Tindakan tampil sesuai tahap dan peran. API tetap memeriksa kewenangannya.
- Sesi dapat dipulihkan sesudah muat ulang. Token CSRF diturunkan dari rahasia sesi dan hanya berada dalam memori browser. Cookie sesi tetap HttpOnly dan SameSite Strict.
- Form menahan pengiriman ganda selama permintaan berjalan dan menampilkan kesalahan server. Dialog menggunakan pengelolaan fokus bawaan browser.

## Bantuan asisten lalu petugas

1. Pengguna masuk, membuka Bantuan, dan memilih pertanyaan umum atau order yang boleh diakses.
2. Percakapan dimulai pada status `assistant`. Provider saat ini adalah **mock lokal berbasis jawaban layanan**, belum model bahasa AI sungguhan.
3. Asisten menjelaskan proses layanan atau membaca status minimal order yang terikat. Asisten tidak mengubah order, memverifikasi uang, menyetujui tanggal, atau memberikan diagnosis/resep.
4. Tombol **Hubungi petugas** memindahkan percakapan ke `waiting`. Asisten berhenti membalas. Status ini belum berarti petugas hadir.
5. Akun `cs` membuka **Layanan chat**. Antrean hanya berisi metadata routing tanpa isi pesan, nama pasien, atau nomor kontak.
6. Petugas mengambil percakapan secara atomik. Status menjadi `human` dan akses transkrip hanya diberikan kepada petugas yang ditugaskan. Petugas CS lain, direktur, IT, dan resepsionis tidak otomatis mendapat akses.
7. Pengguna dan petugas bertukar pesan. Browser mengambil pembaruan setiap lima detik selama panel/halaman aktif. Ini polling HTTP, belum WebSocket maupun indikator petugas online.
8. Pengguna atau petugas yang ditugaskan dapat menutup percakapan. Status `closed` memblokir pesan baru. Pengguna dapat membuka riwayat miliknya dan memulai percakapan baru.

Untuk mitra, `org_id` percakapan tetap organisasi mitra. `service_org_id=1` secara eksplisit merutekan layanan ke Customer Service Naraya, tanpa memberi CS akses ke resep klinis atau daftar order mitra. Hubungan percakapan dan order selalu divalidasi kembali untuk pemiliknya.

Kunci permintaan pada pembuatan percakapan dan setiap pesan mencegah duplikasi saat retry. Handoff, claim, dan penutupan ulang tidak menggandakan kejadian. Audit hanya menyimpan metadata aksi, tanpa isi pesan. Percakapan dan pesan tidak dihapus melalui API.

## Struktur dan migrasi

Backend kini dipisahkan ke `config`, `database`, `models`, `security`, `demo`, serta router domain di `backend/modules/`: auth, clinic, lab, finance, communication, operations, audit, chat. Refactor awal terlebih dahulu melewati sembilan tes regresi tanpa perubahan perilaku.

Migrasi Alembic:

- `0001`: mengadopsi tabel demo lama setelah memeriksa kolom yang diperlukan, atau membangunnya pada database kosong. Tidak menghapus data lama.
- `0002`: menambah tabel percakapan/pesan, indeks, constraint status, dan kunci unik idempotensi.

Startup demo menjalankan `upgrade head` lalu seed hanya bila belum ada pengguna. Otomatisasi startup ini masih khusus demo. Sebelum produksi diperlukan migrasi terkontrol, PostgreSQL, pelepasan seed demo, backup/restore, dan seluruh security gates.

Jalankan manual dari root: `python -m alembic upgrade head`. Buat salinan database sebelum migrasi operasional. Jangan menjalankan downgrade pada data yang perlu dipertahankan.

## Perbaikan kontrol

- Role internal dari organisasi lain tidak mendapat hak staf Naraya.
- Daftar teknisi dan perencanaan memeriksa organisasi, akun aktif, dan jadwal.
- Usulan tanggal yang masih pending tidak dapat ditimpa. Respons memakai `expected_due` dan ditolak jika tidak sama dengan usulan aktif.
- Riwayat detail hanya mengambil jenis kejadian layanan yang diizinkan. Payload audit mentah tidak dibuka kepada pasien/mitra.
- Login ulang mencabut sesi sebelumnya pada browser tersebut. Logout dicatat dan menutup sesi server.

## Bukti dan batas yang masih berlaku

Suite mencakup RBAC, tenant, workflow, idempotensi, perebutan claim petugas, audit, serta migrasi database lama. Pemeriksaan UI meliputi laptop, HP, pembuatan surat kerja, penerimaan Lab, produksi, QC, penerimaan dana, verifikasi FAT, asisten, handoff, dan balasan petugas.

Belum ada OTP, MFA, AI eksternal, pesan WhatsApp/SMS/email sungguhan, settlement bank, audit tahan manipulasi, kapasitas produksi terukur, atau serah-terima fisik final. Status siap diserahkan berarti QC teknis selesai, belum tindakan klinis selesai. Divisi pendukung masih sebatas laporan harian, kecuali ruang layanan CS yang kini menangani chat.

Integrasi AI nyata memerlukan provider, kredensial yang disimpan aman, persetujuan penggunaan layanan, serta batas data, retensi, dan evaluasi jawaban. Jangan mengirim data pasien ke model eksternal berdasarkan konfigurasi demo ini.
