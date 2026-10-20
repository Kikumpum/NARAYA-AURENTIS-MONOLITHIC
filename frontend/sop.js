'use strict';

const reportBadge = status => badge(status === 'submitted' ? 'submitted_report' : status);
const resultLabels = {todo:'Belum diperiksa',ok:'Sesuai',issue:'Ada temuan',na:'Tidak relevan'};
const requestKey = () => crypto.randomUUID();
const evidenceSize = bytes => bytes < 1024 ? `${bytes} B` : bytes < 1048576 ? `${(bytes/1024).toFixed(1)} KB` : `${(bytes/1048576).toFixed(1)} MB`;

function sopsPage() {
  return pageHeading('PEDOMAN KERJA, DRAF 1.0','SOP & checklist','Pilih prosedur, periksa setiap langkah, lalu simpan hasil dan buktinya.',`<a class="secondary" href="/api/sops/manual" download>Panduan seluruh SOP ${icon('reports')}</a>`)+
    `<div class="context-note">${icon('shield')}<p>Draf untuk latihan lokal. SOP klinis, kewenangan, dan prosedur fasilitas harus disahkan penanggung jawab sebelum dipakai secara nyata.</p></div><section class="panel"><div class="order-toolbar"><label class="search-field">${icon('search')}<input id="sop-search" value="${esc(state.sopSearch)}" placeholder="Cari divisi atau prosedur…" aria-label="Cari SOP"></label><label class="check-row"><input type="checkbox" id="sop-mine" ${state.sopMine ? 'checked' : ''}> SOP yang dapat saya kerjakan</label></div><div id="sop-catalog-results">${sopCatalogCards()}</div></section>`;
}
function sopCatalogCards() {
  const q = state.sopSearch.toLocaleLowerCase('id-ID');
  const items = state.sopCatalog.items.filter(s => (!state.sopMine || s.can_start) && `${s.code} ${s.title} ${s.division}`.toLocaleLowerCase('id-ID').includes(q));
  return items.length ? `<div class="sop-catalog">${items.map(s => `<article class="sop-card"><div class="report-card-heading"><span class="division-tag">${esc(s.division)}</span><span>${esc(s.code)}</span></div><h2>${esc(s.title)}</h2><p>${esc(s.purpose)}</p><div class="sop-facts"><span>${s.items.length} pemeriksaan</span><span>${s.items.filter(i => i.evidence_required).length} bukti wajib</span></div><div class="btnrow"><button class="secondary mini" data-sop-detail="${esc(s.code)}">Baca prosedur</button>${s.can_start ? `<button class="primary mini" data-sop-start="${esc(s.code)}">Buat laporan ${icon('arrow')}</button>` : '<span class="muted small">Peran pelaksana berbeda</span>'}</div></article>`).join('')}</div>` : emptyState('Tidak ada prosedur yang cocok','Ubah pencarian atau tampilkan SOP seluruh divisi.');
}
function sopReportsPage() {
  const rows = state.sopReports;
  return pageHeading('HASIL PEMERIKSAAN','Laporan & bukti','Checklist, temuan, tindak lanjut, dan lampiran tersimpan dalam satu laporan.',`<button class="primary" data-action="newReport">${icon('plus')} Buat laporan SOP</button>`)+
    `<div class="report-stats">${[['Draf',rows.filter(r => r.status === 'draft').length],['Diajukan',rows.filter(r => r.status === 'submitted').length],['Perlu perbaikan',rows.filter(r => r.status === 'returned').length],['Ditinjau',rows.filter(r => r.status === 'reviewed').length]].map(([label,n]) => `<div><strong>${n}</strong><span>${label}</span></div>`).join('')}</div><section class="panel"><div class="panel-header"><div><h2>Laporan SOP</h2><p>Isi dan bukti mengikuti kewenangan pemeriksa. Manajemen dapat menerima ringkasan status.</p></div><span class="count-label">${rows.length}</span></div>${rows.length ? `<div class="sop-report-list">${rows.map(r => `<article class="sop-report-row"><div><span class="eyebrow">SOP-${String(r.id).padStart(5,'0')}, ${esc(r.sop_code)}</span><h3>${esc(r.title)}</h3><p>${dateText(r.day)}, ${esc(r.division)}${r.author ? ', '+esc(r.author) : ''}</p>${r.can_read && r.summary ? `<p class="muted">${esc(r.summary.slice(0,180))}</p>` : ''}</div><div class="sop-report-tools">${reportBadge(r.status)}${r.can_read ? `<button class="secondary mini" data-sop-report="${r.id}">Buka laporan ${icon('chevron')}</button>` : '<span class="muted small">Ringkasan status saja</span>'}</div></article>`).join('')}</div>` : emptyState('Belum ada laporan SOP','Mulai dari prosedur yang sesuai pekerjaan Anda.',`<button class="secondary" data-nav="sops">Buka SOP & checklist</button>`)}</section>${state.reports.length ? `<section class="panel legacy-reports"><div class="panel-header"><div><h2>Catatan harian sebelumnya</h2><p>Laporan lama tetap tersimpan. Laporan baru memakai checklist dan lampiran.</p></div></div>${reportCards(state.reports)}</section>` : ''}`;
}
function organizationPage() {
  const data = state.organization;
  const branches = [...new Set(data.positions.map(p => p.division))];
  return pageHeading('NARAYA AURENTIS MONOLITHIC','Struktur organisasi','Susunan jabatan mengikuti bagan. Akun latihan dipetakan berdasarkan fungsi.',data.can_assign ? `<button class="secondary" id="position-map">Petakan akun ke jabatan</button>` : '')+
    `<div class="context-note">${icon('patients')}<p>Semua nama akun di bawah adalah akun simulasi. Jabatan tanpa akun ditampilkan “Belum diisi”; sistem tidak membuat login untuk posisi kosong.</p></div><section class="panel"><div class="panel-header"><div><h2>Jalur pimpinan</h2><p>Hubungan pelaporan tidak menambah izin membaca data atau menyetujui transaksi.</p></div><span class="pill yellow">Draf struktur</span></div><div class="org-leadership">${['commissioner','chief_executive','director','operations'].map(code => {const p = data.positions.find(x => x.code === code); return p ? `<div><span>${esc(p.name)}</span><strong>${p.accounts.length ? esc(p.accounts.map(a => a.name).join(', ')) : 'Belum diisi'}</strong></div>` : '';}).join(`<span class="org-connector">${icon('arrow')}</span>`)}</div></section><div class="organization-grid">${branches.map(division => `<section class="panel org-division"><div class="panel-header"><h2>${esc(division)}</h2></div>${data.positions.filter(p => p.division === division).map(p => {const parent = data.positions.find(x => x.code === p.parent_code);return `<article class="position-card"><h3>${esc(p.name)}</h3><p>Melapor ke ${esc(parent?.name || '—')}</p><div>${p.accounts.length ? p.accounts.map(a => `<span class="account-chip">${esc(a.name)} <small>, ${esc(roleNames[a.role] || a.role)}</small></span>`).join('') : '<span class="vacant-label">Belum diisi</span>'}</div><small>Peran: ${p.allowed_roles.map(r => esc(roleNames[r] || r)).join(', ')}</small></article>`;}).join('')}</section>`).join('')}</div><section class="panel org-notes"><div class="panel-header"><h2>Catatan pemetaan bagan</h2></div><ul>${data.notes.map(n => `<li>${esc(n)}</li>`).join('')}</ul></section>`;
}
function bindSopButtons(root = document) {
  root.querySelectorAll('[data-sop-detail]').forEach(b => b.onclick = () => showSop(b.dataset.sopDetail));
  root.querySelectorAll('[data-sop-start]').forEach(b => b.onclick = () => startSopReport(b.dataset.sopStart));
  root.querySelectorAll('[data-sop-report]').forEach(b => b.onclick = () => openSopReport(Number(b.dataset.sopReport)));
}
function bindSopControls() {
  bindSopButtons();
  const rerender = () => {$('#sop-catalog-results').innerHTML = sopCatalogCards();bindSopButtons($('#sop-catalog-results'));};
  if ($('#sop-search')) $('#sop-search').oninput = e => {state.sopSearch = e.target.value;rerender();};
  if ($('#sop-mine')) $('#sop-mine').onchange = e => {state.sopMine = e.target.checked;rerender();};
  if ($('#position-map')) $('#position-map').onclick = mapPosition;
}
function showSop(code) {
  const s = state.sopCatalog.items.find(x => x.code === code);if (!s) return;
  const dialog = mountDialog(`${dialogHeading(s.title,s.code+', '+s.version)}<p class="dialog-description">${esc(s.purpose)}</p><dl class="detail-grid"><div><dt>Pelaksana</dt><dd>${s.roles.map(r => esc(roleNames[r] || r)).join(', ')}</dd></div><div><dt>Frekuensi</dt><dd>${esc(s.frequency)}</dd></div><div><dt>Peninjau laporan</dt><dd>${s.reviewers.map(r => esc(roleNames[r] || r)).join(', ')}, orang berbeda</dd></div><div><dt>Konteks</dt><dd>${s.order_policy === 'required' ? 'Order dalam penugasan dan tahap yang sesuai' : 'Administratif, tanpa rincian medis'}</dd></div></dl><ol class="sop-step-list">${s.items.map(i => `<li><strong>${esc(i.key)}</strong><span>${esc(i.text)}</span>${i.evidence_required ? '<small>Lampiran bukti wajib</small>' : ''}${i.allow_na ? '<small>Boleh tidak relevan, disertai alasan</small>' : ''}</li>`).join('')}</ol><h3 class="section-title">Contoh lampiran</h3><ul class="sop-examples">${s.evidence_examples.map(t => `<li>${esc(t)}</li>`).join('')}</ul><p class="muted small">Checklist ini adalah draf operasional. Peninjauan laporan tidak menjalankan tindakan bisnis pada order.</p><div class="modal-footer"><button class="secondary" data-close>Tutup</button>${s.can_start ? `<button class="primary" id="start-from-sop">Buat laporan</button>` : ''}</div>`);
  const button = dialog.querySelector('#start-from-sop');if (button) button.onclick = () => startSopReport(code);
}
function startSopReport(code) {
  const items = state.sopCatalog.items.filter(s => s.can_start);
  if (!items.length) return pop('Belum ada SOP pelaksana untuk peran ini.',true);
  if (!code) {
    return showModal('Pilih SOP laporan',[selectField('sop_code','Prosedur yang dikerjakan',items.map(s => ({value:s.code,name:s.code+', '+s.title})))],async data => {setTimeout(() => startSopReport(data.sop_code),0);},'Pilih berdasarkan pekerjaan yang benar-benar diperiksa hari ini.');
  }
  const s = items.find(x => x.code === code);if (!s) return;
  (async () => {
    let choices=[];
    try {if (s.order_policy !== 'none') choices = await api('/sop-orders?sop_code='+encodeURIComponent(code));}
    catch (e) {pop(e.message,true);return;}
    if (s.order_policy === 'required' && !choices.length) return pop('Tidak ada order dalam penugasan dan tahap yang sesuai SOP ini.',true);
    const fields=[{key:'report_day',label:'Tanggal pemeriksaan',type:'date',max:jakartaDate(),value:jakartaDate(),wide:true},...(s.order_policy !== 'none' ? [selectField('order_id','Order dalam penugasan',choices.map(o => ({value:o.id,name:o.code+', '+(statusNames[o.status] || o.status)})))] : [])];
    const key=requestKey();
    showModal('Buat draf, '+s.code,fields,async data => {
      const report=await api('/sop-reports','POST',{sop_code:code,report_day:data.report_day,order_id:data.order_id ? Number(data.order_id) : null,request_key:key});
      setTimeout(() => openSopReport(report.id),0);
    },s.title+', Simpan checklist, unggah bukti, lalu ajukan kepada peninjau.');
  })();
}
function reportResultFields(item,result,editable) {
  const disabled=editable ? '' : 'disabled';
  return `<fieldset class="checklist-item" data-check-item="${esc(item.key)}"><legend><span>${esc(item.key)}</span> ${esc(item.text)}</legend><div class="checklist-item-grid"><label>Hasil pemeriksaan<select name="result" ${disabled}>${Object.entries(resultLabels).filter(([value]) => value !== 'na' || item.allow_na).map(([value,label]) => `<option value="${value}" ${value === result.result ? 'selected' : ''}>${label}</option>`).join('')}</select></label><label>Catatan / alasan<textarea name="note" maxlength="1000" ${disabled} placeholder="Catat hasil pemeriksaan atau uraian temuan.">${esc(result.note)}</textarea></label></div><div class="finding-fields ${result.result === 'issue' ? '' : 'is-hidden'}"><label>Tindakan perbaikan<textarea name="action" maxlength="700" ${disabled}>${esc(result.action)}</textarea></label><div class="form-grid"><label>Penanggung jawab<input name="owner" maxlength="120" value="${esc(result.owner)}" ${disabled}></label><label>Tenggat<input name="due" type="date" value="${esc(result.due || '')}" ${disabled}></label></div></div>${item.evidence_required ? '<small class="evidence-required">Lampiran wajib pada item ini sebelum diajukan.</small>' : ''}</fieldset>`;
}
async function openSopReport(id) {
  let report;
  try {report=await api('/sop-reports/'+id);} catch (error) {pop(error.message,true);return;}
  const editable=report.can_edit, spec=report.sop;
  const results=Object.fromEntries(report.results.map(i => [i.key,i]));
  const dialog=mountDialog(`${dialogHeading(spec.title,'LAPORAN SOP-'+String(id).padStart(5,'0'))}<div class="sop-report-meta">${reportBadge(report.status)}<span>${dateText(report.day)}, ${esc(report.author)}, <span id="report-revision">Revisi ${report.revision}</span></span></div><p class="dialog-description">${esc(report.position)} / ${esc(report.division)}, ${esc(spec.code)} versi ${esc(spec.version)}${report.order_id ? ', '+esc(report.order_code || '#'+report.order_id) : ''}</p>${report.review_note ? `<div class="review-note"><strong>${report.status === 'returned' ? 'Perbaikan dari peninjau' : 'Catatan peninjau'}</strong><p>${esc(report.review_note)}</p></div>` : ''}<form id="sop-report-form"><label class="form-row">Ringkasan hasil pekerjaan<textarea name="summary" maxlength="3000" ${editable ? '' : 'disabled'}>${esc(report.summary)}</textarea></label><h3 class="section-title">Pemeriksaan</h3>${spec.items.map(i => reportResultFields(i,results[i.key],editable)).join('')}</form><section class="evidence-section"><h3>Lampiran bukti</h3><p class="muted small">PDF, PNG, JPG, TXT, 3 MB per berkas, maksimal 8 berkas / 15 MB. Hanya bukti fiktif. Lampiran dikaitkan ke item checklist.</p><div id="evidence-list">${evidenceList(report,editable)}</div>${editable ? `<form id="evidence-form" class="evidence-upload"><label>Item yang dibuktikan<select name="item_key">${spec.items.map(i => `<option value="${esc(i.key)}" ${i.key === spec.items.find(x => x.evidence_required)?.key ? 'selected' : ''}>${esc(i.key)}, ${esc(i.text.slice(0,65))}${i.evidence_required ? ' (wajib)' : ''}</option>`).join('')}</select></label><label>Berkas bukti<input name="file" type="file" accept=".pdf,.png,.jpg,.jpeg,.txt" required></label><button class="secondary" type="submit">Unggah bukti</button></form>` : ''}</section>${report.history.length ? `<details class="report-history"><summary>Riwayat pengajuan dan peninjauan (${report.history.length})</summary>${report.history.map(v => `<article><strong>Revisi ${v.revision}, ${esc(statusNames[v.snapshot.status === 'submitted' ? 'submitted_report' : v.snapshot.status])}</strong><span>${dateText(v.at,true)} WIB</span><p>${esc(v.snapshot.summary)}</p><p>${v.snapshot.attachments.length} lampiran tersimpan pada versi ini.</p>${v.snapshot.attachments.map(a => `<a href="/api/sop-reports/${id}/attachments/${a.id}" download>${esc(a.filename)}</a>`).join('<br>')}</article>`).join('')}</details>` : ''}<div class="form-error" id="sop-report-error" role="alert"></div><p class="muted small">Peninjauan laporan tidak meluluskan QC, memverifikasi pembayaran, atau mengganti persetujuan klinis.</p><div class="modal-footer sop-footer"><div class="btnrow"><a class="secondary mini" href="/api/sop-reports/${id}/export?format=zip" download>Unduh laporan + bukti</a><a class="text-button" href="/api/sop-reports/${id}/export?format=html" download>Versi cetak</a></div><div class="btnrow">${editable ? '<button class="secondary" id="save-sop-report">Simpan draf</button><button class="primary" id="submit-sop-report">Ajukan laporan</button>' : report.can_review ? '<button class="secondary" id="return-sop-report">Minta perbaikan</button><button class="primary" id="review-sop-report">Tandai ditinjau</button>' : '<button class="secondary" data-close>Tutup</button>'}</div></div>`);
  dialog.classList.add('sop-report-dialog');
  let busy=false;
  const keys=new Map();
  const stableKey=(action,payload) => {const text=JSON.stringify([action,payload]);if (!keys.has(text)) keys.set(text,requestKey());return keys.get(text);};
  const run=async task => {
    if (busy) return;busy=true;dialog.querySelector('#sop-report-error').textContent='';
    dialog.querySelectorAll('button').forEach(b => b.disabled=true);
    try {await task();} catch(e) {if (dialog.isConnected) dialog.querySelector('#sop-report-error').textContent=e.message;}
    finally {busy=false;if (dialog.isConnected) dialog.querySelectorAll('button').forEach(b => b.disabled=false);}
  };
  dialog.addEventListener('cancel',event => {if (busy) event.preventDefault();});
  dialog.querySelectorAll('[data-check-item]').forEach(fieldset => {const select=fieldset.querySelector('[name=result]');select.onchange=() => fieldset.querySelector('.finding-fields').classList.toggle('is-hidden',select.value !== 'issue');});
  const save=async () => {
    const fields=[...dialog.querySelectorAll('[data-check-item]')].map(f => ({key:f.dataset.checkItem,result:f.querySelector('[name=result]').value,note:f.querySelector('[name=note]').value,action:f.querySelector('[name=action]').value,owner:f.querySelector('[name=owner]').value,due:f.querySelector('[name=due]').value || null}));
    const payload={expected_revision:report.revision,summary:dialog.querySelector('[name=summary]').value,results:fields};
    const data=await api(`/sop-reports/${id}/save`,'POST',{...payload,request_key:stableKey('save',payload)});
    report=data;dialog.querySelector('#report-revision').textContent='Revisi '+report.revision;
  };
  if (editable) {
    dialog.querySelector('#save-sop-report').onclick=() => run(async () => {await save();await refresh();pop('Draf dan checklist tersimpan.');});
    dialog.querySelector('#submit-sop-report').onclick=() => run(async () => {await save();const p={expected_revision:report.revision};await api(`/sop-reports/${id}/submit`,'POST',{...p,request_key:stableKey('submit',p)});await refresh();await openSopReport(id);pop('Laporan diajukan.');});
    dialog.querySelector('#evidence-form').onsubmit=event => {event.preventDefault();const form=event.target;run(async () => {
      const file=form.elements.file.files[0];if (!file) return;
      if (file.size>3*1024*1024) throw new Error('Maksimal 3 MB per berkas.');
      await save();
      const p={filename:file.name,item_key:form.elements.item_key.value,expected_revision:report.revision,request_key:requestKey()};
      const response=await fetch(`/api/sop-reports/${id}/attachments?`+new URLSearchParams(p),{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/octet-stream','X-CSRF-Token':state.csrf},body:file});
      const data=await response.json();if (!response.ok) throw new Error(data.detail || 'Berkas gagal diunggah.');
      await refresh();await openSopReport(id);pop('Lampiran bukti tersimpan.');
    });};
    dialog.querySelectorAll('[data-remove-evidence]').forEach(b => b.onclick=() => run(async () => {await save();const p={expected_revision:report.revision};await api(`/sop-reports/${id}/attachments/${b.dataset.removeEvidence}/remove`,'POST',{...p,request_key:stableKey('remove-'+b.dataset.removeEvidence,p)});await openSopReport(id);}));
  }
  const review=decision => {
    const old=report, key=requestKey();
    showModal(decision === 'returned' ? 'Catat perbaikan yang diperlukan' : 'Catat hasil peninjauan',[{key:'note',label:'Catatan peninjau',type:'textarea',wide:true,minlength:8,maxlength:1500}],async data => {
      await api(`/sop-reports/${id}/review`,'POST',{expected_revision:old.revision,decision,note:data.note,request_key:key});setTimeout(() => openSopReport(id),0);
    },'Peninjau harus orang berbeda dengan kewenangan SOP yang sesuai. Tindakan ini hanya meninjau laporan.');
  };
  if (dialog.querySelector('#review-sop-report')) dialog.querySelector('#review-sop-report').onclick=() => review('reviewed');
  if (dialog.querySelector('#return-sop-report')) dialog.querySelector('#return-sop-report').onclick=() => review('returned');
}
function evidenceList(report,editable) {
  return report.attachments.length ? `<div class="evidence-list">${report.attachments.map(a => `<article><div><a href="/api/sop-reports/${report.id}/attachments/${a.id}" download>${esc(a.filename)}</a><small>${esc(a.item_key)}, ${evidenceSize(a.size)}, SHA-256 ${esc(a.sha256.slice(0,12))}…</small></div>${editable ? `<button type="button" class="text-button danger" data-remove-evidence="${a.id}">Lepas dari draf</button>` : ''}</article>`).join('')}</div>` : '<p class="muted small">Belum ada bukti dilampirkan.</p>';
}
function mapPosition() {
  const data=state.organization;
  if (!data.can_assign) return;
  const key=requestKey();
  showModal('Petakan akun latihan ke jabatan',[selectField('user_id','Akun aktif',data.staff.map(u => ({value:u.id,name:u.name+', '+roleNames[u.role]}))),selectField('position_id','Jabatan',data.positions.map(p => ({value:p.id,name:p.name+' / '+p.division}))),{key:'reason',label:'Alasan pemetaan',type:'textarea',wide:true,minlength:8,maxlength:500}],async values => {
    const staff=data.staff.find(u => u.id === Number(values.user_id));
    await api('/organization/assignments','POST',{user_id:staff.id,position_id:Number(values.position_id),expected_revision:staff.revision,reason:values.reason,request_key:key});
  },'Hanya jabatan yang sesuai peran akun yang dapat dipilih. Pemetaan ini tidak memberi izin aplikasi baru.');
  const dialog=document.querySelector('dialog'), userSelect=dialog.querySelector('[name=user_id]'), positionSelect=dialog.querySelector('[name=position_id]');
  const update=() => {const selected=data.staff.find(u => u.id === Number(userSelect.value));positionSelect.innerHTML=data.positions.filter(p => p.allowed_roles.includes(selected.role)).map(p => `<option value="${p.id}" ${p.id === selected.position_id ? 'selected' : ''}>${esc(p.name)} / ${esc(p.division)}</option>`).join('');};
  userSelect.onchange=update;update();
}
