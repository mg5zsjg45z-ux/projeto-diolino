export async function persistWebSection(key, expected, next, storage = globalThis.localStorage, lockManager = globalThis.navigator?.locks) {
  const write = async () => {
    const latestRaw = storage.getItem(key);
    if (latestRaw !== expected) throw new Error('Conflito: outra janela alterou estes dados.');
    storage.setItem(key, next);
    if (storage.getItem(key) !== next) throw new Error('Conflito: outra janela alterou estes dados.');
  };
  if (!lockManager?.request) {
    throw new Error('Conflito: este navegador não oferece bloqueio seguro entre janelas. Os dados não foram sobrescritos.');
  }
  return lockManager.request('diolino-section:' + key, { mode: 'exclusive' }, write);
}
