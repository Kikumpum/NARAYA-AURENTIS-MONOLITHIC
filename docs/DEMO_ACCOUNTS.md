# Akun latihan NAM DMS

Terdapat **34 akun fiktif** untuk mencoba seluruh jabatan pada bagan dan portal pasien/mitra.

Kata sandi semua akun: **`DemoNAM2026!`**. Nama pengguna tidak membedakan huruf besar/kecil dan spasi di awal/akhir diabaikan. Kata sandi tetap membedakan huruf besar/kecil dan karakter, termasuk tanda `!`.

Masuk dari halaman portal netral. Akun pasien diarahkan ke portal pasien; akun karyawan/mitra membuka halaman sesuai kewenangannya. `DIREKTUR UTAMA` dan `dirut` juga diterima sebagai alias `direktur_utama`.

| Jabatan / layanan | Nama pengguna |
| --- | --- |
| Komisaris | `komisaris` |
| Direktur Utama | `direktur_utama` |
| Direktur | `direktur` |
| Business Development | `business_development` |
| IT | `it` |
| Auditor | `auditor` |
| Corporate | `corporate` |
| HR | `hr` |
| IC / GA | `ga` |
| FAT | `fat` |
| Insurance | `insurance` |
| Operation | `operation` |
| Procurement | `purchasing` |
| Branch Head | `branch_head` |
| Branch Manager | `branch_manager` |
| Kepala Lab | `lab` |
| Senior Lab | `lab2` |
| Kepala Klinik | `kepala_klinik` |
| Marketing and Sales | `marketing` |
| Editor | `editor` |
| Content Planner | `content_planner` |
| Sales | `sales` |
| Customer Service | `cs` |
| Resepsionis | `resepsionis` |
| Housekeeping | `housekeeping` |
| Dokter Gigi | `dokter` |
| Dokter Gigi (akun kedua) | `dokter2` |
| Perawat | `perawat` |
| Teknisi Lab | `teknisi` |
| CAD/CAM | `cadcam` |
| Quality Control | `qc` |
| Gudang | `gudang` |
| Klinik Mitra | `mitra` |
| Pasien | `pasien` atau `DEMO-P-001` |

Kunci akses demo adalah gerbang terpisah, bukan kata sandi akun. Kunci privat tidak dicantumkan di berkas ini.

Akun tambahan adalah fixture latihan eksplisit, bukan pengisian jabatan nyata. Komisaris/Direktur Utama dan jabatan lainnya memakai hak peran yang sudah ditetapkan; hierarki bagan tidak memberikan akses medis, QC atau keuangan otomatis. Akun yang sudah ada tidak diaktifkan ulang, diubah perannya, dipindahkan tenantnya atau direset sandinya saat startup. Posisi baru pada bagan tidak membuat login secara otomatis.

Verifikasi lokal: 228 tes backend lulus. Cakupan meliputi login semua akun dengan huruf besar, pemulihan sesi/CSRF, alias jabatan, benturan nama/ref pasien, hak peran dan tenant, idempotensi seed, serta perlindungan akun lama.
