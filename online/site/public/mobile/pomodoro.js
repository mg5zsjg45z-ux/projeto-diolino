// In-memory timer. Saving always uses the existing, explicit study form.
(() => {
  const dialog = el('dialog', undefined, 'pomodoro-dialog');
  const heading = el('h2', 'Pomodoro'); heading.id = 'pomodoro-title';
  dialog.setAttribute('aria-labelledby', heading.id);
  const launch = el('button', 'Pomodoro', 'pomodoro-launch');
  launch.type = 'button'; launch.setAttribute('aria-haspopup', 'dialog');
  $('app').querySelector('header').insertBefore(launch, $('logout'));
  const mode = el('select'); mode.setAttribute('aria-label', 'Foco ou descanso');
  for (const [value, text] of [['focus', 'Foco'], ['rest', 'Descanso']]) {
    const option = el('option', text); option.value = value; mode.append(option);
  }
  const duration = el('input'); duration.type = 'number'; duration.min = '1'; duration.max = '180'; duration.value = '25';
  const durationLabel = el('label', 'Duração em minutos'); durationLabel.append(duration);
  const clock = el('div', '25:00', 'pomodoro-clock'); clock.setAttribute('role', 'timer'); clock.setAttribute('aria-label', 'Tempo restante');
  const progress = el('progress'); progress.max = 1500; progress.value = 0; progress.setAttribute('aria-label', 'Tempo decorrido');
  const status = el('p', 'Pronto para iniciar.', 'muted'); status.setAttribute('role', 'status');
  const start = el('button', 'Iniciar', 'primary'), pause = el('button', 'Pausar'), stop = el('button', 'Encerrar'), record = el('button', 'Revisar e registrar estudo'), close = el('button', 'Fechar');
  const actions = el('div', undefined, 'row'); actions.append(start, pause, stop);
  dialog.append(heading, mode, durationLabel, clock, progress, status, actions, record, close,
    el('p', 'O tempo não é salvo como estudo automaticamente. Revise os minutos no formulário e confirme em “Salvar registro”. A sessão continua ao fechar esta janela e pode ser retomada após recarregar a mesma aba.', 'muted'));
  document.body.append(dialog);
  const storageKey='diolino-focus-session-v1';
  let state = 'idle', total = 1500, elapsed = 0, runningSince = 0, ticker = null, studyDate = '';
  try {
    const saved=JSON.parse(sessionStorage.getItem(storageKey)||'null');
    if(saved&&['idle','running','paused','finished','stopped'].includes(saved.state)&&Number.isFinite(saved.total)&&saved.total>=60&&saved.total<=10800&&Number.isFinite(saved.elapsed)&&saved.elapsed>=0&&saved.elapsed<=saved.total){
      state=saved.state;total=saved.total;elapsed=saved.elapsed;runningSince=saved.runningSince||0;studyDate=saved.studyDate||'';mode.value=saved.mode==='rest'?'rest':'focus';duration.value=String(Math.round(total/60));
      if(state==='running'&&Date.now()-runningSince>0){elapsed=Math.min(total,elapsed+(Date.now()-runningSince)/1000);runningSince=Date.now();}
    }
  }catch{}
  function persist(){try{sessionStorage.setItem(storageKey,JSON.stringify({state,total,elapsed,runningSince,studyDate,mode:mode.value}))}catch{}}
  const seconds = () => Math.min(total, elapsed + (state === 'running' ? (Date.now() - runningSince) / 1000 : 0));
  function draw() {
    const spent = seconds(), left = Math.max(0, Math.ceil(total - spent));
    clock.textContent = String(Math.floor(left / 60)).padStart(2, '0') + ':' + String(left % 60).padStart(2, '0');
    progress.max = total; progress.value = spent;
    if (state === 'running' && spent >= total) {
      elapsed = total; state = 'finished'; clearInterval(ticker); ticker = null;
      status.textContent = mode.value === 'focus' ? 'Foco concluído. Revise o estudo antes de registrar.' : 'Descanso concluído.';
    }
    start.disabled = !['idle', 'paused'].includes(state);
    start.textContent = state === 'paused' ? 'Retomar' : 'Iniciar';
    pause.disabled = state !== 'running'; stop.disabled = !['running', 'paused'].includes(state);
    mode.disabled = duration.disabled = state !== 'idle';
    record.hidden = mode.value !== 'focus' || !['finished', 'stopped'].includes(state) || spent < 60;
    launch.textContent = state === 'running' || state === 'paused' ? 'Foco · ' + clock.textContent : 'Pomodoro';
    if (mode.value === 'rest' && ['running', 'paused'].includes(state)) launch.textContent = 'Descanso · ' + clock.textContent;
    persist();
  }
  function pauseTimer() {
    elapsed = seconds(); state = 'paused'; clearInterval(ticker); ticker = null;
    status.textContent = 'Pausado.'; draw();
  }
  start.onclick = () => {
    if (state === 'idle') {
      if (!duration.reportValidity()) return;
      total = Number(duration.value) * 60; elapsed = 0;
      studyDate = new Intl.DateTimeFormat('sv-SE', { timeZone: 'America/Sao_Paulo' }).format(new Date());
    }
    state = 'running'; runningSince = Date.now();
    status.textContent = mode.value === 'focus' ? 'Foco em andamento.' : 'Descanso em andamento.';
    clearInterval(ticker); ticker = setInterval(draw, 1000); draw();
  };
  pause.onclick = pauseTimer;
  stop.onclick = () => { pauseTimer(); state = 'stopped'; status.textContent = 'Sessão encerrada. ' + Math.floor(elapsed / 60) + ' minuto(s) completos.'; draw(); };
  const reset = el('button', 'Nova sessão');
  reset.onclick = () => {
    if (state === 'running' || state === 'paused') { status.textContent = 'Encerre a sessão atual antes de começar outra.'; return; }
    state = 'idle'; elapsed = 0; total = Number(duration.value) * 60; status.textContent = 'Pronto para iniciar.'; draw();
  };
  actions.append(reset);
  mode.onchange = () => { duration.value = mode.value === 'focus' ? '25' : '5'; total = Number(duration.value) * 60; draw(); };
  duration.oninput = () => { if (duration.validity.valid && duration.value) { total = Number(duration.value) * 60; draw(); } };
  record.onclick = () => {
    const minutes = Math.floor(elapsed / 60);
    dialog.close(); state = 'idle'; elapsed = 0; status.textContent = 'Sessão encaminhada ao formulário. Confirme o salvamento nele.'; draw();
    openEditor('study', { date: studyDate, duration_min: minutes });
  };
  close.onclick = () => dialog.close();
  launch.onclick = () => { draw(); dialog.showModal(); (start.disabled ? close : start).focus(); };
  document.addEventListener('visibilitychange', () => { if (!document.hidden) draw(); });
  window.addEventListener('beforeunload', (event) => { if (state !== 'idle') { event.preventDefault(); event.returnValue = ''; } });
  if(state==='running'){ticker=setInterval(draw,1000);status.textContent='Sessão retomada após recarregar a página.';}
  draw();
})();
