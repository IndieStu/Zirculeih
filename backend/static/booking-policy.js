(() => {
  const use = document.getElementById('id_use_mode');
  const mode = document.getElementById('id_time_mode');
  if(!use || !mode) return;
  const before = document.getElementById('id_buffer_before_minutes');
  const after = document.getElementById('id_buffer_after_minutes');
  const sync = () => {
    if(use.value === 'onsite' && Number(before.value)+Number(after.value)<30) after.value = String(30-Number(before.value));
    ['min_days','max_days'].forEach(name => {document.getElementById('id_'+name).closest('p').hidden = mode.value !== 'days';});
    ['granularity_minutes','min_duration_minutes','max_duration_minutes'].forEach(name => {document.getElementById('id_'+name).closest('p').hidden = mode.value === 'days';});
  };
  use.addEventListener('change',sync); mode.addEventListener('change',sync); sync();
})();
