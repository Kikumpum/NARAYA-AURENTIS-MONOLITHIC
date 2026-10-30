'use strict';

function closeDialogs() {document.querySelectorAll('dialog').forEach(dialog => {dialog.close(); dialog.remove();});}
function mountDialog(content, drawer = false) {
  closeDialogs();
  const opener = document.activeElement;
  const dialog = document.createElement('dialog');
  dialog.className = drawer ? 'order-dialog' : 'form-dialog';
  dialog.setAttribute('aria-labelledby','dialog-title');
  dialog.innerHTML = content;
  dialog.addEventListener('close',() => {dialog.remove(); if (opener?.isConnected) opener.focus();});
  dialog.addEventListener('click',event => {if (event.target === dialog) {const bounds = dialog.getBoundingClientRect(); if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();}});
  document.body.append(dialog); dialog.showModal();
  dialog.querySelectorAll('[data-close]').forEach(button => button.onclick = () => dialog.close());
  return dialog;
}
function dialogHeading(title,eyebrow = 'PENCATATAN') {
  return `<div class="dialog-heading"><div><span class="eyebrow">${esc(eyebrow)}</span><h2 id="dialog-title">${esc(title)}</h2></div><button type="button" class="icon-button" data-close aria-label="Tutup dialog">${icon('close')}</button></div>`;
}
function showModal(title,fields,submit,description = 'Gunakan data fiktif. Perubahan akan tercatat pada jejak audit.') {
  const fieldHtml = fields.map(field => {
    const id = `field-${field.key}`, required = field.required !== false ? 'required' : '';
    const attrs = `${required} ${field.min !== undefined ? `min="${esc(field.min)}"` : ''} ${field.max !== undefined ? `max="${esc(field.max)}"` : ''} ${field.minlength ? `minlength="${field.minlength}"` : ''} ${field.maxlength ? `maxlength="${field.maxlength}"` : ''}`;
    let control;
    if (field.type === 'select') control = `<select id="${id}" name="${esc(field.key)}" ${required}>${field.options.map(option => `<option value="${esc(option.value)}">${esc(option.name)}</option>`).join('')}</select>`;
    else if (field.type === 'textarea') control = `<textarea id="${id}" name="${esc(field.key)}" ${attrs} placeholder="${esc(field.placeholder || '')}">${esc(field.value || '')}</textarea>`;
    else if (field.type === 'checkbox') return `<label class="check-row span2" for="${id}"><input id="${id}" name="${esc(field.key)}" type="checkbox"><span>${esc(field.label)}</span></label>`;
    else control = `<input id="${id}" name="${esc(field.key)}" type="${esc(field.type || 'text')}" ${attrs} value="${esc(field.value ?? '')}" placeholder="${esc(field.placeholder || '')}">`;
    return `<div class="form-row ${field.wide ? 'span2' : ''}"><label for="${id}">${esc(field.label)}${field.required === false ? ' <span class="optional">Opsional</span>' : ''}</label>${control}${field.hint ? `<small>${esc(field.hint)}</small>` : ''}</div>`;
  }).join('');
  const dialog = mountDialog(`${dialogHeading(title)}<p class="dialog-description">${esc(description)}</p><form class="modal-form"><div class="form-grid">${fieldHtml}</div><div class="form-error" role="alert" id="form-error"></div><div class="modal-footer"><button type="button" class="secondary" data-close>Batal</button><button class="primary" type="submit">Simpan</button></div></form>`);
  let saving = false;
  dialog.addEventListener('cancel',event => {if (saving) event.preventDefault();});
  dialog.querySelector('form').onsubmit = async event => {
    event.preventDefault(); if (saving) return;
    saving = true;
    const data = Object.fromEntries(new FormData(event.target));
    fields.filter(field => field.type === 'checkbox').forEach(field => data[field.key] = event.target.elements[field.key].checked);
    const buttons = dialog.querySelectorAll('button'); buttons.forEach(button => button.disabled = true);
    const submitButton = dialog.querySelector('[type="submit"]'); submitButton.textContent = 'Menyimpan…';
    dialog.querySelector('#form-error').textContent = '';
    try {await submit(data); dialog.close(); await refresh(); pop('Perubahan berhasil disimpan.');}
    catch (error) {if (dialog.isConnected) {dialog.querySelector('#form-error').textContent = error.message; buttons.forEach(button => button.disabled = false); submitButton.textContent = 'Simpan';}}
    finally {saving = false;}
  };
}
async function openOrder(id) {
  const dialog = mountDialog(`${dialogHeading('Memuat detail order','LABORATORIUM')}<div class="empty">Sedang mengambil data…</div>`,true);
  try {
    const data = await api(`/orders/${id}`);
    if (!dialog.isConnected || !state.user) return;
    const order = data.order;
    const milestones = ['submitted','accepted','production','qc_pending','ready'];
    const labels = ['Diajukan','Diterima','Produksi','QC','Siap'];
    const position = {submitted:0,assigned:0,rejected:0,accepted:1,design:2,production:2,finishing:2,rework:2,qc_pending:3,ready:4,completed:4}[order.status] ?? 0;
    dialog.innerHTML = `${dialogHeading(order.code,'DETAIL ORDER')}<div class="order-detail-body"><div class="order-detail-title"><div><h3>${esc(order.title)}</h3><p>${esc(order.customer)}, ${order.source === 'internal' ? 'Klinik internal' : 'Klinik mitra'}</p></div>${badge(order.status)}</div>
      <ol class="milestones">${milestones.map((_,index) => `<li class="${index <= position ? 'reached' : ''}"><span>${index < position ? icon('check') : index+1}</span><small>${labels[index]}</small></li>`).join('')}</ol>
      ${order.status === 'rejected' || order.status === 'rework' ? `<div class="detail-alert">${icon('alert')}<span>${order.status === 'rejected' ? 'Order ditolak. Tindak lanjut penugasan diperlukan.' : 'Hasil memerlukan perbaikan dan pemeriksaan QC kembali.'}</span></div>` : ''}
      <section class="detail-section"><h3>Komitmen & estimasi</h3><dl class="detail-grid"><div><dt>Komitmen aktif</dt><dd>${dateText(order.promised_due)}</dd></div><div><dt>Estimasi tervalidasi</dt><dd>${dateText(order.estimated_due)}</dd></div>${data.initial_due && data.initial_due !== order.promised_due ? `<div><dt>Komitmen semula</dt><dd>${dateText(data.initial_due)}</dd></div>` : ''}<div><dt>Jenis pekerjaan</dt><dd>${esc(categoryNames[order.category] || 'Ringkasan layanan')}</dd></div><div><dt>Sumber order</dt><dd>${order.source === 'internal' ? 'Klinik internal' : 'Klinik mitra'}</dd></div></dl></section>
      ${order.proposed_due ? `<section class="change-request"><span class="eyebrow">USULAN PERUBAHAN</span><h3>${dateText(order.promised_due)} ${icon('arrow')} ${dateText(order.proposed_due)}</h3>${order.delay_reason ? `<p>${esc(order.delay_reason)}</p>` : ''}<p>Tanggal baru belum menjadi komitmen sampai disetujui penerima yang berwenang.</p>${badge(order.delay_response)}</section>` : ''}
      ${order.patient || order.patient_ref ? `<section class="detail-section"><h3>Referensi pasien</h3><p>${esc(order.patient || order.patient_ref)}</p>${order.patient && order.patient_ref ? `<small class="muted">${esc(order.patient_ref)}</small>` : ''}</section>` : ''}
      ${order.instruction ? `<section class="detail-section"><h3>Instruksi surat kerja</h3><p class="instruction-text">${esc(order.instruction)}</p><small class="muted">Instruksi klinis merupakan kewenangan dokter pengirim.</small></section>` : ''}
      <section class="detail-section"><h3>Riwayat layanan</h3>${data.activity.length ? `<ol class="timeline">${data.activity.map(event => `<li><span class="timeline-dot"></span><div><strong>${esc(eventNames[event.event] || event.event)}</strong><time>${dateText(event.at,true)} WIB</time>${event.old_due && event.new_due ? `<p>${dateText(event.old_due)} → ${dateText(event.new_due)}</p>` : ''}</div></li>`).join('')}</ol>` : '<p class="muted small">Order bawaan demo belum memiliki riwayat tindakan. Aktivitas berikutnya akan tercatat di sini.</p>'}</section></div><div class="drawer-footer">${actionButtons(order) || '<span class="muted small">Tidak ada tindakan yang tersedia untuk akun ini pada tahap sekarang.</span>'}</div>`;
    dialog.querySelector('[data-close]').onclick = () => dialog.close();
    bindActions(dialog);
  } catch (error) {if (dialog.isConnected) {dialog.close(); pop(error.message,true);}}
}
const options = rows => rows.map(row => ({value:row.id,name:row.name}));
const selectField = (key,label,items) => ({key,label,type:'select',options:items});
const choice = (yes,no) => [{value:'yes',name:yes},{value:'no',name:no}];
function noCandidates(message) {pop(message,true);}
async function handle(action,id) {
  try {await performAction(action,id);} catch (error) {pop(error.message,true);}
}
async function performAction(action,id) {
  const order = state.orders.find(row => row.id === id), today = jakartaDate();
  if(['visitStart','visitEstimate','visitFinish','visitAbsent'].includes(action))return visitTimingDialog(action,id);
  if(action==='whatsappStatus')return showWhatsappSetup();
  if (action === 'refresh') {await refresh(); if (!state.loadErrors.length) pop('Data berhasil diperbarui.'); return;}
  if (action === 'partnerPatient') return showModal('Tambah referensi mitra',[{key:'reference',label:'Kode kasus anonim',minlength:3,maxlength:120}],data => api('/partner/patients','POST',data),'Gunakan kode kasus tanpa nama lengkap, kontak, atau data medis asli.');
  if (action === 'patient') return showModal('Registrasi pasien simulasi',[
    {key:'name',label:'Nama simulasi',minlength:2,maxlength:120},{key:'phone',label:'Kontak simulasi',minlength:8,maxlength:40},selectField('channel','Kanal layanan',Object.entries(channelNames).filter(([key]) => key !== 'partner_portal').map(([value,name]) => ({value,name}))),selectField('level','Detail pemberitahuan',Object.entries(detailNames).map(([value,name]) => ({value,name}))),{key:'verified',label:'Verifikasi kontak telah dilakukan — simulasi',type:'checkbox'},{key:'consent',label:'Izin komunikasi layanan telah dicatat — simulasi',type:'checkbox'},
  ],data => api('/patients','POST',data),'Data fiktif saja. Kotak verifikasi dan izin adalah simulasi; tidak mengirim OTP nyata.');
  if (action === 'appointment') {
    if (!state.patients.length) return noCandidates('Registrasikan pasien simulasi terlebih dahulu.');
    return showModal('Jadwalkan kunjungan',[selectField('patient_id','Pasien',options(state.patients)),selectField('dentist_id','Dokter klinik',options(state.roster.filter(row => row.role === 'dentist'))),{key:'scheduled_at',label:'Tanggal & waktu (WIB)',type:'datetime-local',wide:true}],data => api('/appointments','POST',{...data,patient_id:Number(data.patient_id),dentist_id:Number(data.dentist_id),scheduled_at:data.scheduled_at+':00+07:00'}));
  }
  if (action === 'replacement') return showModal('Tawarkan dokter pengganti',[selectField('dentist_id','Dokter pengganti',options(state.roster.filter(row => row.role === 'dentist')))],data => api(`/appointments/${id}/replacement`,'POST',{dentist_id:Number(data.dentist_id)}),'Penawaran belum mengubah dokter aktif. Pasien perlu menyetujui terlebih dahulu.');
  if (action === 'apptRespond') return showModal('Tinjau dokter pengganti',[selectField('approved','Keputusan Anda',choice('Terima dokter pengganti','Tolak pergantian'))],data => api(`/appointments/${id}/respond`,'POST',{approved:data.approved === 'yes'}));
  if (action === 'createOrder') {
    if (!state.patients.length) return noCandidates(state.user.role === 'partner' ? 'Tambahkan referensi kasus mitra terlebih dahulu dari halaman Order laboratorium.' : 'Belum ada pasien dalam lingkup layanan Anda.');
    return showModal('Surat kerja laboratorium',[
      selectField('patient_id',state.user.role === 'partner' ? 'Referensi kasus' : 'Pasien',options(state.patients)),{key:'title',label:'Nama pekerjaan',minlength:3,maxlength:120},selectField('category','Jenis pekerjaan',Object.entries(categoryNames).map(([value,name]) => ({value,name}))),{key:'promised_due',label:'Tanggal komitmen awal',type:'date',required:false},{key:'instruction',label:'Instruksi dokter / klinik',type:'textarea',wide:true,minlength:10,maxlength:1500,placeholder:'Spesifikasi teknis fiktif, minimal 10 karakter.'},
    ],data => api('/orders','POST',{...data,patient_id:Number(data.patient_id),promised_due:data.promised_due || null}));
  }
  if (action === 'assign') {
    const leads = state.roster.filter(row => row.role === 'lab_supervisor');
    if (!leads.length) return noCandidates('Tidak ada supervisor yang terjadwal hari ini.');
    return showModal('Tugaskan penanggung jawab Lab',[selectField('lead_id','Supervisor terjadwal',leads.map(row => ({value:row.id,name:`${row.name}, ${row.active_orders}/${row.capacity} order` })))],data => api(`/orders/${id}/assign-lead`,'POST',{lead_id:Number(data.lead_id)}),'Supervisor yang dipilih tetap perlu menerima order dengan akunnya sendiri.');
  }
  if (action === 'confirm') return showModal('Penerimaan order Lab',[selectField('accept','Keputusan Lab',choice('Terima order','Tolak order')),{key:'reason',label:'Alasan penolakan',required:false,maxlength:400,wide:true}],data => api(`/orders/${id}/confirm`,'POST',{accept:data.accept === 'yes',reason:data.reason || null}));
  if (action === 'plan') {
    const suggestion = await api(`/orders/${id}/eta-suggestion`);
    const technicians = state.roster.filter(row => row.role === 'technician');
    if (!technicians.length) return noCandidates('Tidak ada teknisi terjadwal yang dapat dipilih.');
    return showModal('Rencanakan produksi',[selectField('technician_id','Teknisi',options(technicians)),{key:'due',label:'Estimasi selesai',type:'date',min:today,value:suggestion.recommended_due},{key:'override_reason',label:'Alasan bila lebih cepat dari rekomendasi',required:false,wide:true,maxlength:400}],data => api(`/orders/${id}/plan`,'POST',{technician_id:Number(data.technician_id),due:data.due,override_reason:data.override_reason || null}),`${suggestion.note} Rekomendasi: ${dateText(suggestion.recommended_due)}.`);
  }
  if (action === 'progress') {
    const next = {production:['design','finishing','qc_pending'],design:['production','finishing','qc_pending'],finishing:['qc_pending'],rework:['design','production','finishing','qc_pending']}[order.status] || [];
    return showModal('Perbarui tahap produksi',[selectField('status','Tahap selanjutnya',next.map(value => ({value,name:statusNames[value]})))],data => api(`/orders/${id}/progress`,'POST',data));
  }
  if (action === 'qc') return showModal('Pemeriksaan Quality Control',[selectField('passed','Hasil pemeriksaan',choice('Lulus QC teknis','Perlu perbaikan / rework')),{key:'reason',label:'Temuan bila perlu perbaikan',required:false,wide:true,maxlength:500}],data => api(`/orders/${id}/qc`,'POST',{passed:data.passed === 'yes',reason:data.reason || null}));
  if (action === 'delay') return showModal('Usulkan perubahan tanggal',[{key:'new_due',label:'Tanggal baru yang diusulkan',type:'date',min:today,value:order.promised_due || today,wide:true},{key:'reason',label:'Alasan dan dampak layanan',type:'textarea',wide:true,minlength:8,maxlength:400,placeholder:'Alasan umum tanpa rincian klinis sensitif.'}],data => api(`/orders/${id}/delay`,'POST',data),'Komitmen aktif tidak berubah sampai penerima yang berwenang memberikan persetujuan.');
  if (action === 'delayDecision') return showModal('Tinjau perubahan komitmen',[selectField('approved','Keputusan Anda',choice('Setujui tanggal baru','Tolak usulan tanggal'))],data => api(`/orders/${id}/delay/respond`,'POST',{approved:data.approved === 'yes',expected_due:order.proposed_due}),`Komitmen: ${dateText(order.promised_due)}. Usulan: ${dateText(order.proposed_due)}. ${order.delay_reason || ''}`);
  if (action === 'invoice') return showModal(order.source === 'internal' ? 'Catat biaya internal' : 'Buat tagihan mitra',[{key:'amount_idr',label:'Nilai dalam rupiah',type:'number',min:1,max:1000000000,wide:true}],data => api('/invoices','POST',{order_id:id,amount_idr:Number(data.amount_idr)}));
  if (action === 'pay') {
    const invoice = state.invoices.find(row => row.id === id), remaining = invoice.amount_idr-invoice.paid_idr-invoice.pending_idr;
    return showModal('Catat penerimaan dana',[selectField('method','Metode',Object.entries(methodNames).map(([value,name]) => ({value,name}))),{key:'amount_idr',label:'Nilai dalam rupiah',type:'number',min:1,max:remaining,value:remaining},{key:'reference',label:'Referensi pembayaran',required:false,wide:true,maxlength:120}],data => api(`/invoices/${id}/payments`,'POST',{method:data.method,amount_idr:Number(data.amount_idr),reference:data.reference || null}),'Penerimaan ini belum melunasi tagihan. FAT harus melakukan verifikasi secara terpisah.');
  }
  if (action === 'verify') {
    const invoice = state.invoices.find(row => row.id === id);
    return showModal('Verifikasi penerimaan — demo',[selectField('payment_id','Penerimaan yang diperiksa',invoice.payments.filter(row => row.status === 'pending_verification').map(row => ({value:row.id,name:`#${row.id}, ${methodNames[row.method]}, ${fmt(row.amount_idr)}`})))],data => api(`/payments/${data.payment_id}/verify`,'POST'),'Simulasi manual FAT. Belum ada pemeriksaan settlement bank, QRIS, atau kartu secara nyata.');
  }
  if (action === 'invoiceDetail') {
    const invoice = state.invoices.find(row => row.id === id);
    mountDialog(`${dialogHeading('Rincian tagihan','KEUANGAN')}<p class="dialog-description">INV-${String(id).padStart(4,'0')}, ${esc(invoice.order_code)}</p><dl class="detail-grid"><div><dt>Total</dt><dd>${fmt(invoice.amount_idr)}</dd></div><div><dt>Sisa tagihan</dt><dd>${fmt(invoice.outstanding_idr)}</dd></div></dl><h3 class="section-title">Riwayat penerimaan</h3>${invoice.payments.length ? `<div class="payment-list">${invoice.payments.map(payment => `<div><span><strong>${esc(methodNames[payment.method])}</strong><small>${fmt(payment.amount_idr)}</small></span>${badge(payment.status)}</div>`).join('')}</div>` : '<p class="muted small">Belum ada penerimaan dana yang dicatat.</p>'}<div class="modal-footer"><button class="secondary" data-close>Tutup</button></div>`);
    return;
  }
  if (action === 'newReport') return startSopReport();
}

function visitTimingDialog(action,id){
  const a=state.appts.find(x=>x.id===id);if(!a)return;
  const verb={visitStart:'start',visitEstimate:'estimate',visitFinish:'finish',visitAbsent:'not_attended'}[action];
  const titles={start:'Mulai kunjungan',estimate:'Perbarui perkiraan selesai',finish:'Catat kunjungan selesai',not_attended:'Catat pasien tidak hadir'};
  const fields=[...(['start','estimate'].includes(verb)?[{key:'minutes',label:verb==='start'?'Perkiraan durasi (menit)':'Perkiraan menit tersisa',type:'number',min:5,max:180,value:30}]:[]),{key:'reason',label:'Catatan pembaruan',minlength:5,maxlength:300,wide:true,value:verb==='finish'?'Kunjungan selesai ditangani.':verb==='start'?'Kunjungan dimulai oleh dokter.':''}];
  let pending=null;
  return showModal(titles[verb],fields,data=>{
    const body={action:verb,minutes:data.minutes?Number(data.minutes):null,reason:data.reason,expected_revision:a.timing?.revision||0};
    const signature=JSON.stringify(body);if(!pending||pending.signature!==signature)pending={signature,key:requestKey()};
    return api(`/appointments/${id}/timing`,'POST',{...body,request_key:pending.key});
  },'Perubahan memperbarui perkiraan pasien dan dicatat audit. Jadwal awal tidak diganti. Jangan menulis diagnosis atau data medis dalam catatan waktu.');
}
async function showWhatsappSetup(){
  const [setup,rows]=await Promise.all([api('/whatsapp/status'),api('/whatsapp/outbox')]);
  const dialog=mountDialog(`${dialogHeading('Persiapan WhatsApp','NOTIFIKASI KUNJUNGAN')}<div class="order-detail-body"><p>${esc(setup.message)}</p><h3>Yang perlu disiapkan</h3><ul>${setup.required.map(x=>`<li>${esc(x)}</li>`).join('')}</ul><h3>Pesan menunggu aktivasi</h3>${rows.length?rows.map(r=>`<article class="visit-queue-note"><strong>Kunjungan #${r.appointment_id}</strong><p>${esc(r.message)}</p><small>Belum dikirim · ${dateText(r.created_at,true)} WIB</small></article>`).join(''):'<p>Belum ada pesan untuk kontak WhatsApp yang telah diverifikasi dan memiliki izin layanan.</p>'}</div><div class="modal-footer"><button class="secondary" data-close>Tutup</button></div>`);
  dialog.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>dialog.close());
}
