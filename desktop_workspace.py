"""Calendar, persistent module controls and an offline notebook editor."""
import calendar
import html
import json
import sqlite3
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import ttk, messagebox, filedialog, simpledialog
from navigation import AREAS
from workspace_data import ESSENTIAL, module_states, set_modules, notes, save_note, delete_note, TAGS
from appearance import refresh_widget


class WorkspaceViews:
    def render_modules(self):
        self.heading('Configurações · Gerenciamento de Módulos', 'Ocultar um módulo preserva seus registros e não interrompe lembretes já programados.')
        states = module_states(self.store)
        variables = {}
        for key, label, _ in AREAS:
            variable = tk.BooleanVar(value=states[key])
            variables[key] = variable
            widget = ttk.Checkbutton(self.content, text=label + (' · obrigatório' if key in ESSENTIAL else ''), variable=variable)
            widget.pack(anchor='w', pady=7)
            if key in ESSENTIAL:
                widget.state(['disabled'])
        def apply():
            set_modules(self.store, {key: var.get() for key, var in variables.items()})
            self.render()
            self.set_status('Módulos atualizados. Os dados foram preservados.')
        ttk.Button(self.content, text='Aplicar módulos', command=apply, style='Accent.TButton').pack(anchor='w', pady=16)

    def calendar_panel(self):
        selected = date.fromisoformat(self.day.get())
        if getattr(self, '_calendar_selection', None) != selected.isoformat():
            self.calendar_month = (selected.year, selected.month)
            self._calendar_selection = selected.isoformat()
        shown = getattr(self, 'calendar_month', (selected.year, selected.month))
        year, month = shown
        panel = ttk.Frame(self.content)
        panel.pack(fill='x', pady=(0, 10))
        calendar_box = ttk.Frame(panel)
        calendar_box.pack(side='left')
        header = ttk.Frame(calendar_box)
        header.pack(fill='x')
        def move(amount):
            number = year * 12 + month - 1 + amount
            y, m = divmod(number, 12)
            if 1 <= y <= 9999:
                self.calendar_month = (y, m + 1)
                self.render()
        for text, amount in [('«',-12), ('‹',-1)]:
            ttk.Button(header, text=text, width=2, command=lambda a=amount: move(a)).pack(side='left')
        months = ('Janeiro Fevereiro Março Abril Maio Junho Julho Agosto Setembro Outubro Novembro Dezembro').split()
        ttk.Label(header, text=f'{months[month-1]} {year}', width=20, anchor='center').pack(side='left')
        for text, amount in [('›',1), ('»',12)]:
            ttk.Button(header, text=text, width=2, command=lambda a=amount: move(a)).pack(side='left')
        grid = ttk.Frame(calendar_box)
        grid.pack(fill='x')
        events = {r['date'] for r in self.store.rows('agenda')}
        for col, label in enumerate(['S','T','Q','Q','S','S','D']):
            ttk.Label(grid, text=label, anchor='center').grid(row=0,column=col,sticky='ew')
        def choose(day):
            self.day.set(day)
            self.all_dates.set(False)
            self.render()
        for row, week in enumerate(calendar.monthcalendar(year,month),1):
            for col, number in enumerate(week):
                if not number:
                    continue
                day = date(year,month,number).isoformat()
                label = str(number) + (' •' if day in events else '') + (' ◦' if day == date.today().isoformat() else '')
                ttk.Button(grid, text=label, width=5, style='WeekSelected.TButton' if day == selected.isoformat() else 'Week.TButton', command=lambda d=day: choose(d)).grid(row=row,column=col,padx=1,pady=1)
        side = ttk.Frame(panel, padding=(22,0))
        side.pack(side='left', fill='both', expand=True)
        ttk.Label(side,text='CALENDÁRIO MENSAL',style='Eyebrow.TLabel').pack(anchor='w',pady=(10,8))
        ttk.Label(side,text='• Compromissos cadastrados\n◦ Hoje\n\nSelecione um dia para filtrar a lista.',style='Muted.TLabel').pack(anchor='w')
        def today():
            self.calendar_month = (date.today().year,date.today().month)
            choose(date.today().isoformat())
        ttk.Button(side,text='Ir para hoje',command=today).pack(anchor='w',pady=12)

    def render_notebook(self):
        self.heading('Anotações diárias', 'Caderno local · pesquisa por título, conteúdo, etiquetas ou data.')
        controls = ttk.Frame(self.content)
        controls.pack(fill='x',pady=(0,12))
        query = tk.StringVar()
        scope = tk.StringVar(value='Mês')
        ttk.Button(controls,text='Nova anotação',style='Accent.TButton',command=lambda: NoteEditor(self)).pack(side='left')
        ttk.Entry(controls,textvariable=query,width=26).pack(side='left',padx=8)
        combo = ttk.Combobox(controls,textvariable=scope,values=['Dia','Mês','Ano','Todas'],state='readonly',width=9)
        combo.pack(side='left')
        tree = ttk.Treeview(self.content,columns=('date','title','labels'),show='headings',selectmode='browse')
        for key,label,width in [('date','Data',130),('title','Título',420),('labels','Etiquetas',170)]:
            tree.heading(key,text=label);tree.column(key,width=width)
        tree.pack(fill='both',expand=True)
        scrollbar=ttk.Scrollbar(tree,orient='vertical',command=tree.yview)
        scrollbar.pack(side='right',fill='y');tree.configure(yscrollcommand=scrollbar.set)
        def fill(*args):
            tree.delete(*tree.get_children())
            length={'Dia':10,'Mês':7,'Ano':4,'Todas':0}[scope.get()]
            period=self.day.get()[:length] if length else ''
            for row in notes(self.store,query.get(),period):
                tree.insert('', 'end', iid=str(row['id']),values=(row['date'],('★ ' if row['favorite'] else '')+row['title'],row['labels']))
        query.trace_add('write',fill);combo.bind('<<ComboboxSelected>>',fill)
        def open_selected(event=None):
            if tree.selection():
                NoteEditor(self,int(tree.selection()[0]))
        tree.bind('<Double-1>',open_selected)
        actions=ttk.Frame(self.content);actions.pack(fill='x',pady=10)
        ttk.Button(actions,text='Abrir anotação selecionada',command=open_selected).pack(side='left')
        confirmation=ttk.Frame(self.content)
        prompt=ttk.Label(confirmation,text='');prompt.pack(anchor='w',pady=6)
        selected_for_delete=[None]
        def request_delete():
            if not tree.selection():
                self.set_status('Selecione uma anotação na lista para excluir.');return
            rid=int(tree.selection()[0])
            for window in self.winfo_children():
                if isinstance(window,NoteEditor) and window.rid==rid:
                    window.lift();window.delete();return
            selected_for_delete[0]=rid
            prompt.configure(text='Excluir a anotação selecionada? O histórico será preservado.')
            confirmation.pack(fill='x',before=tree)
        def confirm_delete():
            if selected_for_delete[0] is not None:
                delete_note(self.store,selected_for_delete[0]);selected_for_delete[0]=None
                confirmation.pack_forget();fill();self.set_status('Anotação excluída da lista.')
        ttk.Button(actions,text='Excluir selecionada',command=request_delete).pack(side='left',padx=8)
        ttk.Button(confirmation,text='Confirmar exclusão',command=confirm_delete).pack(side='left')
        ttk.Button(confirmation,text='Manter anotação',command=confirmation.pack_forget).pack(side='left',padx=8)
        self.notebook_tree=tree

        fill()


class NoteEditor(tk.Toplevel):
    def __init__(self, app, rid=None):
        super().__init__(app)
        self.app,self.rid,self.job,self.dirty=app,rid,None,False
        self.title('Diolino · Anotação')
        self.geometry('840x700');self.minsize(600,480)
        self.protocol('WM_DELETE_WINDOW',self.close)
        row = next((r for r in notes(app.store) if r['id']==rid),None)
        self.title_var=tk.StringVar(value=row['title'] if row else '')
        self.day_var=tk.StringVar(value=row['date'] if row else app.day.get())
        self.labels=tk.StringVar(value=row['labels'] if row else '')
        self.favorite=tk.BooleanVar(value=bool(row['favorite']) if row else False)
        frame=ttk.Frame(self,padding=18);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Título').pack(anchor='w')
        ttk.Entry(frame,textvariable=self.title_var).pack(fill='x',pady=(4,10))
        line=ttk.Frame(frame);line.pack(fill='x')
        ttk.Label(line,text='Data · AAAA-MM-DD').pack(side='left')
        ttk.Entry(line,textvariable=self.day_var,width=13).pack(side='left',padx=8)
        ttk.Checkbutton(line,text='Favorita',variable=self.favorite).pack(side='left')
        ttk.Label(frame,text='Etiquetas · separadas por vírgula').pack(anchor='w',pady=(8,0))
        ttk.Entry(frame,textvariable=self.labels).pack(fill='x',pady=4)
        tools=ttk.Frame(frame);tools.pack(fill='x',pady=8)
        for label,tag in [('Negrito','bold'),('Itálico','italic'),('Sublinhar','underline'),('Destaque','highlight'),('Centralizar','center'),('À direita','right')]:
            ttk.Button(tools,text=label,command=lambda t=tag:self.format(t)).pack(side='left',padx=1)
        self.text=tk.Text(frame,wrap='word',undo=True,font=('Segoe UI',12),padx=20,pady=16,spacing1=3,spacing3=6)
        self.text.tag_configure('bold',font=('Segoe UI',12,'bold'))
        self.text.tag_configure('italic',font=('Segoe UI',12,'italic'))
        self.text.tag_configure('underline',underline=True)
        self.text.tag_configure('highlight',background='#ffe6a6',foreground='#302519')
        self.text.tag_configure('center',justify='center');self.text.tag_configure('right',justify='right')
        self.text.tag_configure('link',underline=True)
        if row:
            self.text.insert('1.0',row['body'])
            for span in json.loads(row['formatting']):
                self.text.tag_add(span['tag'],f"1.0+{span['start']}c",f"1.0+{span['end']}c")
        lower=ttk.Frame(frame);lower.pack(side='bottom',fill='x',pady=8)
        for label,command in [('Lista',self.bullet),('Inserir link',self.link),('Salvar',self.save),('Exportar',self.export),('Excluir',self.delete)]:
            ttk.Button(lower,text=label,command=command).pack(side='left',padx=2)
        self.state_text=tk.StringVar(value=('Criada em '+row['created_at'][:19] if row else 'Nova anotação · salvamento automático após digitar'))
        ttk.Label(frame,textvariable=self.state_text,style='Muted.TLabel',wraplength=700).pack(side='bottom',anchor='w')
        if row:
            navigation=ttk.Frame(frame);navigation.pack(side='bottom',fill='x',pady=4)
            ordered=notes(app.store)
            position=next(i for i,item in enumerate(ordered) if item['id']==rid)
            def turn(index):
                if not self.save():return
                next_id=ordered[index]['id']
                self.close();NoteEditor(app,next_id)
            for label,index in [('‹ Anotação anterior',position+1),('Próxima anotação ›',position-1)]:
                if 0<=index<len(ordered):ttk.Button(navigation,text=label,command=lambda i=index:turn(i)).pack(side='left',padx=2)
        self.delete_confirmation=ttk.Frame(frame)
        self.text.pack(fill='both',expand=True)
        self.text.edit_modified(False)
        self.text.bind('<<Modified>>',self.modified)
        for var in (self.title_var,self.day_var,self.labels,self.favorite):
            var.trace_add('write',self.changed)
        refresh_widget(self)

    def modified(self,event=None):
        if self.text.edit_modified():
            self.text.edit_modified(False);self.changed()

    def changed(self,*args):
        self.dirty=True
        if self.job:self.after_cancel(self.job)
        self.state_text.set('Alterações pendentes…')
        self.job=self.after(900,self.autosave)

    def autosave(self):
        self.job=None
        self.save(quiet=True)

    def format(self,tag):
        try:start,end=self.text.index('sel.first'),self.text.index('sel.last')
        except tk.TclError:return
        if tag in self.text.tag_names(start):self.text.tag_remove(tag,start,end)
        else:self.text.tag_add(tag,start,end)
        self.changed()

    def bullet(self):
        self.text.insert('insert linestart','• ')

    def link(self):
        url=simpledialog.askstring('Link','Endereço completo (https://…):',parent=self)
        if url and url.startswith(('https://','http://')):
            self.text.insert('insert',url,'link');self.changed()

    def save(self,quiet=False):
        if not self.dirty:return True
        body=self.text.get('1.0','end-1c')
        spans=[]
        for tag in TAGS:
            ranges=self.text.tag_ranges(tag)
            for start,end in zip(ranges[::2],ranges[1::2]):
                spans.append(dict(tag=tag,start=len(self.text.get('1.0',start)),end=len(self.text.get('1.0',end))))
        try:
            self.rid=save_note(self.app.store,self.title_var.get(),self.day_var.get(),body,spans,self.rid,self.labels.get(),self.favorite.get())
        except (ValueError,OSError,sqlite3.Error) as exc:
            self.state_text.set('Não salvo: '+str(exc))
            if not quiet:messagebox.showerror('Anotação não salva',str(exc),parent=self)
            return False
        self.dirty=False;self.state_text.set('Salvo neste PC · '+self.day_var.get())
        return True

    def close(self):
        if not self.save():return
        if self.job:self.after_cancel(self.job)
        self.destroy()
        if self.app.page=='notebook':self.app.render()

    def delete(self):
        if self.delete_confirmation.winfo_manager():return
        self.delete_confirmation.pack(side='bottom',fill='x',before=self.text)
        for child in self.delete_confirmation.winfo_children():child.destroy()
        ttk.Label(self.delete_confirmation,text='Excluir esta anotação? O histórico será preservado.').pack(anchor='w')
        ttk.Button(self.delete_confirmation,text='Confirmar exclusão',command=self.confirm_delete).pack(side='left',pady=8)
        ttk.Button(self.delete_confirmation,text='Manter anotação',command=self.delete_confirmation.pack_forget).pack(side='left',padx=8)
        refresh_widget(self.delete_confirmation)

    def confirm_delete(self):
        if self.job:
            self.after_cancel(self.job);self.job=None
        if self.rid:delete_note(self.app.store,self.rid)
        self.dirty=False
        self.destroy()
        if self.app.page=='notebook':self.app.render()

    def export(self):
        if not self.save():return
        path=filedialog.asksaveasfilename(parent=self,defaultextension='.txt',filetypes=[('Texto','*.txt'),('Markdown','*.md'),('Documento para impressão','*.html')])
        if not path:return
        content=self.title_var.get()+'\n'+self.day_var.get()+'\n\n'+self.text.get('1.0','end-1c')
        if Path(path).suffix.lower()=='.html':
            # Self-contained print document; plain text escaped to prevent active content.
            content='<!doctype html><meta charset="utf-8"><title>Anotação Diolino</title><style>body{font:16px Georgia;max-width:800px;margin:40px auto;white-space:pre-wrap}button{display:block}@media print{button{display:none}}</style><button onclick="print()">Imprimir / Salvar PDF</button>'+html.escape(content)
        Path(path).write_text(content,encoding='utf-8')
        self.state_text.set('Exportado: '+Path(path).name)
