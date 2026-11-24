"""Search, FSRS review, protected backups and local document tools."""
import queue
import threading
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import ttk, messagebox, filedialog
from appearance import refresh_widget
from theme import BG


def panel(app,title,size='880x700'):
    win=tk.Toplevel(app);win.title(title+' • Diolino');win.geometry(size);win.minsize(600,520);win.configure(bg=BG)
    body=ttk.Frame(win,padding=20);body.pack(fill='both',expand=True)
    ttk.Label(body,text=title,style='Title.TLabel').pack(anchor='w',pady=(0,12))
    return win,body


def text_area(parent,height=5):
    box=ttk.Frame(parent);box.pack(fill='both',expand=True,pady=6)
    text=tk.Text(box,height=height,wrap='word',undo=True)
    scrollbar=ttk.Scrollbar(box,command=text.yview);text.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side='right',fill='y');text.pack(side='left',fill='both',expand=True)
    return text


def background(app,work,on_success):
    """Workers never touch Tk or the app's SQLite connection."""
    win,body=panel(app,'Processando…','620x520')
    ttk.Label(body,text='Você pode continuar usando o aplicativo. Aguarde a conclusão.',wraplength=550).pack(anchor='w')
    progress=ttk.Progressbar(body,mode='indeterminate');progress.pack(fill='x',pady=20);progress.start()
    result=queue.Queue()
    def worker():
        try:result.put((True,work()))
        except Exception as exc:result.put((False,str(exc)))
    threading.Thread(target=worker,daemon=True).start()
    # Closing hides progress; a completed result still returns to the UI.
    win.protocol('WM_DELETE_WINDOW',win.withdraw)
    job=None
    def cancel(event):
        nonlocal job
        if event.widget is app and job:
            app.after_cancel(job);job=None
    app.bind('<Destroy>',cancel,add='+')
    def poll():
        nonlocal job
        try:ok,value=result.get_nowait()
        except queue.Empty:
            job=app.after(100,poll);return
        job=None
        win.destroy()
        if ok:
            try:on_success(value)
            except Exception as exc:messagebox.showerror('Operação não concluída',str(exc),parent=app)
        else:messagebox.showerror('Operação não concluída',value,parent=app)
    job=app.after(100,poll)


class ProductivityViews:
    def show_global_search(self,event=None):
        from unified_search import SearchIndex
        win,body=panel(self,'Buscar em tudo')
        query=tk.StringVar();entry=ttk.Entry(body,textvariable=query);entry.pack(fill='x');entry.focus_set()
        ttk.Label(body,text='Notas, estudos, planos, agenda e registros locais. Resultados aproximados toleram erros de digitação.',wraplength=800).pack(anchor='w',pady=8)
        tree=ttk.Treeview(body,columns=('area','date','title'),show='headings',height=8)
        for key,title,width in [('area','Área',170),('date','Data',110),('title','Resultado',460)]:
            tree.heading(key,text=title);tree.column(key,width=width)
        tree.pack(fill='both',expand=True)
        details=text_area(body,4);status=tk.StringVar(value='Digite para pesquisar.');ttk.Label(body,textvariable=status).pack(anchor='w')
        index=SearchIndex(self.store);results=[];pending=None
        def run():
            nonlocal results,pending
            pending=None
            try:results=index.search(query.get())
            except Exception as exc:status.set(str(exc));return
            tree.delete(*tree.get_children())
            for i,row in enumerate(results):tree.insert('', 'end',iid=str(i),values=(row['label'],row['date'],row['title']+(' · aproximado' if row['approximate'] else '')))
            status.set(f'{len(results)} resultado(s). Atualize a pesquisa após editar registros.')
            if results:tree.selection_set('0');show()
        def changed(*args):
            nonlocal pending
            if pending:win.after_cancel(pending)
            pending=win.after(180,run)
        def selected():
            return results[int(tree.selection()[0])] if tree.selection() else None
        def show(event=None):
            row=selected();details.configure(state='normal');details.delete('1.0','end')
            if row:details.insert('end',row['text'])
            details.configure(state='disabled')
        def open_result(event=None):
            row=selected()
            if not row:return
            if row['kind']=='notebook':
                from desktop_workspace import NoteEditor
                NoteEditor(self,row['id'])
            else:
                record=self.store.get(row['kind'],row['id'])
                if record:self.open_editor(row['kind'],record)
                else:status.set('Este registro foi excluído. Atualize a pesquisa.')
        def new_card():
            row=selected()
            if row:self.edit_review_card(question='',answer=row['text'][:20000],source=f"{row['label']} · {row['title']}"[:1000])
        tree.bind('<<TreeviewSelect>>',show);tree.bind('<Double-1>',open_result);entry.bind('<Return>',lambda e:run())
        actions=ttk.Frame(body);actions.pack(fill='x',pady=10)
        ttk.Button(actions,text='Abrir registro',command=open_result).pack(side='left')
        ttk.Button(actions,text='Criar cartão a partir do resultado',command=new_card).pack(side='left',padx=8)
        ttk.Button(actions,text='Atualizar busca',command=run).pack(side='left')
        query.trace_add('write',changed)
        def close(event=None):
            nonlocal pending
            if event is not None and event.widget is not win:return
            if pending:win.after_cancel(pending);pending=None
            index.close()
        win.bind('<Destroy>',close,add='+');refresh_widget(win)
        return 'break'

    def edit_review_card(self,record=None,question='',answer='',source='',on_saved=None):
        from review_cards import save_card
        win,body=panel(self,'Editar cartão' if record else 'Novo cartão de revisão')
        area=tk.StringVar(value=(record or {}).get('area','Medicina'))
        ttk.Label(body,text='Área').pack(anchor='w');ttk.Combobox(body,textvariable=area,values=['Medicina','Bíblia','Pessoal'],state='readonly').pack(fill='x')
        ttk.Label(body,text='Pergunta · escreva o que deseja recordar').pack(anchor='w',pady=(12,0));front=text_area(body,3)
        front.insert('1.0',(record or {}).get('question',question))
        ttk.Label(body,text='Resposta · confira o conteúdo antes de salvar').pack(anchor='w');back=text_area(body,7)
        back.insert('1.0',(record or {}).get('answer',answer))
        origin=tk.StringVar(value=(record or {}).get('source',source));ttk.Label(body,text='Fonte / referência, se houver').pack(anchor='w')
        ttk.Entry(body,textvariable=origin).pack(fill='x')
        ttk.Label(body,text='Revisar cartões não cria minutos de estudo nem confirma os pilares.',wraplength=780).pack(anchor='w',pady=10)
        def save():
            try:save_card(self.store,front.get('1.0','end-1c'),back.get('1.0','end-1c'),area.get(),
                          key=record['id'] if record else None,expected=record['revision'] if record else None,source=origin.get())
            except Exception as exc:messagebox.showerror('Cartão não salvo',str(exc),parent=win);return
            win.destroy();self.set_status('Cartão salvo para revisão espaçada.')
            if on_saved:on_saved()
        ttk.Button(body,text='Salvar cartão',style='Accent.TButton',command=save).pack(anchor='e',pady=8)
        refresh_widget(win)

    def show_review_cards(self):
        from review_cards import cards,archive_card
        from fsrs import Card
        win,body=panel(self,'Cartões de revisão')
        area=tk.StringVar(value='Todas');ttk.Label(body,text='Área').pack(anchor='w')
        combo=ttk.Combobox(body,textvariable=area,values=['Todas','Medicina','Bíblia','Pessoal'],state='readonly');combo.pack(anchor='w')
        summary=tk.StringVar();ttk.Label(body,textvariable=summary).pack(anchor='w',pady=10)
        tree=ttk.Treeview(body,columns=('area','question','due'),show='headings')
        for key,title,width in [('area','Área',100),('question','Pergunta',460),('due','Próxima revisão',200)]:tree.heading(key,text=title);tree.column(key,width=width)
        tree.pack(fill='both',expand=True);data={}
        def refresh(event=None):
            if not win.winfo_exists():return
            data.clear();tree.delete(*tree.get_children())
            for row in cards(self.store):
                if area.get()!='Todas' and row['area']!=area.get():continue
                data[row['id']]=row
                due=Card.from_json(row['schedule']).due.astimezone().strftime('%d/%m/%Y %H:%M')
                tree.insert('', 'end',iid=row['id'],values=(row['area'],row['question'].replace('\n',' ')[:180],due))
            pending=[r for r in cards(self.store,True) if area.get()=='Todas' or r['area']==area.get()]
            summary.set(f'{len(data)} cartão(ões) · {len(pending)} revisão(ões) pendente(s) agora')
        def selected():return data.get(tree.selection()[0]) if tree.selection() else None
        def edit():
            row=selected()
            if row:self.edit_review_card(record=row,on_saved=refresh)
        def archive():
            row=selected()
            if row and messagebox.askyesno('Arquivar cartão','Retirar este cartão da fila? O histórico será preservado no backup.',parent=win):
                try:archive_card(self.store,row['id'],row['revision']);refresh()
                except Exception as exc:messagebox.showerror('Cartão não arquivado',str(exc),parent=win)
        actions=ttk.Frame(body);actions.pack(fill='x',pady=12)
        for label,command in [('Novo cartão',lambda:self.edit_review_card(on_saved=refresh)),('Editar',edit),('Arquivar',archive),('Revisar pendentes',lambda:self.review_session(area.get(),refresh)),('Atualizar',refresh)]:ttk.Button(actions,text=label,command=command).pack(side='left',padx=(0,6))
        combo.bind('<<ComboboxSelected>>',refresh);refresh();refresh_widget(win)

    def review_session(self,area='Todas',on_review=None):
        from review_cards import cards,rate_card
        win,body=panel(self,'Revisão espaçada')
        caption=tk.StringVar();ttk.Label(body,textvariable=caption).pack(anchor='w')
        front=text_area(body,5);answer=text_area(body,7);current=None;revealed=False
        actions=ttk.Frame(body);actions.pack(fill='x',pady=10);rating_buttons=[]
        def load():
            nonlocal current,revealed
            queue_cards=[r for r in cards(self.store,True) if area=='Todas' or r['area']==area]
            current=queue_cards[0] if queue_cards else None;revealed=False
            front.configure(state='normal');front.delete('1.0','end');answer.configure(state='normal');answer.delete('1.0','end')
            if current:front.insert('end',current['question']);caption.set(f"{current['area']} · {len(queue_cards)} pendente(s)")
            else:caption.set('Não há revisões pendentes agora.');front.insert('end','Volte no horário indicado na lista de cartões.')
            front.configure(state='disabled');answer.configure(state='disabled')
            reveal.configure(state='normal' if current else 'disabled')
            for button in rating_buttons:button.configure(state='disabled')
        def show_answer():
            nonlocal revealed
            if not current:return
            answer.configure(state='normal');answer.insert('end',current['answer']+'\n\nFonte: '+current.get('source',''));answer.configure(state='disabled');revealed=True
            reveal.configure(state='disabled')
            for button in rating_buttons:button.configure(state='normal')
        def rate(value):
            if not current or not revealed:return
            try:rate_card(self.store,current['id'],value,current['revision'])
            except Exception as exc:messagebox.showerror('Revisão não salva',str(exc),parent=win);load();return
            if on_review:on_review()
            load()
        reveal=ttk.Button(actions,text='Mostrar resposta',command=show_answer);reveal.pack(side='left',padx=(0,10))
        for value,label in [(1,'Esqueci'),(2,'Difícil'),(3,'Bom'),(4,'Fácil')]:
            button=ttk.Button(actions,text=label,command=lambda v=value:rate(v));button.pack(side='left',padx=3);rating_buttons.append(button)
        load();refresh_widget(win)

    def password_dialog(self,title,creating,on_submit):
        win,body=panel(self,title,'650x540')
        ttk.Label(body,text='A senha não será salva. Sem ela, não será possível recuperar este backup.',wraplength=570).pack(anchor='w',pady=10)
        value=tk.StringVar();confirm=tk.StringVar()
        ttk.Label(body,text='Senha · mínimo de 12 caracteres para criar').pack(anchor='w');entry=ttk.Entry(body,textvariable=value,show='•');entry.pack(fill='x',pady=8)
        if creating:
            ttk.Label(body,text='Repita a senha').pack(anchor='w');ttk.Entry(body,textvariable=confirm,show='•').pack(fill='x',pady=8)
        def submit():
            password=value.get()
            if not password or (creating and (len(password)<12 or password!=confirm.get())):
                messagebox.showerror('Confira a senha','Informe a senha. Ao criar, use pelo menos 12 caracteres e repita a mesma senha.',parent=win);return
            value.set('');confirm.set('');win.destroy();on_submit(password)
        ttk.Button(body,text='Continuar',style='Accent.TButton',command=submit).pack(anchor='e',pady=12);entry.focus_set();refresh_widget(win)

    def export_protected_backup(self):
        from protected_backup import serialize_backup,encrypt_payload
        path=filedialog.asksaveasfilename(parent=self,title='Salvar backup protegido',defaultextension='.diolinobak',initialfile=f'diolino-protegido-{date.today()}.diolinobak',filetypes=[('Backup protegido Diolino','*.diolinobak')])
        if not path:return
        def start(password):
            payload=serialize_backup(self.store)
            background(self,lambda:encrypt_payload(payload,path,password),lambda result:messagebox.showinfo('Backup protegido criado',str(result)+'\n\nGuarde a senha separadamente. O banco em uso e os backups automáticos locais continuam sem criptografia própria.',parent=self))
        self.password_dialog('Proteger backup por senha',True,start)

    def import_protected_backup(self):
        from protected_backup import decrypt_backup,restore_payload
        path=filedialog.askopenfilename(parent=self,title='Restaurar backup protegido',filetypes=[('Backup protegido Diolino','*.diolinobak')])
        if not path:return
        def decrypted(payload):
            if not messagebox.askyesno('Substituir dados locais','Restaurar este backup? Os dados atuais serão substituídos, com uma cópia de segurança local anterior.',parent=self):return
            if not self.pause_site_for_restore():return
            from desktop_workspace import NoteEditor
            for window in list(self.winfo_children()):
                if isinstance(window,NoteEditor) and not window.save():return
            self.pomodoro.pause()
            safety=restore_payload(self.store,payload)
            # Reload auxiliary state, which is part of the restored database.
            from pomodoro import Pomodoro
            self.pomodoro=Pomodoro(self.store)
            if self.pomodoro_window and self.pomodoro_window.winfo_exists():self.pomodoro_window.destroy()
            self.pomodoro_window=None
            self.render();messagebox.showinfo('Backup restaurado','Cópia anterior preservada em:\n'+str(safety),parent=self)
        self.password_dialog('Abrir backup protegido',False,lambda password:background(self,lambda:decrypt_backup(path,password),decrypted))

    def show_document_tools(self):
        from document_tools import extract_pdf,extract_pages,merge_pdfs,recognize_image
        win,body=panel(self,'PDF e reconhecimento de texto','940x780')
        ttk.Label(body,text='Processamento local, sem enviar documentos à internet. PDFs: até 20 MiB e 200 páginas. Imagens: até 20 MiB e 40 MP.',wraplength=850).pack(anchor='w')
        actions=ttk.Frame(body);actions.pack(fill='x',pady=12)
        status=tk.StringVar(value='Abra um PDF para extrair texto ou uma imagem para OCR.');ttk.Label(body,textvariable=status,wraplength=850).pack(anchor='w')
        output=text_area(body,18)
        def display(text):
            if not win.winfo_exists():return
            output.delete('1.0','end');output.insert('end',text)
            status.set('Confira o texto antes de salvar. PDFs digitalizados podem exigir OCR das imagens; este painel não converte páginas de PDF em imagens.')
        def choose_pdf():return filedialog.askopenfilename(parent=win,title='Escolher PDF',filetypes=[('PDF','*.pdf')])
        def read():
            path=choose_pdf()
            if path:background(self,lambda:extract_pdf(path),display)
        def ocr():
            path=filedialog.askopenfilename(parent=win,title='Escolher imagem',filetypes=[('Imagens','*.png *.jpg *.jpeg *.tif *.tiff *.bmp')])
            if path:background(self,lambda:recognize_image(path),display)
        def combine():
            paths=filedialog.askopenfilenames(parent=win,title='Selecionar PDFs para combinar',filetypes=[('PDF','*.pdf')])
            if len(paths)<2:return
            order,frame=panel(self,'Conferir ordem dos PDFs','700x540');items=list(paths)
            listing=tk.Listbox(frame,height=10);listing.pack(fill='both',expand=True)
            def redraw():listing.delete(0,'end');[listing.insert('end',Path(p).name) for p in items]
            def move(step):
                if not listing.curselection():return
                i=listing.curselection()[0];j=i+step
                if 0<=j<len(items):items[i],items[j]=items[j],items[i];redraw();listing.selection_set(j)
            def save():
                destination=filedialog.asksaveasfilename(parent=order,title='Salvar PDF combinado',defaultextension='.pdf',filetypes=[('PDF','*.pdf')])
                if destination:
                    selected=list(items);order.destroy();background(self,lambda:merge_pdfs(selected,destination),lambda result:messagebox.showinfo('PDF criado',str(result),parent=self))
            row=ttk.Frame(frame);row.pack(fill='x',pady=10)
            for label,command in [('Subir',lambda:move(-1)),('Descer',lambda:move(1)),('Combinar nesta ordem',save)]:ttk.Button(row,text=label,command=command).pack(side='left',padx=4)
            redraw();refresh_widget(order)
        def split():
            path=choose_pdf()
            if not path:return
            dialog,frame=panel(self,'Extrair páginas','650x520');expression=tk.StringVar()
            ttk.Label(frame,text='Páginas, na ordem desejada: por exemplo 1,3-5').pack(anchor='w');ttk.Entry(frame,textvariable=expression).pack(fill='x',pady=10)
            def save():
                destination=filedialog.asksaveasfilename(parent=dialog,title='Salvar páginas',defaultextension='.pdf',filetypes=[('PDF','*.pdf')])
                if destination:
                    value=expression.get();dialog.destroy();background(self,lambda:extract_pages(path,value,destination),lambda result:messagebox.showinfo('PDF criado',str(result),parent=self))
            ttk.Button(frame,text='Extrair para novo PDF',command=save).pack(anchor='w');refresh_widget(dialog)
        for label,command in [('Extrair texto de PDF',read),('Reconhecer imagem (OCR)',ocr),('Combinar PDFs',combine),('Extrair páginas',split)]:ttk.Button(actions,text=label,command=command).pack(side='left',padx=(0,6))
        def save_note():
            text=output.get('1.0','end-1c')
            if not text.strip():return
            from tkinter import simpledialog
            from workspace_data import save_note as persist_note
            title=simpledialog.askstring('Salvar texto revisado','Título da anotação:',parent=win)
            if title is None:return
            try:
                persist_note(self.store,title,date.today().isoformat(),text)
                self.set_status('Texto revisado salvo nas anotações.')
            except Exception as exc:messagebox.showerror('Anotação não salva',str(exc),parent=win)
        def save_text():
            destination=filedialog.asksaveasfilename(parent=win,title='Salvar texto revisado',defaultextension='.txt',filetypes=[('Texto UTF-8','*.txt')])
            if destination:
                try:
                    with Path(destination).open('x',encoding='utf-8') as file:file.write(output.get('1.0','end-1c'))
                except Exception as exc:messagebox.showerror('Texto não salvo',str(exc),parent=win)
        footer=ttk.Frame(body);footer.pack(fill='x',pady=10)
        ttk.Button(footer,text='Salvar como anotação',command=save_note).pack(side='left')
        ttk.Button(footer,text='Salvar texto em arquivo',command=save_text).pack(side='left',padx=8)
        ttk.Button(footer,text='Preparar cartão de revisão',command=lambda:self.edit_review_card(answer=output.get('1.0','end-1c')[:20000],source='Texto de documento revisado')).pack(side='left')
        refresh_widget(win)
