"""Reviewable manual import/export without contacting the online account."""
import json
import tkinter as tk
from datetime import date
from tkinter import ttk, messagebox, filedialog

from manual_sync import export_file, load_file, preview, apply_file
from models import MODELS


class ManualSyncViews:
    def export_manual_sync(self):
        path = filedialog.asksaveasfilename(parent=self, title='Exportar para o site',
                 defaultextension='.json', initialfile=f'diolino-troca-{date.today()}.json',
                 filetypes=[('Troca manual Diolino', '*.json')])
        if not path:
            return
        try:
            export_file(self.store, path)
            messagebox.showinfo('Arquivo criado', 'No site, abra Mais → Seus dados → Troca manual.\n'
                 'Selecione este arquivo e confira a prévia.\n\nO arquivo contém seus registros pessoais, incluindo saúde e notas.\n'
                 'Anexos, exclusões e credenciais não são transferidos.\n\n'+path, parent=self)
        except FileExistsError:
            messagebox.showerror('Preservar exportação', 'Escolha um nome novo. O arquivo anterior foi preservado.', parent=self)
        except Exception as exc:
            messagebox.showerror('Exportação não concluída', str(exc), parent=self)

    def import_manual_sync(self):
        if getattr(self, 'site_sync_busy', False):
            self.site_sync_status.set('Aguarde a sincronização online antes de importar um arquivo.')
            self.show_site_sync()
            return
        from desktop_workspace import NoteEditor
        for window in self.winfo_children():
            if isinstance(window, NoteEditor) and not window.save():
                return
        path = filedialog.askopenfilename(parent=self, title='Importar troca manual do site', filetypes=[('Troca manual Diolino', '*.json')])
        if not path:
            return
        try:
            incoming = load_file(path)
            plan = preview(self.store, incoming)
        except Exception as exc:
            messagebox.showerror('Não foi possível preparar a prévia', str(exc), parent=self)
            return
        win = tk.Toplevel(self)
        win.title('Conferir troca manual • Diolino')
        win.geometry('880x700')
        win.minsize(700, 600)
        frame = ttk.Frame(win, padding=20)
        frame.pack(fill='both', expand=True)
        counts = plan['counts']
        ttk.Label(frame, text='Conferir antes de importar', style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame, text=f"{counts['new']} novos · {counts['same']} iguais · {counts['conflicts']} diferenças · {counts['blocked']} bloqueados",
                  wraplength=800).pack(anchor='w', pady=12)
        ttk.Label(frame, text='Registros iguais são vinculados sem duplicar. Diferenças mantêm a versão deste PC, até você escolher o arquivo.\n'
                  'Bloqueados: registros excluídos neste destino ou com associação indisponível.\n'
                  'Exclusões e anexos não são transferidos. Notas são trocadas em texto simples; alterações do texto substituem a formatação local.',
                  wraplength=800).pack(anchor='w', pady=(0, 10))
        choices = {}
        tree = ttk.Treeview(frame, columns=('area', 'title', 'choice'), show='headings', height=5)
        for col, title in [('area','Área'),('title','Registro com diferença'),('choice','Versão escolhida')]:
            tree.heading(col, text=title)
        tree.column('area', width=140); tree.column('title', width=380); tree.column('choice', width=150)
        tree.pack(fill='x')
        conflicts = {c['key']: c for c in plan['conflicts']}
        for key, conflict in conflicts.items():
            row = conflict['incoming']
            label = next((str(row[k]) for k in ('title','topic','passage','name','date') if row.get(k)), key)
            tree.insert('', 'end', iid=key, values=(MODELS.get(conflict['kind'], ('Anotações',))[0], label, 'Manter neste PC'))
        details = tk.Text(frame, height=10, wrap='word')
        details.pack(fill='both', expand=True, pady=10)
        def show_details(event=None):
            selected = tree.selection()
            if not selected:
                return
            conflict = conflicts[selected[0]]
            local = {k:v for k,v in conflict['local'].items() if k not in ('sync_ids','id','deleted_at')}
            details.configure(state='normal')
            details.delete('1.0', 'end')
            details.insert('end', 'NESTE PC\n'+json.dumps(local, ensure_ascii=False, indent=2)+'\n\nNO ARQUIVO\n'+json.dumps(conflict['incoming'], ensure_ascii=False, indent=2))
            details.configure(state='disabled')
        tree.bind('<<TreeviewSelect>>', show_details)
        actions = ttk.Frame(frame); actions.pack(fill='x', pady=6)
        def choose(value):
            for key in tree.selection():
                if value == 'separate' and not conflicts[key].get('possible'):
                    continue
                choices[key] = value
                tree.set(key, 'choice', {'incoming':'Usar arquivo','keep':'Manter neste PC','separate':'Criar separado'}[value])
        ttk.Button(actions, text='Manter neste PC', command=lambda: choose('keep')).pack(side='left')
        ttk.Button(actions, text='Usar versão do arquivo', command=lambda: choose('incoming')).pack(side='left', padx=8)
        ttk.Button(actions, text='Criar separado se semelhante', command=lambda: choose('separate')).pack(side='left')
        def apply():
            try:
                result = apply_file(self.store, incoming, plan['base'], choices)
            except Exception as exc:
                messagebox.showerror('Importação não concluída', str(exc), parent=win)
                return
            win.destroy()
            self.set_status('Troca manual importada neste computador. Exporte novamente para devolver os vínculos ao site.')
            self.render()
            messagebox.showinfo('Importação concluída', f"{result['counts']['new']} novo(s) · {result['counts']['updated']} atualizado(s).\n"
                                'Backup anterior preservado em:\n'+result['backup'], parent=self)
        ttk.Button(frame, text='Confirmar importação e criar backup', style='Accent.TButton', command=apply).pack(side='right', pady=10)
        ttk.Button(frame, text='Cancelar', command=win.destroy).pack(side='right', padx=8)
        if conflicts:
            tree.selection_set(next(iter(conflicts))); show_details()
