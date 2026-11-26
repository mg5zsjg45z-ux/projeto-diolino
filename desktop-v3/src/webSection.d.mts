export function persistWebSection(
  key: string,
  expected: string | null,
  next: string,
  storage?: Storage,
  lockManager?: LockManager,
): Promise<void>;
