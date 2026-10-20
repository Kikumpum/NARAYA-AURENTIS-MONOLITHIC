'use strict';
// Runtime labels only: no credentials, role data, browser persistence, or external calls.
document.addEventListener('DOMContentLoaded', async () => {
  try {
    const response = await fetch('/api/health', {credentials:'same-origin', headers:{Accept:'application/json'}});
    if (!response.ok) return;
    const runtime = await response.json();
    if (runtime.mode !== 'temporary_online_demo') return;
    const message = 'Demo online sementara. Gunakan data fiktif. Data latihan dan sesi dapat ter-reset atau berbeda antar-instance server. Simpan hasil penting di komputer Anda.';
    const update = () => {
      document.querySelectorAll('.side-footer strong,.login-kicker,.demo-note strong').forEach(node => {
        if (/Demo lokal|DEMO LOKAL/.test(node.textContent)) node.textContent = 'Demo sementara';
      });
      document.querySelectorAll('.demo-strip').forEach(node => {if (node.textContent !== message) node.textContent = message;});
      document.querySelectorAll('.login-card,.login-form,.main').forEach(host => {
        if (host.querySelector('.runtime-demo-notice')) return;
        const note = document.createElement('p'); note.className = 'runtime-demo-notice';
        note.textContent = message; host.prepend(note);
      });
    };
    update(); new MutationObserver(update).observe(document.body, {childList:true, subtree:true});
  } catch { /* The regular application bootstrap reports server failures. */ }
});
