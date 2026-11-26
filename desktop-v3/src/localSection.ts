import { invoke, isTauri } from '@tauri-apps/api/core';
import { useEffect, useRef, useState } from 'react';
import { persistWebSection } from './webSection.mjs';

export function loadLocalSection<T>(key: string, fallback: T): T {
  try {
    const stored = localStorage.getItem(key);
    return stored === null ? fallback : JSON.parse(stored) as T;
  } catch {
    return fallback;
  }
}

const writes = new Map<string, Promise<void>>();
const revisions = new Map<string, unknown>();
const versionPrefix = 'diolino-section-version:';
function version(key: string) {
  return Number(localStorage.getItem(versionPrefix + key) ?? '0');
}
function bumpVersion(key: string) {
  localStorage.setItem(versionPrefix + key, String(version(key) + 1));
}
function conflictMessage(reason: unknown) {
  return String(reason).includes('outra janela') || String(reason).includes('Outra janela');
}
type SectionState<T> = { key: string; value: T };
type ReadyState = { key: string; ready: boolean };
type ErrorState = { key: string; message: string };

export function useLocalSection<T>(key: string, load: () => T) {
  const [state, setState] = useState<SectionState<T>>(() => ({ key, value: load() }));
  const [loaded, setLoaded] = useState<ReadyState>({ key, ready: false });
  const [errorState, setErrorState] = useState<ErrorState>({ key, message: '' });
  const baseline = useRef<SectionState<T>>({ key, value: load() });
  const baselineRaw = useRef<{ key: string; raw: string | null }>({ key, raw: null });
  const value = state.key === key ? state.value : load();
  const ready = loaded.key === key && loaded.ready;
  const error = errorState.key === key ? errorState.message : '';

  const setValue = (next: T | ((previous: T) => T)) => {
    setState(previous => {
      const current = previous.key === key ? previous.value : load();
      const value = typeof next === 'function' ? (next as (previous: T) => T)(current) : next;
      return { key, value };
    });
  };

  useEffect(() => {
    let live = true;
    const fallback = load();
    baseline.current = { key, value: fallback };
    baselineRaw.current = { key, raw: null };
    setState({ key, value: fallback });
    setLoaded({ key, ready: false });
    setErrorState({ key, message: '' });

    if (!isTauri()) {
      try {
        const stored = localStorage.getItem(key);
        if (stored !== null) {
          const parsed = JSON.parse(stored) as T;
          baseline.current = { key, value: parsed };
          baselineRaw.current = { key, raw: stored };
          setState({ key, value: parsed });
        }
      } catch {
        // Keep the section's safe fallback if local storage is unavailable.
      }
      setLoaded({ key, ready: true });
      return () => { live = false; };
    }

    (writes.get(key) ?? Promise.resolve())
      .catch(() => {})
      .then(() => invoke<T | null>('read_local_section', { key }))
      .then(stored => {
        if (!live) return;
        let pending = false;
        try { pending = localStorage.getItem(key + '.sqlite-pending') !== null; } catch { /* SQLite remains available. */ }
        const local = load();
        const loadedValue = stored !== null && !pending ? stored : local;
        baseline.current = { key, value: stored ?? local };
        revisions.set(key, stored);
        if (stored !== null && !pending && version(key) === 0) {
          try { localStorage.setItem(versionPrefix + key, '0'); } catch { /* The SQLite version remains authoritative. */ }
        }
        setState({ key, value: loadedValue });
        setLoaded({ key, ready: true });
      })
      .catch(() => {
        if (live) setErrorState({ key, message: 'O banco 3.0 não pôde ser aberto. Os registros continuam no armazenamento da interface.' });
      });

    return () => { live = false; };
  }, [key]);

  useEffect(() => {
    if (!ready || state.key !== key) return;
    const serialized = JSON.stringify(value);
    const baselineValue = baseline.current.key === key ? baseline.current.value : undefined;
    if (serialized === JSON.stringify(baselineValue)) return;
    const native = isTauri();

    if (!native) {
      const expectedRaw = baselineRaw.current.key === key ? baselineRaw.current.raw : null;
      const save = persistWebSection(key, expectedRaw, serialized).then(() => { baselineRaw.current = { key, raw: serialized }; bumpVersion(key); });
      save.then(() => {
        baseline.current = { key, value };
        baselineRaw.current = { key, raw: serialized };
        setErrorState({ key, message: '' });
      }).catch(reason => {
        setErrorState({
          key,
          message: conflictMessage(reason)
            ? 'Conflito: outra janela alterou estes dados. Atualize a tela para preservar ambas as edições.'
            : 'Não foi possível salvar os registros neste navegador.',
        });
      });
      return;
    }

    try {
      localStorage.setItem(key, serialized);
      localStorage.setItem(key + '.sqlite-pending', serialized);
    } catch {
      setErrorState({ key, message: 'Não foi possível guardar a cópia local dos registros.' });
      return;
    }

    const write = (writes.get(key) ?? Promise.resolve())
      .catch(() => {})
      .then(async () => {
        const expected = revisions.get(key) ?? null;
        await invoke<void>('write_local_section', { key, expected, value });
        revisions.set(key, value);
        baseline.current = { key, value };
        try { localStorage.removeItem(key + '.sqlite-pending'); } catch { /* SQLite write is already complete. */ }
      });
    writes.set(key, write);
    write.then(() => {
      try {
        if (localStorage.getItem(key + '.sqlite-pending') === serialized) {
          localStorage.removeItem(key + '.sqlite-pending');
        }
      } catch { /* SQLite write already completed. */ }
      setErrorState({ key, message: '' });
      baseline.current = { key, value };
    }).catch(async reason => {
      if (conflictMessage(reason)) {
        try {
          const latest = await invoke<T | null>('read_local_section', { key });
          if (latest !== null) {
            localStorage.setItem(key, JSON.stringify(latest));
            localStorage.removeItem(key + '.sqlite-pending');
            baseline.current = { key, value: latest };
            baselineRaw.current = { key, raw: JSON.stringify(latest) };
            setValue(latest);
          }
        } catch { /* Keep the conflict visible if refresh is unavailable. */ }
        setErrorState({ key, message: 'Conflito: outra janela alterou estes dados. Os registros foram recarregados; reaplique sua edição para salvá-la.' });
      } else {
        setErrorState({ key, message: 'Não foi possível gravar no banco 3.0. Confira o armazenamento local.' });
      }
    }).finally(() => {
      if (writes.get(key) === write) writes.delete(key);
    });
  }, [key, ready, state, value]);

  return [value, setValue, error, ready] as const;
}

export function reconcileWebSection<T>(key: string, fallback: T): T {
  const raw = localStorage.getItem(key);
  if (raw === null) return fallback;
  try { return JSON.parse(raw) as T; } catch { return fallback; }
}

export async function flushLocalSections() {
  await Promise.all(writes.values());
  for (let i = 0; i < localStorage.length; i++) {
    if (localStorage.key(i)?.endsWith('.sqlite-pending')) {
      throw new Error('Há registros aguardando gravação. Reabra o aplicativo e tente novamente.');
    }
  }
}