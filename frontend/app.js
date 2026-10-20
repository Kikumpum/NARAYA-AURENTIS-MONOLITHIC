'use strict';

// Session secrets remain in memory and HttpOnly cookies; no browser persistence.
const state = {
  user:null, csrf:null, page:'dashboard', orders:[], roster:[], patients:[], appts:[],
  invoices:[], stats:{}, reports:[], notices:[], audits:[], search:'', orderFilter:'all',
  sourceFilter:'all', sort:'latest', dashboardFilter:'all', loadErrors:[], refreshing:false,
  sopCatalog:{items:[]}, sopReports:[], organization:{positions:[],notes:[],staff:[]}, sopSearch:'', sopMine:true,
};
const roleNames = {reception:'Front Office',dentist:'Dokter Klinik',lab_supervisor:'Supervisor Lab',technician:'Teknisi Lab',qc:'Quality Control',finance:'Finance & FAT',director:'Direktur',partner:'Klinik Mitra',patient:'Pasien',it_admin:'Administrator IT',nurse:'Perawat',cadcam:'CAD/CAM',customer_service:'Customer Service',warehouse:'Gudang',purchasing:'Pembelian',hr:'HRD',marketing:'Marketing'};
Object.assign(roleNames,{commissioner:'Komisaris',chief_executive:'Direktur Utama',auditor:'Auditor',corporate:'Corporate',business_development:'Business Development',general_affairs:'IC / GA',insurance:'Insurance',operations_manager:'Operation',branch_manager:'Branch Manager',clinic_head:'Kepala Klinik',editor:'Editor',content_planner:'Content Planner',sales:'Sales',housekeeping:'Housekeeping'});
const statusNames = {
  submitted:'Menunggu penugasan',assigned:'Menunggu penerimaan',accepted:'Diterima Lab',design:'Desain',production:'Produksi',finishing:'Finishing',qc_pending:'Menunggu QC',ready:'Siap diserahkan',completed:'Selesai',rejected:'Ditolak',rework:'Perlu perbaikan',paid:'Lunas',partial:'Dibayar sebagian',unpaid:'Belum dibayar',verified:'Terverifikasi',pending_verification:'Menunggu FAT',confirmed:'Terjadwal',awaiting_patient:'Menunggu pasien',replacement_rejected:'Pengganti ditolak',queued:'Antrean demo',pending:'Menunggu respons',approved:'Disetujui',
};
const eventNames = {
  'training.opened':'Materi divisi dibuka','patient_portal.service_viewed':'Layanan dibuka di portal pasien','chat.started':'Percakapan bantuan dimulai','chat.message_recorded':'Pesan bantuan dicatat','chat.handoff_requested':'Bantuan petugas diminta','chat.claimed':'Petugas mengambil percakapan','chat.closed':'Percakapan ditutup',
  'lab_order.submitted':'Surat kerja diajukan','lab_order.lead_assigned':'Penanggung jawab ditugaskan','lab_order.accepted':'Order diterima Lab','lab_order.rejected':'Order ditolak Lab','lab_order.plan_validated':'Rencana produksi divalidasi','lab_order.progress':'Tahap produksi diperbarui','lab_order.qc_passed':'Pemeriksaan QC lulus','lab_order.qc_failed':'QC meminta perbaikan','lab_order.delay_proposed':'Perubahan estimasi diusulkan','lab_order.delay_decided':'Respons perubahan diterima','auth.login':'Masuk ke aplikasi','auth.logout':'Keluar dari aplikasi','order.viewed':'Detail order dibuka','patient.registered':'Pasien simulasi diregistrasi','partner.patient_case_registered':'Referensi mitra dibuat','appointment.created':'Janji temu dibuat','appointment.replacement_requested':'Dokter pengganti diusulkan','appointment.replacement_responded':'Respons penggantian dokter','invoice.created':'Tagihan dibuat','payment.recorded':'Penerimaan dana dicatat','payment.manually_verified':'Verifikasi manual demo oleh FAT','daily_report.submitted':'Laporan harian disimpan',
};
const categoryNames = {crown:'Crown',bridge:'Bridge',veneer:'Veneer',denture:'Gigi tiruan',implant:'Implan',other:'Lainnya'};
Object.assign(statusNames,{draft:'Draf',submitted_report:'Diajukan',reviewed:'Ditinjau',returned:'Perlu perbaikan'});
Object.assign(eventNames,{'organization.position_assigned':'Pemetaan jabatan diperbarui','sop_report.created':'Draf laporan SOP dibuat','sop_report.saved':'Checklist laporan disimpan','sop_report.submitted':'Laporan SOP diajukan','sop_report.reviewed':'Laporan SOP ditinjau','sop_report.returned':'Laporan dikembalikan untuk perbaikan','sop_report.evidence_added':'Bukti laporan diunggah','sop_report.evidence_removed':'Lampiran dilepas dari draf','sop_report.evidence_downloaded':'Bukti laporan diunduh','sop_report.viewed':'Laporan SOP dibuka','sop_report.exported':'Laporan dan bukti diekspor'});
const methodNames = {cash:'Tunai',qris:'QRIS',bank_transfer:'Transfer bank',debit_edc:'Debit / EDC',credit_card:'Kartu kredit',insurance_corporate:'Asuransi / perusahaan'};
const channelNames = {portal:'Portal pasien',partner_portal:'Portal mitra',whatsapp:'WhatsApp',sms:'SMS',email:'Email'};
const detailNames = {minimal:'Minimal',standard:'Standar',detail:'Detail'};
const reportRoles = ['reception','dentist','lab_supervisor','technician','qc','finance','nurse','cadcam','customer_service','warehouse','purchasing','hr','marketing','it_admin'];
const staffRoles = Object.keys(roleNames).filter(role => !['partner','patient'].includes(role));
const orderRoles = ['reception','dentist','lab_supervisor','technician','qc','finance','director','partner','patient'];
const iconPaths = {
  dashboard:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  orders:'<path d="M9 5H5v16h14V5h-4"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M8 12h8M8 16h5"/>',
  patients:'<circle cx="9" cy="7" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 4a3 3 0 0 1 0 6M19 21v-3a6 6 0 0 0-2-4"/>',
  finance:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18M7 15h3"/>',
  reports:'<path d="M5 3h10l4 4v14H5zM14 3v5h5M8 12h8M8 16h5"/>',
  notifications:'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
  audit:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',chevron:'<path d="m9 5 7 7-7 7"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',close:'<path d="m6 6 12 12M6 18 18 6"/>',check:'<path d="m5 12 4 4L19 6"/>',
  refresh:'<path d="M20 7v5h-5M4 17v-5h5M6 6a8 8 0 0 1 13 3M18 18A8 8 0 0 1 5 15"/>',
  logout:'<path d="M9 4H4v16h5M14 8l4 4-4 4M8 12h12"/>',
  calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 11h18M8 15h2M14 15h2"/>',
  shield:'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6"/>',clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5h4"/>',
  alert:'<path d="m12 3 10 18H2zM12 9v5M12 17v.1"/>',lab:'<path d="M9 3h6M10 3v7L4 20h16L14 10V3M7 15h10"/>',
  menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',eye:'<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
};
Object.assign(iconPaths,{sops:iconPaths.shield,organization:iconPaths.patients});
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const icon = name => `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${iconPaths[name] || iconPaths.orders}</svg>`;
const fmt = value => new Intl.NumberFormat('id-ID',{style:'currency',currency:'IDR',maximumFractionDigits:0}).format(value || 0);
const jakartaDate = () => new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Jakarta',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
function dateText(value, withTime = false) {
  if (!value) return 'Belum ditetapkan';
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(value);
  const normalized = dateOnly ? `${value}T12:00:00+07:00` : /(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : value.replace(' ','T')+'Z';
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return 'Tanggal tidak valid';
  return new Intl.DateTimeFormat('id-ID',{timeZone:'Asia/Jakarta',day:'numeric',month:'short',year:'numeric',...(withTime && !dateOnly ? {hour:'2-digit',minute:'2-digit'} : {})}).format(date);
}
function badge(status) {
  const tone = ['ready','completed','verified','paid','confirmed','approved'].includes(status) ? 'green' : ['rejected','rework','replacement_rejected'].includes(status) ? 'red' : ['design','production','finishing','accepted','partial'].includes(status) ? 'blue' : 'yellow';
  return `<span class="pill ${tone}">${esc(statusNames[status] || status || 'Belum tersedia')}</span>`;
}
function pop(message, error = false) {
  const toast = document.createElement('div'); toast.className = `toast${error ? ' error' : ''}`;
  toast.setAttribute('role',error ? 'alert' : 'status'); toast.textContent = message;
  document.body.append(toast); setTimeout(() => toast.remove(),5000);
}
async function api(path, method = 'GET', body = null) {
  const headers = {Accept:'application/json'};
  if (body !== null) headers['Content-Type'] = 'application/json';
  if (method !== 'GET' && state.csrf) headers['X-CSRF-Token'] = state.csrf;
  let response;
  try { response = await fetch('/api'+path,{method,credentials:'same-origin',headers,body:body === null ? undefined : JSON.stringify(body)}); }
  catch { throw new Error('Server lokal tidak dapat dihubungi. Periksa apakah demo masih berjalan.'); }
  let data;
  try { data = await response.json(); } catch { throw new Error('Respons server tidak dapat dibaca. Coba muat ulang.'); }
  if (!response.ok) {
    if (response.status === 401 && path !== '/login') {clearSession(); renderLogin('Sesi berakhir. Silakan masuk kembali.');}
    const detail = Array.isArray(data.detail) ? data.detail.map(item => `${item.loc?.slice(1).join('.') || 'Data'}: ${item.msg}`).join('; ') : data.detail;
    throw new Error(detail || 'Permintaan tidak dapat diproses.');
  }
  return data;
}
function clearSession() {
  document.body.classList.remove('menu-open');
  if (typeof resetChat === 'function') resetChat();
  if (typeof learning !== 'undefined') Object.assign(learning,{catalog:null,lesson:null,error:''});
  document.querySelectorAll('dialog').forEach(dialog => dialog.remove());
  Object.assign(state,{user:null,csrf:null,orders:[],roster:[],patients:[],appts:[],invoices:[],stats:{},reports:[],notices:[],audits:[],search:'',loadErrors:[]});
  Object.assign(state,{sopCatalog:{items:[]},sopReports:[],organization:{positions:[],notes:[],staff:[]},sopSearch:'',sopMine:true});
}
function navOptions() {
  if (!state.user) return [];
  const role = state.user.role;
  return ['dashboard',...(orderRoles.includes(role) ? ['orders'] : []),...(['reception','dentist','director','patient'].includes(role) ? ['patients'] : []),...(['reception','finance','director','partner'].includes(role) ? ['finance'] : []),...(staffRoles.includes(role) ? ['training','sops','reports','organization'] : []),...(['patient','partner','reception','lab_supervisor','director'].includes(role) ? ['notifications'] : []),...(role === 'customer_service' ? ['support'] : []),...(role === 'director' ? ['audit'] : [])];
}
const navName = page => ({dashboard:'Ringkasan',orders:'Order laboratorium',patients:state.user?.role === 'patient' ? 'Jadwal saya' : 'Pasien & jadwal',finance:'Keuangan',reports:'Laporan & bukti',training:'Materi divisi',sops:'SOP & checklist',organization:'Struktur organisasi',notifications:'Pemberitahuan',support:'Kotak masuk pasien',audit:'Jejak audit'}[page] || page);
function navigate(page, filter) {
  if (!navOptions().includes(page)) return;
  state.page = page; if (filter) state.orderFilter = filter;
  renderShell(); window.scrollTo({top:0,behavior:'instant'});
}
async function refresh() {
  if (!state.user || state.refreshing) return;
  state.refreshing = true;
  const user = state.user, can = navOptions();
  const endpoints = {stats:'/dashboard',...(can.includes('orders') ? {orders:'/orders'} : {}),...(['reception','lab_supervisor','director','dentist'].includes(user.role) ? {roster:'/roster'} : {}),...(['reception','dentist','director','partner'].includes(user.role) ? {patients:'/patients'} : {}),...(can.includes('patients') ? {appts:'/appointments'} : {}),...(can.includes('finance') ? {invoices:'/invoices'} : {}),...(can.includes('reports') ? {sopReports:'/sop-reports'} : {}),...([...reportRoles,'director'].includes(user.role) ? {reports:'/daily-reports'} : {}),...(can.includes('sops') ? {sopCatalog:'/sops',organization:'/organization'} : {}),...(can.includes('notifications') ? {notices:'/notifications'} : {}),...(can.includes('audit') ? {audits:'/admin/audits'} : {})};
  state.loadErrors = [];
  try {
    await Promise.all(Object.entries(endpoints).map(async ([key,url]) => {
      try {const data = await api(url); if (state.user === user) state[key] = data;}
      catch (error) {if (state.user === user) {state[key] = key === 'stats' ? {} : key === 'sopCatalog' ? {items:[]} : key === 'organization' ? {positions:[],notes:[],staff:[]} : []; state.loadErrors.push(error.message);}}
    }));
    if (state.user === user) renderShell();
  } finally {state.refreshing = false;}
}
function renderLogin(message = '') {
  $('#app').innerHTML = `<div class="login-wrap"><section class="login-story" aria-label="Naraya Aurentis Monolithic"><img class="login-logo" src="/static/assets/naraya-aurentis-transparent.png" alt="Naraya Aurentis Monolithic" width="376" height="202"><div class="login-copy"><span class="eyebrow">KLINIK & LABORATORIUM</span><h1>Manajemen Klinik<br>dan Laboratorium</h1><p>Kelola layanan pasien dan pekerjaan Lab dalam ruang kerja yang sama.</p><div class="brand-rule"></div><span class="login-caption">Dental Management System</span></div><div class="login-story-footer"><span>NARAYA AURENTIS MONOLITHIC</span><span>01 / RUANG KERJA</span></div></section>
    <section class="login-panel"><div class="login-card"><div class="login-kicker"> DEMO LOKAL</div><h2>Masuk ke ruang kerja</h2><p class="login-intro">Gunakan akun kerja yang diberikan kepada Anda.</p><form id="loginform"><div class="form-row"><label for="login-user">Nama pengguna</label><input id="login-user" name="username" autocomplete="username" required placeholder="Masukkan nama pengguna"></div><div class="form-row"><label for="login-password">Kata sandi</label><div class="password-field"><input id="login-password" name="password" type="password" required autocomplete="current-password"><button class="icon-button" type="button" id="toggle-password" aria-label="Tampilkan kata sandi">${icon('eye')}</button></div></div><div class="form-error" id="login-error" role="alert">${esc(message)}</div><button class="primary login-submit" type="submit">Masuk ke ruang kerja ${icon('arrow')}</button></form><div class="login-demo-info">${icon('shield')}<div><strong>Ruang simulasi dengan data fiktif</strong><p>Akun latihan: <code>resepsionis</code>, sandi <code>DemoNAM2026!</code>. Data pasien dan pembayaran nyata tidak diperbolehkan.</p></div></div><div class="login-panel-footer"><span>NAM DMS</span><span>Versi demo 0.4</span></div></div></section></div>`;
  $('#toggle-password').onclick = () => {const input = $('#login-password'); input.type = input.type === 'password' ? 'text' : 'password'; $('#toggle-password').setAttribute('aria-label',input.type === 'password' ? 'Tampilkan kata sandi' : 'Sembunyikan kata sandi');};
  $('#loginform').onsubmit = async event => {
    event.preventDefault(); const button = event.target.querySelector('[type="submit"]'); if (button.disabled) return;
    button.disabled = true; button.textContent = 'Sedang masuk…'; $('#login-error').textContent = '';
    try {const fields = new FormData(event.target); const data = await api('/workspace/login','POST',{username:fields.get('username'),password:fields.get('password')}); clearSession(); Object.assign(state,{user:data.user,csrf:data.csrf,page:'dashboard',orderFilter:'all',sourceFilter:'all'}); await refresh();}
    catch (error) {$('#login-error').textContent = error.message; button.disabled = false; button.innerHTML = `Masuk ke ruang kerja ${icon('arrow')}`;}
  };
}
function renderShell() {
  if (!state.user) return;
  if (!navOptions().includes(state.page)) state.page = 'dashboard';
  const user = state.user;
  const primaryNav = navOptions().filter(page => ['dashboard','orders','patients','finance'].includes(page));
  const secondaryNav = navOptions().filter(page => !primaryNav.includes(page));
  const nav = pages => pages.map(page => `<button class="nav-btn ${state.page === page ? 'active' : ''}" data-nav="${page}" ${state.page === page ? 'aria-current="page"' : ''}>${icon(page)}<span>${navName(page)}</span>${page === 'orders' && state.orders.length ? `<span class="nav-count">${state.orders.length}</span>` : ''}</button>`).join('');
  $('#app').innerHTML = `<a class="skip-link" href="#content">Langsung ke isi</a><aside class="sidebar" id="sidebar"><div class="sidebar-brand"><img src="/static/assets/naraya-aurentis-transparent.png" alt="Naraya Aurentis Monolithic" width="376" height="202"><span>SISTEM MANAJEMEN DENTAL</span></div><div class="workspace-switch">${icon(user.role === 'partner' ? 'patients' : 'lab')}<div><strong>${user.role === 'partner' ? 'Ruang mitra' : user.role === 'patient' ? 'Portal pasien' : 'Operasional Naraya'}</strong><span>${esc(roleNames[user.role])}</span></div></div><nav aria-label="Navigasi utama"><div class="side-section">RUANG KERJA</div>${nav(primaryNav)}${secondaryNav.length ? `<div class="side-section second">PENCATATAN</div>${nav(secondaryNav)}` : ''}</nav><div class="side-footer"><div><strong>Demo lokal</strong><span>Data fiktif</span></div><span class="workspace-version">v0.4</span></div></aside><button class="sidebar-backdrop" aria-label="Tutup menu" id="sidebar-backdrop"></button>
    <div class="workspace-main"><header class="topbar"><div class="breadcrumb"><button class="icon-button mobile-menu" id="menu-toggle" aria-label="Buka menu" aria-expanded="false" aria-controls="sidebar">${icon('menu')}</button><span>Ruang kerja</span>${icon('chevron')}<strong>${navName(state.page)}</strong></div><div class="topbar-tools">${navOptions().includes('orders') ? `<form id="quick-search" class="quick-search" role="search">${icon('search')}<input name="query" aria-label="Cari order di ruang kerja" placeholder="Cari order…" autocomplete="off"><kbd>↵</kbd></form>` : ''}${navOptions().includes('notifications') ? `<button class="icon-button notification-button" data-nav="notifications" aria-label="Buka pemberitahuan">${icon('notifications')}${state.notices.length ? '<span class="notification-count">'+state.notices.length+'</span>' : ''}</button>` : ''}<div class="identity"><span class="avatar">${esc(user.name.slice(0,1))}</span><span class="identity-copy"><strong>${esc(user.name)}</strong><small>${esc(roleNames[user.role])}</small></span></div><button class="icon-button" id="logout" aria-label="Keluar dari akun" title="Keluar dari akun">${icon('logout')}</button></div></header><main class="main"><div class="demo-bar"><span><strong>Mode demo</strong> Gunakan data fiktif. Pembayaran dan pengiriman pesan masih simulasi.</span></div>${state.loadErrors.length ? `<div class="load-error" role="alert">${icon('alert')}<span>Sebagian data gagal dimuat. ${esc(state.loadErrors[0])}</span><button class="secondary mini" data-action="refresh">Coba lagi</button></div>` : ''}<div id="content" tabindex="-1">${pageContent()}</div><footer class="main-footer"><span>© ${new Date().getFullYear()} Naraya Aurentis Monolithic</span></footer></main></div>`;
  bindActions();
  $('#logout').onclick = async () => {try {await api('/logout','POST'); clearSession(); renderLogin();} catch (error) {pop(error.message,true);}};
  const menu = $('#menu-toggle');
  menu.onclick = () => {const opened = document.body.classList.toggle('menu-open'); menu.setAttribute('aria-expanded',String(opened));};
  $('#sidebar-backdrop').onclick = closeMenu;
  if ($('#quick-search')) $('#quick-search').onsubmit = event => {event.preventDefault(); state.search = new FormData(event.target).get('query').trim(); state.orderFilter = 'all'; state.sourceFilter = 'all'; navigate('orders');};
  bindPageControls();
  if (typeof renderChatWidget === 'function') renderChatWidget();
}
function closeMenu() {document.body.classList.remove('menu-open'); $('#menu-toggle')?.setAttribute('aria-expanded','false');}
function bindActions(root = document) {
  root.querySelectorAll('[data-nav]').forEach(button => button.onclick = () => {closeMenu(); navigate(button.dataset.nav,button.dataset.filter);});
  root.querySelectorAll('[data-action]').forEach(button => button.onclick = () => handle(button.dataset.action,Number(button.dataset.id || 0)));
  root.querySelectorAll('[data-order]').forEach(button => button.onclick = () => openOrder(Number(button.dataset.order)));
}
function pageContent() {return ({dashboard:dashboardPage,orders:ordersPage,patients:patientsPage,finance:financePage,reports:sopReportsPage,sops:sopsPage,organization:organizationPage,notifications:noticesPage,audit:auditsPage,training:trainingPage,support:supportPage}[state.page] || dashboardPage)();}
function bindPageControls() {
  if (typeof bindTraining === 'function') bindTraining();
  if (typeof bindSopControls === 'function') bindSopControls();
  if (typeof bindSupportControls === 'function') bindSupportControls();
  if ($('#order-search')) $('#order-search').oninput = event => {state.search = event.target.value; renderOrderResults();};
  if ($('#source-filter')) {$('#source-filter').value = state.sourceFilter; $('#source-filter').onchange = event => {state.sourceFilter = event.target.value; renderOrderResults();};}
  if ($('#order-sort')) {$('#order-sort').value = state.sort; $('#order-sort').onchange = event => {state.sort = event.target.value; renderOrderResults();};}
  document.querySelectorAll('[data-order-filter]').forEach(button => button.onclick = () => {state.orderFilter = button.dataset.orderFilter; document.querySelectorAll('[data-order-filter]').forEach(tab => {tab.classList.toggle('active',tab === button); tab.setAttribute('aria-pressed',String(tab === button));}); renderOrderResults();});
  document.querySelectorAll('[data-dashboard-filter]').forEach(button => button.onclick = () => {state.dashboardFilter = button.dataset.dashboardFilter; renderShell();});
}
function renderOrderResults() {
  const host = $('#order-results'); if (!host) return;
  const rows = filteredOrders(); host.innerHTML = orderTable(rows,true);
  $('#result-count').textContent = `${rows.length} dari ${state.orders.length} order`; bindActions(host);
}
async function bootstrap() {
  try {
    const response = await fetch('/api/me',{credentials:'same-origin',headers:{Accept:'application/json'}});
    if (response.status === 401) {renderLogin(); return;}
    if (!response.ok) throw new Error('Sesi belum dapat dimuat. Silakan masuk kembali.');
    const data = await response.json(); state.csrf = data.csrf;
    const {csrf,...user} = data; if(user.role === 'patient'){window.location.replace('/pasien');return;} state.user = user; await refresh();
  } catch (error) {renderLogin(error.message);}
}
document.addEventListener('keydown',event => {if (event.key === 'Escape') closeMenu();});
document.addEventListener('DOMContentLoaded',bootstrap);
