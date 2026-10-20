# Flowchart NAM DMS - Demo 0.4

Enam diagram A3 lanskap menggambarkan perilaku demo lokal pada 20 Oktober 2026. Diagram memakai proses, keputusan, panah berlabel, serta jalur pengulangan yang terpisah. Data pasien dan database lokal tidak dibaca saat pembuatan.

## Berkas

- [PDF lengkap, enam halaman](../output/flowchart/NAM_Flowchart_Lengkap_Demo_0.4.pdf).
- [Paket PDF, PNG, SVG, dan panduan](../output/NAM_Flowchart_Demo_0.4.zip).
- [Folder gambar dan sumber SVG](../output/flowchart/).

| Halaman | Isi | Gambar | SVG yang dapat disunting |
| --- | --- | --- | --- |
| 01 | Pintu masuk pasien, pegawai dan klinik mitra | [PNG](../output/flowchart/NAM_Flowchart-1.png) | [SVG](../output/flowchart/01_pintu_masuk.svg) |
| 02 | Surat kerja, penugasan Lab, produksi, QC, rework | [PNG](../output/flowchart/NAM_Flowchart-2.png) | [SVG](../output/flowchart/02_klinik_dan_laboratorium.svg) |
| 03 | Persetujuan perubahan tanggal dan dokter | [PNG](../output/flowchart/NAM_Flowchart-3.png) | [SVG](../output/flowchart/03_persetujuan_perubahan.svg) |
| 04 | Asisten pasien, antrean, pengambilan oleh CS, penutupan | [PNG](../output/flowchart/NAM_Flowchart-4.png) | [SVG](../output/flowchart/04_bantuan_pasien.svg) |
| 05 | Invoice, pembayaran menunggu verifikasi, FAT, status tagihan | [PNG](../output/flowchart/NAM_Flowchart-5.png) | [SVG](../output/flowchart/05_keuangan.svg) |
| 06 | Materi divisi, SOP, checklist, bukti, peninjauan, ekspor | [PNG](../output/flowchart/NAM_Flowchart-6.png) | [SVG](../output/flowchart/06_materi_sop_dan_laporan.svg) |

## Cara membaca

Kotak menunjukkan proses, belah ketupat menunjukkan keputusan, dan label panah menunjukkan cabangnya. Hijau tua menandai langkah utama atau hasil yang sah; warna merah muda menunjukkan penolakan atau perbaikan. Setiap halaman dapat dipresentasikan secara terpisah.

Alur diringkas untuk komunikasi operasional. Diagram bukan daftar seluruh endpoint atau pengganti aturan backend. Rincian produksi masih mengikuti transisi status yang diizinkan, termasuk pengajuan `qc_pending` sebelum keputusan QC.

## Batas yang harus dipertahankan

- Portal pasien tidak menampilkan akun divisi, struktur pegawai, SOP atau laporan internal. Sesi pasien dan ruang pegawai terpisah.
- Klinik mitra menerima komunikasi order eksternal. Pasien eksternal tidak otomatis mendapat komunikasi langsung.
- Status `ready` berarti hasil teknis siap diserahkan; diagram tidak mengklaim pencatatan penyerahan akhir sudah menjadi workflow tersendiri.
- Membaca pemberitahuan tidak menyetujui perubahan. Respons tanggal memeriksa versi usulan yang masih aktif; tanggal lama dan keputusan tetap dapat ditelusuri.
- Setelah handoff diminta, asisten berhenti membalas. Antrean belum membuka transkrip kepada CS sebelum percakapan diambil; hanya CS yang ditugaskan dapat membalas.
- Asisten masih simulasi lokal, verifikasi FAT masih simulasi manual, dan materi divisi masih modul baca. Tidak ada integrasi AI, bank, atau pengiriman pesan eksternal yang diklaim.
- Laporan tanpa peninjau tetap menunggu. Peninjau harus berwenang dan berbeda dari pembuat. Peninjauan SOP tidak menggantikan tindakan dokter, keputusan QC, atau verifikasi pembayaran.

## Dasar pencocokan

`docs/WORKSPACE_DEMO_0.4.md`, `docs/PATIENT_PORTAL_FLOW.mmd`, `docs/CHAT_FLOW.mmd`, `docs/SOP_REPORT_FLOW.mmd`, serta implementasi `backend/modules/patient_portal.py`, `clinic.py`, `lab.py`, `communication.py`, `finance.py`, `chat.py`, `training.py`, dan `sop_reports.py`.

## Membuat ulang

Jalankan `python scripts/build_flowcharts.py` dari root proyek. Pembuatan PDF dan SVG memakai `reportlab` dan font Segoe UI pada Windows. Dependency pembuat diagram terpisah dari dependency server; berkas hasil dapat dibuka tanpa menjalankan script.

Untuk membuat PNG dari PDF, gunakan Poppler:

```powershell
pdftoppm -png -scale-to 1900 output/flowchart/NAM_Flowchart_Lengkap_Demo_0.4.pdf output/flowchart/NAM_Flowchart
```

Pemeriksaan: PDF memiliki enam halaman A3 lanskap; keenam halaman dirender dan ditinjau secara visual. Script juga memeriksa batas halaman, lebar teks node, tumpang tindih antarnode, dan jalur konektor tegak lurus. Perubahan hanya pada dokumentasi dan generator diagram; perilaku aplikasi tidak diubah.
