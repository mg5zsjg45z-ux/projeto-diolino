import { invoke, isTauri } from '@tauri-apps/api/core';
import { useEffect, useRef, useState } from 'react';
import { persistWebSection } from './webSection.mjs';
import { queueSectionWrite, sectionWrites } from './sectionWriteQueue.mjs';

export function loadLocalSection<T>(key: string, fallback: T): T {
  try {
    const stored = localStorage.getItem(key);
    return stored === null ? fallback : JSON.parse(stored) as T;
  } catch {
    return fallback;
  }
}

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
  const currentState = useRef(state);
  currentState.current = state;
  const baselineRaw = useRef<{ key: string; raw: string | null }>({ key, raw: null });
  const editedWhileLoading = useRef<{ key: string; edited: boolean }>({ key, edited: false });
  const value = state.key === key ? state.value : load();
  const ready = loaded.key === key && loaded.ready;
  const error = errorState.key === key ? errorState.message : '';

  const setValue = (next: T | ((previous: T) => T)) => {
    const current = state.key === key ? state.value : load();
    const nextValue = typeof next === 'function' ? (next as (previous: T) => T)(current) : next;
    if (!ready) {
      editedWhileLoading.current = { key, edited: true };
      if (isTauri()) {
        try {
          const serialized = JSON.stringify(nextValue);
          localStorage.setItem(key, serialized);
          localStorage.setItem(key + '.sqlite-pending', serialized);
        } catch { /* Keep the in-memory edit available if local storage is unavailable. */ }
      }
    }
    setState({ key, value: nextValue });
  };

  useEffect(() => {
    let live = true;
    const fallback = load();
    baseline.current = { key, value: fallback };
    baselineRaw.current = { key, raw: null };
    editedWhileLoading.current = { key, edited: false };
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

    (sectionWrites.get(key) ?? Promise.resolve())
      .catch(() => {})
      .then(() => invoke<T | null>('read_local_section', { key }))
      .then(stored => {
        if (!live) return;
        let pending = false;
        let localRaw: string | null = null;
        try {
          pending = localStorage.getItem(key + '.sqlite-pending') !== null;
          localRaw = localStorage.getItem(key);
        } catch { /* SQLite remains available. */ }
        const local = load();
        const edited = editedWhileLoading.current.key === key && editedWhileLoading.current.edited;
        const latestState = currentState.current;
        const loadedValue = edited ? (latestState.key === key ? latestState.value : local) : stored !== null && !pending ? stored : local;
        const durableBaseline = stored !== null ? stored : localRaw !== null || pending || edited ? undefined : local;
        baseline.current = { key, value: durableBaseline as T };
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
    const native = isTauri();

    if (!native) {
      if (serialized === JSON.stringify(baselineValue)) return;
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

    const write = queueSectionWrite(key, serialized, {
      getConfirmed: () => baseline.current.key === key ? baseline.current.value : undefined,
      getRevision: () => revisions.get(key) ?? null,
      write: (_sectionKey, expected, nextValue) => invoke<void>('write_local_section', { key, expected, value: nextValue }),
      readLatest: () => invoke<T | null>('read_local_section', { key }),
      isConflict: conflictMessage,
      onCommit: (target: string, nextValue: T) => {
        revisions.set(key, nextValue);
        baseline.current = { key, value: nextValue };
        try { if (localStorage.getItem(key + '.sqlite-pending') === target) localStorage.removeItem(key + '.sqlite-pending'); } catch { /* SQLite write is already complete. */ }
      },
      onNoop: (target: string) => {
        try { if (localStorage.getItem(key + '.sqlite-pending') === target) localStorage.removeItem(key + '.sqlite-pending'); } catch { /* No pending copy to clear. */ }
      },
      onConflict: (latest: T | null) => {
        revisions.set(key, latest);
        baseline.current = { key, value: latest as T };
        if (latest !== null) {
          const latestSerialized = JSON.stringify(latest);
          baselineRaw.current = { key, raw: latestSerialized };
          try { localStorage.setItem(key, latestSerialized); localStorage.removeItem(key + '.sqlite-pending'); } catch { /* Keep the conflict visible. */ }
          setValue(latest);
        }
        setErrorState({ key, message: 'Conflito: outra janela alterou estes dados. Os registros foram recarregados; reaplique sua edição para salvá-la.' });
      },
      onError: () => setErrorState({ key, message: 'Não foi possível gravar no banco 3.0. Confira o armazenamento local.' }),
    });
    write.then(() => {
      setErrorState({ key, message: '' });
    }).catch(() => {});
  }, [key, ready, state, value]);

  return [value, setValue, error, ready] as const;
}

export function reconcileWebSection<T>(key: string, fallback: T): T {
  const raw = localStorage.getItem(key);
  if (raw === null) return fallback;
  try { return JSON.parse(raw) as T; } catch { return fallback; }
}

export async function flushLocalSections() {
  await Promise.all(sectionWrites.values());
  for (let i = 0; i < localStorage.length; i++) {
    if (localStorage.key(i)?.endsWith('.sqlite-pending')) {
      throw new Error('Há registros aguardando gravação. Reabra o aplicativo e tente novamente.');
    }
  }
}
