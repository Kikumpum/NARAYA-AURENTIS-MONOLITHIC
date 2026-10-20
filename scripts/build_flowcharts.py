"""Render the reviewed demo 0.4 flows as vector PDF and editable SVG files.

Requires reportlab and Windows Segoe UI fonts. No application data is read.
Run from the project root: python scripts/build_flowcharts.py
"""
from __future__ import annotations

import html
import json
import math
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output' / 'flowchart'
W, H = landscape(A3)
GREEN = '#203F35'
INK = '#263A33'
MUTED = '#61716A'
LINE = '#71867A'
GOLD = '#A58448'
CREAM = '#FAF8F2'
PALE = '#EDF3EF'
GOLD_PALE = '#F7F0DF'
RED = '#885247'
RED_PALE = '#F8EEEA'
BLUE = '#EDF2F6'


class Diagram:
    def __init__(self, pdf, number, slug, title, subtitle):
        self.pdf, self.number, self.slug = pdf, number, slug
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.2f}" height="{H:.2f}" viewBox="0 0 {W:.2f} {H:.2f}">',
                    '<style>text{font-family:"Segoe UI",Arial,sans-serif}</style>']
        self.nodes = {}
        self.boxes = []
        self.rect(0, 0, W, H, CREAM, CREAM, 0)
        self.text(44, 36, 'NARAYA AURENTIS', 13, GREEN, True)
        self.text(44, 55, 'MONOLITHIC / DENTAL MANAGEMENT SYSTEM', 8.5, MUTED)
        self.text(W - 44, 38, f'FLOWCHART  {number:02d} / 06', 10, GOLD, True, 'right')
        self.text(W - 44, 55, 'Demo 0.4 / 20 Oktober 2026', 8.5, MUTED, anchor='right')
        self.line([(44, 76), (W - 44, 76)], '#DADFD7', .8)
        self.text(44, 100, title, 26, GREEN, True)
        self.text(44, 130, subtitle, 11.5, MUTED)
        self.line([(44, 783), (W - 44, 783)], '#DADFD7', .8)
        self.text(44, 801, 'DEMO LOKAL / DATA FIKTIF', 8.5, GREEN, True)
        self.text(340, 801, 'Kotak: proses     Belah ketupat: keputusan     Panah: urutan kerja', 8.5, MUTED)
        self.text(W - 44, 801, f'{number:02d}', 10, GOLD, True, 'right')

    def rect(self, x, y, w, h, fill, stroke=LINE, radius=10):
        p = self.pdf
        p.setFillColor(HexColor(fill)); p.setStrokeColor(HexColor(stroke)); p.setLineWidth(.9)
        p.roundRect(x, H-y-h, w, h, radius, fill=1, stroke=1)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="0.9"/>')

    def text(self, x, y, value, size=11.5, color=INK, bold=False, anchor='left'):
        font = 'SegoeBold' if bold else 'Segoe'
        self.pdf.setFont(font, size); self.pdf.setFillColor(HexColor(color))
        align = {'left': self.pdf.drawString, 'center': self.pdf.drawCentredString, 'right': self.pdf.drawRightString}[anchor]
        align(x, H-y-size, value)
        svg_anchor = {'left':'start','center':'middle','right':'end'}[anchor]
        self.svg.append(f'<text x="{x}" y="{y+size}" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}" text-anchor="{svg_anchor}">{html.escape(value)}</text>')

    def line(self, pts, color=LINE, width=1.4, dashed=False, arrow=False):
        p = self.pdf; p.setStrokeColor(HexColor(color)); p.setFillColor(HexColor(color)); p.setLineWidth(width)
        p.setDash([4, 4] if dashed else [])
        path=p.beginPath(); path.moveTo(pts[0][0], H-pts[0][1])
        for x,y in pts[1:]: path.lineTo(x,H-y)
        p.drawPath(path); p.setDash([])
        points=' '.join(f'{x},{y}' for x,y in pts)
        dash=' stroke-dasharray="4 4"' if dashed else ''
        self.svg.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"{dash}/>')
        if arrow:
            (x0,y0),(x,y)=pts[-2:]
            angle=math.atan2(y-y0,x-x0); size=7
            points=[(x,y),(x-size*math.cos(angle-.42),y-size*math.sin(angle-.42)),(x-size*math.cos(angle+.42),y-size*math.sin(angle+.42))]
            shape=p.beginPath(); shape.moveTo(points[0][0],H-points[0][1])
            for a,b in points[1:]:shape.lineTo(a,H-b)
            shape.close();p.drawPath(shape,fill=1,stroke=0)
            self.svg.append('<polygon points="'+' '.join(f'{a},{b}' for a,b in points)+f'" fill="{color}"/>')

    def label(self,x,y,text):
        width=pdfmetrics.stringWidth(text,'SegoeBold',10)+14
        self.rect(x-width/2,y-2,width,18,CREAM,CREAM,3)
        self.text(x,y,text,10,MUTED,True,'center')

    def node(self, key, x,y,w,h,title,body=(),kind='process'):
        assert key not in self.nodes
        assert x>=35 and y>=153 and x+w<=W-35 and y+h<=764, (key,x,y,w,h)
        colors={'process':('#FFFFFF','#C8D3CB',INK), 'main':(GREEN,GREEN,'#FFFFFF'),
                'soft':(PALE,'#C8D3CB',INK),'decision':(GOLD_PALE,'#BEA46F',INK),
                'reject':(RED_PALE,'#D8B9AE',RED),'blue':(BLUE,'#C9D3DC',INK)}
        fill,stroke,fg=colors[kind]
        if kind=='decision':
            points=[(x+w/2,y),(x+w,y+h/2),(x+w/2,y+h),(x,y+h/2)]
            p=self.pdf;p.setFillColor(HexColor(fill));p.setStrokeColor(HexColor(stroke));p.setLineWidth(1)
            path=p.beginPath();path.moveTo(points[0][0],H-points[0][1])
            for a,b in points[1:]:path.lineTo(a,H-b)
            path.close();p.drawPath(path,fill=1,stroke=1)
            self.svg.append('<polygon points="'+' '.join(f'{a},{b}' for a,b in points)+f'" fill="{fill}" stroke="{stroke}"/>')
        else:self.rect(x,y,w,h,fill,stroke)
        titles=title.split('\n');body=list(body)
        lines=[(t,12.3,True) for t in titles]+[(t,10.8,False) for t in body]
        total=sum(s+5 for _,s,_ in lines)-5
        ty=y+(h-total)/2-1
        for txt,size,bold in lines:
            usable=w*(.74 if kind=='decision' else 1)-24
            assert pdfmetrics.stringWidth(txt,'SegoeBold' if bold else 'Segoe',size)<=usable, (key,txt)
            self.text(x+w/2,ty,txt,size,fg,bold,'center');ty+=size+5
        self.nodes[key]={'L':(x,y+h/2),'R':(x+w,y+h/2),'T':(x+w/2,y),'B':(x+w/2,y+h)}
        self.boxes.append((key,x,y,w,h))

    def edge(self, a,b, sa='B',sb='T',via=(),label=None,color=LINE,dashed=False):
        pts=[self.nodes[a][sa],*via,self.nodes[b][sb]]
        for u,v in zip(pts,pts[1:]):assert abs(u[0]-v[0])<.01 or abs(u[1]-v[1])<.01,(a,b,u,v)
        self.line(pts,color,1.5,dashed,True)
        if label:self.label(*label)

    def note(self,y,title,body):
        self.rect(44,y,W-88,47,PALE,'#D8E1D9',6)
        self.text(58,y+8,title,10,GREEN,True)
        self.text(58,y+25,body,10,MUTED)

    def section(self,x,y,kicker):self.text(x,y,kicker,10.5,GOLD,True)

    def finish(self):
        # Fixed positions make native vector exports predictable and editable.
        for i,(name,x,y,w,h) in enumerate(self.boxes):
            for other,a,b,c,d in self.boxes[i+1:]:
                assert min(x+w,a+c)-max(x,a)<=0 or min(y+h,b+d)-max(y,b)<=0,(name,other,'overlap')
        (OUT/f'{self.number:02d}_{self.slug}.svg').write_text('\n'.join(self.svg+['</svg>']),encoding='utf-8')
        self.pdf.showPage()


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    fonts=Path('C:/Windows/Fonts')
    pdfmetrics.registerFont(TTFont('Segoe',str(fonts/'segoeui.ttf')))
    pdfmetrics.registerFont(TTFont('SegoeBold',str(fonts/'segoeuib.ttf')))
    pdf=canvas.Canvas(str(OUT/'NAM_Flowchart_Lengkap_Demo_0.4.pdf'),pagesize=(W,H),pageCompression=1)
    pdf.setTitle('Naraya Aurentis - Flowchart Sistem Demo 0.4')
    pdf.setAuthor('Naraya Aurentis Monolithic')
    pdf.setSubject('Enam diagram alur demo lokal: akses, Lab, persetujuan, bantuan, keuangan, dan SOP.')

    d=Diagram(pdf,1,'pintu_masuk','Dua pintu masuk, akses sesuai kebutuhan','Pasien memakai portal sendiri. Pegawai dan klinik mitra masuk melalui ruang kerja dengan hak yang berbeda.')
    columns=[(44,'PASIEN INTERNAL','/pasien','ID pasien + kata sandi','Rekam pasien tertaut','Hanya data milik sendiri',
              ['Layanan dan perkembangan','Jadwal, dokter, pemberitahuan','Persetujuan dan Bantuan'],'Diagram 03 dan 04','soft'),
             (440,'PEGAWAI NARAYA','/','Akun kerja + kata sandi','Peran dan penugasan','Organisasi dan tahap workflow',
              ['Klinik, Lab, QC dan keuangan','Materi divisi, SOP dan laporan','Menu mengikuti jabatan'],'Diagram 02, 05 dan 06','main'),
             (836,'KLINIK MITRA','/','Akun mitra + kata sandi','Organisasi klinik mitra','Hanya kasus organisasi sendiri',
              ['Kirim order eksternal','Pantau status dan tanggal','Invoice serta pemberitahuan'],'Diagram 02, 03 dan 05','blue')]
    for i,(x,role,url,login,check,scope,features,dest,kind) in enumerate(columns):
        d.section(x,168,role)
        d.node(f'l{i}',x,205,310,70,f'Masuk melalui {url}',[login],kind=kind)
        d.node(f'g{i}',x,335,310,76,'Backend memeriksa akses',[check,scope])
        d.node(f'v{i}',x,475,310,102,'Ruang layanan',features,kind='soft')
        d.node(f'c{i}',x,635,310,56,'Lanjut ke alur terkait',[dest])
        d.edge(f'l{i}',f'g{i}');d.edge(f'g{i}',f'v{i}',label=(x+155,435,'Valid'));d.edge(f'v{i}',f'c{i}')
    d.note(719,'Jika validasi gagal, akses ditolak.','Pasien tidak melihat akun divisi, struktur organisasi, SOP, materi pegawai, atau laporan internal. IT tidak otomatis melihat data medis.')
    d.finish()

    d=Diagram(pdf,2,'klinik_dan_laboratorium','Dari surat kerja sampai siap diserahkan','Dokter bertanggung jawab atas instruksi klinis. Setelah diterima, Lab mengelola produksi, progres, dan risiko keterlambatan.')
    d.node('internal',44,178,230,60,'Klinik internal',['Dokter membuat surat kerja'],kind='soft')
    d.node('external',44,270,230,60,'Klinik mitra',['Order dengan referensi kasus'],kind='blue')
    d.node('intake',330,224,230,68,'Antrean order Lab',['Sumber dan organisasi tercatat'],kind='main')
    d.node('assign',616,224,230,68,'Resepsionis menugaskan',['PJ Lab yang tersedia'])
    d.node('accept',916,213,224,90,'PJ Lab\nmenerima?',kind='decision')
    d.node('reject',616,350,230,60,'Tolak dengan alasan',['Tugaskan kembali'],kind='reject')
    d.node('plan',916,480,224,76,'Supervisor validasi rencana',['Teknisi, jadwal dan estimasi'])
    d.node('prod',616,480,230,76,'Teknisi mengerjakan',['Desain, produksi, finishing','Ajukan pemeriksaan QC'])
    d.node('qc',330,473,230,90,'QC lulus?',kind='decision')
    d.node('ready',44,480,230,76,'Siap diserahkan',['Hasil teknis lolos pemeriksaan'],kind='main')
    d.node('rework',330,641,230,65,'Rework tercatat',['Alasan gagal dan perbaikan'],kind='reject')
    d.edge('internal','intake','R','L',[(300,208),(300,258)])
    d.edge('external','intake','R','L',[(300,300),(300,258)])
    d.edge('intake','assign','R','L');d.edge('assign','accept','R','L')
    d.edge('accept','reject','B','R',[(1028,380)],label=(950,361,'Tidak'))
    d.edge('reject','assign','T','B',label=(731,311,'Alihkan'))
    d.edge('accept','plan','R','R',[(1170,258),(1170,518)],label=(1168,399,'Ya'))
    d.edge('plan','prod','L','R');d.edge('prod','qc','L','R')
    d.edge('qc','ready','L','R',label=(302,495,'Ya'))
    d.edge('qc','rework',label=(445,596,'Tidak'))
    d.edge('rework','prod','R','B',[(731,673.5)],label=(676,654,'Perbaiki'))
    d.note(719,'Pemberitahuan mengikuti penerima yang berwenang.','Internal: pasien sesuai verifikasi kontak dan izin. Eksternal: klinik mitra menjadi penerima utama. Status ready berarti siap diserahkan.')
    d.finish()

    d=Diagram(pdf,3,'persetujuan_perubahan','Perubahan perlu persetujuan yang jelas','Membaca pesan bukan persetujuan. Selama belum ada keputusan yang sah, usulan tidak menggantikan komitmen aktif.')
    for prefix,x,heading,title,body,pending,decision,approved,denied in [
        ('eta',44,'PERUBAHAN TANGGAL ORDER','Supervisor Lab mengajukan tanggal',
         ['Tanggal semula, usulan, dan alasan disimpan'],
         ['Pasien internal atau klinik mitra eksternal','meninjau usulan milik ordernya'],
         'Tanggal baru\ndisetujui?',
         ('Komitmen diperbarui',['Tanggal baru menjadi aktif','Riwayat lama tetap disimpan']),
         ('Komitmen lama tetap',['Usulan ditandai ditolak','Lab menindaklanjuti'])),
        ('doc',620,'PERGANTIAN DOKTER KUNJUNGAN','Resepsionis mengusulkan pengganti',
         ['Dokter aktif dan tersedia sesuai shift'],
         ['Pasien yang memiliki jadwal meninjau','nama dokter pengganti melalui portal'],
         'Dokter baru\ndisetujui?',
         ('Pengganti ditetapkan',['Dokter pada jadwal diganti','Status kembali terkonfirmasi']),
         ('Pergantian ditolak',['Dokter awal tidak diganti','Petugas mengatur tindak lanjut']))]:
        d.section(x,168,heading)
        d.node(prefix+'proposal',x,209,526,74,title,body,kind='soft')
        d.node(prefix+'pending',x,332,526,76,'Menunggu respons eksplisit',pending)
        d.node(prefix+'decision',x+151,457,224,90,decision,kind='decision')
        d.node(prefix+'yes',x,625,245,88,approved[0],approved[1],kind='main')
        d.node(prefix+'no',x+281,625,245,88,denied[0],denied[1],kind='reject')
        d.edge(prefix+'proposal',prefix+'pending');d.edge(prefix+'pending',prefix+'decision')
        d.edge(prefix+'decision',prefix+'yes','L','T',[(x+122.5,502)],label=(x+122.5,552,'Ya'))
        d.edge(prefix+'decision',prefix+'no','R','T',[(x+403.5,502)],label=(x+403.5,552,'Tidak'))
    d.note(729,'Keputusan diperiksa di backend dan dicatat dalam audit.','Persetujuan tanggal memeriksa versi usulan. Pergantian dokter hanya diproses ketika jadwal sedang menunggu respons pasien.')
    d.finish()

    d=Diagram(pdf,4,'bantuan_pasien','Bantuan pasien: asisten, lalu petugas','Percakapan pribadi tersedia untuk pasien internal. CS memakai kotak masuk layanan; pegawai lain memakai materi divisi.')
    for key,x,title,body in [('portal',44,'Masuk portal pasien',['Identitas dan data sendiri']),('open',330,'Buka Bantuan',['Konteks umum atau layanan sendiri']),('assistant',616,'Asisten layanan',['Jawaban simulasi lokal'])]:
        d.node(key,x,226,230,76,title,body,kind='soft' if key!='assistant' else 'main')
    d.node('handoff',916,219,224,90,'Meminta\npetugas?',kind='decision')
    d.node('stay',916,366,224,65,'Lanjut dengan asisten',['Selama status masih assistant'])
    d.node('queue',916,532,224,76,'Antrean CS',['Status waiting; hanya metadata'],kind='blue')
    d.node('claim',616,532,230,76,'Satu CS mengambil',['Penugasan dikunci secara atomik'])
    d.node('human',330,532,230,76,'Petugas membalas',['Status human; asisten berhenti'])
    d.node('closed',44,532,230,76,'Percakapan ditutup',['Riwayat tetap tersimpan'],kind='main')
    d.edge('portal','open','R','L');d.edge('open','assistant','R','L');d.edge('assistant','handoff','R','L')
    d.edge('handoff','stay',label=(1028,330,'Tidak'))
    d.edge('stay','assistant','L','B',[(731,398.5)],label=(825,379,'Lanjut'))
    d.edge('handoff','queue','R','R',[(1170,264),(1170,570)],label=(1168,471,'Ya'))
    d.edge('queue','claim','L','R');d.edge('claim','human','L','R');d.edge('human','closed','L','R')
    d.note(663,'Transkrip dibuka hanya oleh pasien pemilik dan CS yang ditugaskan.','CS tidak otomatis memperoleh akses rekam medis. Riwayat dan audit dipertahankan; permintaan chat memakai kunci pencegah duplikasi.')
    d.text(58,736,'Batas demo: belum terhubung ke model AI eksternal, WhatsApp, SMS, atau email. Pertanyaan klinis diarahkan kepada dokter.',10.5,MUTED)
    d.finish()

    d=Diagram(pdf,5,'keuangan','Pencatatan uang dan verifikasi dipisahkan','Tagihan hanya menghitung dana yang berstatus verified. Screenshot bukti pembayaran tidak otomatis membuat tagihan lunas.')
    d.node('invoice',44,210,300,78,'Buat invoice per order',['Resepsionis atau FAT','Internal cost / external invoice'],kind='soft')
    d.node('record',445,210,300,78,'Resepsionis mencatat pembayaran',['Nominal, metode dan referensi','Tidak boleh melampaui tagihan'])
    d.node('pending',846,210,300,78,'Menunggu verifikasi',['Status pending_verification','Belum dihitung sebagai dana masuk'],kind='blue')
    d.node('gate',866,419,260,110,'FAT berwenang\ndan berbeda\ndari pencatat?',kind='decision')
    d.node('wait',445,435,300,78,'Tetap menunggu verifikasi',['Tanpa pemeriksa yang sah,','pembayaran tidak disahkan'],kind='reject')
    d.node('verified',846,626,300,78,'FAT memverifikasi simulasi',['Rekonsiliasi manual demo','Status menjadi verified'],kind='main')
    d.node('sum',445,626,300,78,'Sistem menghitung ulang',['Dana terverifikasi dan sisa tagihan','Riwayat transaksi tetap tersimpan'])
    d.node('status',44,626,300,78,'Status invoice ditampilkan',['Belum lunas / sebagian / lunas','Sesuai total dana terverifikasi'],kind='soft')
    d.edge('invoice','record','R','L');d.edge('record','pending','R','L');d.edge('pending','gate')
    d.label(996,343,'Pemeriksaan terpisah')
    d.edge('gate','wait','L','R',label=(800,452,'Tidak'))
    d.edge('gate','verified',label=(996,570,'Ya'))
    d.edge('verified','sum','L','R');d.edge('sum','status','L','R')
    d.note(726,'Verifikasi ini hanya simulasi lokal, bukan konfirmasi bank atau payment gateway.','Peninjauan SOP tidak melunaskan tagihan. Integrasi settlement dan kontrol produksi perlu diselesaikan sebelum transaksi nyata.')
    d.finish()

    d=Diagram(pdf,6,'materi_sop_dan_laporan','Materi divisi, checklist, bukti, dan laporan','Draf 32 SOP memuat 192 item pemeriksaan. Hak pelaksana dan peninjau mengikuti peran, organisasi, order, dan tahap kerja.')
    d.node('learn',44,223,230,78,'Buka Materi divisi',['Baca urutan dan batas kewenangan','Contoh bukti serta latihan'],kind='soft')
    d.node('sop',330,223,230,78,'Pilih SOP sesuai peran',['Ringkasan divisi lain bersifat umum'])
    d.node('draft',616,223,230,78,'Buat draf laporan',['Versi SOP disimpan','Hubungkan order jika diwajibkan'])
    d.node('check',902,223,244,78,'Lengkapi checklist dan bukti',['Hasil per item, temuan, tindakan','Penanggung jawab dan tenggat'])
    d.node('complete',912,384,224,100,'Lengkap dan\ntahap sesuai?',kind='decision')
    d.node('fix',616,395,230,78,'Perbaiki draf dan bukti',['Versi pengajuan lama dipertahankan'],kind='reject')
    d.node('submit',902,621,244,78,'Ajukan laporan',['Snapshot pengajuan disimpan'],kind='blue')
    d.node('review',616,610,230,100,'Hasil\npeninjauan?',kind='decision')
    d.node('lock',330,621,230,78,'Laporan ditinjau dan dikunci',['Peninjau berwenang','Berbeda dari pembuat laporan'],kind='main')
    d.node('export',44,621,230,78,'Ekspor sesuai hak akses',['HTML atau ZIP','Laporan, bukti dan riwayat'])
    d.edge('learn','sop','R','L');d.edge('sop','draft','R','L');d.edge('draft','check','R','L')
    d.edge('check','complete');d.edge('complete','fix','L','R',label=(880,412,'Belum'))
    d.edge('fix','draft','T','B',label=(731,341,'Perbaiki'))
    d.edge('complete','submit',label=(1024,543,'Ya'))
    d.edge('submit','review','L','R');d.edge('review','lock','L','R',label=(588,637,'Ditinjau'))
    d.edge('review','fix','T','B',label=(731,537,'Perlu perbaikan'))
    d.edge('lock','export','L','R')
    d.text(44,409,'BELUM ADA PENINJAU?',10.5,GOLD,True)
    d.text(44,432,'Laporan tetap menunggu.',11.5,MUTED)
    d.text(44,454,'Pembuat tidak meninjau laporannya sendiri.',10.5,MUTED)
    d.note(726,'Materi divisi saat ini merupakan modul baca, belum LMS dengan ujian atau sertifikat.','Peninjauan laporan tidak mengesahkan diagnosis, meloloskan QC, atau memverifikasi pembayaran. Ekspor dan unduhan tercatat di audit.')
    d.finish()
    pdf.save()
    files=sorted(p.name for p in OUT.glob('*.svg'))
    (OUT/'manifest.json').write_text(json.dumps({'version':'0.4','pages':6,'format':'A3 landscape','pdf':'NAM_Flowchart_Lengkap_Demo_0.4.pdf','editable_svg':files,'data':'Fiktif; tanpa pembacaan database'},ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Created 6 diagram pages in {OUT}')


if __name__=='__main__':build()
