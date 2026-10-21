/* The server supplies valid continuous selections; no independent availability model. */
(() => {
  const source = document.getElementById('calendar-data');
  if (!source) return;
  const data = JSON.parse(source.textContent);
  const form = document.getElementById('calendar-selection');
  if (!form) return;
  const message = document.getElementById('calendar-feedback');
  const submit = document.getElementById('calendar-continue');
  if (data.mode === 'loan-slots') {
    const start = document.getElementById('loan-start');
    const end = document.getElementById('loan-end');
    const params = new URLSearchParams(location.search);
    start.value = params.get('start') || data.initialStart || ''; end.value = params.get('end') || '';
    start.min = `${data.minDate}T00:00`; start.max = `${data.maxStartDate}T23:59`;
    const sync = () => {
      end.min = start.value || `${data.minDate}T00:00`;
      submit.disabled = !start.value || !end.value || end.value <= start.value;
      message.textContent = submit.disabled ? 'Wähle einen Beginn und ein späteres Ende der Ausleihe.' :
        'Die Verfügbarkeit des gesamten Zeitraums und die Abhol-/Rückgabezeiten werden im nächsten Schritt geprüft.';
    };
    start.addEventListener('input',sync); end.addEventListener('input',sync);
    form.addEventListener('submit',event => {sync(); if(submit.disabled) event.preventDefault();});
    sync(); return;
  }
  if (data.mode === 'days') {
    const start = document.getElementById('calendar-start-date');
    const end = document.getElementById('calendar-end-date');
    const params = new URLSearchParams(location.search);
    start.value = params.get('start') || ''; end.value = params.get('end') || '';
    start.min = data.minDate; start.max = data.maxStartDate;
    const revealMonth = date => {
      const target = new URL(location.href); target.searchParams.set('month',date.slice(0,7));
      target.searchParams.set('start',start.value); target.searchParams.set('end',end.value);
      target.hash = 'resource-calendar'; location.assign(target.href);
    };
    const sync = () => {
      const ends = data.dateEnds[start.value] || [];
      if (ends.length) {end.min = ends[0]; end.max = ends[ends.length - 1];}
      else {end.removeAttribute('min'); end.removeAttribute('max');}
      const valid = ends.includes(end.value);
      submit.disabled = !valid;
      message.textContent = valid ? `Gewählter Zeitraum: ${start.value.split("-").reverse().join(".")} – ${end.value.split("-").reverse().join(".")}` :
        start.value && end.value ? `Dieser Zeitraum ist nicht verfügbar. Maximal ${data.maxDays} Tage buchbar.` : 'Wähle Anfang und Ende im Kalender.';
      document.querySelectorAll('[data-date]').forEach(button => {
        button.classList.toggle('in-range', !!start.value && !!end.value && button.dataset.date >= start.value && button.dataset.date <= end.value);
        if (start.value && !end.value) button.disabled = !ends.includes(button.dataset.date);
        else button.disabled = !(data.dateEnds[button.dataset.date] || []).length;
        button.setAttribute("aria-label", `${button.dataset.date}${button.disabled ? ", nicht verfügbar" : ", auswählen"}`);
      });
      document.querySelectorAll('.month-nav').forEach(link => {
        const target = new URL(link.href); target.searchParams.set('start',start.value);
        target.searchParams.set('end',end.value); link.href = target.href;
      });
    };
    document.querySelectorAll('[data-date]').forEach(button => button.addEventListener('click', () => {
      if (!start.value || end.value) {start.value = button.dataset.date; end.value = '';}
      else end.value = button.dataset.date;
      sync();
    }));
    start.addEventListener('change', () => {end.value = ''; if(start.value && !data.dateEnds[start.value] && start.value >= data.minDate && start.value <= data.maxStartDate) revealMonth(start.value); else sync();}); end.addEventListener('change',sync); end.addEventListener('input',sync);
    form.addEventListener('submit', event => {sync(); if(submit.disabled) event.preventDefault();});
    sync(); return;
  }
  const start = document.getElementById('calendar-start-time');
  const end = document.getElementById('calendar-end-time');
  if (!start || !end) return;
  const points = new Map(data.points.map(point => [String(point.value), point]));
  const addOption = (select,point) => select.add(new Option(point.label, String(point.value)));
  data.starts.forEach(value => addOption(start,points.get(String(value))));
  const overlay = document.getElementById('timeline-selection');
  const timelineRoot = document.getElementById('day-timeline');
  timelineRoot.style.height = `${Math.max(240,Math.min(864,(data.viewEnd-data.viewStart)/3600000*36))}px`;
  document.querySelectorAll('.timeline-band').forEach(band => {
    band.style.top = `${band.dataset.top}%`; band.style.height = `${band.dataset.height}%`;
  });
  data.ticks.forEach(tick => {
    const label = document.createElement('span'); label.className = 'timeline-tick';
    label.textContent = tick.label; label.style.top = `${tick.top}%`; timelineRoot.append(label);
  });
  const sync = () => {
    const first = points.get(start.value), last = points.get(end.value);
    const valid = !!first && !!last && (data.ends[start.value] || []).includes(last.value);
    submit.disabled = !valid; overlay.hidden = !valid;
    if(valid) {
      document.getElementById('selected-start').value = first.local;
      document.getElementById('selected-end').value = last.local;
      document.getElementById('selected-start-fold').value = first.fold;
      document.getElementById('selected-end-fold').value = last.fold;
      const total = data.viewEnd - data.viewStart;
      overlay.style.top = `${(first.value-data.viewStart)/total*100}%`;
      overlay.style.height = `${(last.value-first.value)/total*100}%`;
      overlay.querySelector('span').textContent = `${first.label} – ${last.label}`;
      message.textContent = `Gewählter Zeitraum: ${first.label} – ${last.label}`;
    } else message.textContent = first ? 'Wähle ein Ende. Belegung und Übergangszeiten sind berücksichtigt.' :
      data.starts.length ? 'Wähle einen Beginn im Zeitband oder über Von.' : 'An diesem Tag nicht verfügbar.';
  };
  const chooseStart = () => {
    end.replaceChildren(new Option('Ende wählen',''));
    const values = data.ends[start.value] || [];
    values.forEach(value => addOption(end,points.get(String(value))));
    end.disabled = !values.length;
    if(values.length) end.value = String(values[0]);
    sync();
  };
  start.addEventListener('change',chooseStart); end.addEventListener('change',sync); end.addEventListener('input',sync);
  const timeline = document.getElementById('day-timeline');
  timeline.addEventListener('click', event => {
    const bounds = timeline.getBoundingClientRect();
    const instant = data.viewStart + Math.min(1,Math.max(0,(event.clientY-bounds.top)/bounds.height))*(data.viewEnd-data.viewStart);
    const point = data.points.reduce((a,b) => Math.abs(b.value-instant)<Math.abs(a.value-instant)?b:a);
    if(start.value && (data.ends[start.value] || []).includes(point.value)) {end.value = String(point.value); sync(); return;}
    if(data.starts.includes(point.value)) {start.value = String(point.value); chooseStart();}
    else {
      const state = data.segments.find(row => row.start <= instant && instant < row.end)?.state;
      message.textContent = state === 'transition' ? 'Übergangszeit – bitte einen freien Zeitraum wählen.' :
        state === 'booked' ? 'Dieser Zeitraum ist bereits belegt.' : 'Zu dieser Zeit nicht verfügbar.';
    }
  });
  form.addEventListener('submit',event => {sync(); if(submit.disabled) event.preventDefault();});
  sync();
})();
