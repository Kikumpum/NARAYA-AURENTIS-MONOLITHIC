"""Draf struktur dari bagan pengguna; jabatan tidak memberikan izin aplikasi."""

# code, nama, induk pelaporan, divisi, peran aplikasi yang kompatibel
POSITIONS = [
    ('commissioner', 'Komisaris', None, 'Pengawasan', ['commissioner']),
    ('chief_executive', 'Direktur Utama', 'commissioner', 'Direksi', ['chief_executive']),
    ('director', 'Direktur', 'chief_executive', 'Direksi', ['director']),
    ('business_development', 'Business Development', 'director', 'Pengembangan Bisnis', ['business_development']),
    ('it', 'IT', 'director', 'IT', ['it_admin']),
    ('auditor', 'Auditor', 'commissioner', 'Pengawasan', ['auditor']),
    ('corporate', 'Corporate', 'director', 'Corporate', ['corporate']),
    ('hr', 'HR', 'director', 'HR', ['hr']),
    ('general_affairs', 'IC / GA', 'director', 'General Affairs', ['general_affairs']),
    ('finance', 'FAT', 'director', 'FAT', ['finance']),
    ('insurance', 'Insurance', 'hr', 'Asuransi', ['insurance']),
    ('operations', 'Operation', 'director', 'Operasional', ['operations_manager']),
    ('procurement', 'Procurement', 'operations', 'Pengadaan', ['purchasing']),
    ('branch_head', 'Branch Head', 'operations', 'Cabang', ['branch_manager']),
    ('branch_manager', 'Branch Manager', 'branch_head', 'Cabang', ['branch_manager']),
    ('lab_head', 'Kepala Lab', 'operations', 'Laboratorium', ['lab_supervisor']),
    ('senior_lab', 'Senior Lab', 'lab_head', 'Laboratorium', ['lab_supervisor']),
    ('clinic_head', 'Kepala Klinik', 'operations', 'Klinik', ['clinic_head']),
    ('marketing', 'Marketing and Sales', 'operations', 'Marketing & Sales', ['marketing']),
    ('editor', 'Editor', 'marketing', 'Marketing & Sales', ['editor']),
    ('content_planner', 'Content Planner', 'marketing', 'Marketing & Sales', ['content_planner']),
    ('sales', 'Sales', 'marketing', 'Marketing & Sales', ['sales']),
    ('customer_service', 'Customer Service', 'operations', 'Layanan Pelanggan', ['customer_service']),
    ('reception', 'Resepsionis', 'operations', 'Front Office', ['reception']),
    ('housekeeping', 'Housekeeping', 'general_affairs', 'General Affairs', ['housekeeping']),
    # Fungsi aplikasi yang tetap diperlukan walau tidak dirinci pada bagan.
    ('dentist', 'Dokter Gigi', 'clinic_head', 'Klinik', ['dentist']),
    ('nurse', 'Perawat', 'clinic_head', 'Klinik', ['nurse']),
    ('technician', 'Teknisi Lab', 'senior_lab', 'Laboratorium', ['technician']),
    ('cadcam', 'CAD/CAM', 'senior_lab', 'Laboratorium', ['cadcam']),
    ('qc', 'Quality Control', 'lab_head', 'Quality Control', ['qc']),
    ('warehouse', 'Gudang', 'operations', 'Gudang', ['warehouse']),
]

STRUCTURE_NOTES = [
    'Draf berdasarkan bagan pengguna, 20 Oktober 2026. Nama pribadi tidak ditranskripsi dari gambar beresolusi rendah.',
    'Garis pelaporan Auditor ke Komisaris, IC / GA, Branch Head, dan dukungan bersama CS/Resepsionis/Housekeeping adalah usulan yang perlu dikonfirmasi.',
    'Satu kotak di jajaran penasihat belum terbaca jelas; tidak diberi nama atau kewenangan rekaan.',
    'Garis koordinasi pada bagan tidak dianggap sebagai hak membaca data atau menyetujui transaksi.',
    'Dokter, Perawat, Teknisi, CAD/CAM, QC dan Gudang adalah rincian fungsi aplikasi tambahan.',
    'QC harus memeriksa secara independen dari pembuat hasil; Kepala Lab tidak otomatis boleh meluluskan QC.',
]

DEMO_POSITION = {
    'resepsionis':'reception', 'dokter':'dentist', 'dokter2':'dentist', 'lab':'lab_head',
    'lab2':'senior_lab', 'teknisi':'technician', 'qc':'qc', 'fat':'finance',
    'direktur':'director', 'it':'it', 'perawat':'nurse', 'cadcam':'cadcam',
    'cs':'customer_service', 'gudang':'warehouse', 'purchasing':'procurement',
    'hr':'hr', 'marketing':'marketing',
}

ADDITIONAL_ROLES = ('commissioner','chief_executive','auditor','corporate','business_development',
                    'general_affairs','insurance','operations_manager','branch_manager','clinic_head',
                    'editor','content_planner','sales','housekeeping')

from backend.demo_accounts import EXTRA_STAFF
DEMO_POSITION.update({username: position for username, _, _, position in EXTRA_STAFF})
