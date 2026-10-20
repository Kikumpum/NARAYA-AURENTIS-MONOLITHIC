# Demo 0.4 — Portal pasien dan materi divisi

20 Oktober 2026. Seluruh data tetap fiktif dan berjalan lokal.

## Pintu masuk

- `/pasien`: halaman, CSS, dan JavaScript khusus pasien. Login memakai ID pasien atau nama pengguna dan kata sandi. Akun latihan `DEMO-P-001` / `DemoNAM2026!`.
- `/`: ruang kerja pegawai dan mitra. Form nama pengguna biasa, tanpa daftar akun divisi. Akun pasien ditolak oleh `/api/workspace/login`.
- Portal tidak mengunduh bundle navigasi pegawai, struktur organisasi, daftar pegawai, SOP, laporan internal atau materi pelatihan.

Portal hanya menampilkan profil pasien sendiri, layanan internal miliknya, jadwal dan dokter yang terkait, pemberitahuan sendiri, respons eksplisit perubahan tanggal/dokter, serta bantuan. ID penanggung jawab dan teknisi, instruksi klinis, data organisasi, dan JSON audit internal tidak diserialisasi pada API pasien. Riwayat tanggal memakai daftar field yang diizinkan.

## Sesi dan akses

Migrasi 0004 menambah audience sesi tanpa menghapus data lama. Cookie `nam_patient_session` khusus `/api/patient` dan audience `patient`; cookie ruang kerja `nam_session` memakai audience `workspace`. Keduanya HttpOnly, SameSite Strict dan memerlukan CSRF pada perubahan. Menyalin nilai cookie ke nama lain tetap ditolak. Keluar dari pasien tidak mengakhiri akun pegawai pada browser yang sama.

Backend pasien memeriksa akun aktif, peran pasien, organisasi internal, tautan rekam pasien, kepemilikan order/jadwal dan status workflow. Pasien eksternal tetap melalui klinik mitra. Endpoint `/api/login` lama dipertahankan untuk skrip demo; hak aksesnya tetap diperiksa, serializer pasien juga membuang referensi pegawai internal, dan frontend pasien lama diarahkan ke `/pasien` sebelum kerangka pegawai ditampilkan.

## Bantuan pasien

Permintaan terbaru pengguna membatasi live chat untuk pasien. Pegawai dan mitra tidak dapat memulai percakapan personal lewat API, termasuk endpoint lama. Riwayat percakapan lama dipertahankan; percakapan nonpasien tidak muncul di antrean baru. CS tetap mendapat kotak masuk untuk melayani pasien, mengambil percakapan secara atomik, membalas lalu menutupnya. CS tidak otomatis mendapat akses order atau rekam medis.

Asisten tetap mock lokal berbasis aturan, belum provider AI. Tidak ada pesan keluar ke WhatsApp, SMS, email atau layanan eksternal. Setelah pasien meminta petugas, asisten berhenti membalas. Kunci permintaan mencegah pesan dan handoff ganda.

## Materi divisi

Pegawai mendapat menu Materi divisi. Daftar materi rinci mengikuti peran pelaksana pada 32 draf SOP, sedangkan pengenalan divisi lain hanya ringkasan tujuan tanpa nama pegawai/data pasien. Materi memuat urutan kerja, kapan dikerjakan, bukti yang harus disiapkan dan latihan draf laporan. Membuka materi dicatat sebagai `training.opened`.

Ini modul baca dan orientasi, belum LMS dengan ujian, sertifikat atau catatan kelulusan. Membaca materi tidak mengubah akses atau mengesahkan tindakan klinis. Materi wajib ditelaah pemilik proses.

## Perbaikan lain

Label lingkungan dibuat sederhana tanpa titik dekoratif. Input janji temu wajib memuat zona waktu, disimpan dalam UTC dan ditampilkan WIB. Pemeriksaan shift memakai hari WIB, termasuk tanggal yang berbeda di UTC. Data jadwal lama yang ambigu tidak diubah otomatis.

## Verifikasi

125 tes backend lulus pada 20 Oktober 2026. Meliputi kebocoran tenant, pembatasan akun pasien/pegawai, audience dan CSRF, kepemilikan data, transisi persetujuan, idempotensi chat, satu petugas, audit, migrasi, serta cakupan SOP/lampiran sebelumnya. Pemeriksaan browser laptop dan HP melengkapi pengujian, bukan bukti kesiapan produksi.

## Bahan presentasi

`output/Naraya_Aurentis_Alur_Lengkap_Demo_0.4.pptx` berisi 48 slide dengan alur penggunaan, tangkapan layar aplikasi, catatan pembicara, 19 akun latihan, 32 judul SOP dan 31 jabatan. Struktur, geometri, font dan impor file telah diperiksa. Pemeriksaan tersebut tidak menyatakan aplikasi siap produksi atau pengujian native Microsoft PowerPoint.
