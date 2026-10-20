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

Halaman `/` langsung memperlihatkan desain login pegawai yang sama dengan versi lokal; `/pasien` langsung memperlihatkan desain portal pasien. Setelah nama pengguna dan sandi diisi, dialog kecil meminta kunci akses demo apabila browser belum memiliki izin. Kunci hanya diberikan kepada penguji yang diundang. Sesudah kunci diterima, login akun dilanjutkan dan kewenangan akun tetap diperiksa.

Kunci ditukar melalui POST ber-Origin sama menjadi cookie `nam_demo_access`, Secure, HttpOnly, SameSite Strict. Isinya ditandatangani HMAC, terikat audience demo, deployment dan waktu kedaluwarsa; tidak memuat kunci privat. Berlaku maksimal delapan jam atau sampai masa demo berakhir. Membuka akses berulang tidak menambah sesi akun atau mengganti cookie yang masih sah. Cookie ini bukan sesi pasien atau pegawai dan tidak memberi hak atas order, pembayaran, rekam pasien maupun transkrip chat. Kunci tidak disimpan di localStorage, sessionStorage atau URL. Basic auth dengan username `demo` tetap diterima untuk kompatibilitas pemeriksaan CLI; browser tidak lagi menerima popup HTTP Basic atau halaman gerbang putih.

Pada API data, konfigurasi tidak lengkap memberi respons 503; kunci salah atau izin yang tidak sah memberi 401; masa demo berakhir memberi 410, termasuk pada sesi aplikasi yang sudah aktif. Halaman login dan aset allowlist tetap dapat ditampilkan untuk menjelaskan keadaan akses. Ketika konfigurasi belum sah, startup tidak menjalankan migrasi atau seed. Tidak ada jalan pintas dari gerbang ke otorisasi bisnis.

Cookie sesi online selalu memakai Secure, HttpOnly dan SameSite Strict. CSRF, pemeriksaan Origin, role, organisasi, kepemilikan object, state workflow, idempotensi dan audit tetap berlaku. Halaman meminta mesin pencari untuk tidak mengindeksnya.

Database online berada di scratch sementara sistem operasi, dipisahkan berdasarkan deployment dan kunci akses. `DATABASE_URL` eksternal yang mungkin ada di dashboard **tidak dibuka** pada mode ini. Data demo lokal tidak diunggah. Rotasi kunci atau deployment baru menggunakan namespace database yang berbeda tanpa menghapus data demo lokal.

**Batas penting:** SQLite sementara ini milik satu instance fungsi, bukan database bersama yang persisten. Vercel dapat memakai instance berbeda atau menghapus scratch pada cold start/redeployment. Akibatnya data dan sesi dapat ter-reset atau berbeda antarpengguna/permintaan. Demo lintas perangkat, chat CS, penugasan dan laporan tidak dijamin tetap tersambung antar-instance. Simpan ekspor latihan di komputer. Ini bukan penyimpanan operasional atau solusi produksi; database bersama yang dikelola harus disiapkan untuk pengujian multiuser yang konsisten.

UI pasien dan pegawai menampilkan batas tersebut melalui status demo minimal, dengan keterangan tambahan yang dapat dibuka tanpa menutupi desain login. Tidak ada AI eksternal, pengiriman pesan keluar atau settlement bank sungguhan yang diaktifkan.

## Pengaturan proyek Vercel

1. Gunakan repositori `Kikumpum/NARAYA-AURENTIS-MONOLITHIC` dan root directory **root repositori**, bukan `backend` atau `frontend`.
2. Biarkan konfigurasi entrypoint/dependency/framework mengikuti berkas di root. Hapus override build/output lama jika masih menunjuk frontend statis atau subfolder.
3. Tambahkan variabel di atas pada environment yang akan diuji. Untuk pengujian awal, gunakan deployment Preview. Istilah environment Production pada dashboard Vercel tidak sama dengan izin `NAM_ENV=production` pada aplikasi.
4. Buat deployment baru setelah mengubah variabel. Variabel baru tidak memperbaiki URL deployment lama secara retroaktif.
5. Buka URL deployment. Desain login harus langsung tampil lengkap dengan logo dan CSS. API data tetap menolak permintaan tanpa izin. Klik masuk setelah mengisi akun, masukkan kunci privat pada dialog, kemudian periksa pasien di `/pasien`, pegawai di `/`, serta skenario order, QC, keuangan dan SOP memakai data latihan.

Jangan menyimpan token Vercel atau kunci gerbang di GitHub. Jangan menonaktifkan perlindungan deployment yang sudah ada. Login Vercel CLI memerlukan tindakan autentikasi pemilik akun; token tidak perlu ditempel di chat.

## Verifikasi

Jalankan `python -m pytest -q backend/tests`. Seluruh 155 tes backend lulus pada 20 Oktober 2026. Tes hosting mencakup konfigurasi fail closed, startup tanpa DB pada konfigurasi gagal, allowlist presentasi tanpa akses data, Origin pada pertukaran kunci, cookie Secure, signature/audience/deployment/masa akses, larangan IT membaca order, batas resepsionis, CSRF, idempotensi chat dan audit. Startup entrypoint asli juga diuji dari direktori berbeda dengan migrasi, seed, scratch DB dan login HTTPS. Hasil lokal bukan bukti deployment Vercel sudah berhasil; URL dan log runtime perlu diperiksa setelah deployment. Diagram: `TEMPORARY_ONLINE_DEMO_FLOW.mmd`.

Sebelum hosting operasional atau berbayar untuk pemakaian nyata, selesaikan `docs/SECURITY_GATES.md`, database persisten, identitas dan kredensial individual, layanan audit/backup serta validasi klinis dan keuangan. Membayar hosting tidak otomatis memenuhi persyaratan tersebut.

Referensi teknis: [FastAPI pada Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [Python runtime](https://vercel.com/docs/functions/runtimes/python), [filesystem fungsi](https://vercel.com/docs/functions/runtimes#file-system-support).
