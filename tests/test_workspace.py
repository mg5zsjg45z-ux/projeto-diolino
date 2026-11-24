import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import App
from storage import Store
from workspace_data import save_note, notes, delete_note, module_states, set_modules
from desktop_workspace import NoteEditor
from appearance import PALETTES, DEFAULTS, save_preferences, load_preferences
from offline_bible import read_translation, search, validate_translation


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='test-output')
        self.store=Store(self.temp.name)

    def tearDown(self):
        self.store.close();self.temp.cleanup()

    def test_notes_reopen_search_soft_delete_backup_restore(self):
        rid=save_note(self.store,'Consulta','2026-10-26','Texto pessoal',[dict(tag='bold',start=0,end=5)],labels='rotina',favorite=True)
        self.assertEqual(notes(self.store,'PESSOAL','2026')[0]['id'],rid)
        backup=self.store.backup()
        delete_note(self.store,rid)
        self.assertEqual(notes(self.store),[])
        self.store.restore(backup)
        self.store.close();self.store=Store(self.temp.name)
        restored=notes(self.store)[0]
        self.assertEqual(json.loads(restored['formatting'])[0]['tag'],'bold')
        self.assertTrue(restored['favorite'])
        with self.assertRaises(ValueError):save_note(self.store,'x','bad','y')

    def test_modules_hide_without_data_loss_and_essential_locked(self):
        rid=save_note(self.store,'Nota','2026-10-26','Conteúdo')
        set_modules(self.store,dict(notebook=False,home=False,agenda=False))
        self.store.close();self.store=Store(self.temp.name)
        self.assertFalse(module_states(self.store)['notebook'])
        self.assertTrue(module_states(self.store)['home'])
        set_modules(self.store,dict(notebook=True))
        self.assertEqual(notes(self.store)[0]['id'],rid)

    def test_every_theme_persists(self):
        for key in PALETTES:
            save_preferences(self.temp.name,dict(DEFAULTS,theme=key))
            self.assertEqual(load_preferences(self.temp.name)['theme'],key)

    def test_editor_delete_requires_confirmation_and_cancels_autosave(self):
        rid=save_note(self.store,'Nota de teste','2026-10-26','Conteúdo')
        app=App(self.store);app.withdraw()
        try:
            editor=NoteEditor(app,rid)
            editor.title_var.set('Edição pendente')
            editor.delete()
            self.assertEqual(len(notes(self.store)),1)
            editor.confirm_delete()
            self.assertEqual(notes(self.store),[])
        finally:app.destroy()

    def test_list_delete_and_compact_editor_actions(self):
        from tkinter import ttk
        rid=save_note(self.store,'Nota de teste','2026-10-26','Conteúdo')
        app=App(self.store);app.day.set('2026-10-26');app.navigate('notebook')
        def buttons(parent):
            return [child for child in parent.winfo_children() if isinstance(child,ttk.Button)]+[b for child in parent.winfo_children() for b in buttons(child)]
        try:
            app.notebook_tree.selection_set(str(rid))
            next(b for b in buttons(app.content) if b.cget('text')=='Excluir selecionada').invoke()
            self.assertEqual(len(notes(self.store)),1)
            next(b for b in buttons(app.content) if b.cget('text')=='Confirmar exclusão').invoke()
            self.assertEqual(notes(self.store),[])
            editor=NoteEditor(app);editor.geometry('600x480');app.update()
            delete=next(b for b in buttons(editor) if b.cget('text')=='Excluir')
            self.assertTrue(delete.winfo_ismapped())
            editor.destroy()
        finally:app.destroy()

    def test_official_bible_search_and_validation(self):
        data=read_translation('data/bibles/BPM.json')
        self.assertEqual(len(data['books']),81)
        self.assertIn('Deus amou',data['books']['JHN']['chapters']['3']['16'])
        self.assertTrue(search(data,'Deus amou'))
        with self.assertRaises(ValueError):validate_translation(dict(id='../escape'))
        malformed=dict(data,books={'A':{'name':'Livro','chapters':{'0':{'1':'texto'}}}})
        with self.assertRaises(ValueError):validate_translation(malformed)

    def test_interface_offline_autosave_calendar_modules_and_themes(self):
        with patch('socket.socket.connect',side_effect=OSError('Offline')):
            app=App(self.store);app.withdraw()
            try:
                app.day.set('2026-10-26')
                editor=NoteEditor(app)
                editor.title_var.set('Caderno');editor.text.insert('1.0','Anotação automática')
                editor.text.edit_modified(True);editor.modified();editor.autosave()
                self.assertFalse(editor.dirty)
                editor.close()
                for page in ['agenda','notebook','modules','offline_bible','bible_online']:
                    app.navigate(page);app.update_idletasks()
                self.assertEqual(app.local_version.get(),'BPM')
                for key in PALETTES:
                    app.appearance.activate(dict(DEFAULTS,theme=key));app.update_idletasks()
                    self.assertEqual(app.appearance.palette,PALETTES[key])
                app.navigate('modules')
                set_modules(self.store,dict(agenda=False))
                app.render()
                self.assertFalse(app.nav_buttons['agenda'][0].winfo_manager())
            finally:
                app.destroy()
        self.assertEqual(notes(self.store)[0]['body'],'Anotação automática')

if __name__=='__main__':unittest.main()
