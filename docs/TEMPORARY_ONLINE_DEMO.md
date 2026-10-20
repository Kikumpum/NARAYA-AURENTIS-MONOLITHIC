# Demo online sementara - Vercel

Keputusan pengguna pada 20 Oktober 2026: presentasi/PPT tetap berupa berkas lokal. Aplikasi boleh dicoba secara online untuk sementara dengan data fiktif; hosting berbayar dibahas setelah aplikasi matang. Halaman presentasi statis tidak dipakai sebagai pengganti aplikasi.

Ini pengecualian terbatas atas batas demo lokal, bukan persetujuan produksi atau penggunaan data pasien nyata. `NAM_ENV=production` tetap ditolak.

## Konfigurasi yang disediakan

- `app.py` adalah entrypoint ASGI di root repositori.
- `requirements.txt` root merujuk dependency backend; Python 3.12 ditetapkan secara eksplisit.
- `vercel.json` memilih framework FastAPI dan menyertakan frontend serta migrasi. PPT, PDF, dokumen, database dan berkas development tidak disajikan sebagai aset deployment.
- `pyproject.toml` menonaktifkan promosi static mount ke CDN agar middleware tetap memeriksa setiap jalur. Allowlist eksplisit membuka hanya halaman login, aset presentasi yang diperlukan dan status akses minimal; API data tetap tertutup.
- Migrasi memakai lokasi absolut terhadap root proyek, bukan direktori kerja proses.

## Akses dan data

Demo online hanya aktif jika seluruh pengaturan berikut sah:

| Variabel | Nilai |
| --- | --- |
| `NAM_ENV` | `demo` |
| `NAM_ONLINE_DEMO` | `1` |
| `NAM_DEMO_ACCESS_PASSWORD` | Kunci acak privat, minimal 24 karakter; jangan commit atau masukkan ke URL |
| `NAM_DEMO_EXPIRES_AT` | Waktu ISO 8601 dengan zona waktu, maksimal 31 hari ke depan; disarankan tujuh hari |
| `NAM_DEMO_SHARED_DATABASE` | `1` untuk database demo bersama yang telah diizinkan |
| `NAM_DEMO_DATABASE_URL` | URL PostgreSQL khusus demo, TLS `sslmode=require`/`verify-ca`/`verify-full`; diisi integrasi Neon, jangan commit |

Halaman `/` langsung memperlihatkan desain hijau/krem/emas dengan bahasa netral: **Portal Naraya Aurentis**, **Masuk menggunakan akun Anda**, tombol **LOGIN**. Contoh akun internal tidak ditampilkan. Backend memverifikasi kredensial melalui `/api/access/resolve` dan memilih portal yang sesuai; endpoint login pasien atau workspace tetap menerbitkan cookie audience masing-masing. Halaman `/pasien` tetap dapat dibuka langsung tanpa memuat navigasi divisi. Setelah nama pengguna dan sandi diisi, dialog kecil meminta kunci akses demo apabila browser belum memiliki izin. Kunci hanya diberikan kepada penguji yang diundang. Sesudah kunci diterima, login akun dilanjutkan dan kewenangan akun tetap diperiksa.

Kunci ditukar melalui POST ber-Origin sama menjadi cookie `nam_demo_access`, Secure, HttpOnly, SameSite Strict. Isinya ditandatangani HMAC, terikat audience demo, deployment dan waktu kedaluwarsa; tidak memuat kunci privat. Berlaku maksimal delapan jam atau sampai masa demo berakhir. Membuka akses berulang tidak menambah sesi akun atau mengganti cookie yang masih sah. Cookie ini bukan sesi pasien atau pegawai dan tidak memberi hak atas order, pembayaran, rekam pasien maupun transkrip chat. Kunci tidak disimpan di localStorage, sessionStorage atau URL. Basic auth dengan username `demo` tetap diterima untuk kompatibilitas pemeriksaan CLI; browser tidak lagi menerima popup HTTP Basic atau halaman gerbang putih.

Pada API data, konfigurasi tidak lengkap memberi respons 503; kunci salah atau izin yang tidak sah memberi 401; masa demo berakhir memberi 410, termasuk pada sesi aplikasi yang sudah aktif. Halaman login dan aset allowlist tetap dapat ditampilkan untuk menjelaskan keadaan akses. Ketika konfigurasi belum sah, startup tidak menjalankan migrasi atau seed. Tidak ada jalan pintas dari gerbang ke otorisasi bisnis.

Cookie sesi online selalu memakai Secure, HttpOnly dan SameSite Strict. CSRF, pemeriksaan Origin, role, organisasi, kepemilikan object, state workflow, idempotensi dan audit tetap berlaku. Halaman meminta mesin pencari untuk tidak mengindeksnya.

Pada konfigurasi yang aktif setelah perbaikan sesi, database online memakai **Neon PostgreSQL Free**, resource `nam-demo-postgres`, region Singapura, terhubung hanya ke environment Production proyek ini. Pengguna mengizinkan database gratis khusus demo serta menyatakan telah meninjau dan menyetujui syarat integrasi. Layanan auth Neon, upgrade berbayar dan auto-recharge tidak diaktifkan. Kredensial disimpan oleh integrasi sebagai variabel Vercel dengan awalan `NAM_DEMO_`.

Aplikasi hanya membuka URL khusus `NAM_DEMO_DATABASE_URL` jika `NAM_DEMO_SHARED_DATABASE=1` dan konfigurasi TLS sah. `DATABASE_URL` umum tetap diabaikan untuk mencegah pembukaan database operasional tanpa sengaja. Konfigurasi bersama yang tidak sah menutup API dan tidak membuka database. Data SQLite lokal tidak diunggah. Deploy ulang tidak men-seed ulang atau menghapus data latihan yang sudah ada. Rotasi kunci gerbang tidak menghapus riwayat database bersama.

Semua instance membaca sesi dan data dari database bersama. Migrasi serta seed dilindungi `pg_advisory_xact_lock` dalam satu transaksi agar cold start paralel tidak membuat data ganda. Driver memakai koneksi TLS dan endpoint pooler Neon dengan NullPool pada sisi SQLAlchemy. Urutan seed mematuhi foreign key dan sequence ID fixture diselaraskan saat seed pertama.

**Konfigurasi lama/fallback:** jika mode database bersama tidak diaktifkan, demo masih menggunakan SQLite scratch per instance. Ini tidak dapat menjamin sesi/data lintas permintaan dan tidak boleh dipakai untuk mendemonstrasikan login online yang stabil. Keluhan sesi putus sudah direproduksi pada konfigurasi lama, sehingga deployment aktif memakai PostgreSQL bersama. Tidak ada fallback diam-diam ke SQLite saat konfigurasi bersama sudah dipilih tetapi gagal.

UI pasien dan pegawai menampilkan batas tersebut melalui status demo minimal, dengan keterangan tambahan yang dapat dibuka tanpa menutupi desain login. Tidak ada AI eksternal, pengiriman pesan keluar atau settlement bank sungguhan yang diaktifkan.

## Pengaturan proyek Vercel

1. Gunakan repositori `Kikumpum/NARAYA-AURENTIS-MONOLITHIC` dan root directory **root repositori**, bukan `backend` atau `frontend`.
2. Biarkan konfigurasi entrypoint/dependency/framework mengikuti berkas di root. Hapus override build/output lama jika masih menunjuk frontend statis atau subfolder.
3. Tambahkan variabel di atas pada environment yang akan diuji. Untuk pengujian awal, gunakan deployment Preview. Istilah environment Production pada dashboard Vercel tidak sama dengan izin `NAM_ENV=production` pada aplikasi.
4. Pastikan `NAM_DEMO_SHARED_DATABASE=1` dan URL khusus demo sudah disuntikkan oleh integrasi Neon. Buat deployment baru setelah mengubah variabel. Variabel baru tidak memperbaiki URL deployment lama secara retroaktif.
5. Buka URL deployment. Desain login harus langsung tampil lengkap dengan logo dan CSS. API data tetap menolak permintaan tanpa izin. Klik masuk setelah mengisi akun, masukkan kunci privat pada dialog, kemudian periksa pengalihan pasien dari `/` ke `/pasien`, pegawai di `/`, serta skenario order, QC, keuangan dan SOP memakai data latihan.

Jangan menyimpan token Vercel atau kunci gerbang di GitHub. Jangan menonaktifkan perlindungan deployment yang sudah ada. Login Vercel CLI memerlukan tindakan autentikasi pemilik akun; token tidak perlu ditempel di chat.

## Verifikasi

Jalankan `python -m pytest -q backend/tests`. Seluruh **172 tes backend lulus** pada 20 Oktober 2026. Migrasi PostgreSQL dan bootstrap ulang berhasil; tiga proses aplikasi independen membaca sesi yang sama dan menyelesaikan **36 permintaan** dengan status 200. Uji pasien di PostgreSQL juga mempertahankan penolakan order lain, akses organisasi dan mutasi tanpa CSRF. Verifikasi URL online dilakukan kembali setelah deployment. Tes hosting mencakup konfigurasi fail closed, startup tanpa DB pada konfigurasi gagal, allowlist presentasi tanpa akses data, Origin pada pertukaran kunci, cookie Secure, signature/audience/deployment/masa akses, larangan IT membaca order, batas resepsionis, CSRF, idempotensi chat dan audit. Startup entrypoint asli juga diuji dari direktori berbeda dengan migrasi, seed, scratch DB dan login HTTPS. Tes portal netral memeriksa ID pasien, pengenalan akun setelah autentikasi, role spoofing, scope, CSRF, pencabutan sesi saat login ulang dan tidak adanya sesi/audit ganda pada tahap pengenalan akun. Hasil lokal bukan bukti deployment Vercel sudah berhasil; URL dan log runtime perlu diperiksa setelah deployment. Diagram: `TEMPORARY_ONLINE_DEMO_FLOW.mmd`.

Sebelum hosting operasional atau berbayar untuk pemakaian nyata, selesaikan `docs/SECURITY_GATES.md`, database persisten, identitas dan kredensial individual, layanan audit/backup serta validasi klinis dan keuangan. Membayar hosting tidak otomatis memenuhi persyaratan tersebut.

Referensi teknis: [FastAPI pada Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [Python runtime](https://vercel.com/docs/functions/runtimes/python), [filesystem fungsi](https://vercel.com/docs/functions/runtimes#file-system-support).
