# NAM DMS — Spesifikasi Kebutuhan v0.17

**Proyek:** Naraya Aurentis Monolithic — Integrated Dental Clinic & Laboratory Management System  
**Status:** Dokumen kerja; bukan persetujuan implementasi final.  
**Tanggal pembaruan:** 19 Oktober 2026  
**Ruang lingkup:** Wawancara Tahap 1–17: keuangan, penjadwalan, integrasi Klinik–Lab, penugasan, ETA, keterlambatan, komunikasi pasien, dan model penerimaan order internal dan eksternal. **Tahap 17 ditambahkan pada Bagian 20. Bagian sebelumnya dipertahankan sebagai riwayat persyaratan; apabila ada konflik, keputusan pengguna yang lebih baru dan eksplisit mengungguli catatan lama.**

## 1. Struktur organisasi awal (Tahap 1)
Divisi yang diidentifikasi:
1. Front Office / Resepsionis
2. Dokter Gigi
3. Perawat / Asisten Dokter
4. Dental Laboratory / Teknisi
5. CAD/CAM / Digital Design
6. Quality Control (QC)
7. Finance / Accounting / Kasir
8. Marketing / Customer Service
9. Gudang / Purchasing
10. HRD / General Affairs
11. IT / Sistem Informasi
12. Manajemen / Direktur

**Catatan terbuka:** Struktur divisi, jabatan, peran, hierarki FAT (Finance, Accounting & Tax, perlu dikonfirmasi), serta pemisahan tugas belum final. Aliran pekerjaan antara resepsionis dan FAT dianggap area risiko tinggi.

## 2. Kebijakan penerimaan pembayaran (Tahap 2)
- **Keputusan pengguna:** Resepsionis boleh menerima pembayaran pasien secara langsung.
- **Rancangan kontrol:** Resepsionis boleh menerima dan mencatat pembayaran, tetapi tidak boleh secara sepihak mengotorisasi refund, melakukan penghapusan pembayaran yang telah dibukukan, atau menyetujui koreksi sensitif.
- FAT melakukan rekonsiliasi harian independen; hak akses dibagi menurut jabatan dan fungsi, dengan audit log serta otorisasi berjenjang.

## 3. Metode pembayaran yang diminta (Tahap 3)
- Tunai/cash
- QRIS
- Transfer bank
- Kartu debit/EDC
- Asuransi/corporate billing
- Kartu kredit
- Cicilan/pembayaran bertahap

**Catatan pemodelan:** Cicilan adalah *skema/jadwal pembayaran*, bukan saluran penerimaan dana. Klaim asuransi/corporate billing melibatkan pihak penanggung dan piutang terpisah dari pembayaran langsung pasien.

## 4. Keputusan dan rekomendasi Tahap 4
**Riwayat:** Pengguna semula memilih "satu invoice hanya boleh satu metode". Pada pesan berikutnya pengguna meminta **rekomendasi metode gabungan dan bertahap yang paling aman dan fleksibel**. Pilihan semula ditandai **digantikan oleh permintaan evaluasi**, bukan sebagai persetujuan final untuk implementasi gabungan.

### Rekomendasi arsitektur (menunggu konfirmasi)
- **Satu invoice dapat memiliki beberapa pembayaran (1:N).** Masing-masing catatan pembayaran hanya mempunyai **satu kanal/metode**, jumlah, mata uang, waktu, penerima, bukti, status, dan referensi unik.
- Dukung *split tender* (contoh: tunai dan QRIS), DP, pembayaran sebagian, dan jadwal cicilan dengan kebijakan persetujuan yang dapat dikonfigurasi.
- Sisa tagihan dihitung dari total terutang dikurangi pembayaran **terverifikasi/tersettle** dan penyesuaian resmi yang sah; pembayaran belum terverifikasi tidak otomatis melunasi invoice.
- Catatan jadwal cicilan/utang dipisahkan dari catatan penerimaan pembayaran aktual.
- Klaim asuransi dibukukan sebagai klaim/piutang penanggung sesuai status pengajuan, persetujuan, pembayaran dan penolakan; tanggungan pasien dilacak terpisah.
- Refund, void dan koreksi melalui transaksi pembalik/adjustment yang memiliki alasan, pencetus, pemberi persetujuan, dan *audit trail*, bukan penghapusan histori.
- *Idempotency key* serta constraint unik pada referensi pembayaran untuk mengurangi posting ganda dari gateway, transfer, atau EDC.

### Contoh alokasi
Invoice Rp5.000.000; tunai Rp2.000.000 terkonfirmasi; QRIS Rp2.000.000 terkonfirmasi; sisa Rp1.000.000 sebagai piutang pasien dengan jadwal cicilan yang disetujui. Status invoice **sebagian dibayar**, bukan **lunas**.

### Model data konseptual
| Entitas | Peran | Atribut inti (contoh) |
|---|---|---|
| `invoice` | Tagihan klinik/lab | id, patient_or_client_id, branch_id, total, status, currency, issued_at |
| `invoice_line` | Detail tindakan/barang | invoice_id, service_id, quantity, price, tax, discount |
| `payment` | Pembayaran aktual | id, invoice_id, method_id, amount, received_by, external_ref, status, verified_at |
| `payment_allocation` | Alokasi pembayaran jika ke depan pembayaran juga boleh melunasi banyak invoice | payment_id, invoice_id, amount |
| `installment_plan` | Persetujuan skema pembayaran bertahap | invoice_id, debtor_id, schedule, terms, approved_by, status |
| `installment_due` | Angsuran jatuh tempo | installment_plan_id, due_date, amount, status |
| `insurance_claim` | Klaim dan piutang penanggung | invoice_id, insurer_id, claim_amount, approved_amount, status |
| `refund` / `adjustment` | Koreksi dengan approval | payment_id, amount, reason, requested_by, approved_by, status |
| `cash_shift` | Tutup kas petugas | cashier_id, branch_id, opened_at, closed_at, counted_cash, variance |
| `reconciliation` | Verifikasi independen oleh FAT | date, bank_or_gateway, expected, settled, variance, reviewed_by |
| `audit_event` | Jejak tindakan tidak dapat diubah sembarangan | actor_id, event, entity, entity_id, time, before_after_reference |
| `role`, `permission`, `user_role` | Akses berbasis tugas | role, resource, action, scope, actor |

**Catatan desain:** Model final perlu menentukan apakah satu pembayaran boleh dialokasikan ke banyak invoice. Jika tidak, `invoice_id` langsung pada `payment` sudah cukup untuk MVP dan `payment_allocation` bisa ditunda. Hindari menyimpan data kartu sensitif, seperti PIN dan CVV.

### Kontrol keamanan dan keuangan minimum
1. Akses berbasis peran dan lokasi; MFA bagi approver/administrator.
2. Pemisahan penerima dana, pemberi approval, dan pemeriksa rekonsiliasi.
3. Verifikasi pembayaran elektronik dari penyedia resmi, bukan screenshot semata.
4. Transaksi database atomik dan pencegahan transaksi duplikat; pembatasan nilai negatif/kelebihan bayar sesuai kebijakan.
5. Audit log tahan manipulasi, alasan wajib untuk pembatalan/penyesuaian, dan notifikasi transaksi tidak biasa.
6. Rekonsiliasi kas per shift dan QRIS, transfer, kartu per settlement; pelaporan selisih.
7. Enkripsi transit/penyimpanan, backup berkala yang diuji, kontrol akses data pasien dan pemantauan keamanan.
8. Review kewajiban privasi, rekam medis, fiskal/pajak, pembayaran, serta kontrak penyedia sebelum go-live di Indonesia.

## 5. Kebijakan DP dan cicilan — Tahap 5

**Pernyataan pengguna:** Kebijakan persetujuan cicilan/DP **belum ditentukan**. Pengguna meminta **rekomendasi keamanan berlapis**, bukan menyetujui satu kebijakan final.

**Status:** USULAN RANCANGAN / MENUNGGU KEPUTUSAN. Jangan gunakan batas nominal ataupun approval role di bawah sebagai kebijakan perusahaan sebelum ditetapkan.

### 5.1 Pemisahan jenis transaksi
- **DP/uang muka yang diterima:** catatan penerimaan dana yang benar-benar dibayar dan terverifikasi. Pembayaran DP **tidak otomatis mengesahkan kredit/cicilan** atas sisa tagihan.
- **Pembayaran sebagian tanpa fasilitas kredit:** hanya boleh bila syarat layanan dan penyelesaian pelunasan sudah sesuai kebijakan. Status tagihan tetap *sebagian dibayar* sampai total terpenuhi.
- **Izin cicilan/pembayaran tertunda:** komitmen membayar di masa depan sehingga perlu penilaian risiko, jadwal, persetujuan berjenjang, dan pengawasan piutang.
- **Asuransi/corporate billing:** berbeda dari cicilan pasien; perlu otorisasi penanggung, status klaim dan penanggung jawab pembayaran yang eksplisit.

### 5.2 Alur approval yang direkomendasikan
1. **Front Office / Resepsionis (maker):** menginput permohonan DP atau cicilan berdasarkan invoice yang sah, beserta nilai DP, sisa tagihan, tanggal jatuh tempo, alasan dan persetujuan pasien terhadap syarat; tidak dapat menyetujui permintaan yang dia buat sendiri.
2. **Sistem:** mengecek aturan otomatis (nominal, persentase DP minimum *jika ditetapkan*, masa angsuran, tagihan lama tertunggak, dan pengecualian). Permintaan sesuai kebijakan baku dapat diproses pada level yang ditentukan perusahaan; bila di luar aturan, statusnya *menunggu persetujuan* dan tidak dianggap disetujui.
3. **Supervisor operasional:** memastikan identitas permintaan, tindakan dan invoice, tetapi tidak dapat memalsukan penerimaan dana atau menghapus piutang.
4. **FAT / Manajer Keuangan (checker dan approver):** memeriksa kemampuan/risiko penagihan berdasarkan data yang dibolehkan, bukti DP, dan otorisasi sampai ambang yang nantinya ditetapkan. Persetujuan harus oleh pengguna berbeda dengan pengaju/penerima pembayaran dan sebisa mungkin berbeda dari pihak yang merekonsiliasi.
5. **Direktur / pejabat dengan delegasi:** menyetujui permintaan bernilai tinggi, masa cicilan di luar kebijakan, penghapusan piutang, atau pengecualian risiko tinggi. Delegasi, batas waktu, dan batas nominal wajib tercatat.
6. **FAT yang berbeda/rekonsiliator:** mengawasi keterlambatan, pengakuan piutang, saldo, pembayaran yang masuk, dan laporan selisih; tidak boleh mengubah jejak transaksi final.

### 5.3 Tabel kontrol per risiko
| Risiko | Pengendalian yang diusulkan |
|---|---|
| Resepsionis menjanjikan cicilan tanpa wewenang | Approval digital sebelum status 'cicilan disetujui', pembatasan hak akses per aksi |
| DP diinput tetapi uang tidak masuk | Konfirmasi penerimaan sesuai kanal, receipt per pembayaran, shift closing dan rekonsiliasi independen |
| Cicilan fiktif/pemberian kredit kepada relasi | Maker-checker, alasan, matriks batas nominal, jejak identitas approver, exception report |
| Pengubahan jatuh tempo agar tunggakan tersembunyi | Versi jadwal, persetujuan perubahan, histori yang tidak bisa dihapus oleh pengguna biasa |
| Piutang sengaja dihapus | Write-off dan refund terpisah; approval lebih tinggi dan jurnal koreksi terlacak |
| Staf memakai akun approver lain | Akun individual, MFA untuk persetujuan sensitif, log perangkat/sesi, larangan berbagi akun |
| Persetujuan terhenti saat approver cuti | Delegasi formal berbatas waktu/nominal, tanpa akses admin menyeluruh |
| Kebocoran data kesehatan/keuangan | Least privilege, field-level masking, enkripsi, retensi, audit akses, backup diuji |

### 5.4 Konfigurasi kebijakan yang BELUM diputuskan
- Batas nominal untuk approval supervisor, FAT/manajer, dan direktur (angka belum ditetapkan).
- Persentase DP minimal, tenor maksimal, syarat kelayakan, dan pengecualian layanan (belum ditetapkan).
- Ketentuan denda/biaya bila ada, beserta komunikasi dan persetujuan pasien (belum ditetapkan).
- Siapa penagih, kapan pengingat dikirim, dan apa prosedur ketika pasien menunggak (belum ditetapkan).
- Apakah seluruh cabang memakai satu kebijakan atau dapat memiliki kebijakan per cabang (belum ditetapkan).

### 5.5 Implikasi data dan keamanan aplikasi
Melengkapi model Tahap 4 dengan:
- `approval_request` (jenis request, objek terkait, status, maker_id, alasan, submitted_at, policy_version)
- `approval_step` (tahap, role_required, approver_id, decision, decision_at, alasan)
- `approval_policy` (kondisi, mata uang, plafon/tenor, cabang, berlaku_mula/akhir, version)
- `delegation` (delegator, delegate, scope, limit, mulai, berakhir, alasan)
- `installment_plan_version` (revisi jadwal, perubahan, approval, tanggal efektif)
- `receivable_event` (terbit, jatuh tempo, pembayaran, restrukturisasi, penghapusan yang telah disahkan)

Gunakan state machine sehingga request pending tidak bisa dianggap approved, mencegah self-approval, mewajibkan pemisahan akun penagih/pemeriksa sesuai kebijakan, dan mencatat alasan perubahan. Pastikan perubahan transaksi finansial bersifat atomik dan event audit terlindungi dari modifikasi oleh operator biasa.

## 6. Pertanyaan berikutnya — Tahap 6 (Integrasi Klinik–Laboratorium)
**Dari mana order pekerjaan Dental Laboratory akan berasal?**
- Hanya dokter gigi pada klinik sendiri.
- Hanya dokter/klinik eksternal.
- Keduanya: dokter internal dan klien eksternal.
- Belum pasti, perlu rekomendasi untuk desain skala usaha.

Ini menentukan model klien, siapa yang boleh memesan dan membaca kasus, persetujuan klinis, tahapan kerja teknisi/CAD-CAM/QC, penagihan, dan batas akses data pasien.

## 7. Status proyek
Masih tahap wawancara dan rancangan kebutuhan. Belum ada software produksi, basis data aktif, atau kontrol keamanan yang sudah diimplementasikan, diverifikasi, maupun diuji. Perlu kajian regulasi Indonesia terkait perlindungan data, rekam medis, pembayaran, perpajakan, dan ketentuan layanan kesehatan sebelum peluncuran.


---

## 8. Pembaruan Tahap 6 — Dokter Klinik, Dokter Lab & penugasan resepsionis

**Pernyataan pengguna (19 Oktober 2026):** Dokter klinik dan dokter lab harus dibedakan. Resepsionis memberikan order kepada dokter yang tersedia pada hari tersebut; aturan berlaku untuk klinik maupun lab. Seorang dokter lab dapat menerima beberapa pesanan, termasuk order yang berhubungan dengan pasien/dokter klinik.

### 8.1 Kebutuhan terkonfirmasi
1. Pisahkan kategori peran **Dokter Klinik** dan **Dokter Lab**. Jangan menyatukan jadwal, antrian kasus, tugas, atau hak akses begitu saja.
2. Resepsionis perlu melihat daftar petugas/dokter yang **dijadwalkan hadir dan tersedia pada hari itu** pada unit klinik dan lab; ketersediaan aktual mempertimbangkan kehadiran, cuti, kapasitas, jam kerja dan status pekerjaan.
3. Resepsionis memproses penerimaan administratif pasien/order dan meneruskan penugasan kepada dokter yang dipilih sesuai mekanisme yang akan diputuskan.
4. Dokter Lab mendukung **banyak order paralel** dengan nomor order, prioritas, tenggat, dan status masing-masing.
5. Order dari pemeriksaan/tindakan pasien di klinik ke lab harus memiliki referensi ke **kunjungan/tindakan pasien** dan **dokter klinik pengirim** tanpa memerlukan pengisian ganda atau membiarkan resepsionis mengubah instruksi klinis.
6. Status order lab dapat dilacak lintas unit sesuai kebutuhan minimum masing-masing peran, termasuk CAD/CAM, teknisi dan QC bila terlibat.

### 8.2 Alur konseptual (usulan, untuk validasi)
- **Klinik:** resepsionis registrasi/booking -> pilih dokter klinik dari daftar tersedia -> kunjungan/pemeriksaan -> dokter klinik membuat instruksi kebutuhan pekerjaan lab (bila perlu).
- **Lab untuk kasus klinik internal:** instruksi lab dari dokter klinik -> penerimaan/registrasi order administratif di lab -> daftar dokter lab tersedia -> penugasan dokter lab -> desain/produksi/QC -> hasil dikirim ke klinik -> dokter klinik menerima/memeriksa hasil sesuai tanggung jawab.
- **Lab untuk order langsung:** mungkin ada order yang langsung datang ke resepsionis lab; asal dari dokter/klinik eksternal **belum dikonfirmasi**, sehingga hanya dipersiapkan sebagai opsi desain.

### 8.3 Pembatasan tanggung jawab
- Resepsionis **tidak boleh** mengubah diagnosis, instruksi medis, spesifikasi klinis atau menyetujui tindakan klinis atas nama dokter.
- Penetapan jenis layanan, persetujuan klinis, serta otorisasi resep kerja klinis menjadi kewenangan petugas profesional sesuai kompetensi, lisensi dan kebijakan klinik; detail perlu ditinjau bersama tenaga medis yang berwenang.
- Hak membaca data pasien pada lab memakai prinsip **minimum necessary access**; bagian desain/produksi hanya menerima data yang dibutuhkan untuk mengerjakan order, dengan jejak akses dan perubahan.
- Ketersediaan jadwal **bukan** hak untuk mengakses semua kasus; akses dibatasi hubungan penugasan, peran, unit/cabang dan audit.

### 8.4 Usulan entitas data
- `practitioner` / `staff_profile`: petugas, kategori peran, kewenangan klinis, unit/cabang, status aktif; verifikasi status profesi bila relevan.
- `shift` + `availability_status`: jadwal, kehadiran, cuti, blok waktu, kapasitas, ketidakhadiran.
- `patient`, `appointment`, `clinical_encounter`: identitas dan kunjungan klinik, ditata sesuai aturan privasi.
- `clinical_lab_request`: permintaan dari dokter klinik (source encounter, ordering_practitioner, clinical_instructions, signoff).
- `lab_order`: order layanan lab (nomor, sumber, dokter/pemesan, tenggat, prioritas, status).
- `lab_order_item`: item/unit pekerjaan spesifik (mis. crown, bridge; rincian yang diperlukan akan ditentukan).
- `case_assignment`: penanggung jawab kasus/order, penugasan oleh petugas berwenang, status, waktu, alasan pengalihan.
- `production_stage`, `qc_result`, `case_event`: jejak alur produksi dan QC terpisah dari penilaian klinis.
- `order_access_audit`: jejak akses informasi pasien dan pergantian penugasan.

**Aturan integritas rancangan:** order laboratorium internal merujuk permintaan klinis yang ditandatangani/diotorisasi dokter klinik; membatasi penciptaan pesanan duplikat dan mempertahankan histori revisi. Satu dokter lab bisa menangani banyak order; satu order juga mungkin berganti penanggung jawab dengan histori tercatat.

### 8.5 Hal yang belum diketahui
1. Istilah **Dokter Lab**: apakah dokter gigi berizin yang bekerja di lingkungan lab, koordinator/teknisi lab, atau keduanya? Perbedaan ini menentukan hak profesional, alur QC, otorisasi klinis dan struktur akun.
2. Apakah lab menerima order langsung dari dokter/klinik eksternal? Belum dikonfirmasi.
3. Sistem pemilihan dokter: manual oleh resepsionis, usulan otomatis berdasar kehadiran dan beban kerja, atau kombinasi? Belum diputuskan.
4. Unit/bagian resepsionis klinik dan lab terpisah atau satu meja bersama? Belum diputuskan.
5. Apakah urutan klinik–lab selalu dari dokter klinik, atau ada kasus lab langsung ke dokter lab? Perlu alur pengecualian.

### 8.6 Pertanyaan tunggal berikutnya — Tahap 7
**TERJAWAB pada Tahap 7:** “Dokter Lab” adalah teknisi atau penanggung jawab produksi dental lab, bukan otomatis dokter gigi berizin. Lihat Bagian 10.

## 9. Status desain
Ini adalah spesifikasi kebutuhan yang sedang berkembang, bukan software aktif. Hak akses, proses klinis, perlindungan data kesehatan, dan kontrol pembayaran harus diuji serta divalidasi sebelum dipakai pada operasional nyata.


---

## 10. Pembaruan Tahap 7 — Klarifikasi Dokter Lab (DITETAPKAN OLEH PENGGUNA)

**Pernyataan pengguna:** “Dokter Lab” adalah **teknisi atau penanggung jawab produksi dental laboratory** yang biasa disebut “Dokter Lab” secara internal, **bukan kategori dokter gigi klinik**.

**Status kebutuhan: Terkonfirmasi.** Istilah “Dokter Lab” dapat ditampilkan sebagai **alias internal**, tetapi nama peran fungsional di perangkat lunak adalah **Penanggung Jawab Lab** atau **Teknisi Lab** agar tidak mencampurkan kewenangan medis dengan proses teknis. Apabila seseorang juga merupakan dokter gigi berizin, kewenangan klinis harus diberikan melalui **peran dan verifikasi kredensial yang terpisah**, bukan diwariskan dari jabatan lab.

### 10.1 Matriks tanggung jawab dan hak akses (rancangan dasar)

| Peran | Boleh melakukan | Tidak boleh secara default |
|---|---|---|
| Resepsionis | Registrasi pasien/order; melihat petugas terjadwal dan indikator beban kerja; **mengusulkan atau membuat penugasan administratif** sesuai kebijakan; melihat progres ringkas | Mengubah diagnosis/instruksi klinis, hasil QC, menyetujui pekerjaannya sendiri, melihat seluruh rekam medis |
| Dokter Klinik (dokter gigi dengan kewenangan sesuai kredensial) | Pemeriksaan dan catatan klinis; instruksi/permintaan pekerjaan lab untuk pasien yang ditanganinya; tinjau hasil yang dikembalikan | Menyembunyikan jejak revisi, mengubah ledger pembayaran, mengakses kasus lain tanpa dasar |
| Penanggung Jawab Lab (disebut “Dokter Lab” internal) | Menerima/menolak order administratif dengan alasan; menilai kapasitas produksi; membagi tugas teknisi dan CAD/CAM; mengelola progres, prioritas, eskalasi kendala | Membuat diagnosis, meresepkan tindakan, menandatangani instruksi klinis dokter, mengubah invoice/pembayaran |
| Teknisi Lab | Membuka pekerjaan yang ditugaskan; mengisi tahap kerja, bahan, durasi, kendala dan output teknis | Membuka seluruh pasien, menyetujui instruksi klinis, mengubah biaya, menandai QC lulus tanpa otorisasi |
| CAD/CAM | Membuka file desain dan spesifikasi teknis kasus yang ditugaskan; mengunggah revisi desain | Mengakses riwayat klinis yang tidak perlu; menandatangani instruksi medis; mengubah kas |
| QC | Memeriksa kualitas menurut checklist teknis, menahan atau mengembalikan pekerjaan, mengunggah temuan | Menghapus histori kegagalan QC atau mengubah persetujuan klinis |
| FAT | Menerima data penagihan yang relevan, verifikasi pembayaran, rekonsiliasi, piutang dan laporan keuangan | Membaca rincian klinis tidak diperlukan, mengubah hasil diagnosis/instruksi klinis |
| Direktur/Manajemen | Dashboard agregat dan akses detail sesuai kewenangan formal, penyelesaian eskalasi/approval | Melakukan koreksi transaksi yang menghapus histori atau melampaui aturan privasi otomatis |

**Ketentuan:** Matriks ini adalah rancangan izin awal; butuh pengesahan SOP, aturan medis dan privasi sebelum penerapan. Pemisahan akses mengikuti peran, unit/cabang, penugasan per kasus, dan prinsip data minimum.

### 10.2 Alur order pasien Klinik → Lab

1. **Resepsionis Klinik:** registrasi pasien, menampilkan daftar **Dokter Klinik** terjadwal hadir pada hari itu, status ketersediaan dan antrean; melakukan booking/penugasan sesuai izin.
2. **Dokter Klinik:** memeriksa pasien. Bila membutuhkan pekerjaan laboratorium, dokter menerbitkan **permintaan lab yang telah diotorisasi**, mencantumkan spesifikasi klinis yang relevan.
3. **Antrian masuk Lab:** sistem membuat *lab order* dari permintaan klinis terotorisasi, memakai referensi pasien/kunjungan, dokter pengirim, deadline, instruksi, dan daftar item kerja; hindari pencatatan ulang.
4. **Resepsionis Lab (atau FO sesuai SOP):** melihat daftar **Penanggung Jawab Lab/Teknisi Lab** yang dijadwalkan dan kapasitas mereka; mengajukan/menetapkan penugasan administratif sesuai kebijakan yang akan diputuskan.
5. **Penanggung Jawab Lab:** mengonfirmasi penerimaan pekerjaan, membagi tahap kerja ke teknisi, CAD/CAM dan QC; satu penanggung jawab dapat menangani **banyak order paralel**. Perubahan penanggung jawab harus menyimpan alasan dan sejarah penugasan.
6. **Teknisi dan CAD/CAM:** melaksanakan tugas yang ditugaskan; status tahapan, bahan, lampiran dan revisi terlacak per order/item.
7. **QC:** mencatat hasil pemeriksaan mutu; pekerjaan yang gagal kembali ke proses terkait tanpa menghapus riwayat.
8. **Lab → Klinik:** hasil yang lolos pemeriksaan teknis dikirim kembali ke klinik untuk pemeriksaan/penerimaan menurut kewenangan dokter klinik. Keputusan klinis **bukan** kewenangan QC teknis atau teknisi.
9. **Keuangan:** transaksi jasa klinik dan pekerjaan lab mengikuti sumber order serta kebijakan penagihan yang akan ditentukan; FAT tidak mendapatkan akses penuh ke rekam medis.

**Order eksternal:** kebutuhan order dari klinik/dokter luar **belum terjawab**. Struktur data boleh mengakomodasi sumber `internal`/`external`, namun alur eksternal belum boleh dianggap final.

### 10.3 Entitas dan aturan database

- `staff_profile` dan `staff_role`: jabatan resmi, sebutan internal, unit, cabang, kredensial yang relevan. Seseorang boleh memegang beberapa peran **dengan izin terpisah**.
- `work_shift`, `attendance`, `availability_slot`: jadwal, kehadiran, cuti, status tersedia/sibuk, kapasitas kerja. Kehadiran tidak otomatis berarti kompeten/berwenang atas semua jenis order.
- `clinical_lab_request`: `patient_id`, `encounter_id`, `ordering_dentist_id`, spesifikasi, lampiran, status pengesahan, versi. Hanya dokter klinik yang berwenang (sesuai SOP/kredensial) mengesahkan instruksi klinis.
- `lab_order` dan `lab_order_item`: referensi permintaan klinis, sumber order, jenis pekerjaan, prioritas, tanggal janji, status, kode pasien tersamarkan bila memungkinkan.
- `lab_assignment`: `lab_order_id`, `assigned_to`, `assigned_by`, `assigned_at`, `accepted_at`, `reassigned_reason`, status, riwayat immutable per peristiwa.
- `production_task`, `cadcam_asset`, `qc_inspection`, `status_event`: pekerjaan paralel, file desain, checkpoint kualitas, status item/order dan jejak perubahan.
- `access_grant`/`permission`, `audit_event`: izin *least privilege* serta jejak akses data sensitif dan perubahan pekerjaan.

**Kontrol wajib rancangan:** tidak bisa membuat pekerjaan lab klinik dari instruksi belum diotorisasi; petugas hanya melihat order yang menjadi tugasnya (dan ringkasan antrean sesuai tugas); audit pemindahan order; pembatasan unggah dan unduh file klinis; backup dan pengujian pemulihan; MFA untuk operasi sensitif; tidak ada pemberian hak medis otomatis akibat sebutan “Dokter Lab”.

### 10.4 Hal yang masih terbuka

- Kebijakan final persetujuan DP dan cicilan, batas kewenangan dan tenor.
- Order lab eksternal dari praktik/klinik lain.
- Apakah ada resepsionis terpisah untuk lab dan klinik.
- Kapasitas per teknisi/penanggung jawab dan mekanisme prioritas.
- **Mekanisme penugasan order:** manual oleh resepsionis, otomatis berdasarkan ketersediaan/beban kerja, atau rekomendasi otomatis yang disahkan manusia.

### 10.5 Pertanyaan tunggal Tahap 8

**Bagaimana kamu ingin resepsionis memilih Penanggung Jawab Lab dan Dokter Klinik yang mendapat order?**

A. Manual: resepsionis memilih dari daftar yang tersedia.
B. Otomatis: sistem menugaskan menurut jadwal, kompetensi, dan beban kerja.
C. Semi-otomatis (rekomendasi): sistem menyarankan kandidat tersedia berdasarkan jadwal, kewenangan dan beban kerja; resepsionis memilih/menyetujui, dan petugas lab mengonfirmasi penerimaan untuk order produksi.
D. Belum tahu: minta perbandingan lebih rinci.

### 10.6 Status implementasi

Dokumen ini **spesifikasi kebutuhan, bukan software yang sudah berjalan**. Model data dan kebijakan akses masih perlu validasi operasional, keamanan, dan kepatuhan sebelum coding produksi dan go-live.


---

## 11. Pembaruan Tahap 8 — Penugasan Semi-Otomatis (DIPILIH PENGGUNA)

**Keputusan pengguna (19 Oktober 2026):** Penugasan untuk **Dokter Klinik** dan **Penanggung Jawab Lab** menggunakan metode **semi-otomatis**. Sistem menghasilkan rekomendasi berdasarkan petugas yang tersedia, resepsionis memilih dari kandidat yang layak, dan **Penanggung Jawab Lab wajib mengonfirmasi penerimaan order lab**. Keputusan mekanisme ini terkonfirmasi; ambang prioritas, SLA, dan tata cara penolakan masih menunggu penetapan.

### 11.1 Aturan operasional yang ditetapkan sebagai kebutuhan
1. **Dua antrean berbeda:** antrean pasien/kunjungan dokter klinik dan antrean pekerjaan dental lab; keduanya terintegrasi melalui `clinical_lab_request` dan `lab_order` ketika pekerjaan berasal dari klinik.
2. **Hanya petugas layak yang direkomendasikan:** status kerja aktif, dijadwalkan dan benar-benar hadir, berada di unit/cabang yang sah, memiliki kompetensi/jenis layanan sesuai tugas, dan kapasitas yang memadai. Status *available* tidak boleh ditentukan dari jadwal saja.
3. **Rekomendasi bukan keputusan otomatis:** sistem memberi daftar kandidat dan alasan ringkas (contoh: tersedia, jenis pekerjaan sesuai, beban relatif ringan); petugas resepsionis yang diberi kewenangan memilih kandidat, dengan alasan bila menyimpang dari rekomendasi.
4. **Konfirmasi lab wajib:** order lab berstatus *menunggu konfirmasi* setelah dipilih oleh resepsionis; Penanggung Jawab Lab yang dipilih dapat menerima atau menolak **dengan alasan**, sesuai SLA yang nantinya ditetapkan. Order tidak dianggap sedang diproduksi sebelum diterima.
5. **Klinik dibedakan:** resepsionis memilih Dokter Klinik sesuai slot jadwal, jenis layanan, dan ketersediaan. Dokter Klinik tidak boleh dianggap menyetujui tindakan medis hanya karena mendapat booking/penugasan; keputusan klinis tetap oleh dokter sesuai kewenangan.
6. **Satu penanggung jawab, banyak order:** tiap order memiliki identitas, nomor, tenggat, tahapan, bobot kerja, dan riwayatnya sendiri; sistem menghitung beban dari **pekerjaan aktif dan estimasi kapasitas**, bukan jumlah order mentah semata.
7. **Penolakan, kedaluwarsa konfirmasi, atau perubahan staf** kembali ke antrean pengecualian; jangan memindahkan otomatis ke orang lain tanpa kebijakan yang eksplisit. Mekanisme eskalasi final menjadi pertanyaan Tahap 9.
8. Order laboratorium yang bersumber dari klinik wajib merujuk **permintaan klinis yang sudah diotorisasi**; resepsionis tidak boleh mengubah resep kerja atau instruksi klinis. Lab memperoleh atribut minimum yang dibutuhkan untuk pengerjaan.

### 11.2 Alur status yang diusulkan

**Klinik:** `terdaftar` → `menunggu penugasan` → `dokter dijadwalkan` → `menunggu kedatangan` → `sedang dilayani` → `selesai/ditindaklanjuti`. Reschedule dan ketidakhadiran menggunakan status/riwayat khusus. Booking tidak sama dengan keputusan medis.

**Lab:** `order diterima sistem` → `siap ditugaskan` → `menunggu konfirmasi PJ Lab` → (`diterima` → `produksi` → `QC` → `siap dikirim` → `terkirim` → `diterima klinik/pemesan`) atau (`ditolak/kedaluwarsa` → `butuh penugasan ulang`). Gagal QC harus kembali ke tahap produksi/revisi tanpa menghapus jejak sebelumnya. Status final dan penerima hasil perlu divalidasi dalam SOP.

**Transisi aman:** setiap perpindahan status divalidasi server berdasarkan jenis order, peran, penugasan, kelengkapan instruksi, dan kebijakan; perubahan status beserta alasan/aktor/waktu disimpan sebagai event terpisah.

### 11.3 Kriteria ranking rekomendasi (rancangan awal)
1. Hard filter sebelum ranking: jenis peran, unit/cabang, kehadiran, izin/kompetensi, slot kerja, status nonaktif/cuti, konflik jadwal, serta pembatasan akses kasus.
2. Ranking di antara kandidat layak: beban kerja **berbobot durasi/kompleksitas**, tenggat dan urgensi, keahlian, kesinambungan kasus, dan pemerataan penugasan.
3. Jangan gunakan data medis sensitif yang tidak perlu untuk tampilan resepsionis. Paparkan hanya nama petugas, status/slot, kompetensi kerja relevan, indikator kapasitas, dan alasan rekomendasi yang aman.
4. Rekomendasi harus dihitung ulang saat pemilihan/konfirmasi untuk menghindari konflik dua resepsionis menugaskan slot yang sama; gunakan transaksi atomik/optimistic locking dan pembatas kapasitas.
5. Belum menetapkan bobot penilaian, batas kapasitas, waktu konfirmasi atau lama eskalasi. Harus disepakati setelah mempelajari data operasional.

### 11.4 Hak akses dan keamanan
| Aktor | Hak utama | Pembatasan |
|---|---|---|
| Resepsionis Klinik | Melihat slot dan kandidat Dokter Klinik; mendaftarkan pasien; memilih jadwal/penugasan | Tidak mengubah catatan/instruksi klinis, tidak memaksa slot tak tersedia tanpa prosedur pengecualian |
| Dokter Klinik | Melihat pasien/kunjungan yang ditangani; menerbitkan permintaan lab klinis terotorisasi | Tidak dapat mengesahkan permintaan atas nama dokter lain atau melihat kasus tak beralasan |
| Resepsionis Lab / FO dengan izin Lab | Melihat daftar kandidat PJ Lab dan indikator kapasitas; memilih PJ Lab; memantau status administratif | Tidak mengubah resep kerja klinis, menyatakan QC lulus, atau menerima order atas nama PJ Lab |
| Penanggung Jawab Lab | Mengonfirmasi/menolak order yang dialokasikan kepadanya; mengatur tugas teknis | Hanya kasus yang ditugaskan; bukan pemberi persetujuan medis dan bukan pembuat transaksi keuangan |
| Supervisor Lab | Meninjau antrean, konflik kapasitas, dan eskalasi/penugasan ulang sesuai persetujuan yang akan ditentukan | Tidak dapat menghapus audit trail atau mengambil alih akun lain |
| CAD/CAM, Teknisi, QC | Melihat pekerjaan/berkas teknis minimum sesuai tugas dan tahap | Tidak mengakses rekam medis penuh, penagihan penuh, atau order yang tidak ditugaskan |
| FAT dan Direktur | Melihat laporan keuangan dan KPI sesuai lingkup kewenangan | Tidak memperoleh hak untuk memodifikasi instruksi klinis dari hak finansial/manajemen |

Keamanan dasar: RBAC + *case-scoped access*, verifikasi otorisasi pada server, MFA bagi akun hak tinggi, log untuk pembuatan rekomendasi/penugasan/penolakan/penugasan ulang/unduh data sensitif, dan perlindungan informasi pasien dalam notifikasi. Akses organisasi besar dan multiklinik harus tersegmentasi per cabang/tenant. Admin IT tidak otomatis berhak membuka rekam medis.

### 11.5 Dampak pada antrian dan efisiensi
- Satu dashboard antrean klinik dan satu dashboard antrean lab dengan status, pemilik tugas, SLA, prioritas, dan usia order; manajemen melihat KPI lintas unit tanpa memerlukan akses ke isi klinis seluruh pasien.
- Sistem dapat mengurangi ketimpangan beban dan antrean terlupakan, tetapi keakuratan rekomendasi bergantung pada data jadwal, kehadiran, kapasitas, dan estimasi waktu kerja yang benar.
- Perlu indikator: waktu tunggu penugasan, durasi konfirmasi, persentase penolakan/penugasan ulang, workload berbobot per staf, order lewat tenggat, dan turnaround time QC/produksi.
- Jika tidak ada kandidat layak, buat status `butuh intervensi supervisor`, bukan memaksakan penugasan pada staf tidak hadir/tidak kompeten.

### 11.6 Entitas tambahan dan constraints
- `assignment_recommendation`: request_id/order_id, role_type, candidate_id, score_breakdown_safe, algorithm_version, generated_at, expires_at (untuk evaluasi; tidak menggantikan keputusan manusia).
- `case_assignment`: order_id/appointment_id, assignee_id, assigned_by, selected_at, status, confirmation_deadline, accepted_at, rejection_reason, version.
- `assignment_event`: assignment_id, event_type, actor_id, timestamp, from/to, reason, correlation_id (append-only untuk audit).
- `staff_skill`, `shift`, `attendance`, `availability_slot`, `workload_estimate`: atribut untuk filter kelayakan dan kapasitas; sumber kehadiran wajib jelas.
- `order_priority`, `order_deadline`, `order_type`, `stage_estimate`: dasar antrean dan pelaporan prioritas.
- Constraint untuk menghindari dua penugasan aktif yang tidak kompatibel pada kasus/slot yang sama; validasi ulang kapasitas & wewenang pada saat commit. Penolakan dan pengalihan tidak menghapus riwayat penugasan lama.

### 11.7 Kriteria penerimaan awal (untuk pengujian kemudian)
1. Resepsionis tidak bisa memilih dokter/teknisi yang cuti atau tidak mempunyai kompetensi kerja yang diwajibkan.
2. Sistem dapat menampilkan beberapa kandidat tersedia hari ini beserta alasan rekomendasi yang tidak mengungkap data medis sensitif.
3. Penugasan Lab berada di status `menunggu konfirmasi` sampai PJ Lab yang tepat menerimanya menggunakan akunnya sendiri.
4. Penolakan PJ Lab mencatat alasan, waktu, pelaku, dan mengembalikan order ke antrean tindak lanjut.
5. Dua petugas yang berebut slot/ketersediaan yang sama tidak dapat menghasilkan dua komitmen berkonflik.
6. Resepsionis tidak dapat membaca/mengubah instruksi medis atau memalsukan konfirmasi penerimaan PJ Lab.
7. Order lab dari klinik terhubung ke permintaan klinis yang diotorisasi; tidak dibuat dua kali akibat penekanan tombol/gangguan jaringan.
8. Semua pemindahan penugasan tercatat; supervisor bisa mengaudit siapa, kapan, dan mengapa order dipindah.

### 11.8 Pertanyaan tunggal Tahap 9 — Mekanisme jika PJ Lab menolak/tidak konfirmasi
**Jika Penanggung Jawab Lab menolak order atau tidak mengonfirmasi sampai batas waktu, siapa yang berwenang menentukan penugasan penggantinya?**
- A. Resepsionis langsung memilih kandidat lain dari rekomendasi sistem.
- B. Supervisor Lab yang memilih dan menetapkan pengganti.
- C. Sistem menyarankan pengganti; resepsionis mengajukan dan Supervisor Lab menyetujui (rekomendasi awal untuk kasus penolakan/eskalasi).
- D. Belum tahu; minta perbandingan risiko dan prosedur operasional.

**Belum diputuskan:** SLA konfirmasi dan eskalasi, siapa yang boleh memindahkan order yang sudah dalam proses produksi, batas prioritas darurat, dan aturan saat supervisor tidak ada.

**Catatan keseluruhan:** Dokumen ini adalah rancangan kebutuhan. Belum ada aplikasi/database operasional yang dibangun; perlu validasi SOP, pengujian keamanan dan kepatuhan regulasi sebelum menggunakan data riil.


---

## 12. Pembaruan Tahap 9 — Penugasan Ulang Lab, Persetujuan Pasien Klinik, dan Antrean ETA Lab (DIPILIH PENGGUNA)

**Keputusan pengguna (19 Oktober 2026):**
1. **Penugasan ulang Lab:** saat order Lab ditolak atau belum dikonfirmasi, sistem merekomendasikan petugas pengganti; resepsionis mengajukan; **Supervisor Lab menyetujui**.
2. **Dokter Klinik:** jika dokter klinik yang telah direncanakan tidak tersedia, resepsionis menawarkan dokter pengganti yang relevan dan harus **mengonfirmasi pilihan dengan pasien** sebelum penjadwalan pengganti dinyatakan final.
3. **Laboratorium:** pekerjaan dapat **ditampung dalam antrean** meskipun kapasitas saat ini penuh, dan pihak pemesan diberitahu estimasi pengerjaan yang dapat dipertanggungjawabkan. Estimasi **tidak boleh otomatis diperlakukan sebagai janji tetap** sebelum divalidasi menurut kebijakan.

**Batas makna:** “Dokter Lab” adalah sebutan internal untuk **Penanggung Jawab Lab/Teknisi**, bukan jabatan dokter gigi berizin. Persetujuan pasien atas *pergantian jadwal/dokter* berbeda dari persetujuan tindakan medis (*informed consent*). Pada order eksternal, “pelanggan/pemesan Lab” dapat berupa dokter/klinik pengirim; bukan otomatis pasien.

### 12.1 Alur pengganti dokter klinik dan konfirmasi pasien
1. Ketika dokter utama berhalangan, sistem menandai slot penjadwalan sebagai `needs_reassignment`; appointment tidak boleh diam-diam dialihkan tanpa pemberitahuan.
2. Resepsionis melihat rekomendasi **Dokter Klinik** yang tersedia sesuai kompetensi layanan, jadwal, lokasi, dan kapasitas. Daftar tidak boleh mencampur teknisi Lab.
3. Penawaran ke pasien dicatat sebagai `replacement_offered` dengan dokter alternatif, media pemberitahuan, waktu, dan petugas penghubung. Jangan cantumkan diagnosis atau detail medis tidak perlu dalam pesan.
4. Pasien memilih **setuju**, **menolak/meminta dokter lain**, atau **minta jadwal ulang**; status `awaiting_patient_confirmation` sampai ada jawaban.
5. Setelah pasien setuju dan sistem memvalidasi ulang slot, jadwal ditetapkan menjadi `replacement_confirmed`. Jika menolak, usulkan alternatif; bila tak ada pilihan cocok, lakukan penjadwalan ulang/eskalasi sesuai kebijakan.
6. Bukti konfirmasi sesuai kanal dan dasar pemrosesan yang berlaku disimpan seminimal mungkin, dengan kontrol akses dan retensi yang tepat. Petugas tidak boleh mencatat konfirmasi palsu atau mewakili persetujuan pasien.
7. Dokter Klinik tetap bertanggung jawab atas keputusan klinis. Perubahan dokter tidak menyetujui prosedur medis dengan sendirinya.

### 12.2 Alur order Lab penuh atau menunggu kapasitas
1. Order Lab dengan instruksi kerja yang valid diterima ke antrean terpusat dan diperiksa kelengkapan, sumber order internal/eksternal, prioritas, dan kompetensi yang diperlukan.
2. Jika kapasitas Lab saat ini penuh atau PJ belum tersedia, set `waiting_for_scheduling` atau `awaiting_capacity`; **jangan mengklaim sudah diproduksi**. Order tetap terpantau, tidak hilang atau dibuat ulang.
3. Sistem menghitung **usulan estimasi mulai** dan **usulan estimasi selesai** memakai antrean berbobot, kalender staf, jenis pekerjaan, durasi tiap tahap (produksi, CAD/CAM, QC), bahan yang tersedia, dan hari libur. Jika data belum cukup, tampilkan `estimasi belum dapat dipastikan` dan lakukan estimasi manual terotorisasi.
4. Penanggung jawab yang ditetapkan oleh kebijakan (masih ditanyakan pada Tahap 10) meninjau dan mengesahkan estimasi sebelum disampaikan sebagai *estimasi resmi*. Catat asumsi dan versi estimasi.
5. Resepsionis/CS menyampaikan estimasi beserta sifatnya (perkiraan, belum janji pasti) kepada **pemesan yang sah**: pasien atau klinik/dokter pengirim sesuai sumber order dan kesepakatan komunikasi. Catat `communicated_at`, `communicated_by`, `recipient_type`, `channel`, dan versi ETA.
6. Jika ETA bergeser, sistem menandai perubahan, mengirim tugas pemberitahuan, dan mencatat kapan pemesan diinformasikan. Tidak boleh mengubah tanggal yang sudah diinformasikan tanpa jejak.
7. Saat penugasan memerlukan penggantian PJ setelah penolakan/tidak konfirmasi, sistem menampilkan kandidat; resepsionis mengajukan, **Supervisor Lab menyetujui** dan petugas baru tetap mengonfirmasi penerimaan order sesuai mekanisme Tahap 8. Hindari *self-approval* oleh pengaju.
8. Kasus keterlambatan, order urgent, atau tidak ada kandidat yang kompeten masuk antrean eskalasi Supervisor Lab; pengecualian tidak boleh melewati persyaratan kompetensi dan QC.

### 12.3 Hak akses dan segregation of duties

| Peran | Hak yang diusulkan | Larangan utama |
|---|---|---|
| Resepsionis Klinik | Menawarkan dokter pengganti, mencatat tanggapan pasien, memperbarui jadwal sesuai konfirmasi | Menyatakan persetujuan tanpa pasien, mengubah diagnosis/instruksi medis |
| Dokter Klinik | Mengakses encounter/catatan pasien yang ditanganinya, keputusan klinis, dan instruksi Lab | Mengatasnamakan dokter lain tanpa kewenangan |
| Resepsionis/CS Lab | Memasukkan order valid, mengajukan pengalihan, menginformasikan ETA yang sudah ditinjau | Menyetujui pengalihannya sendiri, menjanjikan tanggal final secara sepihak, mengubah resep klinis |
| Penanggung Jawab Lab | Menerima/menolak order, mengatur pekerjaan teknis, meninjau kelayakan durasi sesuai kewenangan | Memberi keputusan medis dan menghapus jejak kerja |
| Supervisor Lab | Menyetujui/menolak pengalihan yang diajukan, menangani keterlambatan, meninjau kapasitas | Menghapus audit atau mengambil alih akun petugas |
| Teknisi/CAD-CAM/QC | Mengerjakan dan memperbarui tahapan teknis sesuai penugasan | Mengakses rekam medis penuh, menetapkan persetujuan pasien |

Khusus penugasan Dokter Klinik, apakah penggantian memerlukan persetujuan supervisor klinik selain pasien **belum diputuskan**; jangan mengalihkan wewenang Supervisor Lab ke Klinik.

### 12.4 Entitas database tambahan
- `clinical_appointment_change`: `appointment_id`, `original_dentist_id`, `proposed_dentist_id`, `status`, `offered_by`, `offered_at`, `confirmed_at`, `confirmation_channel`, `patient_response`, `slot_version`.
- `patient_communication`: `subject_type`, `subject_id`, `recipient_category`, `channel`, `purpose`, `sent_at`, `outcome`, `actor_id`, `reference` (tanpa menyimpan detail medis tak perlu).
- `lab_capacity_plan`: `order_id`, `workload_minutes`, `required_skill`, `work_stage`, `staff_availability_snapshot`, `revision`.
- `lab_eta_revision`: `order_id`, `estimated_start`, `estimated_finish`, `confidence_or_range`, `assumptions`, `proposed_by`, `approved_by`, `approved_at`, `reason`, `revision`.
- `lab_eta_communication`: `order_id`, `eta_revision_id`, `recipient_type`, `recipient_ref`, `channel`, `communicated_by`, `communicated_at`, `delivery_status`.
- `reassignment_request`: `order_id`, `previous_assignee`, `proposed_assignee`, `requested_by`, `requested_at`, `reason`, `approved_by`, `approved_at`, `status`.
- Gunakan audit event append-only dan transaksi atomik untuk menghindari slot ganda, persetujuan palsu, perubahan ETA tanpa riwayat, dan order yang menghilang dari antrean.

### 12.5 Pengujian penerimaan (harus lulus sebelum rilis)
1. Pergantian Dokter Klinik tidak menjadi final saat pasien belum menyetujui.
2. Penolakan pasien tidak menghapus jadwal atau riwayat penawaran sebelumnya dan menghasilkan opsi tindak lanjut.
3. Order Lab yang kapasitasnya penuh tetap terlihat dengan status menunggu, tanpa dianggap sedang diproduksi.
4. Estimasi mulai dan estimasi selesai dipisahkan; jika datanya kurang, sistem tidak membuat janji palsu.
5. Pemesan yang sah menerima informasi estimasi terbaru, dan histori revisi maupun notifikasi bisa diaudit.
6. Resepsionis tidak bisa menyetujui pengalihan Lab yang diajukannya sendiri; hanya Supervisor Lab yang mempunyai otorisasi.
7. Setelah pengalihan disetujui, penanggung jawab baru harus tetap menerima/menolak menggunakan akunnya sendiri.
8. Petugas Lab tidak mendapat akses rekam medis lengkap hanya karena melihat order atau estimasinya.

### 12.6 Isu yang masih terbuka
- Siapa yang memiliki otoritas final menyetujui estimasi mulai/selesai Lab sebelum diinformasikan (Tahap 10).
- Apakah pasien harus konfirmasi via saluran tertentu (telepon, WhatsApp, aplikasi) dan bukti apa yang sah.
- Waktu tenggat konfirmasi order dan durasi eskalasi ketika supervisor tidak tersedia.
- Apakah order eksternal Lab diterima; jenis pemesan dan pihak yang berhak menerima notifikasi.
- Apakah estimasi cukup berupa rentang atau tanggal pasti, serta aturan revisi jika bahan/QC terlambat.

### 12.7 Pertanyaan tunggal Tahap 10
**Siapa yang berwenang menetapkan dan menyetujui estimasi pengerjaan/penyelesaian Lab sebelum resepsionis menyampaikannya kepada pemesan?**
- A. Resepsionis menghitung dan menyampaikan langsung.
- B. Penanggung Jawab Lab menentukan ETA dan resepsionis menyampaikannya.
- C. Sistem mengusulkan ETA berdasarkan antrean; Penanggung Jawab/Supervisor Lab memvalidasi dan menyetujui; resepsionis menyampaikan (rekomendasi).
- D. Belum diputuskan; butuh rekomendasi lebih lanjut.

**Status:** Spesifikasi v0.9 merupakan dokumen kerja, **bukan perangkat lunak produksi**. Diperlukan konfirmasi SOP, kontrol keamanan, uji beban dan uji privasi sebelum implementasi data nyata.


---

## 13. Pembaruan Tahap 10 — ETA Otomatis, Validasi Lab, dan Komunikasi Customer (DISETUJUI PENGGUNA)

**Keputusan pengguna (19 Oktober 2026):** **Sistem menghitung estimasi berdasarkan antrean dan kapasitas; Penanggung Jawab/Supervisor Lab memvalidasi; resepsionis menyampaikan.** Ini adalah kebijakan fungsional NAM DMS yang telah dipilih, **belum merupakan fitur yang diimplementasikan**.

### 13.1 Aturan operasional terkonfirmasi
1. Perhitungan estimasi (*Estimated Time of Arrival/Completion*, ETA) disediakan oleh mesin penjadwalan produksi, bukan dihitung sendiri oleh resepsionis. Untuk istilah yang lebih akurat, gunakan **perkiraan waktu mulai** dan **perkiraan waktu selesai** pekerjaan Lab.
2. Mesin estimasi mempertimbangkan antrean serta **kapasitas nyata** teknisi, shift, hari libur, kompetensi spesifik, variasi tingkat kesulitan, tahap CAD/CAM, produksi, finishing, QC, ketersediaan bahan/alat dan kapasitas mesin. Untuk sumber yang tidak tersedia, tampilkan asumsi/keterbatasan secara eksplisit.
3. ETA keluaran sistem diberi status **draft/usulan** terlebih dahulu; tidak dapat disampaikan sebagai estimasi resmi sampai **Penanggung Jawab atau Supervisor Lab berwenang memvalidasi/menyetujui** menggunakan akun sendiri.
4. Resepsionis/Customer Service hanya boleh mengkomunikasikan **versi ETA yang telah disetujui** kepada pemesan yang berhak (pasien klinik atau dokter/klinik pemesan, tergantung sumber order). Jangan membuka data klinis yang tidak diperlukan.
5. Order tetap boleh diterima dalam **antrean menunggu kapasitas**, tetapi tidak boleh ditandai sedang dikerjakan, ataupun diberi kepastian tenggat tanpa penilaian kapasitas.
6. Perubahan yang bermakna terhadap estimasi yang sudah diinformasikan harus menghasilkan **revisi baru**, alasan, pemeriksaan ulang, tugas pemberitahuan, dan catatan komunikasi, tanpa menghapus versi sebelumnya.
7. Kewenangan klinis dokter gigi tetap terpisah dari pengelolaan produksi Lab; revisi jadwal tidak boleh digunakan untuk mengubah instruksi klinis tanpa persetujuan dokter klinik yang berwenang.

### 13.2 Mesin estimasi — rancangan awal

**Input:** jenis pekerjaan, jumlah unit, kebutuhan skill dan teknologi, daftar tahapan wajib, durasi standar historis per tahap, lead-time bahan, antrean aktif yang sudah diotorisasi, kapasitas staf dan alat, status kehadiran/shift, QC/rework, prioritas yang sah, waktu cut-off, dan kalender kerja.

**Proses:**
1. Validasi order dan semua instruksi yang diperlukan; untuk order dari klinik internal, permintaan klinis harus disahkan dokter klinik terlebih dahulu.
2. Pecah order menjadi tahap seperti *intake → CAD/CAM (jika ada) → produksi → finishing → QC → siap kirim*. Identifikasi tahap yang bisa paralel dan yang harus menunggu hasil tahap sebelumnya.
3. Hitung antrian berbobot berdasarkan estimasi durasi, bukan sekadar jumlah order; hindari alokasi ganda staf/mesin di periode yang sama.
4. Terapkan kalender kapasitas, kehadiran, ketergantungan bahan dan jeda pengujian. Sisihkan kapasitas cadangan/ketidakpastian yang besarnya harus diputuskan secara operasional, bukan diada-adakan.
5. Buat **estimated_start**, **estimated_finish**, dan idealnya **range atau tingkat keyakinan** dari asumsi yang dipakai. Bila data terlalu lemah, hasil menjadi `unavailable_pending_review`/"estimasi belum dapat dipastikan".
6. Tampilkan ringkasan alasan kepada PJ/Supervisor Lab (misalnya antrian 2 hari, tahap produksi 1 hari, QC 1 hari) agar keputusan bukan sekadar persetujuan buta.
7. Setelah disetujui, resepsionis dapat menyampaikan estimasi resmi dengan cap versi. SLA/janji kontraktual **tidak otomatis sama** dengan perkiraan ETA.

**Catatan:** Keakuratan mesin ETA perlu diuji menggunakan data historis; bobot durasi per produk, tingkat buffer, cut-off, dan target SLA **belum ditetapkan**. Tidak boleh menyebut sistem AI yang akurat tanpa data dan evaluasi yang memadai; kalkulasi berbasis aturan dan kapasitas yang dapat diaudit lebih tepat sebagai fase awal.

### 13.3 Hak akses dan pemisahan tanggung jawab

| Peran | Diizinkan | Dibatasi |
|---|---|---|
| Resepsionis Klinik/Lab dan CS | Melihat ETA draft sebagai **belum disetujui** untuk perencanaan internal; mengirim ETA versi approved kepada pemesan sah; mencatat komunikasi | Tidak mengubah angka ETA approved atau menekan tombol persetujuan atas nama Lab |
| Sistem penjadwalan | Menghasilkan rekomendasi ETA berdasarkan sumber data terverifikasi, mencatat algoritme dan versi parameter | Tidak membuat janji waktu resmi tanpa langkah validasi |
| Penanggung Jawab Lab | Memeriksa aspek teknis, merevisi usulan dengan alasan, mengesahkan sesuai delegasi operasional | Tidak mengubah catatan medis, keuangan, atau menghapus audit |
| Supervisor Lab | Memvalidasi kasus kompleks/penyimpangan, menilai dampak kapasitas, eskalasi keterlambatan | Tidak boleh menyetujui sebagai akun staf lain; tidak menghapus riwayat ETA |
| Teknisi / CAD-CAM / QC | Memperbarui status tahap, output, kapasitas dan kendala teknis untuk bahan perhitungan | Tidak menyampaikan tanggal final ke customer atas nama resepsionis tanpa izin |
| Direktur/manajemen | Melihat metrik akurasi ETA, backlog dan keterlambatan berdasarkan kebutuhan tugas | Tidak otomatis mendapat akses bebas ke seluruh data kesehatan pasien |

Jika PJ Lab sekaligus pembuat override angka ETA, usulan diberi jejak alasan dan dapat memerlukan review Supervisor Lab untuk pengecualian berisiko. **Matriks kapan persetujuan Supervisor diperlukan** belum ditentukan; sistem harus bisa dikonfigurasi.

### 13.4 Status alur estimasi

`not_calculable` / `draft_calculated` → `pending_lab_review` → (`approved` | `rejected_for_revision`) → `communicated_to_customer` → [bila ada perubahan] `superseded` dan buat **revisi baru** mulai dari `draft_calculated`.

Setiap versi ETA memiliki identitas dan tanggal berlaku, status, pengaju/perhitungan, reviewer, alasan override, tanggal approval, dan hubungan ke komunikasi kepada pemesan. Status `approved` tidak berarti order pasti selesai pada tanggal tersebut; penundaan harus dilaporkan sesuai kebijakan layanan dan kontrak.

### 13.5 Risiko, pengendalian dan penanganan pengecualian

| Risiko | Pengendalian wajib dalam rancangan |
|---|---|
| Estimasi terlalu optimistis karena staf/machine overloaded | Reservasi kapasitas berbasis jadwal nyata, perhitungan ulang saat data berubah, kalibrasi data historis |
| Bahan habis atau mesin rusak | Integrasi status inventory, purchasing/maintenance, serta penanda estimasi belum dapat dipastikan bila perlu |
| Produk gagal QC atau remake | Rework menjadi tahap tambahan dengan durasi dan alasan terukur; revisi ETA, bukan sembunyikan keterlambatan |
| Resepsionis menjanjikan ETA yang belum diperiksa | Tampilan jelas `DRAFT — BUKAN UNTUK DIKIRIM`, blokir template notifikasi ETA resmi sebelum approved |
| ETA diubah diam-diam demi KPI | Versioning append-only, perubahan dengan alasan, audit log tahan manipulasi dan laporan deviasi |
| Reviewer melakukan persetujuan kosong/tidak kompeten | Validasi jabatan/scope, minimal checklist kapasitas dan kendala, autentikasi ulang untuk pengecualian kritis |
| Customer salah diberitahu atau data pasien bocor | Verifikasi penerima dan kanal, kontrol akses berbasis sumber order, template notifikasi minim data klinis |
| Revisi jadwal tidak tersampaikan | Task follow-up CS/resepsionis, status pengiriman dan pencatatan tanggapan, eskalasi keterlambatan |
| Order ganda menghabiskan kapasitas | Idempotency, unique order reference, perhitungan dengan snapshot/locking saat penjadwalan |

### 13.6 Entitas database tambahan dan atribut minimal

- `production_stage_template`: tipe produk, tahap wajib, urutan/dependensi, kompetensi dan sumber daya yang diperlukan, standar durasi per versi.
- `capacity_calendar`: cabang/ruang/mesin/petugas, shift dan jam kerja tersedia, jeda, cuti, gangguan, slot terpakai.
- `material_readiness`: hubungan order dengan ketersediaan bahan dan tanggal kesiapan; tidak harus mengekspos harga atau vendor ke teknisi.
- `eta_calculation_run`: order_id, algorithm_version, input_snapshot_hash, calculated_at, estimated_start, estimated_finish, range/confidence, constraints, status, calculation_reason.
- `eta_approval`: calculation_id, approver_id, authority_scope, approved_at, decision, override_reason, status. Revisi disimpan sebagai record baru.
- `eta_revision`: order_id, revision_no, previous_eta_id, supersession_reason, proposed_by, approved_eta_id, effective_at.
- `eta_notification`: eta_revision_id, recipient_role/id, template_version, channel, status, sent_at, acknowledged_at, sent_by.
- `lab_stage_execution`: order_id, stage_id, started_at, finished_at, worker_id, blocker_reason, qc/rework_flag; menjadi data aktual untuk evaluasi akurasi.

**Persyaratan integritas:** approval hanya dapat dilakukan oleh peran yang berwenang; ETA yang dilihat saat pengiriman notifikasi harus merupakan **versi approved terakhir**; revisi dan perubahan kapasitas tidak menimpa histori, akses data dibatasi menurut cabang/kasus/peran; tanggal harus memakai timezone operasional dan timestamp audit yang konsisten.

### 13.7 Metrik untuk Dashboard Lab dan Direktur

- Jumlah order masuk, dalam antrean, sedang proses, menunggu QC, dan selesai.
- Backlog berbobot durasi serta kapasitas pemakaian per lini proses, teknisi, dan mesin.
- Akurasi ETA: deviasi antara tanggal selesai aktual dan estimasi approved pertama/terbaru.
- **On-time delivery rate**, keterlambatan per tahapan, dan jumlah revisi ETA yang dikomunikasikan.
- Lama review ETA sampai approved dan lama antara approval dan pemberitahuan customer.
- Penyebab dominan delay: material, kapasitas, rework, kendala mesin, revisi instruksi, dan sebagainya.

Pengukuran KPI harus mendorong transparansi, bukan memotivasi staf memundurkan estimasi diam-diam untuk memperbaiki angka.

### 13.8 Kriteria penerimaan tahap pengujian

1. Order dengan staf/mesin tidak tersedia tidak menghasilkan estimasi pasti yang salah tanpa penanda keterbatasan.
2. Penanggung Jawab/Supervisor Lab berwenang bisa meninjau dan menyetujui ETA, tetapi resepsionis tidak dapat menyetujui ETA miliknya sendiri atau mengubah ETA approved.
3. ETA yang dikirim ke customer selalu terkait versi approved yang benar.
4. Perubahan kapasitas/stok/QC setelah ETA approved menandai perlunya penilaian revisi, dengan histori tidak hilang.
5. Order klinik internal tidak diproses secara produksi tanpa instruksi klinis yang sah.
6. PJ/supervisor melihat dasar estimasi serta alasan manual override; semua kejadian tercatat dengan waktu, pelaku dan versi.
7. Notifikasi tidak memuat diagnosis atau data kesehatan yang tidak perlu dan tidak dikirim ke penerima tidak sah.
8. Modul berjalan benar saat dua staf memvalidasi/memperbarui order yang sama secara hampir bersamaan.
9. Pelaporan mampu menghitung deviasi estimasi versus durasi aktual per tipe pekerjaan.

### 13.9 Isu terbuka dan Tahap 11 (SATU PERTANYAAN)

**Jika estimasi penyelesaian Lab yang sudah diinformasikan harus mundur, apakah customer cukup diberi pemberitahuan, atau harus menyetujui tanggal baru sebelum jadwal dinyatakan disepakati?**

Rekomendasi awal: customer **wajib diberi tahu** jika ada perubahan material; persetujuan eksplisit diperlukan untuk perubahan komitmen/kontrak atau perubahan signifikan menurut kebijakan yang nanti ditetapkan. Belum ditentukan: siapa contact of record saat order dari klinik luar, ambang perubahan material, kanal notifikasi, dan prosedur bila customer menolak.

### 13.10 Catatan status

Dokumen v0.10 merupakan **spesifikasi rancangan**. Belum ada software produksi, mesin ETA aktif, basis data operasional, ataupun kontrol keamanan yang telah diuji. Pengembangan berikutnya memerlukan pembuktian data, SOP tertulis, pengujian performa dan keamanan, serta kajian privasi dan regulasi yang berlaku.


---

## 14. Pembaruan Tahap 11 — Customer Notification & Delay Approval (KEPUTUSAN PENGGUNA)

**Tanggal keputusan:** 19 Oktober 2026.

**Pernyataan pengguna:** **Customer wajib diberi pemberitahuan tentang perubahan estimasi Lab; persetujuan customer diperlukan apabila keterlambatan signifikan atau mengubah komitmen yang sudah disepakati.** Aturan ini menutup pertanyaan Tahap 11 di §13.9. Ambang *signifikan* dan definisi komitmen khusus masih harus ditetapkan pada Tahap 12. Sistem belum diimplementasikan.

### 14.1 Perbedaan konsep yang wajib dijaga
- **Estimasi internal:** hasil kalkulasi sistem mengenai target waktu mulai/selesai; dapat berubah berdasarkan kondisi produksi dan memiliki status draft.
- **Estimasi resmi yang diinformasikan:** revisi ETA yang telah divalidasi PJ/Supervisor Lab dan disampaikan kepada penerima yang benar. Ini tidak otomatis membentuk komitmen kontraktual.
- **Komitmen/janji layanan yang disepakati:** tanggal atau ketentuan layanan yang secara eksplisit dijanjikan atau disetujui kepada pemesan; perubahan perlu mengikuti syarat layanan dan proses persetujuan yang berlaku.
- **Penundaan signifikan:** kriteria objektif yang akan disusun berdasarkan risiko, tanggal penting, batas waktu, dan/atau ambang keterlambatan per jenis pekerjaan. **Belum ditentukan**; sistem harus dapat dikonfigurasi tanpa mengarang angka batas.
- **Customer/pemesan yang berwenang:** untuk order klinik internal dapat berupa pasien atau perwakilan yang berhak; untuk order lab eksternal dapat berupa dokter/klinik pemesan. Kontak yang berwenang dan dasar hubungan pelanggan harus diverifikasi dan tidak boleh diasumsikan sama untuk semua order.

### 14.2 Alur perubahan ETA Lab dan keterlambatan
1. **Deteksi:** perubahan pada antrean, jadwal staf, kerusakan alat, suplai bahan, produksi, QC atau permintaan pekerjaan dapat menandai risiko keterlambatan. Sistem membuat *delay risk event* tanpa otomatis mengganti ETA/komitmen yang sudah tercatat.
2. **Usulan:** mesin ETA membuat revisi yang menyimpan estimasi lama, estimasi baru, alasan, versi kalkulasi, kendala, dan dampak terhadap janji/appointment terkait. Bila input tidak cukup, tandai perlu penilaian manual, jangan mengeluarkan tanggal palsu.
3. **Validasi Lab:** Penanggung Jawab/Supervisor Lab sesuai matriks otorisasi memeriksa dan menyetujui usulan estimasi baru. Resepsionis tidak dapat memvalidasi/menyetujui revisi ETA.
4. **Klasifikasi:** evaluasi apakah hanya perubahan estimasi biasa atau termasuk signifikan/mengubah komitmen. Bila kebijakan belum dapat memutuskan otomatis, status masuk *manual review*, bukan langsung dianggap perubahan kecil.
5. **Pemberitahuan wajib:** CS/resepsionis diberi tugas untuk memberitahukan perubahan kepada customer yang berwenang; gunakan informasi minimum yang diperlukan: ID/order yang aman, tanggal lama, tanggal baru yang diusulkan, alasan umum, opsi, dan instruksi respons. Jangan memasukkan data medis sensitif dalam notifikasi umum.
6. **Persetujuan eksplisit jika diperlukan:** bila perubahan signifikan atau berpengaruh pada komitmen, customer dapat menerima, menolak, atau meminta alternatif. Status menjadi `awaiting_customer_approval` sampai persetujuan sah diterima. Tidak ada *auto-approval* karena diam, tidak membalas, atau pesan terbaca. Persetujuan yang sah memiliki identitas/otoritas penerima, versi ETA yang disetujui, waktu, kanal, serta bukti sesuai kebijakan.
7. **Jika diterima:** catat tanggal baru yang disepakati sebagai versi baru berikut hubungan ke komitmen terdahulu; jangan menghapus histori atau secara otomatis mengubah catatan medis/appointment klinik.
8. **Jika ditolak/tidak ada respons:** berikan alternatif (percepatan bila benar-benar mungkin, reschedule layanan terkait, diskusi kompensasi sesuai kebijakan, atau eskalasi). Catat status tanpa menyatakan customer telah menyetujui. Jadwal produksi boleh terus berjalan sesuai kondisi aman; persetujuan komunikasi bukan otorisasi untuk melewati QC atau memodifikasi instruksi klinis.
9. **Jika notifikasi gagal:** simpan status pengiriman gagal, ulangi melalui kanal terotorisasi, dan eskalasikan ke CS/Supervisor; status *sent* tidak sama dengan *delivered*, *acknowledged*, atau *approved*.
10. **Pemantauan & penutupan:** semua order tertunda tetap muncul di dashboard sampai penyebab, respons pelanggan, dan penanganan selesai atau tercatat secara sah.

### 14.3 Hak akses dan pemisahan tugas

| Aktor | Hak dan tanggung jawab | Pembatasan |
|---|---|---|
| Mesin estimasi | Menghitung ulang ETA dan mendeteksi potensi pelanggaran target; menampilkan dampak | Tidak boleh mengubah komitmen final secara otomatis |
| Penanggung Jawab Lab | Memvalidasi usulan ETA sesuai delegasi, memberi alasan perubahan | Tidak boleh memalsukan persetujuan customer atau mengubah data klinis |
| Supervisor Lab | Menyetujui pengecualian, memeriksa keterlambatan signifikan, menentukan opsi tindak lanjut produksi | Tidak boleh menghapus histori ETA/komitmen |
| Resepsionis / CS | Memberi pemberitahuan, mengonfirmasi penerima, mencatat tanggapan dengan bukti dan menawarkan opsi yang sudah diotorisasi | Tidak dapat membuat persetujuan atas nama customer, mengubah ETA yang sudah disetujui, atau membuka data medis penuh |
| Customer/pemesan berwenang | Menyetujui, menolak, atau meminta alternatif untuk perubahan komitmen/revisi signifikan | Tidak boleh mendapat akses ke order pasien lain atau data internal perusahaan |
| Dokter Klinik pengirim | Diberi informasi apabila keterlambatan mengganggu kunjungan atau perawatan; mengelola keputusan klinis terkait | ETA Lab tidak bisa mengubah jadwal klinik tanpa prosedur dan kewenangan klinis yang sesuai |
| Manajemen / Auditor | Memantau tren, keterlambatan, pengiriman notifikasi, dan kasus yang tak terselesaikan | Pembatasan data sensitif sesuai kebutuhan tugas |

### 14.4 Notifikasi dan eskalasi
- **Trigger:** revisi ETA approved, risiko gagal memenuhi komitmen, tidak berhasil menghubungi customer, penolakan customer, dan dampak kepada appointment/pengiriman.
- **Channels:** kanal yang sah dan disetujui (misalnya telepon, WhatsApp bisnis, SMS, email, portal); kanal tertentu belum dipilih pengguna. Atur verifikasi identitas dan nomor/alamat tujuan.
- **Isi:** gunakan template dengan versi, identitas bisnis, referensi order yang aman, ETA/komitmen sebelumnya, usulan tanggal baru, penjelasan umum, opsi respons, dan kontak layanan. Hindari mencantumkan diagnosis atau data kesehatan yang tidak diperlukan.
- **Tenggat:** waktu pemberitahuan setelah deteksi, masa tunggu respons, jumlah percobaan dan jenjang eskalasi **belum ditetapkan**; harus bisa diatur per lini layanan/prioritas.
- **Eskalasi:** CS -> Supervisor Lab untuk risiko produksi, Supervisor Klinik/dokter pengirim bila jadwal perawatan terdampak, pimpinan berwenang untuk pengecualian atau sengketa; jangan otomatis mengirim setiap kasus ke direktur.
- **Audit evidence:** status *queued/sent/delivered/failed/acknowledged/responded*, waktu, kanal, identitas aktor dan penerima, template, versi ETA, alasan perubahan serta catatan tanggapan. Simpan konten bukti secara minimal, terlindungi dan sesuai masa retensi yang ditetapkan.
- **Tidak ada persetujuan diam-diam:** status *read* atau *delivered* tidak pernah menjadi *customer_approved*.

### 14.5 Status dan integritas data

**State machine usulan:**
`delay_detected` -> `eta_revision_draft` -> `pending_lab_approval` -> `eta_revision_approved` -> `notification_required` -> (`notified_minor_change` | `awaiting_customer_approval`) -> (`accepted` | `declined` | `no_response_escalated`) -> `resolved_or_escalated`.

Untuk minor change, catat bukti pemberitahuan; untuk perubahan signifikan/komitmen, persetujuan eksplisit menjadi syarat perubahan status komitmen ke `accepted`. Jika status belum dapat diklasifikasikan karena ambang belum ditentukan, tahan di `pending_policy_review`.

**Entitas/kolom tambahan (konseptual):**
- `customer_contact_authorization`: order_id, contact_id, role_of_contact, verified_at, allowed_channels, consent_or_authority_basis.
- `lab_delay_event`: order_id, reason_code, detected_at, source_stage, previous_eta_version, proposed_eta_version, severity, impact_on_appointment, event_status.
- `lab_commitment`: order_id, version, committed_finish, terms_reference, agreed_by, agreed_at, current_status, supersedes_id.
- `delay_policy`: scope/branch, product_group, significant_rule, appointment_impact_rule, contract_change_rule, effective_from, policy_version; **nilai ambang belum diputuskan**.
- `customer_notice`: event_id, eta_revision_id, recipient_id, template_version, channel, queued/sent/delivered/failed_at, operator_id, error_reason.
- `customer_delay_decision`: delay_event_id, proposed_eta_version, authorized_contact_id, decision (accept/decline), decision_at, channel, evidence_reference, recorded_by.
- `escalation_task`: delay_event_id, assigned_role/user, reason, priority, due_at, status, outcome.
- `audit_event`: catatan append-only terhadap pembuatan, perubahan, approval, komunikasi, eskalasi dan penyelesaian.

**Persyaratan:** gunakan kontrol akses kasus/cabang, timestamp yang konsisten, validasi versi agar persetujuan customer tidak mengacu pada ETA lama, *idempotency* notifikasi, perlindungan bukti/payload sensitif, dan pembatasan siapa yang boleh melakukan perubahan komitmen. Tidak boleh menghapus atau meng-overwrite komitmen lama untuk menyembunyikan keterlambatan.

### 14.6 Dampak pada layanan, risiko dan KPI

| Risiko | Pengendalian / KPI |
|---|---|
| Customer mendapat pemberitahuan terlambat | Antrian notifikasi dengan peringatan dan metrik *time-to-notify* |
| Customer setuju pada tanggal yang berbeda dari versi terakhir | Persetujuan ditautkan ke `eta_revision_id` dan versi komitmen; validasi versi saat disimpan |
| Resi pesan gagal tetapi dianggap sukses | Bedakan sent, delivered dan acknowledged; fallback dan eskalasi |
| Perubahan tanggal disembunyikan untuk memperbaiki KPI | Simpan komitmen awal dan seluruh revisi; laporkan deviasi terhadap janji awal dan revisi terakhir |
| Penolakan customer diabaikan | Status `declined`, tiket eskalasi serta jejak solusi |
| Informasi pasien bocor lewat notifikasi | Verifikasi penerima, data minimum, templat dan audit akses |
| Pekerjaan mendesak memotong QC/otorisasi klinis | Pertahankan tahapan QC dan kewenangan profesional, walau di bawah tekanan keterlambatan |

**Metrik tambahan:** jumlah keterlambatan dan penyebabnya; persentase customer yang diberi tahu sebelum tenggat; keterlambatan notifikasi; rate tanggapan/persetujuan/penolakan; jumlah gagal kirim; perubahan komitmen disetujui; backlog kasus belum terselesaikan; dampak pada janji temu Klinik.

### 14.7 Kriteria penerimaan sebelum rilis
1. ETA yang direvisi tidak dapat dipublikasikan sebagai resmi sebelum mendapat validasi petugas Lab yang berwenang.
2. Semua perubahan ETA yang sudah diinformasikan menghasilkan kewajiban pemberitahuan; pesan hanya kepada contact of record yang terverifikasi.
3. Perubahan signifikan atau komitmen baru **tidak** dianggap disetujui sebelum ada respons afirmatif dari pihak yang berwenang; read receipt dan timeout bukan approval.
4. Penolakan atau tidak ada respons membuat tugas eskalasi, tidak menghilangkan riwayat janji semula.
5. Notifikasi gagal tidak boleh dilabeli tersampaikan; ada penanganan retry/fallback sesuai kebijakan.
6. Pengguna resepsionis tidak dapat memvalidasi ETA lab, menyetujui perubahan atas nama customer, atau menghapus audit.
7. Tanggal janji semula tetap dapat diaudit setelah revisi berulang; pelaporan KPI menghitung deviasi terhadap komitmen awal.
8. Revisi yang berdampak pada kunjungan Klinik mengirim tindakan koordinasi kepada pihak berwenang tanpa mengubah keputusan medis otomatis.
9. Saat persetujuan untuk versi yang sudah superseded masuk, sistem menolak atau meminta konfirmasi ulang pada versi paling baru.
10. Tidak ada data klinis sensitif yang bocor melalui pesan umum atau dashboard staf yang tidak berwenang.

### 14.8 Riwayat pertanyaan Tahap 12 (sudah dijawab pada Bagian 15)
**Kapan suatu perubahan jadwal Lab dianggap signifikan, sehingga wajib mendapat persetujuan customer?**

Pilihan yang perlu dikonfirmasi berikutnya:
- A. Setiap mundur minimal 1 hari kerja.
- B. Setiap mundur minimal 2 hari kerja.
- C. **Berbasis dampak:** wajib persetujuan bila mengganggu jadwal pasien/dokter, melanggar janji pengiriman, atau mengubah syarat kesepakatan; keterlambatan biasa hanya diberitahukan. Batas tambahan per jenis pekerjaan dapat ditentukan setelah ada data (rekomendasi).
- D. Belum menentukan; butuh analisis lanjut.

**Catatan:** Perubahan komitmen yang sudah disepakati tetap memerlukan proses persetujuan meskipun kurang dari ambang hari yang dipilih. Pastikan aturan yang dipilih tidak digunakan untuk menghapus kewajiban kontrak/layanan yang berlaku.

### 14.9 Status penerapan
Dokumen ini adalah **rancangan kebutuhan fungsional/keamanan**. Belum terdapat aplikasi produksi, integrasi pesan, verifikasi identitas customer, atau kontrol audit yang sudah dibuat dan diuji. Matriks hak akses, dasar pemrosesan data kesehatan, persyaratan rekam medis dan perlindungan data, serta SOP layanan harus dikaji bersama pihak berwenang sebelum implementasi.

---

## 15. Pembaruan Tahap 12 — Keterlambatan Berbasis Dampak dan Aturan per Jenis Pekerjaan (DISETUJUI PENGGUNA)

**Pernyataan keputusan, 19 Oktober 2026:** Keterlambatan Lab dinilai **berdasarkan dampak pada jadwal pasien, janji pengiriman, dan komitmen customer**; batas/parameter tambahan dapat dikonfigurasi **per jenis pekerjaan**. Pilihan ambang tetap 1 hari/2 hari **tidak dipilih**. Tidak ada angka toleransi maupun SLA final yang diasumsikan dalam spesifikasi ini.

**Presedensi:** Bagian 15 menyelesaikan pertanyaan Bagian 14.8. Segala aturan terdahulu yang berbeda harus dibaca sebagai riwayat diskusi, bukan kebijakan aktif. Ketentuan Tahap 11 bahwa customer harus diberitahu atas perubahan estimasi yang telah dikomunikasikan dan bahwa perubahan signifikan/komitmen memerlukan persetujuan tetap berlaku.

### 15.1 Definisi operasional dan batasan

1. **ETA internal:** perkiraan mesin/proses produksi yang belum tentu telah disahkan atau dijanjikan.
2. **ETA tervalidasi:** hasil perhitungan yang telah diperiksa Penanggung Jawab atau Supervisor Lab; dapat diteruskan ke CS sesuai alur.
3. **ETA yang sudah diinformasikan:** estimasi yang telah disampaikan kepada pemesan; perubahan dari nilai tersebut menghasilkan kewajiban pemberitahuan.
4. **Komitmen customer:** tenggat/ketentuan yang sudah disepakati, dilacak terpisah dari ETA internal. Perubahan komitmen membutuhkan persetujuan berwenang tanpa bergantung pada besarnya selisih hari.
5. **Dampak klinis/appointment:** keterlambatan mengancam jadwal tindakan, kontrol, pemasangan atau kelanjutan perawatan yang dijadwalkan. Sistem membuat tugas koordinasi untuk pihak klinik berwenang; sistem Lab **tidak** otomatis memindahkan jadwal pasien atau mengubah instruksi klinis.
6. **Dampak operasional pengiriman:** keterlambatan melewati janji kirim/terima atau cut-off pengiriman yang berlaku.
7. **Jenis pekerjaan:** klasifikasi terstandar (mis. crown, bridge, veneer, denture, implant prosthesis) agar parameter estimasi, kompleksitas, QC, SLA/ambang, dan eskalasi dapat diatur terpisah. Nilai aturan tiap kelas **belum ditentukan**.

### 15.2 Mesin penilaian dampak (*impact rules engine*)

**Urutan pemeriksaan yang diusulkan:**
1. Catat `eta_previous`, `eta_proposed`, `delta_business_minutes`, tahap produksi, hambatan, dan *quality constraints*.
2. Periksa keterkaitan ke `clinic_appointment` aktif, kebutuhan tanggal pemasangan, serta titik ketergantungan klinis. Jika tidak ada data linkage, tandai **informasi tidak lengkap**.
3. Bandingkan ETA dengan jadwal kirim dan `customer_commitment` yang masih berlaku.
4. Evaluasi `impact_policy` versi aktif untuk produk/jenis pekerjaan, prioritas, cabang, dan status customer. Tidak boleh mengurangi hak customer yang muncul dari perjanjian yang berlaku.
5. Klasifikasikan: `NORMAL` (tidak ada perubahan yang mengganggu), `ATTENTION` (revisi ETA yang telah diinformasikan atau risiko yang perlu diberitahukan), `CRITICAL` (terancamnya jadwal pasien, janji kirim, atau komitmen signifikan), atau `REVIEW_REQUIRED` (data tidak lengkap atau konflik aturan). Status `REVIEW_REQUIRED` tidak boleh otomatis dikonversi ke normal.
6. Buat tugas persetujuan, koordinasi klinik, notifikasi, dan eskalasi menurut hasil penilaian. Tidak ada pemberitahuan yang boleh menyatakan tanggal baru **disepakati** sebelum persetujuan yang diperlukan diperoleh.

| Situasi | Hasil minimum | Komunikasi & otorisasi |
|---|---|---|
| Perhitungan ulang ETA internal, belum disampaikan dan tidak memengaruhi komitmen/jadwal | NORMAL atau REVIEW_REQUIRED | Validasi Lab menurut SOP; belum otomatis wajib mengirim notifikasi customer |
| Perubahan ETA yang pernah disampaikan, tetapi tanpa dampak material | ATTENTION | Notifikasi customer wajib; bukti pengiriman dan statusnya dicatat |
| Pelanggaran janji kirim/komitmen customer, meskipun hanya beberapa jam | CRITICAL | Notifikasi + permintaan persetujuan pihak berwenang untuk mengubah janji, kemudian eskalasi bila ditolak/tidak menjawab |
| Keterlambatan mengancam appointment atau tindakan pasien | CRITICAL | Koordinasi dokter/klinik pengirim; komunikasi ke pihak terkait; bila jadwal pasien perlu diubah, gunakan alur persetujuan penjadwalan klinik |
| Tidak ada data jadwal/komitmen yang andal, atau konflik aturan | REVIEW_REQUIRED | Pemeriksaan manusia; jangan menampilkan status aman atau mengubah tanggal komitmen otomatis |

**Catatan:** Kategori memperingatkan risiko, **tidak menggantikan** syarat kontraktual atau persetujuan medis. Dampak terhadap appointment dapat menuntut koordinasi segera walaupun perubahan ETA belum melewati ambang produk.

### 15.3 Perubahan SOP: prosedur lintas divisi

**SOP LAB-DEL-012 (usulan, perlu pengesahan manajemen):**
1. **Deteksi:** sistem membandingkan ETA terhitung dengan milestone proses, jadwal pengiriman, komitmen, dan appointment terkait. Sistem atau petugas membuka *delay event*.
2. **Triage awal:** sistem memberi klasifikasi dampak serta daftar sumber pemicu; risiko tinggi diberi prioritas. Resepsionis tidak dapat menyembunyikan atau menurunkan klasifikasi.
3. **Validasi Lab:** PJ/Supervisor Lab menilai penyebab, estimasi baru, kemampuan percepatan yang realistis, kebutuhan material, dan tetap mempertahankan QC.
4. **Koordinasi Klinik:** jika order berasal dari Dokter Klinik dan appointment terdampak, dokter/koordinator klinik berwenang menerima tugas koordinasi. Tidak ada pembatalan atau pemindahan jadwal pasien otomatis.
5. **Komunikasi:** resepsionis/CS menghubungi **kontak pemesan yang sah** melalui kanal yang diizinkan dan menyampaikan status estimasi serta opsi yang sudah disahkan.
6. **Persetujuan:** perubahan komitmen atau kondisi signifikan harus mendapat tanggapan afirmatif dari pihak yang berwenang. Sistem mencatat persetujuan terhadap **versi usulan yang spesifik**; balasan diam, pesan terbaca, dan timeout tidak dianggap setuju.
7. **Ketidaksepakatan:** penolakan, notifikasi gagal, atau tidak ada respons membuat tugas eskalasi. Jadwal yang pernah dijanjikan tetap tersimpan dan kasus tidak boleh ditutup hanya karena tanggal baru telah diinput.
8. **Pelaksanaan:** perubahan yang sudah sah diteruskan ke perencanaan Lab dan, jika perlu, proses janji temu Klinik yang memiliki approval terpisah.
9. **Penutupan & evaluasi:** pantau apakah hasil dikirim, masalah terselesaikan, dan customer sudah mendapat pembaruan. Analisis sebab keterlambatan serta akurasi ETA untuk perbaikan kapasitas.

**Keputusan yang masih terbuka:** waktu eskalasi, siapa yang tepatnya menjadi pemesan/penyetuju pada order Lab internal, daftar kanal kontak, parameter kelas pekerjaan, serta tanggung jawab penyampaian informasi kepada pasien.

### 15.4 Keamanan, tata kelola & pemisahan tugas

- **Least privilege:** mesin membuat rekomendasi; petugas Lab memvalidasi; CS mengomunikasikan; pihak customer yang berwenang menyetujui perubahan komitmen; dokter/klinik berwenang menangani dampak klinis. Direktur/auditor memperoleh ringkasan atau rincian menurut hak akses, bukan akses tanpa batas ke informasi kesehatan.
- **Approval tidak boleh *self-approve*:** pihak yang mengusulkan tidak boleh menyetujui pengecualian sensitif sendiri, sesuai matriks wewenang yang perlu disahkan.
- **Role + order scope:** penugasan dan akses hanya ke kasus yang menjadi tanggung jawabnya; order eksternal tidak boleh membuka daftar pasien atau pekerjaan pelanggan lain.
- **Versioning dan jejak audit:** simpan ETA semula, ETA revisi, tanggal komitmen awal, setiap perubahan aturan, siapa mengubah/menyetujui, alasan, waktu, dan referensi bukti. Persetujuan untuk versi yang kedaluwarsa ditolak dan diminta ulang.
- **Perlindungan data pasien:** batasi data untuk CS dan personel Lab; pesan tidak memuat diagnosis, nama lengkap pasien atau prosedur sensitif kecuali ada dasar dan kanal yang sesuai. Verifikasi alamat kontak serta kewenangan penerima.
- **Konfigurasi berizin dan berversi:** hanya penanggung jawab yang diberi kewenangan mengubah `impact_policy`; perubahan harus diaudit, diuji, menggunakan tanggal berlaku dan tidak mengubah histori keputusan lama.
- **Kontrol sistem produksi:** autentikasi kuat/MFA untuk aktor sensitif, proteksi API, validasi concurrency, enkripsi, pemantauan anomali, backup serta uji pemulihan. Semua ini adalah **persyaratan implementasi**, bukan klaim bahwa sistem sudah ada.

### 15.5 Notifikasi, eskalasi, dan komunikasi customer

- **Pemicu notifikasi:** perubahan ETA yang sebelumnya telah diinformasikan, keterancaman komitmen, appointment berisiko, revisi tervalidasi, customer menolak, gagal dihubungi, atau order sudah mendekati tenggat penting.
- **Penerima sementara:** kontak order yang terverifikasi; bila order berasal dari Klinik, koordinasi kepada pihak klinik yang berwenang sebelum menghubungi pasien. **Aturan penerima final masih menunggu keputusan Tahap 13.**
- **Isi notifikasi:** referensi order aman, estimasi/komitmen sebelumnya, perkiraan baru, alasan non-sensitif, langkah yang tersedia, apakah memerlukan persetujuan, dan cara merespons.
- **Status pengiriman terpisah:** `queued`, `sent`, `delivered`, `failed`, `acknowledged`, `accepted`, `declined`. `sent`/`delivered`/`read` bukan `accepted`.
- **Eskalasi berjenjang:** CS → Supervisor Lab untuk masalah pengerjaan; ke Dokter/Koordinator Klinik untuk dampak terhadap pasien; manajer berwenang untuk sengketa atau pengecualian. Tenggat respons dan pengulangan pesan harus dapat dikonfigurasi, belum diputuskan angkanya.
- **Saluran:** portal, telepon, email, WhatsApp bisnis atau SMS hanya sebagai opsi; implementasi perlu izin, koneksi resmi, verifikasi identitas, ketentuan privasi, dan bukti komunikasi yang pantas.
- **KPI:** *on-time delivery* terhadap janji awal dan terbaru; waktu dari deteksi sampai pemberitahuan; proporsi notifikasi gagal; kasus menunggu persetujuan; kasus berdampak janji temu; ETA error per jenis produk; jumlah pengecualian manual.

### 15.6 Integrasi Klinik–Lab dan model data v0.12

**Integrasi inti:** `lab_order` ↔ `originating_clinic_order` ↔ `clinic_appointment` (bila ada) ↔ `lab_eta_revision` ↔ `lab_commitment` ↔ `lab_delay_event` ↔ `customer_notification`/`customer_delay_decision`.

| Entitas/kolom (konseptual) | Kebutuhan tambahan |
|---|---|
| `lab_order` | `job_type_id`, `origin_type`, `origin_clinic_id`, `authorized_customer_contact_id`, `priority`, `production_status` |
| `lab_job_type` | Kategori crown/bridge/veneer/denture/dll, alur tahap kerja, durasi historis dan kebutuhan QC |
| `impact_policy` | `policy_id`, `job_type_id`, `site_id`, `revision`, `effective_from`, `effective_to`, aturan toleransi, prioritas dampak appointment/komitmen, `approved_by` |
| `lab_delay_impact_assessment` | `delay_event_id`, `policy_revision`, `appointment_at_risk`, `delivery_at_risk`, `commitment_at_risk`, `data_complete`, `classification`, `reason_codes`, `assessed_at` |
| `lab_eta_revision` | `order_id`, `old_eta`, `proposed_eta`, `validated_eta`, `revision_no`, `validated_by`, `validated_at`, `reason` |
| `lab_commitment` | `order_id`, `promised_at`, `terms_ref`, `version`, `customer_approved_by`, `approved_at`, `supersedes_id` |
| `clinic_order_appointment_link` | `lab_order_id`, `appointment_id`, `dependence_type`, `last_confirmed_by` |
| `customer_notification` | `revision_id`, `recipient_authorization_ref`, `channel`, `delivery_status`, `message_template_version`, `sent_at` |
| `customer_delay_decision` | `commitment_revision_id`, `recipient_id`, `decision`, `decision_at`, `evidence_ref`, `identity_verified_at` |
| `escalation_task` | `risk_source`, `assigned_role`, `deadline`, `reason`, `status`, `resolution` |
| `audit_event` | *append-only* event untuk perubahan aturan, estimasi, janji, penilaian risiko, pesan, persetujuan, dan eskalasi |

**Validasi proses (contoh pseudo-rule):**

```
IF changed(previously_communicated_eta) THEN require_customer_notice
IF proposed_eta exceeds active_customer_commitment
   OR impacts_clinic_appointment
   OR changes_material_customer_terms THEN classify_critical_and_escalate
IF changes_existing_commitment THEN require_authorized_customer_approval
IF impact_data_missing THEN set_review_required (never auto-normal)
IF customer_approval.references_old_revision THEN reject_stale_approval
IF appointment_reschedule_requested THEN require_separate_clinic_workflow
```

**Catatan teknis:** relasi yang belum diketahui atau parameter yang belum diisi harus diperlakukan sebagai *unknown*, bukan bukti tidak ada dampak. Rekam medis tidak disalin seluruhnya ke Lab; cukup identifier pseudonim dan atribut teknis yang diperlukan, dengan pengungkapan minimum sesuai kebutuhan layanan.

### 15.7 Kriteria uji penerimaan sebelum rilis (minimum)

1. Keterlambatan beberapa jam yang melanggar janji pengiriman langsung diklasifikasi kritis walau ambang kerja produk lebih besar.
2. Keterlambatan yang mengganggu appointment memunculkan tugas koordinasi Klinik dan tidak mengubah jadwal pasien otomatis.
3. Revisi ETA yang pernah diinformasikan memunculkan kewajiban pemberitahuan walaupun tidak signifikan.
4. Perubahan tanggal komitmen customer tanpa persetujuan pihak sah ditolak; pesan terkirim/terbaca tidak dianggap persetujuan.
5. Penolakan customer, kegagalan notifikasi, atau data dampak yang tidak lengkap membuat tiket eskalasi/peninjauan sesuai aturan.
6. Resepsionis tidak dapat menurunkan klasifikasi risiko, mengubah ETA final, menyetujui sendiri perubahan komitmen, atau menghapus audit.
7. Pembaruan aturan kategori crown tidak diam-diam mengubah aturan bridge maupun catatan penilaian risiko yang telah diambil berdasarkan versi kebijakan sebelumnya.
8. Notifikasi hanya dikirim kepada penerima yang tervalidasi, tanpa data medis yang tidak diperlukan.
9. Dua aktor yang mengedit ETA/persetujuan secara bersamaan tidak boleh menghasilkan dua komitmen aktif yang saling bertentangan.
10. Laporan membedakan performa terhadap tanggal komitmen awal versus tanggal hasil revisi; perubahan tanggal tidak boleh dipakai untuk menyembunyikan keterlambatan.

### 15.8 Status, batas yang belum ditentukan, dan kelanjutan

**Terkonfirmasi oleh pengguna:** klasifikasi keterlambatan berdasarkan dampak ke jadwal pasien, janji pengiriman, dan kesepakatan customer; kebijakan dapat dikonfigurasi per jenis pekerjaan; pemberitahuan selalu diperlukan ketika ETA yang telah disampaikan berubah, dan perubahan signifikan/komitmen membutuhkan persetujuan.

**Masih terbuka:** siapa pelanggan/penandatangan persetujuan sah untuk order dari Klinik, ambang nominal atau durasi per jenis pekerjaan, toleransi operasional, prioritas dan SLA eskalasi, pilihan kanal notifikasi, integrasi janji temu eksternal, kebijakan privasi dan retensi, serta persetujuan pembagian data kepada Lab.

**Pokok wawancara Tahap 13:** penentuan penerima pemberitahuan serta pihak yang berhak menyetujui perubahan komitmen untuk order Lab asal Klinik. Pilihan tersebut akan memengaruhi RBAC, kontak order, arus notifikasi, dan alur persetujuan pasien bila jadwal perawatan ikut berubah.

**Status implementasi:** hanya spesifikasi desain. Belum ada kode aplikasi, database produksi, portal pelanggan, sistem notifikasi, atau audit operasional yang diimplementasikan maupun diuji. Seluruh SOP/kontrol keamanan masih memerlukan validasi, implementasi, pengujian, dan pengesahan sebelum penggunaan nyata.


---

## 16. Pembaruan Tahap 13 — Serah Terima Klinik ke Lab dan Komunikasi Langsung Pasien (KEPUTUSAN PENGGUNA)

**Pernyataan keputusan, 19 Oktober 2026:** Ketika order berasal dari Dokter Klinik, dokter menerbitkan surat/perintah kerja terkait pembuatan gigi atau pekerjaan prostetik. Setelah dokumen diserahkan **dan order diterima secara resmi oleh Lab**, Penanggung Jawab Lab (istilah internal: “Dokter Lab”, jabatan teknis/non-dokter gigi sebagaimana Tahap 7) menjadi pemilik operasional untuk pengerjaan, kualitas teknis, antrean, keterlambatan, estimasi dan pemberitahuan pasien secara langsung melalui NAM DMS. Dokter Klinik tidak menjadi penghubung rutin atau pemberi persetujuan setiap revisi ETA produksi. Ini memperbarui **opsi rekomendasi** yang sebelumnya menyarankan semua komunikasi melewati Klinik (Bagian 15.5).

### 16.1 Batas tanggung jawab penting
- **Dokter Klinik (klinisi berwenang):** pemeriksaan, diagnosis, keputusan perawatan, spesifikasi/resep kerja klinis, otorisasi perubahan klinis, penilaian kecocokan klinis dan tindakan pemasangan sesuai kewenangan. Tanggung jawab klinis **tidak beralih** hanya karena order diserahkan.
- **Penanggung Jawab/Supervisor Lab:** menerima dan memeriksa kelengkapan order, mengatur produksi, material, teknisi dan CAD/CAM, memvalidasi ETA dan revisi, mengawasi QC teknis, menindaklanjuti keterlambatan, dan memastikan pasien memperoleh pembaruan.
- **Resepsionis/CS:** membantu registrasi, administrasi, verifikasi kontak dan eskalasi komunikasi bila diperlukan, namun tidak boleh mengubah instruksi dokter atau mengesahkan QC/ETA tanpa kewenangan.
- **Pasien:** pihak penerima informasi perkembangan dan persetujuan untuk perubahan komitmen yang material, setelah identitas dan izin komunikasi diverifikasi. Bukan pemberi persetujuan atas modifikasi klinis teknis yang menjadi keputusan tenaga kesehatan.
- **Pengecualian wajib:** jika material/spesifikasi/resep kerja tidak lengkap atau memerlukan perubahan yang berdampak klinis, perlu konsultasi balik ke Dokter Klinik yang berwenang; jangan produksi dengan asumsi klinis. Jika jadwal pemasangan/tindakan klinis terdampak, koordinasi ke unit Klinik agar perubahan appointment dilakukan oleh pihak berwenang — tidak perlu menjadikan Dokter Klinik admin harian order.

### 16.2 Alur operasional resmi (draft untuk validasi SOP)
1. Dokter Klinik membuat dan menandatangani/menyetujui **surat perintah kerja Lab**, mencantumkan kode pasien/order, jenis prostesis/pekerjaan, spesifikasi teknis, material dan lampiran minimal yang diperlukan; versi dan identitas pengirim tercatat.
2. Sistem mengirim surat dan berkas terkait ke antrean **Lab – Pending Review** dengan catatan penerimaan elektronik. Pengiriman saja belum berarti Lab telah menerima tanggung jawab produksi; status tetap **menunggu penerimaan**.
3. Penanggung Jawab Lab memeriksa kelengkapan, menerima atau meminta klarifikasi, dan mencatat timestamp serta personel yang menerima. Setelah diterima, `production_owner_role=lab` dan SLA/ETA yang relevan mulai dihitung berdasarkan kebijakan yang ditetapkan.
4. Sistem merekomendasikan penugasan dari jadwal, kompetensi dan beban kerja. Pengalihan order mengikuti persetujuan Supervisor Lab (Tahap 8–9).
5. Sistem menyusun ETA berdasarkan material, beban produksi, jenis kasus, proses CAD/CAM, finishing dan QC. Penanggung Jawab/Supervisor Lab memvalidasi sebelum dinyatakan resmi (Tahap 10).
6. NAM DMS mengirim update status/ETA atas nama unit Lab **langsung ke pasien** melalui kanal yang telah disetujui dengan isi minimal; status pengiriman dan balasan disimpan (sent, delivered, acknowledged, consented).
7. Risiko keterlambatan dinilai berdasarkan dampak (Tahap 11–12). Perubahan ETA yang sudah dikomunikasikan wajib diberitahukan; perubahan komitmen signifikan membutuhkan persetujuan eksplisit pasien/pihak yang sah dan versi ETA yang tepat.
8. Lab melakukan QC teknis dan menandai barang siap serah. Penyerahan, jadwal pemasangan, dan tindakan lanjut harus melalui alur/otorisasi klinis yang relevan, bukan otomatis dinyatakan tuntas secara medis saat QC lulus.

### 16.3 Keamanan dan pembatasan akses
- **Role-based + order-based access control:** teknisi dan petugas Lab melihat hanya order yang relevan serta informasi minimum yang diperlukan untuk pembuatan. Jangan membuka rekam medis lengkap atau daftar pasien di luar wewenang.
- **Surat dokter wajib terotorisasi, berversi dan terlacak.** Staf Lab tidak bisa menyunting instruksi klinis yang sudah ditandatangani; permintaan koreksi menghasilkan revisi formal yang memerlukan persetujuan Dokter Klinik bila menyangkut keputusan klinis.
- **Kontak pasien diverifikasi.** Pengiriman langsung hanya lewat nomor/alamat/portal yang benar serta berdasarkan pemberitahuan dan dasar persetujuan/otorisasi komunikasi yang sah menurut kebijakan privasi; jangan otomatis mengasumsikan nomor pada invoice adalah nomor yang aman untuk pesan kesehatan.
- **Notifikasi minim data:** gunakan kode/order yang aman, progres umum, estimasi, dan petunjuk mengakses portal terautentikasi untuk detail; hindari diagnosis, foto mulut atau rincian sensitif di SMS/WhatsApp terbuka.
- **Persetujuan perubahan komitmen:** wajib autentikasi penerima yang layak, catat kanal, waktu, identitas, versi ETA/janji, dan bukti. Status pesan 'terkirim/dibaca' tidak menjadi persetujuan.
- **Audit tidak bisa ditimpa:** buat event serah-terima, penerimaan/penolakan, revisi surat, penugasan, QC, ETA, notifikasi, persetujuan dan penyelesaian, berikut pelaku/timestamp/alasan.
- **Kegagalan pengiriman:** antrean pengiriman ulang terkendali, pemberitahuan ke CS/PJ Lab, alternatif kanal, dan pencatatan gagal kirim; jangan tandai customer 'sudah diberi tahu' bila belum ada bukti yang sesuai.

### 16.4 Perubahan rancangan data/API
| Entitas / atribut | Tujuan |
|---|---|
| `lab_work_order` | Link ke order induk, kode pasien, jenis pekerjaan, status dan pemilik operasional |
| `clinical_prescription_version` | Dokter pembuat, tanda tangan/otorisasi, spesifikasi dan lampiran minimum, riwayat revisi |
| `lab_handoff_event` | `submitted_at`, `received_at`, penerima, status `pending/accepted/clarification_required/rejected`, alasan |
| `assignment_event` | Petugas yang direkomendasikan, pemilih, persetujuan Supervisor, pergantian penugasan |
| `production_schedule` dan `eta_revision` | Tahap produksi, estimasi internal, ETA tervalidasi, komitmen awal/revisi |
| `patient_contact_authorization` | Kanal kontak disetujui, sumber verifikasi, tujuan, bukti, status dan pencabutan |
| `customer_notification_event` | Penerima, template, versi pesan, status pengiriman, percobaan ulang, bukti |
| `customer_approval_event` | Keputusan pasien/pihak berwenang untuk perubahan komitmen spesifik |
| `clinical_escalation_case` | Masalah yang perlu dokter gigi (spesifikasi klinis, risiko appointment, kesesuaian medis) |
| `qc_event` / `audit_event` | Hasil QC teknis dan riwayat audit terproteksi |

### 16.5 Kriteria penerimaan minimum
1. Order yang baru dikirim Klinik belum boleh dianggap diterima Lab sampai ada penerimaan resmi.
2. Sesudah Lab menerima, supervisor Lab mengelola ETA, keterlambatan, dan notifikasi rutin tanpa meminta persetujuan Dokter Klinik untuk setiap perubahan produksi.
3. Perubahan spesifikasi dengan dampak klinis tidak boleh dijalankan tanpa klarifikasi dan persetujuan klinisi yang berwenang.
4. Pesan perkembangan dikirim hanya kepada kontak pasien terverifikasi sesuai dasar izin yang sah; tidak mengandung informasi kesehatan sensitif tanpa perlindungan memadai.
5. Ketika perubahan berpengaruh pada janji temu pemasangan, sistem membuat tugas koordinasi Klinik tetapi tidak otomatis memindahkan appointment atau membebaskan tanggung jawab klinis dokter.
6. Keputusan persetujuan pasien terikat pada versi ETA/janji tertentu; persetujuan untuk versi lama tidak berlaku otomatis untuk versi baru.
7. Manajemen dapat mengaudit kapan tanggung jawab operasional diterima Lab, siapa yang memperbarui ETA, kapan pasien diberi tahu dan apa tanggapannya.

### 16.6 Status pertanyaan Tahap 14 (sudah dijawab)
**Diputuskan pada Tahap 14:** Resepsionis Klinik melakukan verifikasi kontak dan mencatat pilihan/izin komunikasi pasien saat registrasi. Lab kemudian mengirim pembaruan order langsung kepada pasien **melalui NAM DMS**, dengan batasan privasi dan kendali di Bagian 17. Kanal pengiriman dan provider spesifik masih terbuka.

### 16.7 Status implementasi
Dokumen ini merupakan rancangan persyaratan, **belum** aplikasi berjalan, sistem notifikasi nyata, persetujuan digital aktif, atau bukti pengujian keamanan. Aturan masih harus divalidasi terhadap SOP klinik, peraturan kesehatan dan privasi yang berlaku, serta kontrak layanan Lab sebelum produksi.


---

## 17. Pembaruan Tahap 14 — Verifikasi Kontak Pasien & Izin Komunikasi Lab (KEPUTUSAN PENGGUNA)

**Keputusan yang dikonfirmasi, 19 Oktober 2026:** Resepsionis Klinik memverifikasi informasi kontak dan mencatat pilihan/izin komunikasi pasien pada saat registrasi. Setelah surat perintah kerja diserahkan dan diterima resmi oleh Lab, pembaruan status produksi dan keterlambatan dikirim **langsung kepada pasien melalui sistem NAM DMS** atas tanggung jawab operasional Lab. Dokter Klinik tidak menjadi perantara komunikasi rutin produksi (lihat Bagian 16), tetapi tetap memiliki kewenangan dan tanggung jawab pada urusan klinis.

**Kode kebutuhan:** `COM-014-001` sampai `COM-014-014` — status: *kebutuhan fungsional disetujui; prosedur teknis/legal dan kanal provider belum final*.

### 17.1 SOP saat registrasi dan pengumpulan pilihan komunikasi

1. **Registrasi:** Front Office membuka/membuat profil pasien menggunakan pengenal internal; memeriksa kemungkinan data pasien ganda tanpa menampilkan data orang lain secara berlebihan.
2. **Validasi identitas & kontak:** konfirmasi nama dan sarana komunikasi dari pasien/kuasa sah. Nomor/alamat harus diverifikasi melalui metode yang layak (misalnya OTP atau verifikasi terkontrol sesuai kebijakan yang akan ditetapkan). Membaca ulang nomor tanpa bukti penguasaan kanal belum cukup untuk menjamin nomor aman dipakai.
3. **Pemberitahuan privasi yang jelas:** jelaskan bahwa pekerjaan Lab dapat memakai status pesanan, perkiraan tanggal selesai, dan pesan keterlambatan; sebutkan kanal, siapa pengirim, tujuan, kemungkinan perantara layanan pesan, serta cara memperbaiki data dan mengubah preferensi. Persetujuan pemasaran dipisahkan secara tegas dari pesan layanan.
4. **Pencatatan pilihan/otorisasi:** simpan tujuan, kanal terpilih, teks/kebijakan versi berapa yang telah ditampilkan, timestamp, petugas, metode verifikasi, subjek yang menyatakan pilihan (pasien/wali sah), dan bukti yang sesuai. Landasan pemrosesan data harus divalidasi terhadap hukum dan kebijakan yang berlaku; jangan memperlakukan semua aktivitas operasional sebagai 'izin pemasaran'.
5. **Penolakan, tidak bisa verifikasi, atau pencabutan:** jangan memaksa pengiriman pesan ke nomor yang belum dapat dipastikan. Tawarkan cara alternatif yang terkontrol (portal pasien terautentikasi, konfirmasi tatap muka, telepon melalui SOP verifikasi). Catat tanggung jawab tindak lanjut oleh CS dan jangan menghapus kewajiban Lab mengelola order.
6. **Perubahan nomor / kontak:** lakukan verifikasi baru, nonaktifkan tujuan lama untuk pesan berikutnya, dan log perubahan; hindari mengirim detail order ke nomor lama saat proses pemutakhiran berlangsung.
7. **Pasien anak atau pasien yang diwakili:** hanya perwakilan sah yang telah diverifikasi dan diberi wewenang sesuai kebijakan dapat menentukan kanal atau menyetujui perubahan komitmen atas nama pasien. Catat relasi dan dasar kewenangannya tanpa membuka data berlebihan.

### 17.2 Alur notifikasi operasional dari Lab ke pasien

- **Pemicu resmi:** `lab_handoff_accepted`, `validated_eta_published`, `production_milestone`, `delivery_or_pickup_ready`, `delay_revision_validated`, `approval_required`. Tidak semua langkah produksi perlu dikirim: frekuensi dikendalikan agar tidak membanjiri pasien.
- **Pemeriksaan sebelum kirim (*policy gate*):** nomor/kanal terverifikasi dan aktif; pilihan komunikasi masih berlaku; penerima sesuai order; template yang disetujui; data minimal; tidak sedang diblokir/di-*opt out* sesuai aturan. Bila tidak lolos, buat tugas tindak lanjut ke Front Office/CS, bukan mengirim ke kanal yang meragukan.
- **Pemisahan tugas:** Lab mengubah progres dan memvalidasi ETA; sistem menyiapkan notifikasi otomatis; CS dapat menindaklanjuti notifikasi gagal; resepsionis tidak bisa membuat progres/QC palsu atau mengubah komitmen produksi.
- **Konten aman di WhatsApp/SMS/email:** pesan hanya mencantumkan identitas merek, status generik, estimasi umum bila sesuai preferensi, dan tautan ke portal pasien yang memerlukan autentikasi. **Jangan** mencantumkan diagnosis, foto medis, rekam medis, detail desain gigi sensitif, atau lampiran terbuka. Tautan menggunakan token aman berumur pendek dan tidak menampilkan informasi pribadi pada URL.
- **Kondisi keterlambatan:** setiap revisi estimasi yang telah diinformasikan mewajibkan pemberitahuan baru. Bila komitmen berubah secara signifikan, kirim permintaan persetujuan terautentikasi yang merujuk tepat pada versi usulan. Status `sent`, `delivered` atau `read` **bukan** `approved`.
- **Kegagalan pengiriman:** antrean pengiriman dengan idempotency key, percobaan ulang terkendali dan batas retry; lalu alihkan ke CS/Front Office untuk kanal alternatif setelah verifikasi. Bedakan `queued`, `sent_to_provider`, `delivered`, `failed`, `acknowledged`, `approved`, dan `rejected`.
- **Catatan:** memilih kanal notifikasi pasien tidak memberi Lab hak mengubah jadwal klinis, resep kerja dokter, atau instruksi medis. Kasus klinis dieskalasikan ke klinisi berwenang.

### 17.3 Matriks akses berdasarkan peran (usulan kontrol wajib)

| Peran | Melihat kontak pasien | Mengubah kontak/pilihan komunikasi | Mengirim pembaruan Lab | Menyetujui revisi ETA/komitmen |
|---|---|---|---|---|
| Resepsionis Klinik | Minimum diperlukan; dapat melihat bagian termask | Ya, dengan verifikasi ulang dan audit | Melakukan tindak lanjut CS bila diotorisasi | Tidak untuk revisi produksi; tidak boleh mengatasnamakan pasien |
| Penanggung Jawab/Supervisor Lab | Status kontak *verified/available* dan kanal yang boleh dipakai; nomor lengkap bila kebutuhan sah dan izin eksplisit | Tidak | Memicu melalui status/ETA yang berwenang, bukan ekspor daftar nomor | Validasi revisi ETA operasional; bukan persetujuan sebagai pasien |
| Teknisi / CAD-CAM / QC | Tidak perlu melihat nomor telepon | Tidak | Tidak; hanya memperbarui status teknis sesuai tugas | Tidak |
| CS / Tim komunikasi | Akses terbatas sesuai order yang ditugaskan | Koreksi melalui SOP verifikasi dan izin | Follow-up kegagalan notifikasi dan bantuan pasien | Tidak dapat menyetujui atas nama pasien |
| Pasien/perwakilan sah | Data/kontaknya sendiri | Mengajukan perubahan setelah autentikasi/verifikasi | Menerima pesan sesuai preferensi | Ya, bila pihak sah dan persetujuan eksplisit terautentikasi |
| FAT | Hanya data kontak penagihan yang diperlukan dan memiliki dasar akses | Tidak kecuali alur koreksi resmi | Hanya notifikasi penagihan dalam ruang lingkup berbeda | Tidak |
| Admin IT | Akses operasional terbatas, tanpa membaca pesan pasien secara default | Hanya melalui kontrol *break-glass* yang teraudit bila benar-benar diperlukan | Mengelola infrastruktur provider, tidak mengirim pesan sembarang | Tidak |
| Direktur/Auditor | Laporan agregat dan jejak audit; akses kasus sensitif berbasis kewenangan | Tidak | Tidak | Sesuai kebijakan eskalasi bisnis, tidak menggantikan persetujuan pasien |

Pengamanan implementasi: RBAC bersama otorisasi tingkat order (ABAC), MFA untuk akses sensitif, enkripsi transport dan penyimpanan, pemisahan environment, masking PII pada log, kredensial provider di secret manager, *least privilege*, pencatatan perubahan yang tahan manipulasi, pembatasan ekspor, retensi dan penghapusan sesuai kebijakan/hukum yang ditetapkan.

### 17.4 Ancaman dan mitigasi

| Ancaman / dampak | Mitigasi minimum |
|---|---|
| Salah nomor atau nomor milik orang lain | Verifikasi kontrol kanal; blokir kirim bila belum diverifikasi; ulangi saat nomor berubah |
| Nomor lama dipakai setelah pasien memperbarui kontak | Versi kontak aktif dan pemeriksaan izin pada saat pengiriman, bukan hanya ketika antrean pesan dibuat |
| Tenaga Lab melihat seluruh rekam medis | Akses berdasarkan order dan data minimum, kontak termask, larangan ekspor massal |
| Pesan sensitif muncul pada layar orang lain | Notifikasi generik; informasi privat hanya di portal login |
| Pasien menolak notifikasi tetapi sistem tetap mengirim | Preferensi/otorisasi diperiksa sebelum setiap pengiriman; jalur layanan alternatif yang tercatat |
| Komitmen baru dianggap disetujui karena pesan terbaca | Modul `approval_request` terpisah dengan identitas, versi, waktu, keputusan eksplisit |
| Pengiriman ganda atau notifikasi terlewat | Event idempotent, outbox queue, retry terkontrol, monitoring dan eskalasi gagal kirim |
| Pengubahan izin atau nomor kontak secara tidak sah | Login individual, verifikasi ulang, audit before/after terbatas, peringatan perubahan kontak |
| Isi pesan dipakai untuk pemasaran tanpa dasar | Pisahkan preferensi operasional dan pemasaran; template serta otorisasi provider dibatasi |

### 17.5 Model data minimum dan integrasi

| Tabel / objek | Field utama dan aturan |
|---|---|
| `patient_contact` | `patient_id`, `channel`, `contact_value_encrypted`, `contact_mask`, `verified_at`, `verification_method`, `status`, `version`; data sensitif tidak bocor ke audit/log |
| `communication_preference` | `patient_id`, `service_notification_channels`, `marketing_opt_in` terpisah, `updated_at`, `updated_by` |
| `communication_authorization_event` | `patient_id`, `purpose`, `basis_or_authorization_type`, `policy_version`, `recorded_by`, `acted_by_patient_or_guardian`, `evidence_ref`, `effective_at`, `withdrawn_at` jika berlaku |
| `lab_work_order` | Link order Klinik, penerimaan resmi oleh Lab, `production_owner_id`, status, dan hubungan pasien tanpa duplikasi rekam medis |
| `notification_template` | `event_type`, `channel`, `approved_template_version`, klasifikasi data yang boleh ditampilkan |
| `notification_event` | `order_id`, `recipient_contact_version`, `trigger_event_id`, `template_version`, `consent_or_basis_ref`, `delivery_status`, `provider_ref`, `retry_count`, timestamps dan error code non-PII |
| `customer_approval_request` | `order_id`, `commitment_revision_id`, `authorized_recipient`, `decision`, `verified_actor`, `evidence_ref`, `decided_at`; tidak disimpulkan dari `delivered/read` |
| `audit_event` | Aktor, aksi, order, timestamp, hasil, alasan, referensi bukti; tanpa nomor HP lengkap atau pesan medis dalam log biasa |

**Desain teknis:** notifikasi masuk ke *transactional outbox* pada saat status resmi berubah; pekerja pengirim mengambil event dan mengecek ulang verifikasi/otorisasi penerima sebelum memanggil provider. `idempotency_key` memastikan satu event tidak diproses sebagai banyak notifikasi. Integrasi dengan Klinik tetap memerlukan alur terpisah untuk appointment dan instruksi klinis.

### 17.6 Kriteria uji penerimaan v0.14 (harus lulus sebelum produksi)

1. Resepsionis dapat merekam kontak terverifikasi dan preferensi kanal pada registrasi; bukti tersimpan.
2. Sistem **menahan pesan** jika kontak belum diverifikasi, izin/landasan komunikasi tidak terpenuhi, atau pasien mencabut pilihan kanal terkait.
3. Lab dapat melihat kesiapan kanal, tetapi staf teknis tidak dapat melihat nomor penuh atau rekam medis yang tidak diperlukan.
4. Status `order accepted` memicu pembaruan sesuai preferensi; `order submitted but not accepted` tidak salah disebut `in production`.
5. Hanya ETA tervalidasi yang dapat dikomunikasikan sebagai estimasi resmi.
6. Jika nomor diubah setelah pesan terantre, pengiriman melalui nomor lama harus diblokir dan dievaluasi ulang.
7. Pesan WhatsApp/SMS/email tidak memuat diagnosis, foto pasien, atau rincian medis sensitif.
8. Kegagalan provider memicu retry terukur dan tiket CS; status `sent` tidak sama dengan `delivered`.
9. Perubahan komitmen signifikan hanya berlaku setelah persetujuan terautentikasi dari pihak berwenang, untuk revisi yang benar.
10. Pesan dibaca atau tidak direspons tidak mengubah status menjadi setuju.
11. Permintaan kontak oleh teknisi atau akses order yang bukan bagiannya harus ditolak dan diaudit.
12. Pasien di bawah perwakilan sah memakai alur verifikasi wewenang sebelum konfirmasi komitmen.
13. Data kontak tidak terlihat pada ekspor laporan KPI yang tidak memerlukannya.
14. Komunikasi operasional tidak otomatis mengaktifkan pemasaran, dan pengaturan pemasaran tidak menghapus kewajiban layanan yang ditangani dengan dasar/jalur berbeda.

### 17.7 Keputusan yang ditetapkan dan yang masih terbuka

**Ditetapkan pengguna:** (a) Klinik/Front Office memverifikasi kontak dan mencatat pilihan/izin saat registrasi; (b) setelah serah-terima order diterima Lab, pembaruan produksi dan keterlambatan disampaikan Lab langsung kepada pasien **via NAM DMS**; (c) kewenangan klinis Dokter Klinik tetap terpisah.

**Belum ditentukan:** kanal notifikasi (WhatsApp, SMS, email, portal, atau kombinasi), provider pesan, metode verifikasi kontak yang diwajibkan, preferensi alternatif untuk pasien tanpa smartphone, template dan frekuensi pesan, mekanisme otorisasi wali, retensi/penyimpanan bukti, evaluasi hukum PDP/rekam medis dan perjanjian pengolah data, SLA kegagalan pengiriman, serta hasil uji keamanan.

**Tahap 15 — SATU PERTANYAAN berikutnya:** kanal komunikasi apa yang menjadi pilihan resmi untuk pembaruan status pekerjaan Lab kepada pasien? Opsi: (1) WhatsApp utama dengan fallback SMS; (2) Portal pasien utama dengan WhatsApp/SMS sebagai pemberitahuan; (3) Pilihan pasien per kanal saat registrasi (disarankan), dengan fallback terverifikasi; (4) minta perbandingan lebih dulu.

**Status implementasi:** dokumen ini hanya spesifikasi, bukan bukti bahwa aplikasi, portal, OTP, provider pesan atau kontrol keamanan telah diprogram, diuji atau diterapkan pada lingkungan produksi.


---

## 18. PEMBARUAN NORMATIF TAHAP 15 — Komunikasi Multi-Kanal dan Portal Pasien (v0.15)

**Sumber kebutuhan:** Keputusan pengguna pada 19 Oktober 2026: *Pasien memilih WhatsApp, SMS, email, atau portal saat registrasi.* Keputusan ini menyelesaikan pertanyaan Tahap 15 pada §17.7. Setiap bagian lama yang menyatakan kanal masih belum dipilih merupakan riwayat sebelum keputusan ini, **bukan status kebijakan terbaru**.

**Status:** Kebutuhan bisnis DITETAPKAN; arsitektur teknis berikut adalah REKOMENDASI yang perlu disahkan, diimplementasikan dan diuji. Belum ada integrasi provider, portal pasien atau pengiriman pesan aktif.

### 18.1 Aturan bisnis yang disepakati
1. Resepsionis Klinik memeriksa identitas dan verifikasi alamat/nomor kontak saat registrasi, lalu merekam pilihan pasien untuk menerima pesan operasional melalui WhatsApp, SMS, email, atau portal pasien. Bila pasien memilih lebih dari satu kanal, aplikasi menyimpan urutan prioritas dan ketentuan penggunaannya; pilihan default dan fallback **belum ditentukan**.
2. Kontak dan preferensi berlaku sesuai identitas pasien/perwakilan sah. Petugas tidak boleh menganggap semua nomor/emails sah hanya karena dimasukkan di formulir.
3. Setelah surat perintah kerja klinis secara resmi diterima oleh Lab, **Penanggung Jawab/Supervisor Lab** bertanggung jawab atas progres, ketepatan produksi dan validasi ETA. NAM DMS menyampaikan pemberitahuan langsung ke pasien berdasarkan peristiwa sah dari Lab. Keputusan klinis (diagnosis, instruksi medis, perubahan desain yang memerlukan kewenangan dokter gigi, penyesuaian appointment) tetap berada pada praktisi klinis berwenang; informasi medis ditangani terpisah.
4. Pasien dapat melihat/ubah preferensi kanal dalam portal setelah autentikasi dan verifikasi perubahan yang sesuai. Resep kerja klinis atau progres/QC tidak dapat diubah oleh pasien atau resepsionis.
5. Pesan operasional layanan dipisahkan dari pesan pemasaran; catat preferensi, pemberitahuan privasi, dasar pemrosesan/otorisasi yang berlaku dan bukti sesuai hasil penilaian hukum. Jangan mengasumsikan satu kotak persetujuan berlaku untuk semua tujuan pemrosesan.
6. Estimasi yang dikomunikasikan harus telah divalidasi oleh Lab. Perubahan atas estimasi yang pernah disampaikan memicu pemberitahuan. Perubahan komitmen material mensyaratkan persetujuan pihak sah **untuk versi revisi yang tepat**; `sent`, `delivered`, dan `read` bukan `approved`.

### 18.2 Kanal komunikasi & batas konten
| Kanal | Tujuan | Batasan keamanan |
|---|---|---|
| WhatsApp Business resmi | Pemberitahuan singkat, tautan ke portal, permintaan pasien membuka detail | Gunakan provider resmi/ketentuan template, nomor diverifikasi; tanpa diagnosis, foto medis, desain rinci, atau detail sensitif dalam pesan |
| SMS | Pemberitahuan minimal, terutama saat sesuai pilihan pasien | Hindari data medis; nomor diverifikasi; tautan menuju portal login, bukan membuka data langsung |
| Email | Pemberitahuan status generik dan tautan portal | Verifikasi alamat; hindari lampiran rekam medis tanpa kanal/otorisasi yang tepat; tidak menganggap email selalu privat |
| Portal pasien | Informasi terautentikasi, status order, ETA, riwayat revisi dan persetujuan | HTTPS, autentikasi kuat yang proporsional, kontrol sesi, pengujian otorisasi per pasien, log akses, proteksi akun |

**Prinsip isi pesan:** identitas merek, status generik, referensi order yang tidak mengungkap data sensitif, pemberitahuan bahwa informasi diperbarui, dan tautan aman. Link boleh memiliki token anti-penyalahgunaan jangka pendek untuk *navigasi*, tetapi detail pasien tetap mensyaratkan autentikasi dan otorisasi; token di URL tidak boleh membawa PII/PHI.

### 18.3 Proses notifikasi terintegrasi
1. Petugas berwenang mengesahkan event, misalnya `lab_order_accepted`, `validated_eta_published`, `production_status_changed`, `lab_delay_confirmed`, `ready_after_qc`.
2. Aplikasi membuat event pada *transactional outbox* dalam transaksi yang konsisten dengan pembaruan status. Event membawa order, pasien/penerima sah, jenis event, dan versi template, tanpa menaruh isi sensitif di antrean umum.
3. Pekerja notifikasi memeriksa ulang status kontak dan verifikasi, preferensi kanal saat itu, otorisasi/pembatasan pemrosesan, kategori pesan dan status event. Jika gagal validasi, jangan kirim: catat alasan dan buat tugas follow-up.
4. Kirim melalui provider sesuai kanal yang terpilih, dengan kunci idempotensi berbasis event/penerima/kanal/versi; sertakan *request correlation id* agar callback provider tidak mem-posting status pada pesan lain.
5. Rekam status secara akurat: `queued` → `sent_to_provider` → `delivered` (jika provider mengkonfirmasi); alternatif `failed`/`cancelled`. Status `acknowledged`, `approved`, `rejected` adalah peristiwa **terpisah**, bukan sinonim terkirim/terbaca.
6. Lakukan retry terbatas berdasarkan tipe kegagalan. Jika gagal permanen atau melewati waktu respons, buat tiket CS. Pergantian kanal hanya boleh ke kanal alternatif yang telah diverifikasi dan dipilih/diizinkan secara sah, bukan otomatis mengirim ke semua kontak.
7. Bila pasien menolak revisi komitmen, tidak membalas, atau verifikasi gagal, supervisor menerima tugas eskalasi. Perubahan komitmen belum menjadi efektif sampai persetujuan yang diperlukan tercatat.

**Pemicu dan volume pesan masih perlu keputusan Tahap 16:** jangan menyimpulkan bahwa semua perubahan status teknis kecil wajib dikirim ke pasien. Risiko keterlambatan material tetap memerlukan eskalasi dan pemberitahuan sesuai Tahap 11–12.

### 18.4 Portal pasien — ruang lingkup MVP yang direkomendasikan
- **Ringkasan order milik sendiri:** nomor referensi aman, status saat ini, tanggal order diterima Lab dan penanggung jawab layanan (kontak/unit, bukan nomor pribadi teknisi).
- **Progress timeline:** mis. order diterima → dijadwalkan → produksi → QC → siap, hanya milestone yang sudah sah; jangan tampilkan status menyesatkan saat order belum diterima Lab.
- **ETA:** tanggal mulai bila ada, ETA selesai yang sudah divalidasi, keterangan *perkiraan*, peringatan keterlambatan dan referensi komitmen aktif jika relevan.
- **Pembaruan dan pesan:** notifikasi yang dikirim, status pengiriman yang tersedia, informasi perubahan, serta kanal komunikasi yang dipilih.
- **Persetujuan revisi:** lihat tanggal lama, tanggal usulan, alasan non-sensitif, dampak dan opsi setuju/tolak; audit identitas, waktu, versi dan keputusan; berikan bukti konfirmasi kepada pasien.
- **Kontak & preferensi:** nomor/email termask, status verifikasi, perbarui kanal dengan otentikasi serta verifikasi ulang; kontrol komunikasi pemasaran terpisah.
- **Bantuan:** fasilitas menghubungi CS/Lab untuk pertanyaan produksi, tanpa memberi akses ke seluruh rekam medis dan tanpa membuat pasien dapat mengubah instruksi dokter.
- **Pendamping/wali:** akses hanya dengan hubungan perwakilan sah yang diverifikasi, dibatasi pada pasien dan jangka waktu yang relevan.

**Pengecualian awal:** akses langsung seluruh rekam medis, foto klinis, detail resep dokter atau data pasien lain tidak termasuk fitur otomatis portal Lab. Setiap perluasan harus melalui tinjauan profesi medis, privasi, dan otorisasi.

### 18.5 Matriks hak akses v0.15 (fungsi tambahan)
| Peran | Pilihan kanal & kontak | Status/ETA | Isi pesan & persetujuan |
|---|---|---|---|
| Resepsionis Klinik | Memverifikasi dan mencatat pilihan pasien; membaca kontak minimum perlu | Ringkasan layanan sesuai tugas | Follow-up administratif, tidak boleh memalsukan persetujuan pasien |
| Penanggung Jawab/Supervisor Lab | Melihat kesiapan kanal, bukan seluruh daftar kontak tanpa kebutuhan | Mengonfirmasi progres produksi dan memvalidasi ETA | Memicu event yang sah; tidak boleh menyetujui perubahan atas nama pasien |
| Teknisi, CAD/CAM, QC | Tidak perlu akses nomor/email penuh | Memperbarui tahap teknis sesuai tugas; QC memverifikasi hasil | Tidak boleh mengirim pesan langsung atau melakukan approval pasien |
| CS / petugas komunikasi | Kontak terbatas ke order yang ditugaskan dan kanal terverifikasi | Melihat konteks pelayanan minimum | Menindaklanjuti kegagalan, mencatat respons, mengeskalasi masalah; tidak menyetujui atas nama pasien |
| Pasien / wali terverifikasi | Akses/ubah kanal sendiri dengan verifikasi ulang | Membaca order dan ETA yang boleh diketahui | Memberi respons eksplisit pada revisi komitmen miliknya sendiri |
| FAT / Direktur / Auditor | Akses hanya sejauh perlu sesuai fungsi | KPI/agregat; rincian kasus hanya dengan otorisasi | Tidak bebas membaca isi komunikasi atau bertindak atas nama pasien |
| Admin IT | Pengelolaan provider, log teknis teredaksi | Diagnostik metadata, tidak otomatis isi rekam medis | Tidak dapat menyetujui perubahan sebagai pasien; akses darurat diaudit |

**Enforcement:** Role-based dan scope order/pasien diterapkan pada API/backend, bukan sekadar menyembunyikan tombol di layar. Perubahan kontak, persetujuan, ekspor dan akses sensitif harus diaudit; batasi akses pengelolaan template dan credentials provider.

### 18.6 Skema database konseptual (penyesuaian dan penambahan)
| Entitas | Kolom kunci dan tujuan |
|---|---|
| `patient_contact` (dari v0.14) | pasien/perwakilan, kanal, nilai kontak terenkripsi, mask, verified_at, version, active_status |
| `communication_preference` (diperluas) | `patient_id`, `purpose=LAB_SERVICE`, `selected_channel`, `channel_priority`, `portal_enabled`, `marketing_choice_separate`, `effective_at`, `updated_by` |
| `communication_basis_event` | catatan dasar pemrosesan/izin yang relevan, tujuan, bukti, versi kebijakan, ditarik/diganti bila berlaku |
| `patient_portal_account` | akun, pasien/perwakilan, identitas terverifikasi, status, MFA/recovery-policy reference |
| `patient_portal_access_grant` | grant akses per pasien dan perwakilan, masa berlaku, pembatalan, audit |
| `lab_notification_event` | sumber `lab_order_event_id`, type, patient_id, recipient_id, validated_order_revision_id, template/version, created_at |
| `notification_delivery_attempt` | event_id, contact_version, channel, provider, provider_message_ref, idempotency_key, status, attempts, error_code, time |
| `notification_template` | event_type, channel, language, version, minimum-content classification, approved_by |
| `patient_portal_view_event` | actor, patient scope, order scope, action, date/time, result; minimalkan data sensitif pada log |
| `customer_approval_request` (dari v0.14) | order, commitment_revision, authenticated recipient, decision, evidence, timestamps; `read != approve` |
| `audit_event` | jejak perubahan kontak, pilihan, pengiriman, kegagalan, keputusan, perubahan hak akses dan kebijakan |

**Kendali integritas:** pastikan seluruh key menunjuk order/pasien yang benar, pembatasan tenant/cabang, constraint pengiriman duplikat, dan pengambilan status terbaru saat akan mengirim. Gunakan retensi dan penghapusan sesuai aturan hukum/kebijakan terverifikasi, bukan durasi yang diasumsikan.

### 18.7 Kriteria uji penerimaan Tambahan Tahap 15
1. Saat registrasi, pasien dapat memilih tepat satu atau beberapa kanal sesuai kebijakan dan preferensi tercatat dengan petugas serta waktu; tidak ada kanal tercentang diam-diam.
2. Tidak mengirim pesan ke nomor/email belum diverifikasi atau kanal yang tidak dipilih/disetujui untuk tujuan layanan tersebut.
3. Perubahan nomor setelah event masuk antrean membatalkan pengiriman ke versi nomor lama.
4. Pembaruan ETA sebelum divalidasi tidak dinotifikasi sebagai jadwal resmi.
5. Peristiwa yang sama tidak dikirim ganda saat callback provider berulang/retry.
6. Kanal tidak tersedia → pengiriman gagal tercatat, tiket CS dibuat, dan sistem tidak otomatis beralih ke kontak yang tidak berizin.
7. Pesan eksternal tidak membocorkan diagnosis, foto klinis, spesifikasi prostesis, ataupun data pasien lain.
8. Pengguna tanpa izin tidak dapat menebak ID order/akun pasien lain untuk melihat timeline; diuji pada endpoint backend.
9. Pasien dapat mengubah preferensi kanal sendiri dengan verifikasi ulang; histori perubahan dan aktor tercatat.
10. Persetujuan perubahan komitmen harus dibuat oleh pihak sah, terautentikasi, untuk versi usulan yang masih berlaku; tanpa respons tetap pending.
11. CS melihat metadata komunikasi hanya pada order tugasnya; teknisi tidak melihat nomor/email penuh dan tidak dapat mengirim pesan secara langsung.
12. Pengaturan pemasaran dan komunikasi order tidak boleh dicampur; perubahan preferensi menjalankan kebijakan pemrosesan yang sesuai.
13. Bila pasien menjadi tanggung jawab wali sah, hanya wali dengan grant akses aktif boleh melihat/menyetujui sesuai kewenangan.
14. Prosedur pemulihan akun portal dan penyimpanan bukti diuji untuk mencegah pengambilalihan akun.

### 18.8 Hal yang sudah diputuskan versus yang masih perlu keputusan
**Keputusan Tahap 15 (final kebutuhan bisnis):** Pasien memilih kanal WhatsApp, SMS, email, atau portal pada registrasi. Notifikasi progres Lab langsung kepada pasien dipertahankan. Portal sebagai pusat detail dan kanal eksternal sebagai pengingat adalah **rekomendasi arsitektur**, bukan kewajiban tunggal pelanggan untuk memiliki portal.

**Masih terbuka:** kapan tepatnya status teknis harus menimbulkan notifikasi; pilihan satu vs beberapa kanal dan fallback; provider WhatsApp/SMS/email; verifikasi identitas dan wali; bentuk otorisasi/pemberitahuan privasi sesuai hukum Indonesia; kebijakan retensi, keamanan akun dan respons insiden; SLA retry dan eskalasi; rencana integrasi, hasil audit keamanan, serta hasil uji fungsional.

**PERTANYAAN TUNGGAL TAHAP 16:** Untuk pembaruan progres Dental Lab, apakah notifikasi harus dikirim pada *setiap tahapan produksi*, hanya *peristiwa penting*, atau *pasien dapat memilih tingkat detail* (dengan pemberitahuan penting tetap wajib menurut ketentuan layanan)?

**Status implementasi:** Dokumen ini spesifikasi kebutuhan untuk pengembangan; belum membuktikan bahwa aplikasi, sistem OTP, integrasi WhatsApp/SMS/email, dashboard portal, autentikasi maupun keamanan sudah dibangun atau diuji.

---

## 19. PEMBARUAN NORMATIF TAHAP 16 — Preferensi Frekuensi Notifikasi & Tata Kelola Profesional (v0.16)

**Sumber:** Keputusan eksplisit pengguna pada 19 Oktober 2026: *Pasien memilih tingkat detail notifikasi sendiri, tetapi pemberitahuan penting tetap dikirim sesuai ketentuan layanan.* Pengguna juga meminta agar keputusan teknis dan tindak lanjut yang tidak kritis mengikuti rekomendasi profesional perancang sistem.

**Status kebijakan bisnis:** DIPUTUSKAN untuk preferensi frekuensi notifikasi. **Status usulan teknis:** standar baku pada bagian ini adalah *rancangan awal yang direkomendasikan*; kewajiban hukum, persyaratan klinis, persetujuan eksplisit per kasus, kontrak layanan, integrasi provider dan hasil pengujian perlu divalidasi sebelum produksi. Delegasi teknis tidak dianggap sebagai persetujuan mengabaikan privasi pasien, menentukan tarif, plafon kredit, mengikat kontrak, atau menetapkan tanggung jawab profesional medis.

### 19.1 Aturan pemilihan tingkat detail oleh pasien

Pasien/perwakilan sah memilih satu profil berikut pada saat registrasi dan boleh memperbaruinya melalui portal aman:

| Profil | Pemberitahuan layanan penting | Milestone produksi nonkritis | Ringkasan status |
|---|---|---|---|
| **Minimal** | Dikirim sesuai kebijakan layanan dan preferensi kanal yang sah | Tidak dikirim terpisah | Dapat dilihat kapan pun di portal |
| **Standar (default usulan)** | Dikirim sesuai kebijakan layanan dan preferensi kanal yang sah | Hanya milestone utama terkurasi | Tersedia di portal |
| **Detail** | Dikirim sesuai kebijakan layanan dan preferensi kanal yang sah | Pembaruan tahapan yang disetujui untuk ditampilkan | Opsi ringkasan/digest agar tidak spam |

- **Contoh peristiwa layanan penting (diusulkan):** order diterima dan estimasi tervalidasi; estimasi berubah; keterlambatan yang berisiko terhadap tanggal atau janji; permintaan persetujuan revisi komitmen; order sudah lolos QC dan siap diserahkan; pembatalan atau kendala yang memerlukan tindakan customer. Jenis peristiwa final ditetapkan menurut kontrak dan SOP per layanan. Keputusan Tahap 11 tetap berlaku: perubahan estimasi yang telah diberitahukan harus dikomunikasikan dan perubahan komitmen material memerlukan persetujuan yang sah.
- Pemberitahuan layanan penting **bukan** izin universal untuk menghubungi tanpa batas. Sistem harus menerapkan hukum, dasar pemrosesan, pilihan kanal, preferensi kontak yang berlaku, serta jalur alternatif bila pasien menolak suatu kanal. Tidak boleh mengirim ke kanal tidak terverifikasi.
- Jenis komunikasi **pemasaran** memakai pilihan dan dasar pemrosesan terpisah. Menonaktifkan pesan progres opsional tidak boleh menghapus informasi wajib di portal ataupun tugas tindak lanjut layanan yang sah.
- Perubahan preferensi berlaku untuk pesan yang *belum terkirim* setelah pemeriksaan ulang pada saat pengiriman. Simpan versi preferensi agar setiap pesan dapat diaudit.

### 19.2 Batas kendali per divisi

| Peran | Hak terkait notifikasi |
|---|---|
| **Resepsionis Klinik** | Memverifikasi kontak, menjelaskan pilihan notifikasi dan mencatat preferensi; tidak mengarang progres atau mengubah ETA teknis. |
| **Penanggung Jawab/Supervisor Lab** | Mengesahkan perubahan status produksi dan ETA; memiliki tanggung jawab komunikasi layanan pasca serah-terima order. Tidak mengubah persetujuan pasien. |
| **Teknisi/CAD-CAM/QC** | Memperbarui data operasional sesuai peran; catatan teknis mentah tidak otomatis menjadi pesan pasien. |
| **CS Lab** | Menindaklanjuti pesan gagal, tidak dibalas bila respons diperlukan, komplain dan eskalasi sesuai SLA; akses dibatasi ke order yang ditugaskan. |
| **Pasien/perwakilan sah** | Mengatur detail dan kanal sesuai kebijakan, melihat status sendiri, mengesahkan/menolak perubahan material secara terautentikasi. |
| **IT/Keamanan** | Mengelola keandalan, provider dan keamanan tanpa otomatis mendapat akses data medis utuh; akses darurat diatur dan diaudit. |
| **Direktur/Auditor** | KPI agregat keterkiriman, keterlambatan, kepuasan dan kasus eskalasi; pembukaan detail individual sesuai kebutuhan dan izin. |

### 19.3 Alur teknis yang direkomendasikan

1. *Approved domain event*: status order/ETA hanya dipublikasikan setelah validasi peran yang berwenang.
2. *Transactional outbox*: catat event beserta transaksi bisnis secara konsisten.
3. *Policy engine*: tentukan klasifikasi penting/opsional, profil tingkat detail, pilihan kanal, verifikasi kontak, identitas penerima, umur pesan dan status revisi terkini.
4. *Notification orchestrator*: kirim pesan minim informasi ke provider resmi dengan key idempoten; gunakan mekanisme agregasi/rate limit untuk milestone opsional, serta ketentuan jam tenang jika sesuai SLA.
5. *Status & evidence*: bedakan `queued`, `sent_to_provider`, `delivered`, `failed`, `acknowledged`, `approved`, `rejected` dan jangan menganggap `read` sebagai persetujuan.
6. *Exception workflow*: pengiriman gagal atau respons wajib tak diterima → tiket CS/Supervisor, bukan fallback otomatis ke nomor yang tidak dipilih. Jika kontak tidak valid, gunakan kanal yang sah/portal dan prosedur verifikasi ulang.
7. *Portal*: semua progres yang boleh dilihat pasien tersaji di timeline, sementara push mengikuti tingkat detail pilihannya.

**Standar isi dan keamanan:** notifikasi luar portal memakai teks generik, tanpa rincian diagnosis, scan medis atau instruksi pembuatan prostesis; informasi khusus pasien hanya diakses melalui portal dengan autentikasi, otorisasi objek, perlindungan sesi dan log. Terapkan enkripsi, retensi terkontrol, manajemen rahasia provider, pemantauan kegagalan dan pemeriksaan keamanan aplikasi.

### 19.4 Dampak pada operasional dan KPI

- **Efisiensi Lab:** staf cukup mencatat progres sekali; komunikasi dipicu status tervalidasi, bukan diketik satu per satu ke semua pasien.
- **Pengalaman pasien:** pasien tidak dibanjiri pesan teknis, tetap mendapat informasi penting dan dapat memilih tingkat detail.
- **SOP klinik–lab:** begitu surat kerja diterima Lab, tanggung jawab pengerjaan/ETA/notifikasi ada di Lab; perubahan yang memerlukan keputusan klinis harus dikembalikan kepada dokter gigi yang berwenang, tanpa memindahkan tanggung jawab produksi rutin.
- **Pemantauan:** KPI jumlah pesan penting gagal terkirim, waktu respons, keterlambatan pemberitahuan, SLA penyelesaian komplain, jumlah revisi ETA, persetujuan tertunda, dan biaya provider per kanal. KPI disajikan agregat; tidak membocorkan identitas pasien pada dashboard umum.
- **Keandalan:** jika gateway pesan berhenti, pekerjaan Klinik/Lab tetap berjalan; sistem mencatat pesan yang tertunda dan eskalasi, tanpa menggandakan notifikasi.

### 19.5 Perubahan model data

- `notification_preference`: `patient_id`, `legal_representative_id?`, `service_type`, `detail_level` (MINIMAL/STANDARD/DETAIL), `channel_priority`, `effective_at`, `version`, `updated_by`, `legal_basis_ref`.
- `notification_event_policy`: `event_type`, `is_critical_service_event`, `audience`, `allowed_levels`, `template_id`, `requires_human_validation`, `quiet_hours_exception`, `effective_version`, `approved_by`.
- `notification_dispatch`: `event_id`, `patient_id`, `contact_version`, `policy_version`, `preference_version`, `channel`, `idempotency_key`, `status`, `attempt_count`, `provider_ref`, `created_at`, `sent_at`, `delivered_at`.
- `patient_acknowledgement`: `order_id`, `commitment_revision_id`, `actor_verified_id`, `decision`, `decision_at`, `evidence_ref`; tidak digabung dengan status pesan dibaca.
- `follow_up_ticket`: `event_id`, `assigned_team`, `reason`, `deadline`, `status`, `escalated_at`, `resolution`.

**Kendala integritas:** satu event tidak boleh mengirim ganda ke penerima/kanal/revisi yang sama secara tidak sengaja; perubahan informasi kontak/penerima/order harus memicu pemeriksaan ulang. Pastikan isolasi cabang, hak akses level objek dan auditing diterapkan pada backend/API.

### 19.6 Pengujian penerimaan Tahap 16

1. Profil MINIMAL tidak mendapat milestone rutin opsional, tetapi tetap menerima pemberitahuan layanan penting lewat kanal yang sah.
2. Profil DETAIL mendapat tahapan yang layak ditampilkan, tanpa membocorkan rincian teknis/medis dan tanpa duplikasi bila status sering berubah.
3. Perubahan profil atau kanal segera dihormati oleh pekerja pengirim pada saat eksekusi; nomor lama tidak dipakai.
4. Pesan perubahan komitmen tidak pernah diartikan disetujui hanya karena terkirim, dibaca atau tidak direspons.
5. Event ETA yang belum divalidasi Lab tidak menghasilkan pemberitahuan resmi.
6. Kegagalan WA/SMS/email memunculkan tiket follow-up sesuai SLA dan tidak dikirim ulang ke kanal belum diverifikasi.
7. Pengguna Lab tidak dapat melihat order pasien lain hanya dengan mengganti parameter order_id atau patient_id.
8. Tidak ada detail medis sensitif dalam template pesan luar portal; riwayat dan identitas pada portal terlindungi.
9. Event berulang, retry dan callback provider tidak menggandakan pesan/approval.
10. Dashboard direktur menyajikan KPI agregat, sesuai hak akses dan tanpa nomor pasien terbuka.

### 19.7 Standar profesional pengembangan — mandat desain awal

**Rencana pengerjaan yang disarankan (bukan berarti produk sudah dibangun):**

- **Fase A — Validasi kebutuhan:** selesaikan model proses internal vs eksternal, peta jabatan & RBAC/ABAC, definisi data pasien, kriteria penerimaan, SOP dan persetujuan otoritas medis/keuangan.
- **Fase B — Fondasi aman:** autentikasi individual, MFA untuk peran sensitif, multi-cabang/tenant isolation, audit log, backup dan restore test, otorisasi backend, pemantauan keamanan, manajemen rilis.
- **Fase C — MVP Klinik & Lab:** registrasi pasien, surat perintah kerja digital dari dokter, serah-terima, antrean penugasan semi-otomatis, dashboard teknisi/CAD-CAM/QC, ETA tervalidasi, portal dan notifikasi penting.
- **Fase D — Finansial & divisi lain:** invoice/payment/settlement, FAT approval, inventaris, purchasing, HR, customer service, KPI direktur dan laporan harian terpadu.
- **Fase E — Hardening dan go-live terkendali:** pengujian unit/integrasi/end-to-end, UAT per divisi, penetration testing independen bila sesuai risiko, kebijakan privasi/retensi, migrasi data, pelatihan dan rencana rollback.

**Prinsip keputusan:** rekomendasi teknis rutin dapat dijadikan *default rancangan*. Tetapi keputusan material seperti tarif, kontrak pasien, plafon cicilan, batas keterlambatan per produk, cara identifikasi pasien/anak dan siapa pengendali data, integrasi payment/provider serta kesiapan kepatuhan harus mendapat validasi pemangku kepentingan sebelum rilis.

### 19.8 Status dan pertanyaan berikutnya

**Ditetapkan:** pilihan detail notifikasi oleh pasien; peristiwa penting dikomunikasikan sesuai ketentuan layanan yang sah. **Direkomendasikan sebagai default:** profil STANDAR, pusat informasi di portal, pesan eksternal singkat, alur notifikasi berbasis event tervalidasi, eskalasi kegagalan, dashboard KPI agregat.

**Satu pertanyaan Tahap 17:** Apakah Dental Lab juga menerima order dari **dokter/klinik di luar Naraya Aurentis Monolithic**, selain surat kerja dari Dokter Klinik internal? Pilihan: internal saja; internal dan eksternal; eksternal saja; belum diputuskan. Ini menentukan privasi hubungan dokter-pasien, pemilik hubungan customer, portal pemesan, invoice, dan hak akses.

**Status implementasi:** dokumen ini adalah spesifikasi/desain; tidak membuktikan software, integrasi WhatsApp, SMS, email, portal, pembayaran, keamanan, atau fitur produksi telah dibangun dan diuji.


---

## 20. PEMBARUAN NORMATIF TAHAP 17 — Order Lab Internal & Eksternal (v0.17)

**Tanggal keputusan:** 19 Oktober 2026  
**Keputusan eksplisit pengguna:** NAM Dental Laboratory menerima **(a) surat kerja dari Dokter Klinik Naraya internal** dan **(b) pesanan dari dokter gigi/klinik eksternal**. Kedua sumber wajib didukung pada arsitektur data, alur order dan kontrol keamanan.  
**Status:** sumber order **DITETAPKAN**; model arsitektur dan kebijakan komersial di bawah adalah **REKOMENDASI DESAIN** sampai SOP, kontrak, pihak yang bertanggung jawab atas data, dan aturan keuangan perusahaan divalidasi.

### 20.1 Prinsip arsitektur enterprise

1. **Modular monolith terlebih dahulu**, dengan modul domain yang terisolasi: Identity & Access, Organization/Client, Clinic/Clinical, Lab Order, Production/CAD-CAM, QC, Scheduling/ETA, Billing/AR, Payment/FAT, Notification & Patient/Client Portal, Inventory/Purchasing, HR, Audit/Reporting. Modul dapat berkembang independen melalui antarmuka internal berversi; jangan mengandalkan satu tabel besar untuk semua kebutuhan.
2. **Satu sistem operasional dengan pembatasan organisasi ketat**. Order internal dan eksternal masuk ke kapasitas Lab yang sama hanya bila benar-benar memakai sumber daya produksi yang sama, tetapi tetap mempunyai pemilik hubungan customer, hak akses, kontrak, dan proses penagihan berbeda.
3. **Pembatasan di backend dan database**, bukan sekadar menyembunyikan menu. Terapkan pemeriksaan izin per aksi dan per objek: organisasi, cabang, peran, hubungan user terhadap order, konteks layanan, serta tujuan penggunaan data. Pertimbangkan row-level security sebagai lapisan tambahan, tanpa menganggapnya pengganti pengujian kontrol akses API.
4. **Order dan komunikasi berbasis event yang tahan duplikasi**: transaksi database dan transactional outbox untuk penerimaan order, persetujuan ETA, pembuatan invoice, dan notifikasi. Worker idempotent memproses pesan WhatsApp/SMS/email secara asinkron. Kegagalan gateway komunikasi tidak boleh menghilangkan order maupun menghentikan produksi.
5. **Integritas alur keuangan**: invoice, pembayaran terverifikasi, piutang, jurnal, koreksi, dan rekonsiliasi dipisahkan dari status produksi. Pemrosesan otomatis tidak boleh membuat penerimaan uang fiktif atau menggandakan pendapatan.
6. **Kesiapan multi-cabang/multi-klien**: definisi `organization`/`legal_entity`, `branch`, dan `external_client_account` dipisahkan; hak administrator korporat berbeda dari administrator klinik mitra. Tentukan kepemilikan hubungan customer, kebijakan retensi, dasar komunikasi, dan kewajiban hukum sebelum implementasi nyata.
7. **Pilihan teknologi awal (belum diputuskan):** aplikasi web responsif/PWA, API bertipe dan berversi, PostgreSQL, object storage terenkripsi untuk lampiran, antrean kerja untuk notifikasi, dan audit log yang dilindungi dari perubahan. Teknologi spesifik vendor/hosting diputuskan pada desain teknis dan evaluasi keamanan, bukan diasumsikan telah tersedia.

### 20.2 Dua jalur penerimaan order yang berbeda

#### A. Order dari Klinik Naraya (internal)

1. Pasien diregistrasi Klinik Naraya; Dokter Klinik berwenang menilai kondisi pasien dan mengotorisasi surat kerja spesifik (contoh crown/bridge/denture), lengkap dengan instruksi dan lampiran minimum yang diperlukan.
2. Surat kerja ber-ID unik, berversi dan ditandatangani/disahkan sesuai SOP. Order berstatus `SUBMITTED_TO_LAB`, **belum** menjadi tanggung jawab produksi Lab sampai penerimaan resmi.
3. Penanggung Jawab Lab memeriksa kelengkapan dan menerima, menolak atau meminta klarifikasi. Saat `ACCEPTED`, kepemilikan operasional produksi/ETA/notifikasi dialihkan ke Lab sesuai keputusan Tahap 13.
4. Resepsionis menjalankan penugasan semi-otomatis; Penanggung Jawab Lab mengonfirmasi; pengalihan setelah penolakan memerlukan persetujuan Supervisor Lab sebagaimana Tahap 8–9.
5. Lab mengelola kapasitas, produksi, CAD/CAM, QC, ETA yang divalidasi, dan **notifikasi langsung kepada pasien** melalui kanal terverifikasi/pilihan pasien sebagaimana Tahap 14–16. Masalah yang memerlukan keputusan klinis dieskalasikan kembali ke Dokter Klinik.
6. Pengeluaran produksi dapat dialokasikan sebagai biaya internal, cost center, atau transaksi antarentitas **bergantung pada struktur badan hukum**. Jangan membuat invoice penjualan eksternal hanya karena ada serah-terima internal.
7. QC teknis selesai tidak otomatis berarti tindakan medis atau pemasangan di Klinik selesai.

#### B. Order dari dokter/klinik eksternal (B2B)

1. Organisasi mitra di-*onboard* dengan identitas organisasi, perjanjian layanan, dokter/penanggung jawab pengirim, pengguna portal, hak akses, preferensi komunikasi dan alamat penagihan yang diverifikasi.
2. Pengguna mitra yang berwenang mengirim **surat kerja lab eksternal** dan spesifikasi teknis minimum melalui portal B2B atau alur input yang disetujui; rekam siapa yang mengajukan serta dokter pengirim berwenang. Dokumen yang tidak lengkap ditempatkan dalam `NEEDS_CLARIFICATION`.
3. Lab mengakui penerimaan, memastikan ketersediaan bahan, estimasi biaya bila berlaku, kapasitas, lalu menerapkan penerimaan/penolakan dan penugasan yang sama dengan order internal, tanpa mencampurkan hak akses mitra.
4. Supervisor Lab memvalidasi ETA. **Secara default pembaruan dikirim kepada klinik/dokter pemesan eksternal**, karena pelanggan kontraktualnya biasanya klinik/dokter pengirim. Hubungan langsung Lab–pasien eksternal hanya boleh diaktifkan apabila ada kesepakatan dan dasar komunikasi yang sah serta kontak pasien terverifikasi. Keputusan kebijakan eksternal **belum final** dan menjadi pertanyaan Tahap 18.
5. Lab mengelola tahap produksi/CAD-CAM/QC, keterlambatan dan komunikasi terhadap pihak pemesan yang sah. Perubahan yang berdampak pada instruksi klinis harus diotorisasi dokter pengirim; jangan menghubungi pasien untuk membuat keputusan klinis.
6. Setelah aturan komersial yang dipilih terpenuhi (contoh: pada persetujuan order, sebelum dispatch, atau setelah QC), Billing menerbitkan invoice kepada **entitas pembeli/pihak yang secara kontraktual wajib membayar**, dengan tarif kontrak, jatuh tempo, pajak dan diskon terotorisasi.
7. Barang dikirim/diambil dengan bukti penyerahan dan penerima yang sah; piutang B2B ditagih, dibayar dan direkonsiliasi oleh FAT. Portal mitra dapat melihat status order dan invoice **milik organisasinya sendiri**, tidak milik mitra lain.

**Keamanan serah-terima:** `LAB_ACCEPTED` harus mencatat waktu, versi surat kerja, identitas pengirim dan penerima serta scope organisasi. Sebuah order tidak boleh dianggap telah diterima hanya karena berkas berhasil diunggah.

### 20.3 Perbedaan kewenangan, customer dan hak akses

| Peran | Internal | Eksternal | Batas akses penting |
|---|---|---|---|
| Dokter Klinik Naraya | Membuat surat kerja dan keputusan klinis pasiennya | Tidak otomatis terlibat | Tidak melihat order pasien dari klinik eksternal |
| Dokter pengirim dari klinik mitra | Tidak ada akses default ke pasien Naraya | Mengirim/merevisi instruksi untuk kasusnya | Hanya order organisasi mitranya dan data yang diizinkan |
| Resepsionis Klinik | Registrasi pasien Naraya, penjadwalan | Tidak otomatis melayani seluruh mitra eksternal | Tidak dapat mengubah resep atau hasil QC |
| Admin/CS Lab | Validasi administratif, komunikasi, penugasan sesuai SOP | Mengelola order mitra sesuai penugasan | Tidak boleh membuka seluruh rekam medis atau menyetujui refund sendiri |
| Penanggung Jawab Lab | Menerima dan memimpin produksi | Sama, dengan pembatasan kerahasiaan tiap pelanggan | Hanya informasi minimum untuk produksi; bukan otoritas medis |
| Supervisor Lab | Persetujuan pengalihan, ETA dan eskalasi | Sama | Persetujuan tercatat, tidak boleh diwakilkan via akun bersama |
| Teknisi/CAD-CAM/QC | Pekerjaan dan hasil teknis | Sama | Akses per pekerjaan; tidak mengakses seluruh pasien/keuangan |
| FAT | Rekonsiliasi, biaya internal sesuai entitas | Invoice, AR, settlement, piutang, pajak sesuai entitas | Akses pembayaran/keuangan tanpa paparan rekam medis lengkap |
| Klinik mitra — admin | Tidak dapat masuk workspace Klinik Naraya | Melihat order, status dan invoice organisasinya | Tidak melihat tarif/identitas/customer klinik lain |
| IT/system admin | Dukungan infrastruktur | Dukungan infrastruktur | Tidak otomatis berhak membaca isi medis; akses darurat terotorisasi dan diaudit |
| Direktur/Manajemen | KPI konsolidasi sesuai izin | KPI B2B dan margin | KPI agregat terlebih dahulu; akses pasien individual hanya bila sah dan perlu |

**Istilah:** sebutan internal “Dokter Lab” tetap mengacu pada **Penanggung Jawab Lab/Teknisi**, bukan dokter gigi berizin. Jangan gunakan label ambigu tersebut sebagai dasar memberi kewenangan medis (Tahap 7).

### 20.4 Kebijakan komunikasi & persetujuan yang wajib dibedakan

- **Pasien Klinik Naraya:** keputusan Tahap 13–16 tetap berlaku. Resepsionis Klinik memverifikasi kontak dan izin/preferensi saat registrasi; setelah Lab menerima surat kerja, NAM DMS menyampaikan progres langsung kepada pasien lewat kanal pilihan (WhatsApp, SMS, email atau portal), dengan tingkat detail MINIMAL/STANDARD/DETAIL dan notifikasi layanan penting sesuai ketentuan.
- **Pasien dari klinik eksternal:** jangan otomatis memakai aturan kontak pasien Naraya, bahkan jika data pasien dikirim bersama surat kerja. Default rancangan: pemberitahuan ke akun klinik/dokter pemesan. Notifikasi langsung ke pasien memerlukan verifikasi bahwa pihak terkait memang berwenang mengatur komunikasi dan bahwa dasar komunikasi serta tujuan pengolahan data sudah jelas.
- **Penerima persetujuan perubahan komitmen:** tentukan sesuai hubungan kontrak dan siapa yang terdampak; respons pasien eksternal tidak otomatis dapat menggantikan persetujuan dokter pengirim atas perubahan teknis/klinis ataupun persetujuan pihak pembeli atas komitmen B2B.
- **Konten eksternal minimal:** status generik, referensi aman, tautan ke portal dengan autentikasi. Jangan menyertakan diagnosis, foto intraoral, berkas scan, nomor identitas berlebihan, atau rincian prostesis sensitif dalam pesan biasa.
- **Pemberitahuan perubahan ETA:** setiap perubahan yang sudah disampaikan wajib diinformasikan; perubahan signifikan/komitmen membutuhkan persetujuan pihak yang tepat. Jika tidak merespons, eskalasikan; tidak ada persetujuan implisit.

### 20.5 Pembukuan internal vs penagihan eksternal

**Internal** — model dibedakan setelah memastikan struktur legal dan akuntansi:
- Jika Klinik dan Lab satu badan hukum: lazimnya *cost allocation*, internal charge atau pusat biaya; **hindari mengakui pendapatan eksternal dua kali** atas layanan yang sama.
- Jika Klinik dan Lab badan hukum berbeda: dapat membutuhkan transaksi antarentitas, invoicing dan eliminasi konsolidasi sesuai kebijakan akuntansi, pajak dan kontrak yang diverifikasi profesional keuangan.
- Dokter Klinik/pasien tidak otomatis menerima invoice B2B dari Lab karena hanya ada surat perintah kerja; pastikan siapa pembayar yang sah.

**Eksternal** — rekomendasi:
- Tarif diturunkan dari `client_contract` + `price_list` berversi, jenis pekerjaan, material, tingkat urgensi yang disetujui, diskon terotorisasi, dan aturan pajak yang telah dikonfirmasi.
- Pihak pembayar default adalah akun organisasi mitra, kecuali kontrak yang sah menyatakan pihak lain. Pisahkan *customer*, *patient*, *ordering clinician*, *bill-to party*, dan *ship-to party* dalam model data.
- Dukung invoice, DP, termin/jatuh tempo, pembayaran sebagian, rekonsiliasi FAT, credit note atau pembalikan yang disetujui; kebijakan batas cicilan/approval tetap **belum final** sesuai Tahap 4–5.
- Pisahkan `billable`, `invoiced`, `paid`, `overdue`, `disputed` dan `written_off`. Status `QC_PASSED` tidak otomatis berarti invoice sudah dibayar.
- Semua diskon, perubahan harga, retur, remake tanpa biaya dan penghapusan piutang harus mengikuti wewenang serta audit.

### 20.6 Model data konseptual tambahan

| Entitas/field | Kebutuhan | Kontrol integritas |
|---|---|---|
| `organization` / `legal_entity` | Perusahaan Naraya, badan hukum Lab dan organisasi mitra | Scope data dan entitas penagih eksplisit |
| `branch` / `site` | Lokasi Klinik/Lab atau lokasi mitra | Scope cabang tidak melampaui organisasi tanpa izin |
| `external_client_account` | Profil B2B, kontrak, billing party, SLA | Nomor akun unik per entitas; onboarding diverifikasi |
| `client_user_membership` | User mitra, peran dan organisasi | Hak akses di-revoke saat staf mitra keluar |
| `patient_reference` | ID pasien internal atau kode pasien kiriman eksternal | Jangan menggabung rekam pasien antarorganisasi hanya berdasar nama/nomor |
| `lab_order` | `source_type` INTERNAL/EXTERNAL, `origin_organization_id`, `ordering_clinician_id`, `contract_id?`, `production_owner_id`, `status` | Konsistensi scope; tidak bisa beralih tipe tanpa koreksi berversi |
| `lab_work_order_document` | Surat perintah kerja, versi, penandatangan, lampiran | Lampiran terenkripsi, diakses per order, revisi tidak menimpa versi lama |
| `lab_order_handoff` | Penerimaan, penolakan, klarifikasi, timestamp, actor | Order tidak menjadi accepted tanpa keputusan dan versi dokumen |
| `lab_order_stage` / `qc_event` | Produksi, CAD/CAM, finishing, QC | Pemilik tugas, bukti dan cap waktu |
| `lab_eta_revision` | ETA usulan dan tervalidasi, komitmen, dampak | Validasi Supervisor/PJ, versi tidak ditimpa |
| `lab_notification_recipient` | Pasien internal vs kontak klinik eksternal | Kebijakan tujuan, verifikasi, izin, dan kontrak |
| `client_contract` / `price_list_version` | Tarif, diskon, SLA dan syarat komersial | Berlaku per tanggal dan disetujui |
| `invoice` / `invoice_line` | `seller_legal_entity_id`, `bill_to_account_id`, `source_order_id`, status | Larang invoice ganda dari event sama; pajak/nominal konsisten |
| `accounts_receivable` / `payment` / `reconciliation` | Piutang/settlement dan kontrol FAT | Verifikasi pembayaran, pemisahan tugas, larangan hapus audit |
| `internal_cost_allocation` / `intercompany_transaction` | Pengalokasian biaya antarunit/entitas | Tidak otomatis diklasifikasikan sebagai penjualan B2B |
| `audit_event` / `access_decision_log` | Lacak tindakan dan akses sensitif | Proteksi dari perubahan, retensi terdefinisi |

**Skema migrasi dan keputusan data**: definisikan ID organisasi asal, pasien internal vs kode pasien mitra, kategori data sensitif, aturan unik order/revisi, skema file dan penghapusan data sebelum membuat tabel produksi. Hindari menyimpan rekam medis lengkap dalam modul penagihan.

### 20.7 Keamanan dan risiko spesifik dual-source order

1. **Kebocoran silang antar-mitra:** endpoint daftar/detail order, attachment, invoice, chat, dan pencarian wajib selalu dicek dengan organisasi serta izin per order di server; uji IDOR/BOLA, pagination, export, webhook, dan report builder.
2. **Pengiriman dokumen palsu:** verifikasi identitas dokter/petugas pengirim sesuai SOP, lampiran dipindai malware, pencatatan versi dan integritas dokumen; jangan menerima surat medis hanya dari profil bebas verifikasi.
3. **Salah identifikasi pasien:** pisahkan pasien internal, referensi pasien eksternal, dan *cross-org mapping* yang memerlukan dasar sah; nomor HP yang sama tidak berarti rekam medis boleh otomatis digabung.
4. **Salah penerima pesan:** pekerja pengirim memeriksa ulang status kontak, izin, jenis sumber order dan kebijakan komunikasi *tepat sebelum mengirim*, bukan hanya saat antrean dibuat.
5. **Manipulasi status dan ETA:** only PJ/Supervisor yang memiliki mandat memvalidasi, pemisahan maker-checker, seluruh revisi berversi dan punya alasan; eskalasi saat komitmen berubah.
6. **Fraud tarif/invoice:** harga kontrak terkunci dengan versi yang berlaku; override memerlukan approval; idempotency key menghindari invoice/pembayaran ganda; FAT merekonsiliasi secara independen.
7. **Akses teknis berlebihan:** identitas individual, prinsip least privilege, MFA untuk peran sensitif, pembatasan koneksi database, backup terenkripsi, log akses data dan prosedur break-glass yang disetujui.
8. **Kepatuhan:** validasi bersama penasihat hukum/privasi dan penanggung jawab klinis atas persyaratan hukum perlindungan data pribadi, rekam medis, perizinan profesi, perjanjian pemrosesan data dengan mitra/vendor, pajak dan penyimpanan dokumen. Dokumen ini bukan penilaian kepatuhan final.

### 20.8 KPI dan daily report lintas sumber

Dashboard direktur memisahkan metrik per `source_type` (internal/eksternal), organisasi, cabang, divisi dan periode: order masuk, diterima, menunggu klarifikasi, WIP, selesai QC, terlambat, remake, rata-rata lead time, ETA variance, produktivitas kapasitas, nilai invoice B2B, umur piutang, penerimaan terverifikasi, biaya produksi internal, serta jumlah pemberitahuan gagal dan approval tertunda. Metrik agregat tidak mengungkap data medis yang tidak diperlukan.

**Prinsip laporan:** satu order dihitung satu kali sesuai definisi metrik; jangan menggandakan omzet bila Lab memenuhi order internal Klinik. Tentukan sumber data dan *metric definitions* untuk setiap KPI sebelum merilis dashboard.

### 20.9 Kriteria uji penerimaan Tahap 17 (wajib sebelum rilis)

1. Dokter Klinik internal dapat mengirim surat kerja sah yang menghasilkan satu order; Lab harus menerima secara eksplisit sebelum SLA produksi aktif sesuai kebijakan.
2. Akun klinik eksternal dapat mengirim dan memantau ordernya, tetapi gagal membaca daftar, file, pasien, tarif maupun invoice organisasi mitra lain, termasuk jika ID dimodifikasi langsung pada API.
3. Dokter mitra tidak bisa mengakses rekam medis lengkap atau appointment pasien Klinik Naraya hanya karena menjadi pelanggan Lab.
4. Teknisi yang ditugaskan hanya melihat spesifikasi relevan; tidak dapat membuka data pembayaran/rekam medis lengkap maupun menerima order atas nama supervisor.
5. Order internal tidak otomatis membuat invoice B2B atau pendapatan ganda. Order eksternal menghasilkan invoice hanya ketika kebijakan penagihan sah terpenuhi dan dengan bill-to party yang tepat.
6. Penerimaan order, approval ETA, alih penugasan, QC, pembatalan dan revisi dokumen menghasilkan audit event yang dapat ditelusuri tanpa menimpa histori.
7. Pesan status pasien internal mengikuti izin Tahap 14–16; pesan pasien eksternal **tidak dikirim otomatis** tanpa kebijakan delegasi/kontak yang disahkan.
8. Perubahan ETA signifikan pada order eksternal meminta persetujuan pihak yang sesuai kontrak; sistem tidak memperlakukan pesan dibaca sebagai persetujuan.
9. Retry unggah order/webhook maupun gagal jaringan tidak menghasilkan dua order, dua invoice atau dua pesan identik.
10. Laporan direktur dapat memisahkan KPI internal dan eksternal; jumlah pendapatan konsolidasi tidak melebih-lebihkan transaksi internal.
11. Penarikan akses staf mitra segera membatasi akses ke semua portal/API termasuk tautan file unduhan yang belum kedaluwarsa; uji sesi dan token.
12. Backup/restorasi diuji dengan sampel data terlindungi, audit tetap lengkap, dan skenario kehilangan penyedia notifikasi tidak menghentikan workflow produksi.

### 20.10 Keputusan terbuka dan satu pertanyaan Tahap 18

**Sudah ditetapkan oleh pengguna:** (a) Lab menerima order internal dan eksternal; (b) alur internal dengan serah-terima dari Dokter Klinik ke Lab dan notifikasi langsung Lab–pasien setelah verifikasi; (c) penugasan semi-otomatis; (d) ETA divalidasi Lab; (e) pasien internal dapat memilih kanal dan detail notifikasi.

**Belum final:** tipe badan hukum Klinik dan Lab; apakah billing Lab internal hanya alokasi biaya atau transaksi antarentitas; kontrak/harga/SLA mitra; cara onboarding kredensial dokter eksternal; dasar hukum dan peran pengendali/pemroses data; batas kredit pelanggan, pajak, aturan DP/cicilan; model penerima komunikasi eksternal.

**Rekomendasi default eksternal:** hubungan komunikasi rutin Lab adalah dengan **dokter/klinik eksternal pemesan**, bukan pasien eksternal secara otomatis. Persetujuan komunikasi langsung ke pasien baru dibuka berdasarkan kewenangan yang jelas, perjanjian kerja sama, verifikasi kontak dan dasar komunikasi yang sah.

**Satu pertanyaan Tahap 18:** Untuk order **dari dokter/klinik eksternal**, siapa yang harus menerima status produksi, estimasi selesai, serta pemberitahuan keterlambatan: (A) hanya dokter/klinik pemesan; (B) dokter/klinik pemesan sebagai penerima utama, dengan opsi notifikasi langsung kepada pasien setelah otorisasi/izin terverifikasi; (C) langsung pasien dan salinan kepada klinik, setelah hak/kontak terverifikasi; atau (D) minta perbandingan terlebih dahulu?

**Status implementasi:** keseluruhan v0.17 masih spesifikasi dan rekomendasi desain. Belum membuktikan adanya sistem produksi, database terimplementasi, koneksi payment/WhatsApp, audit keamanan, kepatuhan hukum, ataupun kelayakan go-live.
