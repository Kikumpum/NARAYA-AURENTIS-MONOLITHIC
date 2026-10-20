"""Explicit fictional login fixtures. An organization chart never creates users."""

# Existing IDs remain stable for orders, appointments and acceptance scenarios.
BASE_USERS = (
    (1,'resepsionis','Resepsionis Demo','reception',1), (2,'dokter','Dokter Klinik Demo','dentist',1),
    (3,'lab','Supervisor Lab Demo','lab_supervisor',1), (4,'teknisi','Teknisi Demo','technician',1),
    (5,'qc','QC Demo','qc',1), (6,'fat','FAT Demo','finance',1),
    (7,'direktur','Direktur Demo','director',1), (8,'mitra','Klinik Mitra Demo','partner',2),
    (9,'pasien','Pasien Demo','patient',1), (10,'it','IT Demo','it_admin',1),
    (11,'dokter2','Dokter Klinik 2 Demo','dentist',1), (12,'lab2','Supervisor Lab 2 Demo','lab_supervisor',1),
    (13,'perawat','Perawat Demo','nurse',1), (14,'cadcam','CAD CAM Demo','cadcam',1),
    (15,'cs','Customer Service Demo','customer_service',1), (16,'gudang','Gudang Demo','warehouse',1),
    (17,'purchasing','Purchasing Demo','purchasing',1), (18,'hr','HR Demo','hr',1),
    (19,'marketing','Marketing Demo','marketing',1),
)

# Added at the owner's request for testing every division. No real appointment,
# inherited authority or additional clinical/financial permission is implied.
# username, display name, existing application role, draft position code
EXTRA_STAFF = (
    ('komisaris','Komisaris Demo','commissioner','commissioner'),
    ('direktur_utama','Direktur Utama Demo','chief_executive','chief_executive'),
    ('business_development','Business Development Demo','business_development','business_development'),
    ('auditor','Auditor Demo','auditor','auditor'),
    ('corporate','Corporate Demo','corporate','corporate'),
    ('ga','IC / GA Demo','general_affairs','general_affairs'),
    ('insurance','Insurance Demo','insurance','insurance'),
    ('operation','Operation Demo','operations_manager','operations'),
    ('branch_head','Branch Head Demo','branch_manager','branch_head'),
    ('branch_manager','Branch Manager Demo','branch_manager','branch_manager'),
    ('kepala_klinik','Kepala Klinik Demo','clinic_head','clinic_head'),
    ('editor','Editor Demo','editor','editor'),
    ('content_planner','Content Planner Demo','content_planner','content_planner'),
    ('sales','Sales Demo','sales','sales'),
    ('housekeeping','Housekeeping Demo','housekeeping','housekeeping'),
)

# Explicit aliases are only used when no actual username matches. Passwords
# remain exact and never undergo normalization or aliasing.
LOGIN_ALIASES = {
    'direktur utama':'direktur_utama', 'direkturutama':'direktur_utama', 'dirut':'direktur_utama',
    'business development':'business_development', 'ic / ga':'ga', 'ic/ga':'ga',
    'branch head':'branch_head', 'branch manager':'branch_manager',
    'kepala klinik':'kepala_klinik', 'content planner':'content_planner',
    'kepala lab':'lab', 'senior lab':'lab2', 'procurement':'purchasing',
    'hrd':'hr', 'quality control':'qc', 'customer service':'cs',
    'dokter gigi':'dokter', 'teknisi lab':'teknisi',
}
