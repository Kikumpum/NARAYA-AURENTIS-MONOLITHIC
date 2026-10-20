'use strict';
// The original login UI stays visible. Only the private demo key uses this dialog.
window.NAMDemo = (() => {
  let pending = null;
  async function status() {
    const response = await fetch('/api/demo/status', {credentials:'same-origin', headers:{Accept:'application/json'}});
    if (!response.ok) throw new Error('Akses demo belum dapat diperiksa. Coba lagi.');
    return response.json();
  }
  async function unlock() {
    const info = await status();
    if (!info.available) throw new Error(info.message);
    if (info.authorized) return;
    if (pending) return pending;
    pending = new Promise((resolve, reject) => {
      const dialog = document.createElement('dialog');
      dialog.className = 'demo-access-dialog';
      dialog.setAttribute('aria-labelledby', 'demo-access-title');
      dialog.setAttribute('aria-describedby', 'demo-access-description');
      dialog.innerHTML = '<form><span class="demo-access-kicker">DEMO SEMENTARA</span><h2 id="demo-access-title">Akses demo Naraya</h2><p id="demo-access-description">Masukkan kunci akses yang diberikan pemilik proyek. Setelah itu, proses masuk akan dilanjutkan.</p><label for="demo-access-key">Kunci akses demo</label><input id="demo-access-key" name="access_key" type="password" autocomplete="off" spellcheck="false" maxlength="512" required><p class="demo-access-error" role="alert"></p><div class="demo-access-actions"><button class="demo-access-cancel" type="button">Kembali</button><button class="demo-access-submit" type="submit">Lanjutkan masuk</button></div></form>';
      const form = dialog.querySelector('form');
      let busy = false;
      const finish = error => {
        form.reset(); dialog.close(); dialog.remove();
        if (error) reject(error); else resolve();
      };
      dialog.querySelector('.demo-access-cancel').onclick = () => {if (!busy) finish(new Error('Masuk dibatalkan. Anda dapat mencoba lagi kapan saja.'));};
      dialog.addEventListener('cancel', event => {event.preventDefault(); if (!busy) finish(new Error('Masuk dibatalkan. Anda dapat mencoba lagi kapan saja.'));});
      form.onsubmit = async event => {
        event.preventDefault(); if (busy) return; busy = true;
        const error = dialog.querySelector('.demo-access-error'); error.textContent = '';
        const buttons = dialog.querySelectorAll('button'); buttons.forEach(button => button.disabled = true);
        const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 20000);
        try {
          const response = await fetch('/api/demo/access', {method:'POST', credentials:'same-origin',
            headers:{'Content-Type':'application/json', Accept:'application/json'},
            body:JSON.stringify({access_key:form.elements.access_key.value}), signal:controller.signal});
          const data = await response.json();
          if (!response.ok) throw new Error(data.detail || 'Kunci akses belum dapat diperiksa.');
          finish();
        } catch (failure) {
          error.textContent = failure.name === 'AbortError' ? 'Koneksi belum merespons. Silakan coba lagi.' : failure.message;
          form.elements.access_key.focus();
        } finally {clearTimeout(timer); busy = false; buttons.forEach(button => button.disabled = false);}
      };
      document.body.append(dialog); dialog.showModal(); form.elements.access_key.focus();
    });
    try {await pending;} finally {pending = null;}
  }
  document.addEventListener('DOMContentLoaded', async () => {
    try {
      const info = await status(); if (info.mode !== 'temporary_online_demo') return;
      const text = info.storage === 'shared_postgresql'
        ? 'Data latihan tersimpan pada database demo. Gunakan data fiktif dan simpan ekspor laporan yang diperlukan.'
        : 'Data latihan bersifat sementara dan dapat ter-reset. Simpan laporan penting di komputer Anda.';
      const update = () => {
        document.querySelectorAll('.side-footer strong,.login-kicker').forEach(node => {
          if (/Demo lokal|DEMO LOKAL/.test(node.textContent)) node.textContent = 'Demo sementara';
        });
        document.querySelectorAll('.demo-strip').forEach(node => {
          const message = 'Demo sementara dengan data fiktif. ' + text;
          if (node.textContent !== message) node.textContent = message;
        });
        document.querySelectorAll('.login-demo-info>div,.demo-note,.demo-bar').forEach(host => {
          if (host.querySelector('.demo-runtime-note')) return;
          const note = document.createElement('details'); note.className = 'demo-runtime-note';
          const summary = document.createElement('summary'); summary.textContent = 'Tentang demo sementara';
          const description = document.createElement('p'); description.textContent = info.available ? text : info.message;
          note.append(summary, description); host.append(note);
        });
      };
      update(); new MutationObserver(update).observe(document.body, {childList:true, subtree:true});
    } catch { /* Normal application bootstrap reports connectivity failures. */ }
  });
  return {unlock};
})();
