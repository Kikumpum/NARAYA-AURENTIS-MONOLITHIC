"""Rebuild reviewable draft SOP files and blank annexes; no application data exported."""
from pathlib import Path
import json
import sys
import zipfile
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from backend.sop_catalog import CATALOG, CATALOG_VERSION
from backend.sop_documents import manual_html, manual_markdown
from backend.organization_catalog import POSITIONS, STRUCTURE_NOTES

output=ROOT/'output'/'SOP_NAM_Draf_1.0'
output.mkdir(parents=True,exist_ok=True)
(output/'Panduan_SOP_dan_Lampiran.html').write_text(manual_html(),encoding='utf-8')
(ROOT/'docs'/'SOP_OPERASIONAL_DRAF_1.0.md').write_text(manual_markdown(),encoding='utf-8')
(output/'Katalog_SOP.json').write_text(json.dumps(CATALOG,ensure_ascii=False,indent=2),encoding='utf-8')
for s in CATALOG:
    lines=[f"NAM DMS — {s['code']} — {s['title']}",f"Versi {CATALOG_VERSION} · BELUM DISAHKAN · hanya bukti fiktif",
        '', 'Tanggal / Shift: __________________', 'Unit / Jabatan: __________________',
        'Penyusun: __________________', 'Order / Referensi: __________________',
        'Ringkasan: __________________________________________________', '']
    for i in s['items']:
        lines.extend([f"{i['key']} — {i['text']}",'[ ] Sesuai  [ ] Ada temuan'+('  [ ] Tidak relevan (alasan wajib)' if i['allow_na'] else ''),
            'Catatan / Alasan: ___________________________________',
            'Tindakan / Penanggung jawab / Tenggat: ___________________________________',
            'Nama bukti: __________________'+(' (WAJIB)' if i['evidence_required'] else ''),''])
    lines.extend(['Peninjau (orang berbeda): __________________','Hasil: [ ] Ditinjau [ ] Perlu perbaikan',
        'Catatan: ___________________________________', '', 'Checklist tidak menjalankan persetujuan bisnis, pembayaran, QC, atau instruksi klinis.'])
    (output/(s['code']+'_Form_Checklist.txt')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
annexes={
    'Lampiran_A_Laporan.txt':'Nomor laporan | SOP / Versi | Revisi | Tanggal / Shift | Unit | Penyusun / Jabatan | Order / Referensi\nRingkasan hasil:\nTemuan | Tindakan | Penanggung jawab | Tenggat | Status\nPeninjau berbeda | Catatan peninjauan\n',
    'Lampiran_B_Register_Bukti.txt':'Nomor laporan | Item SOP | Nama berkas / Versi | Isi bukti anonim | Pengunggah | Waktu | SHA-256\n[ ] Fiktif [ ] Sesuai item [ ] Dapat dibaca [ ] Tanpa data pasien asli\n',
    'Lampiran_C_Serah_Terima.txt':'Waktu | Pengirim | Penerima berwenang | Referensi | Kelengkapan | Kondisi / Temuan | Tindak lanjut / Tenggat\nHasil siap diserahkan tidak otomatis berarti telah diterima atau selesai fitting.\n',
    'Lampiran_D_Kendali_Revisi.txt':'Versi | Alasan / Bagian berubah | Penyusun | Peninjau | Tanggal | Referensi bukti lama\nVersi lama dan lampiran pengajuan sebelumnya tetap dipertahankan.\n',
}
for name,content in annexes.items():(output/name).write_text('NAM DMS — DRAF / DATA FIKTIF\n'+content,encoding='utf-8')
(output/'BACA_DULU.txt').write_text('Buka Panduan_SOP_dan_Lampiran.html di browser untuk membaca/mencetak.\nForm TXT dapat diedit dengan editor teks. Unggah hanya bukti fiktif pada item checklist yang sesuai.\nSemua SOP adalah draf untuk penelaahan pemilik proses. SOP klinis dan kebijakan keuangan belum disahkan.\nArsip ini berisi template kosong, bukan laporan yang sudah dikerjakan.\n',encoding='utf-8')
package=ROOT/'output'/'NAM_Draf_SOP_Checklist_dan_Lampiran_1.0.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
    names=['Panduan_SOP_dan_Lampiran.html','Katalog_SOP.json','BACA_DULU.txt',
           *[s['code']+'_Form_Checklist.txt' for s in CATALOG],*annexes]
    if (output/'Contoh_Bukti_IT_Demo.txt').exists():names.append('Contoh_Bukti_IT_Demo.txt')
    for name in sorted(names):z.write(output/name,name)
diagram=['flowchart TB']
for code,name,parent,division,roles in POSITIONS:
    diagram.append(f'  {code}["{name}"]')
    if parent:diagram.append(f'  {parent} --> {code}')
diagram.extend(['  lab_head -. "koordinasi teknis; QC independen" .-> qc','  clinic_head -. "dukungan layanan" .-> reception','  lab_head -. "dukungan layanan" .-> customer_service'])
(ROOT/'docs'/'ORGANIZATION_DRAFT.mmd').write_text('\n'.join(diagram)+'\n',encoding='utf-8')
print(json.dumps({'sops':len(CATALOG),'checklist_items':sum(len(s['items']) for s in CATALOG),'positions':len(POSITIONS),'package':str(package),'manual':str(output/'Panduan_SOP_dan_Lampiran.html')},ensure_ascii=False))
