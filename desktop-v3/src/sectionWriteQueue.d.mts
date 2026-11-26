export const sectionWrites: Map<string, Promise<void>>;

export function queueSectionWrite<T>(
  key: string,
  serialized: string,
  handlers: {
    getConfirmed: () => T | undefined;
    getRevision: (key: string) => unknown;
    write: (key: string, expected: unknown, value: T) => Promise<void>;
    readLatest: (key: string) => Promise<T | null>;
    isConflict: (error: unknown) => boolean;
    onCommit: (serialized: string, value: T) => void;
    onNoop?: (serialized: string) => void | Promise<void>;
    onConflict: (latest: T | null) => void;
    onError: (error: unknown) => void;
  },
): Promise<void>;
