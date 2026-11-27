const fonts = {
  system: ['Sistema', 'var(--system-type)'],
  serif: ['Georgia', 'Georgia, serif'],
  sans: ['Verdana', 'Verdana, sans-serif'],
  mono: ['Monoespaçada', 'Consolas, monospace'],
} as const;

type Font = keyof typeof fonts;
type TextStyle = {font: Font; size: number};
export type Typography = {app: TextStyle; notebook: TextStyle};
const defaults: Typography = {
  app: {font: 'system', size: 13},
  notebook: {font: 'serif', size: 16},
};
const sizes = {app: [12, 13, 14, 16, 18], notebook: [14, 15, 16, 18, 20, 22]};
const key = 'diolino-typography';

export function loadTypography(): Typography {
  try {
    const saved = JSON.parse(localStorage.getItem(key) ?? 'null');
    const read = (scope: keyof Typography): TextStyle => {
      const value = saved?.[scope];
      return {
        font: Object.hasOwn(fonts, value?.font) ? value.font : defaults[scope].font,
        size: sizes[scope].includes(value?.size) ? value.size : defaults[scope].size,
      };
    };
    return {app: read('app'), notebook: read('notebook')};
  } catch {
    return defaults;
  }
}

export function saveTypography(value: Typography) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* Preferences are optional. */ }
}

export function typographyStyle(value: Typography) {
  return {
    '--ui-font': fonts[value.app.font][1],
    '--ui-size': value.app.size + 'px',
    '--notebook-font': fonts[value.notebook.font][1],
    '--notebook-size': value.notebook.size + 'px',
  };
}

export function TypographySettings({value, onChange}: {value: Typography; onChange: (value: Typography) => void}) {
  return <section className="panel typography-settings" aria-labelledby="typography-title">
    <h2 id="typography-title">Tipografia</h2>
    {(['app', 'notebook'] as const).map(scope => {
      const name = scope === 'app' ? 'do Diolino' : 'do Caderno';
      const update = (change: Partial<TextStyle>) =>
        onChange({...value, [scope]: {...value[scope], ...change}});
      return <fieldset key={scope}>
        <legend>{scope === 'app' ? 'Diolino' : 'Caderno'}</legend>
        <label>Fonte <select aria-label={'Fonte ' + name} value={value[scope].font}
          onChange={event => update({font: event.target.value as Font})}>
          {Object.entries(fonts).map(([id, [label]]) => <option key={id} value={id}>{label}</option>)}
        </select></label>
        <label>Tamanho <select aria-label={'Tamanho ' + name} value={value[scope].size}
          onChange={event => update({size: Number(event.target.value)})}>
          {sizes[scope].map(size => <option key={size} value={size}>{size} px</option>)}
        </select></label>
      </fieldset>;
    })}
    <button type="button" onClick={() => onChange(defaults)}>Restaurar tipografia padrão</button>
  </section>;
}
