"""Local scripture reader and personal bookmarks, themed by the application."""
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from offline_bible import installed, read_translation, search
from workspace_data import preference


class OfflineBibleViews:
    def render_offline_bible(self):
        self.heading('Bíblia · Leitura offline', 'Textos instalados neste PC. Ler ou favoritar não confirma automaticamente o pilar diário.')
        self.local_bibles=installed(self.store.directory)
        top=ttk.Frame(self.content);top.pack(fill='x')
        ttk.Button(top,text='Importar tradução JSON',command=self.import_translation).pack(side='left')
        ttk.Button(top,text='Versões online e planos',command=lambda:self.navigate('bible_online')).pack(side='left',padx=8)
        if not self.local_bibles:
            ttk.Label(self.content,text='Nenhuma tradução válida instalada. Importe um arquivo autorizado.').pack(pady=20)
            return
        last=preference(self.store,'bible_position',{})
        version=last.get('version') if last.get('version') in self.local_bibles else next(iter(self.local_bibles))
        self.local_version=tk.StringVar(value=version)
        self.local_book=tk.StringVar()
        self.local_chapter=tk.StringVar()
        self.local_size=tk.IntVar(value=preference(self.store,'bible_font',14))
        self.local_spacing=tk.IntVar(value=preference(self.store,'bible_spacing',8))
        selectors=ttk.Frame(self.content);selectors.pack(fill='x',pady=14)
        version_combo=ttk.Combobox(selectors,textvariable=self.local_version,values=list(self.local_bibles),state='readonly',width=10)
        version_combo.pack(side='left')
        self.local_book_combo=ttk.Combobox(selectors,state='readonly',width=28)
        self.local_book_combo.pack(side='left',padx=8)
        chapter_combo=ttk.Combobox(selectors,textvariable=self.local_chapter,state='readonly',width=6)
        chapter_combo.pack(side='left')
        self.local_chapter_combo=chapter_combo
        def books(event=None):
            data=self.local_bibles[self.local_version.get()]
            self.local_codes=list(data['books'])
            self.local_book_combo.configure(values=[b['name'] for b in data['books'].values()])
            code=last.get('book') if last.get('book') in data['books'] else self.local_codes[0]
            self.local_book_combo.current(self.local_codes.index(code));chapters()
        def chapters(event=None):
            code=self.local_codes[self.local_book_combo.current()]
            self.local_book.set(code)
            chapters=list(self.local_bibles[self.local_version.get()]['books'][code]['chapters'])
            chapter_combo.configure(values=chapters)
            self.local_chapter.set(str(last.get('chapter')) if str(last.get('chapter')) in chapters else chapters[0])
            self.show_local_chapter()
        version_combo.bind('<<ComboboxSelected>>',books)
        self.local_book_combo.bind('<<ComboboxSelected>>',chapters)
        chapter_combo.bind('<<ComboboxSelected>>',lambda e:self.show_local_chapter())
        controls=ttk.Frame(self.content);controls.pack(fill='x')
        def move(delta):
            values=list(chapter_combo['values']);index=values.index(self.local_chapter.get())+delta
            if 0<=index<len(values):self.local_chapter.set(values[index]);self.show_local_chapter()
        for label,delta in [('‹ Capítulo',-1),('Capítulo ›',1)]:
            ttk.Button(controls,text=label,command=lambda d=delta:move(d)).pack(side='left',padx=2)
        ttk.Label(controls,text='Fonte').pack(side='left',padx=(12,3))
        ttk.Spinbox(controls,from_=10,to=28,width=4,textvariable=self.local_size,command=self.show_local_chapter,state='readonly').pack(side='left')
        ttk.Label(controls,text='Espaço').pack(side='left',padx=(12,3))
        ttk.Spinbox(controls,from_=0,to=20,width=4,textvariable=self.local_spacing,command=self.show_local_chapter,state='readonly').pack(side='left')
        self.local_text=tk.Text(self.content,wrap='word',height=15,padx=18,pady=16)
        self.local_text.pack(fill='both',expand=True,pady=10)
        self.local_text.configure(state='disabled')
        self.local_meta=ttk.Label(self.content,style='Muted.TLabel',wraplength=850)
        self.local_meta.pack(anchor='w')
        bottom=ttk.Frame(self.content);bottom.pack(fill='x',pady=10)
        verse=tk.StringVar(value='1')
        ttk.Label(bottom,text='Versículo').pack(side='left')
        ttk.Entry(bottom,textvariable=verse,width=5).pack(side='left',padx=4)
        def favorite():
            try:
                v=int(verse.get());data=self.local_bibles[self.local_version.get()]
                if str(v) not in data['books'][self.local_book.get()]['chapters'][self.local_chapter.get()]:raise ValueError()
            except ValueError:
                messagebox.showerror('Favorito','Informe um versículo deste capítulo.',parent=self);return
            args=(self.local_version.get(),self.local_book.get(),int(self.local_chapter.get()),v)
            with self.store.conn:
                if self.store.conn.execute('SELECT 1 FROM bible_marks WHERE version=? AND book=? AND chapter=? AND verse=?',args).fetchone():
                    self.store.conn.execute('DELETE FROM bible_marks WHERE version=? AND book=? AND chapter=? AND verse=?',args)
                else:self.store.conn.execute('INSERT INTO bible_marks VALUES(?,?,?,?)',args)
            self.show_local_chapter()
        ttk.Button(bottom,text='Marcar / desmarcar favorito',command=favorite).pack(side='left')
        query=tk.StringVar();ttk.Entry(bottom,textvariable=query,width=22).pack(side='left',padx=8)
        def results(favorites=False):
            data=self.local_bibles[self.local_version.get()]
            found=search(data,query.get()) if not favorites else [(r['book'],r['chapter'],r['verse'],'Favorito') for r in self.store.conn.execute('SELECT * FROM bible_marks WHERE version=?',(self.local_version.get(),))]
            window=tk.Toplevel(self);window.title('Diolino · Resultados');window.geometry('760x450')
            listing=tk.Listbox(window,font=('Segoe UI',11));listing.pack(fill='both',expand=True)
            for b,c,v,text in found:listing.insert('end',f"{data['books'][b]['name']} {c}:{v} · {text[:110]}")
            def open_result(event=None):
                if not listing.curselection():return
                b,c,v,_=found[listing.curselection()[0]]
                self.local_book_combo.current(self.local_codes.index(b));chapters()
                self.local_chapter.set(str(c));self.show_local_chapter();window.destroy()
            listing.bind('<Double-1>',open_result)
            ttk.Button(window,text='Abrir passagem selecionada',command=open_result).pack(pady=8)
            from appearance import refresh_widget
            refresh_widget(window)
        ttk.Button(bottom,text='Pesquisar',command=results).pack(side='left')
        ttk.Button(bottom,text='Favoritos',command=lambda:results(True)).pack(side='left',padx=4)
        books()

    def show_local_chapter(self):
        if not hasattr(self,'local_text') or not self.local_text.winfo_exists():return
        version,b,c=self.local_version.get(),self.local_book.get(),self.local_chapter.get()
        data=self.local_bibles[version]
        marks={str(r[0]) for r in self.store.conn.execute('SELECT verse FROM bible_marks WHERE version=? AND book=? AND chapter=?',(version,b,int(c)))}
        self.local_text.configure(state='normal',font=('Georgia',self.local_size.get()),spacing3=self.local_spacing.get())
        self.local_text.delete('1.0','end')
        for v,text in data['books'][b]['chapters'][c].items():self.local_text.insert('end',('★ ' if v in marks else '')+v+'  '+text+'\n\n')
        self.local_text.configure(state='disabled')
        self.local_meta.configure(text=data['name']+' · '+data['language']+' · '+data['license']+'\n'+data['source']+'\n'+data.get('status',''))
        preference(self.store,'bible_position',value=dict(version=version,book=b,chapter=c))
        preference(self.store,'bible_font',value=self.local_size.get())
        preference(self.store,'bible_spacing',value=self.local_spacing.get())

    def import_translation(self):
        path=filedialog.askopenfilename(parent=self,filetypes=[('Tradução Diolino JSON','*.json')])
        if not path:return
        try:
            data=read_translation(path)
            if not messagebox.askyesno('Condições de uso',data['name']+'\nLicença declarada: '+data['license']+'\n\nConfirma que possui autorização para armazenar esta cópia local?',parent=self):return
            folder=self.store.directory/'bibles';folder.mkdir(exist_ok=True)
            target=folder/(data['id']+'.json')
            if data['id'] in installed(self.store.directory):raise ValueError('Esta identificação já está instalada. Use outra identificação para uma edição diferente.')
            target.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
            self.render()
        except (OSError,ValueError,TypeError,AttributeError) as exc:
            messagebox.showerror('Importação não concluída',str(exc),parent=self)
