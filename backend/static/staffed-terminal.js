/* A transient staffed context, never a global keystroke hook or offline queue. */
(() => {
  const banner = document.querySelector('[data-terminal-id]');
  if (!banner) return;
  let valid = true;
  const generation = banner.dataset.terminalId;
  const lock = () => { valid = false; document.body.replaceChildren(); window.location.replace('/konto/anmelden/'); };
  // Server enforces the same timeout; local timer hides PII even without another request.
  let timer = setTimeout(lock, Number(banner.dataset.idle) * 1000);
  window.addEventListener("pageshow", event => { if(event.persisted) lock(); });
  const form = document.querySelector('[data-terminal-scan]');
  if (!form) return;
  const input = form.querySelector('[data-scan-input], [name=code]');
  const scanState = document.querySelector('[data-scan-state]');
  const submitButton=form.querySelector('button:not([type])');
  const results = document.querySelector('[data-scan-results]');
  const queue = [];
  let epoch = 0;
  let running = false;
  function show(text) { const item = document.createElement('li'); item.textContent = text; results.prepend(item); while(results.children.length>20) results.lastChild.remove(); }
  async function drain() {
    if(running || !valid) return;
    running=true;scanState.textContent='Scan wird verarbeitet';
    while(queue.length && valid) {
      const pending=queue.shift();
      const data=pending.data;
      try {
        const response=await fetch(form.getAttribute('action') || window.location.href,{method:'POST',body:data,headers:{'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin',redirect:'error'});
        if([401,409].includes(response.status)) { lock(); break; }
        const value=await response.json();
        if(!valid || value.generation!==generation) break;
        if(pending.epoch!==epoch) continue;
        show(value.message);
        clearTimeout(timer);timer=setTimeout(lock,Number(banner.dataset.idle)*1000);
      } catch (_) {
        show('Verbindung unklar. Keine Erfolgsmeldung. Aktuellen Vorgangsstand prüfen, dann bewusst erneut scannen.');
        queue.length=0; break; // no offline replay
      }
    }
    running=false;scanState.textContent='Scanner bereit';
    if(document.activeElement===submitButton || document.activeElement===input) input.focus();
  }
  form.addEventListener('submit',event=>{
    event.preventDefault();
    if(!valid || !form.reportValidity()) return;
    if(queue.length>=50){show('Scanfolge voll. Verarbeitung abwarten.');return;}
    const data=new FormData(form);if(form.dataset.scanAction) data.set('action',form.dataset.scanAction);data.set('request_key',crypto.randomUUID());queue.push({data,epoch});input.value='';
    if(form.dataset.scanAction) document.querySelectorAll('button[name=action][value=confirm]').forEach(button=>button.disabled=true);
    drain();
  });
  const review=document.querySelector('[data-review-preparation]');
  if(review) review.addEventListener('click',event=>{if(running || queue.length){event.preventDefault();show('Scanfolge erst fertig verarbeiten lassen.');}else{valid=false;}});
  form.querySelector('[data-resume-scan]').addEventListener('click',()=>input.focus());
  // Context changes invalidate queued responses before a navigation can expose them.
  document.querySelectorAll('form:not([data-terminal-scan])').forEach(other=>other.addEventListener('submit',()=>{valid=false;queue.length=0;}));
  form.querySelectorAll('select').forEach(select=>select.addEventListener('change',()=>{epoch++;queue.length=0;results.replaceChildren();}));
})();
