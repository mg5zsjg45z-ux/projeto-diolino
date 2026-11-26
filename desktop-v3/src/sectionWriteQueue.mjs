export const sectionWrites = new Map();
const desiredValues = new Map();

export function queueSectionWrite(key, serialized, handlers) {
  if (sectionWrites.has(key) && desiredValues.get(key) === serialized) return sectionWrites.get(key);
  desiredValues.set(key, serialized);
  if (sectionWrites.has(key)) return sectionWrites.get(key);

  let tracked;
  const worker = (async () => {
    while (desiredValues.has(key)) {
      const target = desiredValues.get(key);
      const confirmed = handlers.getConfirmed();
      if (target === JSON.stringify(confirmed)) {
        if (desiredValues.get(key) === target) desiredValues.delete(key);
        await handlers.onNoop?.(target);
        continue;
      }

      const value = JSON.parse(target);
      try {
        await handlers.write(key, handlers.getRevision(key) ?? null, value);
        handlers.onCommit(target, value);
        if (desiredValues.get(key) === target) desiredValues.delete(key);
      } catch (error) {
        if (handlers.isConflict(error)) {
          try {
            const latest = await handlers.readLatest(key);
            handlers.onConflict(latest);
          } catch {
            handlers.onConflict(null);
          }
        } else {
          handlers.onError(error);
        }
        desiredValues.delete(key);
        throw error;
      }
    }
  })();
  tracked = worker.finally(() => {
    if (sectionWrites.get(key) === tracked) sectionWrites.delete(key);
  });
  sectionWrites.set(key, tracked);
  return tracked;
}
