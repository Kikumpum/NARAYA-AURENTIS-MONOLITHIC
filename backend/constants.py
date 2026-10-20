ROLES = ('reception', 'dentist', 'lab_supervisor', 'technician', 'qc', 'finance', 'director', 'partner', 'patient', 'it_admin', 'nurse', 'cadcam', 'customer_service', 'warehouse', 'purchasing', 'hr', 'marketing')
METHODS = ('cash', 'qris', 'bank_transfer', 'debit_edc', 'credit_card', 'insurance_corporate', 'installment')
# 'installment' is allowed as accounting-plan request only; no fake settlement is created.
CATEGORIES = {'crown': 4, 'bridge': 6, 'veneer': 5, 'denture': 9, 'implant': 8, 'other': 5}

ROLE_LABELS = {
    'reception':'Resepsionis','dentist':'Dokter Gigi','lab_supervisor':'Supervisor Lab','technician':'Teknisi Lab',
    'qc':'Quality Control','finance':'FAT','director':'Direktur','partner':'Klinik Mitra','patient':'Pasien',
    'it_admin':'IT','nurse':'Perawat','cadcam':'CAD/CAM','customer_service':'Customer Service','warehouse':'Gudang',
    'purchasing':'Procurement','hr':'HR','marketing':'Marketing and Sales','commissioner':'Komisaris',
    'chief_executive':'Direktur Utama','auditor':'Auditor','corporate':'Corporate',
    'business_development':'Business Development','general_affairs':'IC / GA','insurance':'Insurance',
    'operations_manager':'Operation','branch_manager':'Branch Manager','clinic_head':'Kepala Klinik',
    'editor':'Editor','content_planner':'Content Planner','sales':'Sales','housekeeping':'Housekeeping',
}
