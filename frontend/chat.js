'use strict';

iconPaths.chat = '<path d="M21 11a8 8 0 0 1-8 8H7l-5 3 2-6a8 8 0 0 1 7-13h2a8 8 0 0 1 8 8Z"/><path d="M7 10h10M7 14h6"/>';
iconPaths.support = iconPaths.chat;
const chatState = {open:false,conversation:null,history:[],poll:null,draft:'',error:'',sending:false,pending:null,starting:null};
const supportState = {queue:[],selected:null,transcript:null,poll:null,draft:'',error:'',sending:false,pending:null,signature:''};
const chatStatusNames = {assistant:'Asisten AI, simulasi',waiting:'Menunggu petugas',human:'Terhubung ke petugas',closed:'Percakapan selesai'};
const requestId = () => crypto.randomUUID();
function resetChat() {
  $('#chat-widget')?.remove();
  clearInterval(chatState.poll); clearInterval(supportState.poll);
  Object.assign(chatState,{open:false,conversation:null,history:[],poll:null,draft:'',error:'',sending:false,pending:null,starting:null});
  Object.assign(supportState,{queue:[],selected:null,transcript:null,poll:null,draft:'',error:'',sending:false,pending:null,signature:''});
}
function timeOnly(value) {return new Intl.DateTimeFormat('id-ID',{timeZone:'Asia/Jakarta',hour:'2-digit',minute:'2-digit'}).format(new Date(value));}
function messageMarkup(messages,operator = false) {
  return messages.map(message => {
    const mine = operator ? message.sender === 'agent' : message.sender === 'user';
    return message.sender === 'system' ? `<div class="chat-system">${esc(message.body)}</div>` : `<article class="chat-message ${mine ? 'mine' : ''}"><span class="chat-author">${esc(message.sender === 'assistant' ? 'Asisten AI, simulasi' : message.sender === 'agent' ? 'Petugas Customer Service' : 'Pengguna')}</span><div class="chat-bubble">${esc(message.body)}</div><time>${timeOnly(message.at)} WIB</time></article>`;
  }).join('');
}
function renderChatWidget() {
  $('#chat-widget')?.remove();
  if (!state.user || state.user.role !== 'patient') return;
  const root = document.createElement('div'); root.id = 'chat-widget';
  root.innerHTML = `<button class="chat-launcher" id="chat-launcher" aria-label="${chatState.open ? 'Tutup' : 'Buka'} bantuan chat" aria-expanded="${chatState.open}" aria-controls="chat-panel">${icon(chatState.open ? 'close' : 'chat')}<span>${chatState.open ? 'Tutup' : 'Bantuan'}</span></button><section class="chat-panel ${chatState.open ? 'is-open' : ''}" id="chat-panel" aria-label="Bantuan Naraya"></section>`;
  document.body.append(root);
  $('#chat-launcher').onclick = async () => {
    chatState.open = !chatState.open;
    if (chatState.open && !chatState.conversation) {
      try {
        const rows = await api('/chat/conversations');
        chatState.history = rows;
        const active = rows.find(row => row.status !== 'closed');
        if (active) chatState.conversation = await api(`/chat/conversations/${active.id}`);
      } catch (error) {chatState.error = error.message;}
    }
    if (!state.user) return;
    renderChatWidget();
    if (chatState.open) {startChatPolling(); $('#chat-panel').querySelector('textarea,select,button')?.focus();}
    else clearInterval(chatState.poll);
  };
  if (chatState.open) renderChatPanel();
}
function renderChatPanel() {
  const panel = $('#chat-panel'); if (!panel) return;
  const focused = document.activeElement?.id === 'chat-input';
  const cursor = focused ? document.activeElement.selectionStart : null;
  const conversation = chatState.conversation;
  panel.innerHTML = `<header class="chat-header"><span class="chat-brand-icon">${icon('chat')}</span><div><strong>Bantuan Naraya</strong><span>${conversation ? chatStatusNames[conversation.status] : 'Asisten terlebih dahulu, lalu petugas'}</span></div><button class="icon-button" id="chat-minimize" aria-label="Minimalkan chat">${icon('close')}</button></header>
    ${conversation ? `<div class="chat-mode-bar"><span>${conversation.status === 'assistant' ? 'Jawaban layanan dari simulasi AI lokal' : conversation.status === 'waiting' ? 'Petugas belum bergabung ke percakapan' : conversation.status === 'human' ? 'Balasan ditulis langsung oleh petugas' : 'Riwayat percakapan tetap tersimpan'}</span>${conversation.status === 'assistant' ? '<button class="chat-handoff" id="chat-handoff">Hubungi petugas</button>' : ''}</div><div class="chat-messages" id="chat-messages" role="log" aria-label="Riwayat percakapan" aria-live="polite">${messageMarkup(conversation.messages || [])}</div>` : `<div class="chat-welcome"><div class="chat-welcome-mark">${icon('chat')}</div><span class="eyebrow">LAYANAN NARAYA</span><h2>Ada yang bisa dibantu?</h2><p>Mulai dengan asisten untuk informasi layanan. Jika perlu bantuan lebih lanjut, lanjutkan ke petugas Customer Service.</p><label for="chat-order">Konteks percakapan</label><select id="chat-order"><option value="">Pertanyaan umum</option>${state.orders.map(order => `<option value="${order.id}">${esc(order.code)}</option>`).join('')}</select><button class="primary" id="chat-start">Mulai percakapan ${icon('arrow')}</button><small>Asisten pada demo menggunakan jawaban simulasi lokal.</small></div>`}
    ${chatState.error ? `<div class="chat-error" role="alert">${esc(chatState.error)}</div>` : ''}
    ${conversation && conversation.status !== 'closed' ? `<form class="chat-compose" id="chat-form"><label class="sr-only" for="chat-input">Pesan bantuan</label><textarea id="chat-input" name="message" maxlength="2000" rows="2" placeholder="Tulis pesan Anda…" required ${chatState.sending ? 'disabled' : ''}>${esc(chatState.draft)}</textarea><button class="primary" type="submit" aria-label="Kirim pesan" ${chatState.sending ? 'disabled' : ''}>${icon('arrow')}</button></form><div class="chat-bottom"><span>Data fiktif saja, Maks. 2.000 karakter</span><button id="chat-end" ${chatState.sending ? 'disabled' : ''}>Akhiri</button></div>` : conversation ? `<div class="chat-closed"><button class="primary" id="chat-new">Percakapan baru ${icon('plus')}</button></div>` : ''}`;
  $('#chat-minimize').onclick = () => {chatState.open = false; clearInterval(chatState.poll); renderChatWidget();};
  if ($('#chat-start')) $('#chat-start').onclick = startConversation;
  if (!conversation && chatState.history.length) {
    const history = document.createElement('div'); history.className = 'chat-history-picker';
    history.innerHTML = `<label for="chat-history">Riwayat percakapan Anda</label><select id="chat-history"><option value="">Pilih riwayat…</option>${chatState.history.map(row => `<option value="${row.id}">${dateText(row.created_at,true)}, ${chatStatusNames[row.status]}</option>`).join('')}</select>`;
    panel.querySelector('.chat-welcome').append(history);
    $('#chat-history').onchange = async event => {
      if (!event.target.value) return;
      try {chatState.conversation = await api(`/chat/conversations/${event.target.value}`); chatState.error = ''; renderChatPanel(); startChatPolling();}
      catch (error) {chatState.error = error.message; renderChatPanel();}
    };
  }
  if ($('#chat-handoff')) $('#chat-handoff').onclick = async () => {
    try {await api(`/chat/conversations/${conversation.id}/handoff`,'POST'); await pollChat();}
    catch (error) {chatState.error = error.message; renderChatPanel();}
  };
  if ($('#chat-new')) $('#chat-new').onclick = () => {Object.assign(chatState,{conversation:null,draft:'',error:'',pending:null,starting:null}); renderChatPanel();};
  if ($('#chat-end')) $('#chat-end').onclick = async () => {
    try {await api(`/chat/conversations/${conversation.id}/close`,'POST'); await pollChat();}
    catch (error) {chatState.error = error.message; renderChatPanel();}
  };
  if ($('#chat-form')) {
    $('#chat-input').oninput = event => chatState.draft = event.target.value;
    $('#chat-input').onkeydown = event => {if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {event.preventDefault(); $('#chat-form').requestSubmit();}};
    $('#chat-form').onsubmit = event => {event.preventDefault(); sendChatMessage();};
  }
  const messages = $('#chat-messages'); if (messages) messages.scrollTop = messages.scrollHeight;
  if (focused && $('#chat-input')) {$('#chat-input').focus(); $('#chat-input').setSelectionRange(cursor,cursor);}
}
async function startConversation() {
  const button = $('#chat-start'); if (!button || button.disabled) return;
  const order = $('#chat-order').value;
  if (!chatState.starting || chatState.starting.order_id !== (order ? Number(order) : null)) chatState.starting = {request_id:requestId(),order_id:order ? Number(order) : null};
  button.disabled = true; button.textContent = 'Menyiapkan percakapan…';
  try {
    const created = await api('/chat/conversations','POST',chatState.starting);
    chatState.conversation = await api(`/chat/conversations/${created.id}`);
    chatState.error = ''; renderChatPanel(); startChatPolling(); $('#chat-input')?.focus();
  } catch (error) {chatState.error = error.message; renderChatPanel();}
}
async function sendChatMessage() {
  const body = chatState.draft.trim(); if (!body || chatState.sending) return;
  const id = chatState.conversation.id;
  if (!chatState.pending || chatState.pending.body !== body) chatState.pending = {body,request_id:requestId()};
  chatState.sending = true; chatState.error = ''; renderChatPanel();
  try {
    await api(`/chat/conversations/${id}/messages`,'POST',chatState.pending);
    chatState.draft = ''; chatState.pending = null;
    await pollChat(true);
  } catch (error) {chatState.error = error.message;}
  finally {chatState.sending = false; if (state.user) {renderChatPanel(); $('#chat-input')?.focus();}}
}
function startChatPolling() {
  clearInterval(chatState.poll);
  chatState.poll = setInterval(() => {if (state.user && chatState.open && !document.hidden && !chatState.sending) pollChat();},5000);
}
async function pollChat(force = false) {
  if (!chatState.conversation || !state.user) return;
  const user = state.user, id = chatState.conversation.id;
  try {
    const data = await api(`/chat/conversations/${id}`);
    if (state.user !== user || chatState.conversation?.id !== id) return;
    const changed = JSON.stringify(data) !== JSON.stringify(chatState.conversation);
    chatState.conversation = data;
    if (changed || force) renderChatPanel();
  } catch (error) {if (state.user === user) {chatState.error = error.message; renderChatPanel();}}
}
function supportPage() {
  return pageHeading('CUSTOMER SERVICE','Kotak masuk pasien','Ambil percakapan pasien dari antrean setelah mereka meminta bantuan petugas.')+`<div class="support-layout"><section class="panel support-queue"><div class="panel-header"><h2>Antrean layanan</h2><span class="count-label" id="support-count">${supportState.queue.length}</span></div><div id="support-queue-list"><div class="empty">Memuat antrean…</div></div><p class="support-queue-note">Isi pesan dibuka setelah Anda mengambil percakapan. Antrean diperbarui otomatis saat halaman aktif.</p></section><section class="panel support-transcript" id="support-transcript">${emptyState('Pilih percakapan','Ambil satu percakapan untuk membaca konteks dan membalas sebagai petugas.')}</section></div>`;
}
function bindSupportControls() {
  clearInterval(supportState.poll);
  if (state.page !== 'support') return;
  supportState.signature = ''; loadSupportQueue();
  if (supportState.selected) loadSupportTranscript();
  supportState.poll = setInterval(() => {if (state.page === 'support' && state.user && !document.hidden) {loadSupportQueue(); if (supportState.selected && !supportState.sending) loadSupportTranscript();}},5000);
}
async function loadSupportQueue() {
  const user = state.user;
  try {
    const queue = await api('/chat/queue');
    if (state.user !== user || state.page !== 'support') return;
    const signature = JSON.stringify(queue);
    supportState.queue = queue;
    if (signature === supportState.signature) return;
    supportState.signature = signature;
    $('#support-count').textContent = queue.length;
    $('#support-queue-list').innerHTML = queue.length ? queue.map(chat => `<div class="support-ticket ${chat.id === supportState.selected ? 'selected' : ''}"><span class="eyebrow">CHAT ${esc(chat.id.slice(-6).toUpperCase())}</span><strong>${chat.order_id ? `Terkait order #${chat.order_id}` : 'Pertanyaan layanan umum'}</strong><small>${dateText(chat.updated_at,true)} WIB</small><span class="pill ${chat.status === 'human' ? 'green' : 'yellow'}">${chatStatusNames[chat.status]}</span><button class="${chat.status === 'waiting' ? 'primary' : 'secondary'} mini" data-support-id="${chat.id}">${chat.status === 'waiting' ? 'Ambil percakapan' : 'Buka percakapan'}</button></div>`).join('') : emptyState('Antrean kosong','Percakapan akan muncul setelah pasien memilih Hubungi petugas.');
    $('#support-queue-list').querySelectorAll('[data-support-id]').forEach(button => button.onclick = async () => {
      button.disabled = true;
      try {await api(`/chat/conversations/${button.dataset.supportId}/claim`,'POST'); supportState.selected = button.dataset.supportId; supportState.transcript = null; supportState.draft = ''; supportState.pending = null; supportState.error = ''; await loadSupportTranscript(); await loadSupportQueue();}
      catch (error) {pop(error.message,true); await loadSupportQueue(); button.disabled = false;}
    });
  } catch (error) {if (state.user === user && $('#support-queue-list')) $('#support-queue-list').textContent = error.message;}
}
async function loadSupportTranscript(force = false) {
  const id = supportState.selected, user = state.user;
  if (!id) return;
  try {
    const data = await api(`/chat/conversations/${id}`);
    if (state.user !== user || supportState.selected !== id || !$('#support-transcript')) return;
    const changed = JSON.stringify(data) !== JSON.stringify(supportState.transcript);
    supportState.transcript = data;
    if (changed || force) renderSupportTranscript();
  } catch (error) {if (state.user === user) {supportState.error = error.message; renderSupportTranscript();}}
}
function renderSupportTranscript() {
  const host = $('#support-transcript'), data = supportState.transcript;
  if (!host || !data) return;
  const focused = document.activeElement?.id === 'support-input';
  host.innerHTML = `<div class="panel-header"><div><h2>CHAT ${esc(data.id.slice(-6).toUpperCase())}</h2><p>${chatStatusNames[data.status]}, Riwayat asisten disertakan</p></div>${data.status === 'human' ? '<button class="secondary mini" id="support-close">Selesaikan</button>' : ''}</div><div class="support-messages" id="support-messages" role="log" aria-label="Percakapan layanan" aria-live="polite">${messageMarkup(data.messages,true)}</div>${supportState.error ? `<div class="chat-error" role="alert">${esc(supportState.error)}</div>` : ''}${data.status === 'human' ? `<form class="chat-compose" id="support-form"><label class="sr-only" for="support-input">Balasan petugas</label><textarea id="support-input" maxlength="2000" rows="2" required placeholder="Balas sebagai petugas Customer Service…" ${supportState.sending ? 'disabled' : ''}>${esc(supportState.draft)}</textarea><button class="primary" type="submit" ${supportState.sending ? 'disabled' : ''}>Kirim ${icon('arrow')}</button></form><span class="support-sender-note">Anda membalas sebagai petugas manusia, Data fiktif saja</span>` : '<p class="support-sender-note">Percakapan telah selesai. Riwayat tetap tersimpan.</p>'}`;
  $('#support-messages').scrollTop = $('#support-messages').scrollHeight;
  if ($('#support-input')) {$('#support-input').oninput = event => supportState.draft = event.target.value; if (focused) $('#support-input').focus();}
  if ($('#support-form')) $('#support-form').onsubmit = async event => {
    event.preventDefault(); const body = supportState.draft.trim(); if (!body || supportState.sending) return;
    if (!supportState.pending || supportState.pending.body !== body) supportState.pending = {body,request_id:requestId()};
    supportState.sending = true; supportState.error = ''; renderSupportTranscript();
    try {await api(`/chat/conversations/${data.id}/messages`,'POST',supportState.pending); supportState.draft = ''; supportState.pending = null; await loadSupportTranscript(true);}
    catch (error) {supportState.error = error.message;}
    finally {supportState.sending = false; renderSupportTranscript(); $('#support-input')?.focus();}
  };
  if ($('#support-close')) $('#support-close').onclick = async () => {
    try {await api(`/chat/conversations/${data.id}/close`,'POST'); await loadSupportTranscript(true); await loadSupportQueue();}
    catch (error) {supportState.error = error.message; renderSupportTranscript();}
  };
}
