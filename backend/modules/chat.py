"""AI-first local support, explicit human handoff and case-scoped conversation access.

The initial assistant is a deterministic mock. No message leaves this machine.
Only the assigned Customer Service agent can read or reply to a human conversation.
"""
import secrets
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ChatConversation, ChatMessage, LabOrder, User
from backend.modules.audit import audit
from backend.security import current_user, require_order, role_only
from backend.utils import utcnow

router = APIRouter(prefix='/api/chat', tags=['Bantuan lokal'])
WELCOME = ('Halo, saya asisten layanan Naraya (simulasi lokal). Saya dapat membantu tentang '
           'alur order, jadwal, dan pembayaran. Pilih "Hubungi petugas" kapan saja untuk '
           'meminta bantuan tim layanan. Gunakan data fiktif; jangan tulis data medis asli.')


def timestamp(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value.tzinfo is None else value.isoformat()


def conversation_view(chat):
    return {'id':chat.id, 'order_id':chat.order_id, 'status':chat.status,
            'assigned':chat.assigned_agent_id is not None, 'assistant_mode':'mock',
            'created_at':timestamp(chat.created_at), 'updated_at':timestamp(chat.updated_at)}


def message_view(message):
    return {'id':message.id,'sender':message.sender,'body':message.body,'at':timestamp(message.created_at)}


def require_conversation(db, user, ident, *, owner_only=False):
    chat = db.get(ChatConversation,ident)
    if not chat:
        raise HTTPException(404,'Percakapan tidak ditemukan')
    owner = user.role == 'patient' and user.org_id == 1 and chat.owner_id == user.id and chat.org_id == user.org_id
    agent = (not owner_only and user.role == 'customer_service' and user.org_id == 1
             and chat.service_org_id == 1 and chat.assigned_agent_id == user.id
             and chat.status in ('human','closed'))
    if not owner and not agent:
        raise HTTPException(404,'Percakapan tidak ditemukan')
    if owner and chat.order_id is not None:
        require_order(db,user,chat.order_id)
    return chat


def add_message(db,chat,sender,body,key,author=None):
    message = ChatMessage(conversation_id=chat.id,sender=sender,body=body,request_key=key,author_id=author)
    db.add(message)
    db.flush()
    return message


def serialized_chat(db,chat):
    # A write lock serializes replies, handoff and close against this conversation.
    db.execute(update(ChatConversation).where(ChatConversation.id==chat.id).values(updated_at=utcnow())
               .execution_options(synchronize_session=False))
    db.refresh(chat)


def local_reply(text,order=None,patient=False):
    """Mock provider boundary: curated service facts, never clinical decision making."""
    text = text.casefold()
    if any(word in text for word in ('diagnosis','obat','sakit','nyeri','medis','resep')):
        return 'Pertanyaan klinis perlu ditangani dokter gigi yang berwenang. Saya hanya membantu urusan layanan. Petugas dapat membantu koordinasi kunjungan, tanpa menggantikan penilaian dokter.'
    if any(word in text for word in ('bayar','tagihan','qris','transfer','uang','kartu')):
        if patient:
            return 'Pembayaran perlu diperiksa oleh petugas terlebih dahulu. Bukti gambar belum menyatakan pembayaran berhasil. Pada demo ini, pemeriksaan masih simulasi manual. Pilih Hubungi petugas jika perlu bantuan.'
        return 'Penerimaan dana dicatat oleh Front Office, lalu diverifikasi oleh FAT secara terpisah. Bukti gambar belum menyatakan pembayaran berhasil. Pada demo ini, verifikasi FAT masih simulasi manual.'
    if any(word in text for word in ('jadwal','dokter','kunjungan','janji')):
        if patient:
            return 'Buka Jadwal kunjungan untuk melihat janji Anda. Jika ada usulan dokter pengganti, Anda dapat membaca namanya lalu memilih Setujui atau Tolak. Membaca pemberitahuan tidak dianggap sebagai persetujuan.'
        return 'Jadwal kunjungan tersedia di menu Pasien & jadwal, atau Jadwal saya pada portal pasien. Pergantian dokter memerlukan persetujuan pasien sebelum ditetapkan. Petugas dapat membantu bila ada kendala.'
    if any(word in text for word in ('terlambat','tanggal','estimasi','eta','komitmen')):
        due = str(order.promised_due) if order and order.promised_due else 'belum ditetapkan'
        return f'Komitmen order terkait: {due}. Estimasi divalidasi Lab. Usulan tanggal baru tidak menggantikan komitmen aktif sebelum disetujui pihak berwenang. Lihat detail order untuk meninjau usulan.' if order else 'Estimasi pekerjaan divalidasi Lab. Usulan tanggal baru perlu ditinjau pihak berwenang dan tidak otomatis menggantikan komitmen sebelumnya. Pilih order saat memulai percakapan untuk konteks layanan.'
    if any(word in text for word in ('order','status','proses','lab','qc')):
        labels = {'submitted':'menunggu penugasan','assigned':'menunggu penerimaan Lab','accepted':'diterima Lab','design':'tahap desain','production':'dalam produksi','finishing':'tahap finishing','qc_pending':'menunggu QC','ready':'siap diserahkan','rework':'memerlukan perbaikan','rejected':'ditolak Lab','completed':'selesai'}
        menu = 'Layanan saya' if patient else 'Order laboratorium'
        return f'Order {order.code} saat ini {labels.get(order.status,"dalam peninjauan")}. Detail dan riwayat layanan tersedia di {menu}.' if order else 'Pengerjaan dimulai setelah permintaan diterima, dilanjutkan dengan produksi dan pemeriksaan hasil. Pilih layanan ketika memulai percakapan untuk menanyakan statusnya.'
    return 'Saya dapat membantu menjelaskan status order, perubahan estimasi, jadwal kunjungan, atau verifikasi pembayaran. Untuk kebutuhan di luar informasi ini, pilih Hubungi petugas. Jawaban ini berasal dari simulasi lokal, belum dari model AI eksternal.'


class StartIn(BaseModel):
    request_id: str = Field(min_length=8,max_length=64,pattern=r'^[a-zA-Z0-9_-]+$')
    order_id: int | None = None


class MessageIn(BaseModel):
    body: str = Field(min_length=1,max_length=2000)
    request_id: str = Field(min_length=8,max_length=64,pattern=r'^[a-zA-Z0-9_-]+$')

    @field_validator('body')
    @classmethod
    def meaningful_text(cls,value):
        if not value.strip(): raise ValueError('Pesan tidak boleh kosong')
        return value.strip()


@router.get('/conversations')
def list_conversations(user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user, 'patient')
    if user.org_id != 1: raise HTTPException(403, 'Akses organisasi tidak diizinkan')
    rows = db.scalars(select(ChatConversation).where(ChatConversation.owner_id==user.id,
                      ChatConversation.org_id==user.org_id).order_by(ChatConversation.updated_at.desc()).limit(30)).all()
    visible = []
    for row in rows:
        try: require_conversation(db,user,row.id,owner_only=True)
        except HTTPException: continue
        visible.append(conversation_view(row))
    return visible


@router.post('/conversations')
def start_conversation(data:StartIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user, 'patient')
    if user.org_id != 1: raise HTTPException(403, 'Akses organisasi tidak diizinkan')
    if user.org_id is None: raise HTTPException(403,'Organisasi pengguna belum tersedia')
    if data.order_id is not None: require_order(db,user,data.order_id)
    existing = db.scalar(select(ChatConversation).where(ChatConversation.owner_id==user.id,ChatConversation.request_id==data.request_id))
    if existing:
        require_conversation(db,user,existing.id,owner_only=True)
        if existing.order_id != data.order_id: raise HTTPException(409,'Referensi permintaan sudah digunakan untuk konteks berbeda')
        return conversation_view(existing)
    chat = ChatConversation(id=secrets.token_hex(16),owner_id=user.id,org_id=user.org_id,service_org_id=1,
                            order_id=data.order_id,status='assistant',request_id=data.request_id)
    try:
        db.add(chat); db.flush()
        add_message(db,chat,'assistant',WELCOME,'welcome')
        audit(db,user,'chat.started','chat',0,conversation=chat.id,order_id=chat.order_id)
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(ChatConversation).where(ChatConversation.owner_id==user.id,ChatConversation.request_id==data.request_id))
        if existing and existing.order_id==data.order_id:
            require_conversation(db,user,existing.id,owner_only=True)
            return conversation_view(existing)
        raise HTTPException(409,'Percakapan tidak dapat dibuat. Muat ulang dan coba lagi')
    return conversation_view(chat)


@router.get('/queue')
def support_queue(user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user,'customer_service')
    rows = db.scalars(select(ChatConversation).where(ChatConversation.service_org_id==user.org_id,
                      ChatConversation.status.in_(('waiting','human'))).order_by(ChatConversation.updated_at)).all()
    # Queue exposes routing metadata only. Transcript access starts after an atomic claim.
    return [conversation_view(row) for row in rows if db.get(User,row.owner_id).role=='patient' and row.org_id==1 and row.owner_id!=user.id and
            (row.status=='waiting' or row.assigned_agent_id==user.id)]


@router.get('/conversations/{ident}')
def read_conversation(ident:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    chat = require_conversation(db,user,ident)
    messages = db.scalars(select(ChatMessage).where(ChatMessage.conversation_id==chat.id)
                         .order_by(ChatMessage.id.desc()).limit(200)).all()
    return {**conversation_view(chat),'messages':[message_view(message) for message in reversed(messages)]}


@router.post('/conversations/{ident}/messages')
def send_message(ident:str,data:MessageIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    chat = require_conversation(db,user,ident)
    serialized_chat(db,chat)
    key = f'{user.id}:{data.request_id}'
    existing = db.scalar(select(ChatMessage).where(ChatMessage.conversation_id==chat.id,ChatMessage.request_key==key))
    if existing:
        if existing.body != data.body: raise HTTPException(409,'Referensi pesan sudah dipakai untuk isi berbeda')
        db.rollback()
        return {'message':message_view(existing),'duplicate':True}
    if chat.status=='closed': raise HTTPException(409,'Percakapan sudah ditutup. Mulai percakapan baru')
    is_owner = chat.owner_id==user.id
    if not is_owner and chat.status!='human': raise HTTPException(409,'Percakapan belum ditangani petugas')
    message = add_message(db,chat,'user' if is_owner else 'agent',data.body,key,user.id)
    if is_owner and chat.status=='assistant':
        order = require_order(db,user,chat.order_id) if chat.order_id else None
        add_message(db,chat,'assistant',local_reply(data.body,order,patient=user.role=='patient'),'assistant:'+data.request_id)
    audit(db,user,'chat.message_recorded','chat',0,conversation=chat.id,message_id=message.id,sender=message.sender)
    db.commit()
    return {'message':message_view(message),'duplicate':False}


@router.post('/conversations/{ident}/handoff')
def handoff(ident:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    chat = require_conversation(db,user,ident,owner_only=True)
    serialized_chat(db,chat)
    if chat.status=='closed': raise HTTPException(409,'Percakapan sudah ditutup')
    if chat.status in ('waiting','human'):
        db.rollback()
        return conversation_view(chat)
    chat.status='waiting'
    add_message(db,chat,'system','Permintaan Anda masuk antrean bantuan. Petugas belum bergabung. Anda dapat menambahkan pesan sambil menunggu.','handoff')
    audit(db,user,'chat.handoff_requested','chat',0,conversation=chat.id,order_id=chat.order_id)
    db.commit()
    return conversation_view(chat)


@router.post('/conversations/{ident}/claim')
def claim(ident:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    role_only(user,'customer_service')
    chat = db.get(ChatConversation,ident)
    if not chat or chat.service_org_id!=user.org_id or chat.owner_id==user.id or chat.org_id!=1 or db.get(User,chat.owner_id).role!='patient':
        raise HTTPException(404,'Percakapan tidak ditemukan')
    if chat.status=='human' and chat.assigned_agent_id==user.id:
        return conversation_view(chat)
    result = db.execute(update(ChatConversation).where(ChatConversation.id==ident,
                        ChatConversation.status=='waiting',ChatConversation.assigned_agent_id.is_(None))
                        .values(status='human',assigned_agent_id=user.id,updated_at=utcnow())
                        .execution_options(synchronize_session=False))
    if result.rowcount!=1: raise HTTPException(409,'Percakapan telah ditangani atau belum meminta petugas')
    db.refresh(chat)
    add_message(db,chat,'system','Petugas layanan telah bergabung. Balasan berikutnya ditulis oleh petugas.','claimed')
    audit(db,user,'chat.claimed','chat',0,conversation=chat.id)
    db.commit()
    return conversation_view(chat)


@router.post('/conversations/{ident}/close')
def close_conversation(ident:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    chat = require_conversation(db,user,ident)
    serialized_chat(db,chat)
    if chat.status=='closed':
        db.rollback()
        return conversation_view(chat)
    chat.status='closed'
    add_message(db,chat,'system','Percakapan ditutup. Riwayat tetap tersimpan. Mulai percakapan baru bila membutuhkan bantuan lagi.','closed')
    audit(db,user,'chat.closed','chat',0,conversation=chat.id)
    db.commit()
    return conversation_view(chat)
