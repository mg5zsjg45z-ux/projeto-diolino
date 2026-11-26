export const isBackupDate = value => typeof value === 'string'
  && /^\d{4}-\d{2}-\d{2}$/.test(value)
  && !Number.isNaN(Date.parse(value + 'T00:00:00Z'))
  && new Date(value + 'T00:00:00Z').toISOString().slice(0, 10) === value;

export const isBackupTime = value => value === null
  || typeof value === 'string' && /^([01]\d|2[0-3]):[0-5]\d$/.test(value);
