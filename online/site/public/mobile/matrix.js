// Appearance preferences only. Records, permissions and authentication are unchanged.
(() => {
  const root = document.documentElement;
  const read = (key) => { try { return localStorage.getItem(key); } catch { return null; } };
  const write = (key, value) => { try { localStorage.setItem(key, value); } catch {} };
  const skip = el('a', 'Ir para o conteúdo', 'matrix-skip');
  skip.href = '#title';
  document.body.prepend(skip);
  $('title').tabIndex = -1;
  skip.onclick = () => $('title').focus();
  $('nav').setAttribute('aria-label', 'Navegação principal');
  const collapse = el('button', undefined, 'matrix-collapse');
  collapse.type = 'button';
  collapse.append(outlineGlyph('list-checks'), el('span', 'Recolher menu'));
  const setCollapsed = (value) => {
    root.dataset.sidebar = value ? 'collapsed' : 'expanded';
    collapse.setAttribute('aria-expanded', String(!value));
    collapse.setAttribute('aria-label', value ? 'Expandir menu' : 'Recolher menu');
    collapse.title = collapse.getAttribute('aria-label');
    collapse.lastChild.textContent = value ? 'Expandir menu' : 'Recolher menu';
    write('diolino-sidebar', String(value));
  };
  collapse.onclick = () => setCollapsed(root.dataset.sidebar !== 'collapsed');
  $('nav').append(collapse);
  setCollapsed(read('diolino-sidebar') === 'true');
  for (const button of document.querySelectorAll('#nav button[data-page]')) {
    button.setAttribute('aria-label', button.textContent.trim());
    button.title = button.textContent.trim();
  }
  const syncNav = () => {
    for (const button of document.querySelectorAll('#nav button[data-page]')) {
      if (button.classList.contains('active')) button.setAttribute('aria-current', 'page');
      else button.removeAttribute('aria-current');
    }
    const planner = document.querySelector('#nav button[data-page="planner"]');
    if (planner && workspacePreferences) planner.hidden = workspacePreferences.modules.planning === false;
  };
  const oldShow = show;
  show = async function(next) {
    $('app').setAttribute('aria-busy', 'true');
    try { return await oldShow(next); }
    finally { $('app').setAttribute('aria-busy', 'false'); syncNav(); }
  };
  syncNav();
  // Associate existing adjacent form labels without modifying the record schema.
  let labelId = 0;
  const labelFields = (host) => {
    for (const label of host.querySelectorAll('label:not([for])')) {
      if (label.querySelector('input,select,textarea')) continue;
      const field = label.nextElementSibling;
      if (field?.matches('input,select,textarea')) {
        field.id ||= 'matrix-field-' + (++labelId);
        label.htmlFor = field.id;
      }
    }
  };
  labelFields(document);
  new MutationObserver((changes) => {
    for (const change of changes) for (const node of change.addedNodes) {
      if (node.nodeType === 1) labelFields(node.parentElement || node);
    }
  }).observe(document.body, { childList: true, subtree: true });

  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const canvas = el('canvas', undefined, 'matrix-rain');
  canvas.setAttribute('aria-hidden', 'true');
  $('app').querySelector('header').prepend(canvas);
  let timer = null, columns = [], enabled = read('diolino-matrix-rain') === 'true';
  function resize() {
    const bounds = canvas.parentElement.getBoundingClientRect();
    canvas.width = Math.ceil(bounds.width); canvas.height = Math.ceil(bounds.height);
    columns = Array.from({ length: Math.ceil(canvas.width / 20) }, () => Math.random() * -12);
  }
  function updateRain() {
    clearInterval(timer); timer = null;
    const active = enabled && !motion.matches && !document.hidden && root.dataset.palette === 'matrix' && !$('app').classList.contains('hidden');
    canvas.hidden = !active;
    if (!active) return;
    resize();
    const context = canvas.getContext('2d');
    if (!context) { canvas.hidden = true; return; }
    timer = setInterval(() => {
      context.fillStyle = '#05080630'; context.fillRect(0, 0, canvas.width, canvas.height);
      context.fillStyle = '#39FF88'; context.font = '14px Consolas, monospace';
      columns = columns.map((y, x) => {
        context.fillText(Math.random() > .5 ? '1' : '0', x * 20, y * 20);
        return y * 20 > canvas.height && Math.random() > .97 ? -1 : y + .35;
      });
    }, 100); // Decorative header only, capped at 10 fps.
  }
  new ResizeObserver(resize).observe(canvas.parentElement);
  new MutationObserver(updateRain).observe(root, { attributes: true, attributeFilter: ['data-palette'] });
  new MutationObserver(updateRain).observe($('app'), { attributes: true, attributeFilter: ['class'] });
  motion.addEventListener('change', updateRain);
  document.addEventListener('visibilitychange', updateRain);
  const oldMore = renderMore;
  renderMore = async function() {
    await oldMore();
    const card = el('div', undefined, 'card matrix-settings');
    card.append(el('h2', 'Movimento e navegação'));
    const label = el('label', undefined, 'check'), input = el('input');
    input.type = 'checkbox'; input.checked = enabled;
    label.append(input, el('span', 'Chuva de código no cabeçalho'));
    input.onchange = () => { enabled = input.checked; write('diolino-matrix-rain', String(enabled)); updateRain(); };
    card.append(label, el('p', 'Desativada por padrão. A preferência de movimento reduzido do sistema sempre prevalece. O efeito pausa quando esta aba fica oculta.', 'muted'));
    more.prepend(card); syncNav();
  };
  updateRain();
})();
