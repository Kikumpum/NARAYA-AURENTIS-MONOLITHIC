"""Draf SOP operasional v1.0. Tidak memuat protokol tindakan medis."""
from copy import deepcopy

CATALOG_VERSION = '1.0-draf'


def sop(code, title, division, roles, reviewers, purpose, frequency, steps, evidence,
        order='none', states=(), sensitive=False):
    items = []
    for n, text in enumerate(steps, 1):
        # Prefix * = bukti wajib; ? = tidak relevan boleh dipilih dengan alasan.
        required_evidence = text.startswith('*')
        allow_na = text.lstrip('*').startswith('?')
        items.append({'key':f'{code}-{n:02}', 'text':text.lstrip('*?'),
                      'allow_na':allow_na, 'evidence_required':required_evidence})
    return dict(code=code, version=CATALOG_VERSION, title=title, division=division,
                roles=roles.split(), reviewers=reviewers.split(), purpose=purpose,
                frequency=frequency, order_policy=order, allowed_states=list(states),
                sensitive=sensitive, items=items, evidence_examples=evidence,
                draft=True)


CATALOG = [
    sop('GOV-01','Pengawasan dan tindak lanjut manajemen','Pengawasan',
        'commissioner auditor','chief_executive',
        'Menilai pengendalian dari ringkasan dan bukti administratif tanpa membuka rekam medis.', 'Bulanan / saat temuan',[
        'Periode, unit, dan ruang lingkup pemeriksaan dicatat.',
        'Ringkasan kinerja diperiksa tanpa data identitas atau rincian medis pasien.',
        'Pemisahan pelaksana, pemeriksa, dan pemberi persetujuan ditinjau.',
        '*Temuan, tingkat urgensi, dan bukti administratif dicatat.',
        'Setiap temuan mempunyai penanggung jawab dan tenggat tindak lanjut.',
        'Tindak lanjut sebelumnya dicek; penutupan disertai bukti, bukan pernyataan lisan.'
        ],['Ringkasan audit tanpa identitas pasien','Daftar temuan dan rencana perbaikan']),
    sop('DIR-01','Evaluasi direksi dan keputusan operasional','Direksi',
        'director chief_executive','commissioner',
        'Mencatat keputusan bisnis beserta dasar, pemilik tindakan, dan batas kewenangannya.', 'Mingguan / saat keputusan',[
        'Agenda, periode, dan unit yang dibahas ditetapkan.',
        'Angka ringkasan diperiksa sumbernya; biaya internal tidak digandakan sebagai omzet.',
        'Risiko layanan, keterlambatan, kapasitas, dan temuan terbuka ditinjau.',
        '*Keputusan dan alasan dicatat dalam notulen; pengecualian diberi batas waktu.',
        'Penanggung jawab serta tenggat setiap keputusan ditetapkan.',
        'Keputusan bisnis tidak mengganti persetujuan pasien atau instruksi klinis dokter.'
        ],['Notulen rapat fiktif','Daftar keputusan dan tindak lanjut']),
    sop('OPS-01','Pembukaan, koordinasi, dan penutupan operasional','Operasional',
        'operations_manager branch_manager','director chief_executive',
        'Memastikan layanan lintas divisi mempunyai petugas dan tindak lanjut yang jelas.', 'Setiap shift',[
        'Petugas, jadwal, dan unit layanan shift ini dikonfirmasi.',
        'Antrean, kapasitas Lab/Klinik, dan komitmen yang berisiko ditinjau.',
        'Kendala fasilitas diteruskan ke GA/IT tanpa membagikan isi medis.',
        'CS dan Resepsionis memahami jalur eskalasi serta penanggung jawab shift.',
        '*Hasil serah terima shift dan masalah terbuka dicatat.',
        'Insiden mempunyai pemilik tindakan, prioritas, dan tenggat.'
        ],['Form serah terima shift','Daftar kendala fasilitas']),
    sop('BIZ-01','Penjajakan kerja sama dan klinik mitra','Pengembangan Bisnis',
        'business_development corporate','director chief_executive',
        'Menilai kerja sama sebelum akses atau pertukaran data diaktifkan.', 'Setiap calon kerja sama',[
        'Identitas organisasi calon mitra dan kontak bisnisnya dicatat.',
        'Ruang lingkup layanan, kapasitas, dan rencana tarif diperiksa bersama pihak terkait.',
        'Peran pengendali data, penerima komunikasi, dan otorisasi kontak dibahas.',
        '*Draf kerja sama serta daftar isu yang belum disepakati dilampirkan.',
        'Tidak ada akses tenant atau janji komersial final sebelum persetujuan berwenang.',
        'Serah terima ke Operasional/FAT/IT dicatat dengan batas akses yang disepakati.'
        ],['Draf kerja sama sintetis','Checklist kesiapan mitra']),
    sop('COR-01','Pengendalian dokumen corporate','Corporate',
        'corporate general_affairs','director',
        'Menjaga versi, otorisasi, dan tindak lanjut dokumen perusahaan.', 'Setiap perubahan dokumen',[
        'Nomor, jenis, versi, dan pemilik dokumen dicatat.',
        'Kelengkapan administratif ditelaah oleh pihak yang sesuai.',
        'Tanggal berlaku dan pengingat pembaruan dicatat.',
        '*Salinan draf yang sudah disamarkan dan daftar perubahan dilampirkan.',
        'Distribusi dibatasi kepada penerima yang memerlukan.',
        'Dokumen lama dipertahankan sebagai riwayat, bukan ditimpa.'
        ],['Register dokumen','Riwayat revisi tanpa dokumen pribadi']),
    sop('HR-01','Jadwal, kompetensi, dan serah terima personel','HR',
        'hr','director operations_manager',
        'Memastikan penempatan tugas sesuai jadwal dan kompetensi yang diverifikasi.', 'Harian / perubahan personel',[
        'Jadwal dan kehadiran petugas dikonfirmasi tanpa membuat absensi rekaan.',
        'Kebutuhan pengganti dan beban kerja unit dicatat.',
        'Kompetensi dan kewenangan tugas diverifikasi oleh penanggung jawab terkait.',
        '?Pelatihan atau pembaruan kompetensi yang jatuh tempo ditindaklanjuti.',
        '*Ringkasan perubahan jadwal atau hasil pemeriksaan shift dilampirkan.',
        'Onboarding/offboarding diteruskan ke IT untuk penyesuaian akses yang disetujui.'
        ],['Jadwal petugas fiktif','Register pelatihan tanpa dokumen pribadi']),
    sop('GA-01','Pemeriksaan fasilitas dan pemeliharaan','General Affairs',
        'general_affairs housekeeping','operations_manager director',
        'Mencatat kondisi fasilitas dan menindaklanjuti gangguan operasional.', 'Setiap shift / saat gangguan',[
        'Area kerja, akses keluar, penerangan, dan fasilitas umum diperiksa.',
        'Peralatan yang rusak diberi penanda dan diteruskan kepada petugas berwenang.',
        'Pekerjaan pemeliharaan tidak mengganggu keamanan area dan data.',
        '?Pihak luar yang masuk dicatat dan didampingi sesuai kebutuhan.',
        '*Temuan atau hasil inspeksi fasilitas dilampirkan tanpa foto pasien.',
        'Tindak lanjut perbaikan dan pemeriksaan ulang dicatat.'
        ],['Foto fasilitas kosong','Log pemeliharaan fiktif']),
    sop('HK-01','Kebersihan area dan serah terima housekeeping','General Affairs',
        'housekeeping','general_affairs operations_manager',
        'Memastikan pemeriksaan kebersihan tercatat dan masalah diarahkan ke petugas terkait.', 'Setiap shift',[
        'Area dan jadwal pembersihan dikonfirmasi kepada penanggung jawab.',
        'Perlengkapan tersedia dan digunakan sesuai prosedur fasilitas yang disahkan.',
        'Area umum dan titik kontak diperiksa setelah dibersihkan.',
        'Bahan, limbah, atau alat klinis hanya ditangani oleh petugas berwenang sesuai SOP klinis terpisah.',
        '*Hasil inspeksi area kosong dan kendala dicatat.',
        'Kebutuhan perlengkapan serta serah terima shift diteruskan ke GA.'
        ],['Checklist area','Foto area tanpa orang atau dokumen pasien']),
    sop('IT-01','Pemeriksaan layanan dan pengelolaan akses','IT',
        'it_admin','director auditor',
        'Memelihara layanan dan akses tanpa membuka isi medis atau transkrip pasien.', 'Harian / permintaan akses',[
        'Kesehatan layanan, kapasitas penyimpanan, dan log teknis diperiksa.',
        'Status backup diperiksa; keberhasilan pemulihan hanya ditandai setelah uji restore.',
        '?Permintaan akses mempunyai pemohon, persetujuan, lingkup, dan masa berlaku.',
        'Hak akses mengikuti kebutuhan minimum; jabatan atasan tidak memberi akses medis otomatis.',
        '*Bukti pemeriksaan teknis disamarkan dari token, kata sandi, dan data pasien.',
        'Gangguan, perubahan konfigurasi, dan rencana pemulihan dicatat.'
        ],['Log kesehatan layanan yang disamarkan','Hasil uji restore sintetis']),
    sop('FO-01','Registrasi dan pembukaan layanan pasien','Front Office',
        'reception','operations_manager clinic_head',
        'Memastikan data administratif dan pilihan komunikasi tercatat dengan benar.', 'Setiap registrasi / shift',[
        'Gunakan identitas fiktif; cocokkan referensi layanan sesuai prosedur verifikasi demo.',
        'Jadwal dan dokter tujuan dikonfirmasi tanpa mengubah diagnosis.',
        'Pilihan kanal serta frekuensi komunikasi dicatat; izin layanan dipisahkan dari pemasaran.',
        'Status kontak dan izin diberi label simulasi, bukan dianggap verifikasi sungguhan.',
        '?Penggantian dokter menunggu persetujuan pasien sebelum perubahan final.',
        'Kendala registrasi dan tindak lanjut dicatat tanpa rincian medis pada laporan umum.'
        ],['Form registrasi kosong/sintetis','Ringkasan antrean tanpa identitas']),
    sop('CLI-01','Pemeriksaan administratif surat kerja dokter','Klinik',
        'dentist','dentist',
        'Memeriksa kelengkapan surat kerja; keputusan klinis tetap pada dokter berwenang.', 'Setiap surat kerja',[
        'Kode order dan referensi pasien cocok dengan layanan dokter pembuat.',
        'Jenis pekerjaan dan instruksi telah ditulis oleh dokter yang berwenang.',
        'Spesifikasi serta dokumen yang diperlukan diperiksa sesuai protokol klinis yang disahkan.',
        'Janji layanan dicatat tanpa menjanjikan kapasitas Lab yang belum dikonfirmasi.',
        '*Salinan surat kerja sintetis atau lembar pengesahan administratif dilampirkan.',
        'Revisi dikembalikan kepada dokter pembuat; riwayat instruksi tidak ditimpa.'
        ],['Surat kerja fiktif','Catatan klarifikasi dokter'],order='required',
        states=['submitted','assigned','rejected','accepted'],sensitive=True),
    sop('NUR-01','Kesiapan ruang dan bantuan pelayanan','Klinik',
        'nurse','clinic_head dentist',
        'Mendokumentasikan kesiapan ruang; tidak mengganti SOP tindakan klinis.', 'Setiap shift',[
        'Jadwal ruang dan petugas penanggung jawab dikonfirmasi.',
        'Ketersediaan alat dan bahan diperiksa sesuai daftar yang disahkan penanggung jawab klinis.',
        'Status kesiapan alat dikonfirmasi melalui catatan resmi; tidak mengarang proses sterilisasi.',
        'Privasi area, dokumen, dan layar kerja diperiksa.',
        '?Kekurangan atau insiden diteruskan segera kepada penanggung jawab klinis.',
        'Serah terima ruang dan kebutuhan bahan dicatat tanpa identitas pasien.'
        ],['Checklist kesiapan ruang','Daftar kebutuhan bahan']),
    sop('LAB-01','Penerimaan dan perencanaan order Lab','Laboratorium',
        'lab_supervisor','lab_supervisor',
        'Memastikan order diterima oleh PJ dan kapasitas rencana dapat ditelusuri.', 'Setiap penerimaan order',[
        'Kode order, sumber internal/mitra, dan penugasan PJ sesuai.',
        'Kelengkapan instruksi diperiksa; pertanyaan klinis dikembalikan ke dokter pengirim.',
        'Kapasitas teknisi, jadwal, alat, dan kebutuhan material diperiksa.',
        'Keputusan terima/tolak beserta alasan dicatat pada workflow order.',
        '*Rencana kerja dan estimasi awal dilampirkan sebagai bukti sintetis.',
        'Tanggung jawab progres dan komunikasi sesudah penerimaan berada pada Lab.'
        ],['Lembar penerimaan order fiktif','Rencana produksi'],order='required',
        states=['assigned','accepted'],sensitive=True),
    sop('LAB-02','Pengerjaan, bahan, dan progres produksi','Laboratorium',
        'technician','lab_supervisor',
        'Mencatat pekerjaan sesuai penugasan, instruksi, serta tahap produksi.', 'Setiap tahap / shift',[
        'Order yang dikerjakan sesuai penugasan teknisi.',
        'Versi instruksi dan desain acuan diperiksa sebelum bekerja.',
        '?Identitas bahan, lot/batch, dan kebutuhan penggantian dicatat bila relevan.',
        'Progres sesuai hasil aktual; kendala atau ketidaksesuaian diteruskan ke PJ Lab.',
        '*Bukti hasil tahap kerja sintetis dilampirkan tanpa data pasien.',
        'Serah terima ke tahap berikut/QC dicatat; teknisi tidak meluluskan hasilnya sendiri.'
        ],['Foto model latihan','Log tahap produksi dan bahan fiktif'],order='required',
        states=['design','production','finishing','rework','qc_pending'],sensitive=True),
    sop('CAD-01','Pengendalian desain CAD/CAM','Laboratorium',
        'cadcam','lab_supervisor',
        'Mencatat versi desain dan serah terima tanpa menimpa acuan lama.', 'Setiap desain / revisi',[
        'Kode referensi pekerjaan sintetis dan pemilik instruksi dicatat.',
        'Versi input serta spesifikasi acuan dikonfirmasi kepada PJ Lab.',
        'Hasil desain ditinjau terhadap daftar teknis yang disahkan PJ.',
        '*Bukti tampilan desain latihan dan identitas revisinya dilampirkan.',
        'Perubahan instruksi klinis menunggu dokter berwenang.',
        'Versi, kendala, dan penerima serah terima dicatat; file medis asli tidak diunggah.'
        ],['Tangkapan layar desain latihan','Register revisi sintetis']),
    sop('QC-01','Pemeriksaan teknis dan pencatatan ketidaksesuaian','Quality Control',
        'qc','qc',
        'Merekam bukti pemeriksaan; hasil QC bisnis tetap dilakukan pada workflow order.', 'Setiap pemeriksaan QC',[
        'Kode order, versi instruksi, dan tahap menunggu QC sesuai.',
        'Pemeriksa berbeda dari teknisi pembuat hasil.',
        'Kesesuaian spesifikasi, material, dan kriteria teknis diperiksa menurut daftar yang disahkan.',
        '*Bukti pemeriksaan sintetis dan temuan dilampirkan.',
        'Ketidaksesuaian mempunyai alasan serta tindak lanjut rework yang dapat ditelusuri.',
        'Keputusan QC dicatat terpisah pada order; checklist ini bukan pengesahan klinis.'
        ],['Lembar inspeksi teknis','Foto model latihan / temuan'],order='required',
        states=['qc_pending'],sensitive=True),
    sop('ETA-01','Keterlambatan dan usulan perubahan komitmen','Laboratorium',
        'lab_supervisor','lab_supervisor',
        'Mencatat dampak keterlambatan dan persetujuan pihak berwenang.', 'Saat risiko keterlambatan',[
        'Komitmen semula dan estimasi aktif dicatat.',
        'Penyebab, dampak pada layanan, dan pilihan penanganan ditinjau.',
        '*Usulan tanggal, alasan, dan rencana tindak lanjut dilampirkan.',
        'Usulan dibuat melalui workflow; tanggal lama tidak ditimpa sebelum persetujuan.',
        'Penerima sah adalah pasien internal atau klinik mitra sesuai sumber order.',
        'Pesan dibaca tidak dianggap persetujuan; penolakan dan tindak lanjut tetap dicatat.'
        ],['Form revisi ETA fiktif','Ringkasan respons tanpa transkrip sensitif'],order='required',
        states=['accepted','design','production','finishing','rework','qc_pending'],sensitive=True),
    sop('HND-01','Persiapan dan bukti serah terima hasil','Front Office',
        'reception lab_supervisor','operations_manager',
        'Membedakan hasil siap diserahkan dengan hasil yang benar-benar telah diterima.', 'Setiap serah terima',[
        'Order berstatus siap setelah QC pada sistem.',
        'Penerima yang berwenang dan tujuan internal/mitra dikonfirmasi.',
        'Kelengkapan paket dan dokumen diperiksa tanpa mengubah instruksi dokter.',
        '*Bukti serah terima sintetis mencatat waktu, pengirim, dan penerima.',
        'Hasil yang baru siap tidak dinyatakan sudah diterima; fitting tetap tanggung jawab klinis.',
        'Ketidaksesuaian saat penerimaan diteruskan ke PJ tanpa menghapus jejak sebelumnya.'
        ],['Form tanda terima fiktif','Checklist paket latihan'],order='required',states=['ready','completed']),
    sop('FIN-01','Pencatatan tagihan dan penerimaan','FAT',
        'reception finance','finance',
        'Mencatat transaksi dengan referensi dan pemisahan petugas penerima/pemeriksa.', 'Setiap transaksi',[
        'Order dan jenis biaya internal/invoice mitra telah sesuai.',
        'Nilai serta metode penerimaan cocok dengan catatan transaksi.',
        '*Bukti pencatatan transaksi fiktif dan referensinya dilampirkan.',
        'Penerimaan belum terverifikasi tidak dihitung sebagai pelunasan.',
        'Penerima uang tidak memverifikasi transaksi yang dicatatnya sendiri.',
        'Selisih, pembayaran sebagian, atau permintaan pengecualian diteruskan ke FAT.'
        ],['Kuitansi fiktif','Rekap transaksi tanpa data rekening pribadi'],order='required'),
    sop('FIN-02','Verifikasi dan rekonsiliasi penerimaan demo','FAT',
        'finance','director auditor',
        'Memisahkan bukti laporan dari verifikasi transaksi; seluruh proses masih simulasi.', 'Setiap shift / rekonsiliasi',[
        'Daftar transaksi dan periode rekonsiliasi ditetapkan.',
        'Petugas pemeriksa berbeda dari pencatat penerimaan.',
        'QRIS/transfer/kartu tidak dinyatakan sukses hanya dari screenshot.',
        '*Rekap transaksi fiktif, sumber pemeriksaan, dan selisih dilampirkan.',
        'Verifikasi di aplikasi diberi label manual demo; tidak digunakan untuk pembayaran nyata.',
        'Selisih dan piutang ditindaklanjuti tanpa menghapus atau menimpa riwayat pembayaran.'
        ],['Rekap rekonsiliasi sintetis','Daftar selisih dan tindak lanjut']),
    sop('INS-01','Kelengkapan administrasi asuransi dan corporate','Asuransi',
        'insurance finance','finance director',
        'Memeriksa kelengkapan administratif tanpa menyatakan klaim disetujui.', 'Setiap berkas klaim',[
        'Referensi klaim sintetis, penjamin, dan periode dicatat.',
        'Kebutuhan dokumen dikonfirmasi sesuai perjanjian yang berlaku.',
        'Dokumen medis hanya diproses melalui petugas dan kanal yang berwenang.',
        '*Daftar kelengkapan anonim dan status kekurangan dilampirkan.',
        'Berkas lengkap tidak dianggap persetujuan penjamin atau pelunasan.',
        'Tenggat, penerima tindak lanjut, dan respons penjamin dicatat.'
        ],['Form kelengkapan klaim kosong','Register klaim anonim']),
    sop('PRC-01','Permintaan, pembelian, dan penerimaan barang','Pengadaan',
        'purchasing','operations_manager finance',
        'Menjaga jejak kebutuhan, persetujuan, pembelian, dan penerimaan.', 'Setiap permintaan pembelian',[
        'Pemohon, kebutuhan, jumlah, dan tenggat dicatat.',
        'Ketersediaan stok dicek sebelum pemesanan.',
        'Pemasok, penawaran, dan dasar pemilihan didokumentasikan.',
        '*Permintaan serta bukti persetujuan administratif sintetis dilampirkan.',
        'Pemesan dan pemeriksa penerimaan dipisahkan sesuai kewenangan.',
        'Selisih penerimaan dan tagihan diteruskan ke Gudang/FAT; checklist tidak menerbitkan PO otomatis.'
        ],['Form permintaan pembelian','Perbandingan penawaran fiktif']),
    sop('INV-01','Pemeriksaan stok dan serah terima bahan','Gudang',
        'warehouse','operations_manager purchasing',
        'Mencatat kondisi, jumlah, serta penelusuran bahan untuk tindak lanjut.', 'Setiap shift / mutasi',[
        'Jenis bahan, lokasi, dan satuan cocok dengan catatan.',
        'Jumlah fisik diperiksa; selisih tidak ditutup dengan penyesuaian tanpa alasan.',
        '?Lot/batch dan kedaluwarsa diperiksa bila relevan.',
        'Bahan rusak atau kedaluwarsa dipisahkan dan dilaporkan.',
        '*Lembar hitung atau serah terima bahan sintetis dilampirkan.',
        'Kebutuhan pembelian dan ketidaksesuaian diteruskan ke petugas terkait.'
        ],['Lembar stok fiktif','Bukti serah terima bahan latihan']),
    sop('CS-01','Bantuan asisten dan pengalihan ke petugas','Layanan Pelanggan',
        'customer_service','operations_manager',
        'Menjaga pengalihan layanan dan penyelesaian keluhan secara terkontrol.', 'Setiap percakapan / shift',[
        'Percakapan dimulai dari asisten yang jelas diberi label simulasi.',
        'Petugas mengambil percakapan melalui antrean sebelum membaca atau membalas.',
        'Pertanyaan klinis diarahkan ke dokter; status produksi dikonfirmasi ke Lab.',
        'CS tidak menyetujui perubahan tanggal, pembayaran, atau tindakan atas nama pasien.',
        '*Ringkasan anonim mencatat kebutuhan, tindak lanjut, dan referensi chat tanpa menyalin transkrip.',
        'Penutupan atau eskalasi dicatat; akses hanya pada percakapan yang ditugaskan.'
        ],['Ringkasan tiket anonim','Catatan eskalasi tanpa transkrip pasien']),
    sop('MKT-01','Perencanaan dan peninjauan materi pemasaran','Marketing & Sales',
        'marketing content_planner','director corporate',
        'Memastikan materi mempunyai tujuan, sumber, dan persetujuan sebelum dipublikasikan.', 'Setiap kampanye / materi',[
        'Tujuan, audiens, kanal, dan jadwal materi dicatat.',
        'Sumber angka dan pernyataan layanan diperiksa bersama pemilik informasi.',
        'Foto, testimoni, dan data pribadi tidak digunakan tanpa izin terpisah yang sah.',
        '*Draf materi dan daftar sumber/izin sintetis dilampirkan.',
        'Pemeriksa serta status persetujuan publikasi dicatat.',
        'Hasil evaluasi dicatat dari data yang tersedia; tidak mengarang capaian.'
        ],['Kalender konten','Draf materi tanpa data pasien']),
    sop('EDT-01','Pemeriksaan dan revisi materi kreatif','Marketing & Sales',
        'editor','marketing',
        'Memastikan hasil suntingan mengikuti brief dan riwayat revisinya jelas.', 'Setiap materi kreatif',[
        'Brief, ukuran, kanal, dan versi sumber dikonfirmasi.',
        'Nama merek, logo, warna, dan ejaan diperiksa.',
        'Hak penggunaan aset dan privasi subjek diperiksa.',
        '*Pratinjau hasil dan nomor revisi dilampirkan.',
        'Persetujuan pemilik konten dicatat sebelum publikasi.',
        'Berkas sumber dan versi sebelumnya dipertahankan.'
        ],['Pratinjau materi latihan','Daftar revisi']),
    sop('SLS-01','Tindak lanjut prospek dan penawaran','Marketing & Sales',
        'sales business_development','marketing director',
        'Mencatat komunikasi bisnis dan serah terima prospek tanpa akses medis.', 'Setiap prospek / shift',[
        'Sumber prospek dan izin komunikasi pemasaran dicatat.',
        'Kebutuhan layanan bisnis diklarifikasi tanpa meminta rincian medis.',
        'Penawaran menggunakan tarif serta ketentuan yang berwenang.',
        '?Diskon atau pengecualian menunggu persetujuan dan tidak dijanjikan terlebih dahulu.',
        '*Ringkasan penawaran anonim serta tindak lanjut dilampirkan.',
        'Prospek yang diteruskan ke Operasional mempunyai pemilik dan tenggat.'
        ],['Penawaran fiktif','Register prospek anonim']),
    sop('CLI-02','Koordinasi dan kesiapan pelayanan Klinik','Klinik',
        'clinic_head','operations_manager director',
        'Memeriksa kesiapan administratif Klinik tanpa mengganti keputusan klinis dokter.', 'Setiap shift',[
        'Jadwal ruang, dokter, dan petugas pendamping dikonfirmasi.',
        'Kewenangan serta kompetensi petugas dikonfirmasi melalui penanggung jawab yang sah.',
        'Daftar kesiapan ruang dan kendala dari Perawat ditinjau.',
        'Risiko antrean dan serah terima dengan Lab ditindaklanjuti.',
        '*Ringkasan kesiapan anonim dan daftar tindakan operasional dilampirkan.',
        'Keputusan klinis tetap pada dokter; manajemen hanya menerima ringkasan yang diperlukan.'
        ],['Ringkasan kesiapan Klinik','Daftar tindak lanjut fasilitas']),
    sop('FIN-03','Permintaan pengecualian keuangan dan koreksi','FAT',
        'finance','director',
        'Mendokumentasikan permintaan kredit, koreksi, refund, atau penghapusan sebelum keputusan berwenang.', 'Setiap permintaan pengecualian',[
        'Jenis permintaan, nilai fiktif, dan alasan dicatat dengan referensi transaksi.',
        'Bukti dan dampak terhadap saldo diperiksa oleh FAT.',
        'Pemohon, pemeriksa, dan pemberi keputusan dipisahkan.',
        '*Draf permintaan dan hasil penelaahan administratif dilampirkan.',
        'Batas nominal dan kebijakan yang belum disahkan tidak diasumsikan berlaku.',
        'Checklist ini tidak menjalankan refund, memberi kredit, atau menghapus piutang; riwayat transaksi dipertahankan.'
        ],['Form pengecualian keuangan fiktif','Register keputusan belum/sudah ditelaah']),
    sop('COM-01','Pemeriksaan izin dan komunikasi layanan','Layanan Pelanggan',
        'reception customer_service lab_supervisor','operations_manager',
        'Memastikan penerima komunikasi, preferensi, dan tindak lanjut tercatat tanpa menyalin pesan sensitif.', 'Setiap shift / kendala komunikasi',[
        'Penerima utama mengikuti sumber layanan: pasien internal atau klinik mitra.',
        'Kontak, izin, kanal, dan frekuensi diperiksa melalui petugas berwenang; verifikasi tetap simulasi.',
        'Tidak mengirim data medis melalui kanal umum atau menghubungi pasien eksternal tanpa otorisasi yang tervalidasi.',
        'Pilihan notifikasi minimal tidak menghapus komunikasi layanan yang wajib.',
        '*Ringkasan anonim dari pemberitahuan tertunda/gagal atau hasil pemeriksaan dilampirkan.',
        'Perubahan janji memerlukan respons tegas; pesan dibaca tidak dianggap persetujuan.'
        ],['Register tindak lanjut komunikasi anonim','Form pilihan komunikasi kosong']),
    sop('CMP-01','Pencatatan keluhan dan tindak lanjut layanan','Layanan Pelanggan',
        'customer_service operations_manager','director',
        'Menetapkan pemilik penanganan keluhan dan menelusuri penyelesaiannya.', 'Setiap keluhan',[
        'Waktu, referensi anonim, dan kebutuhan pelapor dicatat.',
        'Keluhan klinis diteruskan ke dokter; produksi ke Lab; transaksi ke FAT.',
        'Dampak dan urgensi ditinjau tanpa menyampaikan janji di luar kewenangan.',
        '*Ringkasan keluhan yang disamarkan dan bukti tindak lanjut dilampirkan.',
        'Pemilik tindakan, tenggat, dan penerima pembaruan ditetapkan.',
        'Hasil penanganan dikonfirmasi; penutupan tidak menghapus temuan atau riwayat keluhan.'
        ],['Form keluhan anonim','Rencana dan bukti perbaikan layanan']),
    sop('INC-01','Pencatatan insiden dan tindakan perbaikan','Lintas Divisi',
        'reception dentist lab_supervisor technician qc finance nurse cadcam customer_service warehouse purchasing hr marketing it_admin director commissioner chief_executive auditor corporate business_development general_affairs insurance operations_manager branch_manager clinic_head editor content_planner sales housekeeping',
        'operations_manager director',
        'Mencatat insiden operasional tanpa menyebarkan data sensitif.', 'Setiap insiden',[
        'Waktu, lokasi/unit, dan dampak layanan dicatat.',
        'Tindakan awal berada dalam kewenangan petugas; kebutuhan klinis diteruskan ke dokter.',
        '*Bukti insiden yang telah disamarkan dilampirkan.',
        'Penanggung jawab eskalasi dan prioritas ditetapkan.',
        'Rencana perbaikan mempunyai pemilik serta tenggat.',
        'Pemeriksaan ulang dan bukti penutupan dicatat; riwayat insiden dipertahankan.'
        ],['Form insiden anonim','Rencana tindakan perbaikan']),
]

BY_CODE = {entry['code']: entry for entry in CATALOG}


def snapshot(code):
    return deepcopy(BY_CODE[code])
