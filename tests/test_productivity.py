import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from PIL import Image,ImageDraw,ImageFont
from pypdf import PdfWriter,PdfReader
from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
from storage import Store
from workspace_data import save_note
from unified_search import SearchIndex
from review_cards import save_card,cards,rate_card,get_card,archive_card
from protected_backup import create_protected_backup,restore_protected_backup,decrypt_backup
from document_tools import extract_pdf,extract_pages,merge_pdfs,page_numbers,recognize_image
from fsrs import Card


class ProductivityTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory(dir='test-output');self.root=Path(self.folder.name)
        self.store=Store(self.root/'data')

    def tearDown(self):self.store.close();self.folder.cleanup()

    def test_anki_transaction_and_retention(self):
        from io import StringIO
        from review_cards import export_anki_tsv, import_anki_tsv, retention_target
        with self.assertRaises(ValueError):
            import_anki_tsv(self.store, StringIO('A\tB\ninvalid'), 'Medicina')
        self.assertEqual(cards(self.store), [])
        save_card(self.store, 'A', 'B\nC')
        output = StringIO()
        export_anki_tsv(cards(self.store), output)
        output.seek(0)
        self.assertEqual(import_anki_tsv(self.store, output, 'Pessoal'), 1)
        output.seek(0)
        self.assertEqual(import_anki_tsv(self.store, output, 'Pessoal'), 0)
        retention_target(self.store, 85)
        with self.assertRaises(ValueError):
            retention_target(self.store, 100)
        self.assertEqual(retention_target(self.store), 85)

    def study(self,topic='Cardiologia'):
        return self.store.save('study',dict(date='2026-11-04',topic=topic,duration_min=25,format='Leitura'))

    def pdf(self,path,pages=1):
        writer=PdfWriter()
        for _ in range(pages):
            page=writer.add_blank_page(300,200)
            font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
            page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
            stream=DecodedStreamObject();stream.set_data(b'BT /F1 14 Tf 30 100 Td (Diolino PDF de teste) Tj ET')
            page[NameObject('/Contents')]=writer._add_object(stream)
        with path.open('wb') as file:writer.write(file)

    def test_global_search_accent_typo_deleted_and_external_changes(self):
        rid=self.study();save_note(self.store,'Reflexão','2026-11-04','Conteúdo de João e hábitos')
        index=SearchIndex(self.store)
        try:
            self.assertEqual(index.search('reflexao')[0]['kind'],'notebook')
            self.assertTrue(any(r['id']==rid and r['kind']=='study' for r in index.search('cardilogia')))
            self.store.delete('study',rid)
            self.assertFalse(any(r['kind']=='study' for r in index.search('cardiologia')))
            other=Store(self.store.directory)
            try:other.save('study',dict(date='2026-11-04',topic='Nefrologia',duration_min=20,format='Vídeo'))
            finally:other.close()
            self.assertTrue(any(r['title']=='Nefrologia' for r in index.search('nefrologia')))
            self.assertEqual(index.search('" OR 1=1 --'),[])
            saved=self.store.backup()
            self.study('Dermatologia')
            self.assertTrue(any(r['title']=='Dermatologia' for r in index.search('dermatologia')))
            self.store.restore(saved)
            self.assertFalse(any(r['title']=='Dermatologia' for r in index.search('dermatologia')))
        finally:index.close()

    def test_fsrs_due_review_revision_archive_and_backup(self):
        card=save_card(self.store,'Pergunta','Resposta','Medicina',source='Material pessoal')
        self.assertEqual(len(cards(self.store,True)),1)
        now=datetime.now(timezone.utc)+timedelta(seconds=1)
        reviewed=rate_card(self.store,card['id'],3,card['revision'],now)
        self.assertGreater(Card.from_json(reviewed['schedule']).due,now)
        with self.assertRaises(ValueError):rate_card(self.store,card['id'],3,card['revision'],now)
        self.assertEqual(self.store.rows('study'),[])
        backup=self.store.backup()
        archive_card(self.store,card['id'],reviewed['revision']);self.assertEqual(cards(self.store),[])
        self.store.restore(backup);self.assertEqual(len(cards(self.store)),1)
        self.assertEqual(get_card(self.store,card['id'])['revision'],reviewed['revision'])

    def test_fsrs_edit_preserves_schedule_and_invalid_card_does_not_write(self):
        card=save_card(self.store,'Q','A')
        edited=save_card(self.store,'Q2','A2',key=card['id'],expected=card['revision'])
        self.assertEqual(edited['schedule'],card['schedule'])
        with self.assertRaises(ValueError):save_card(self.store,'','A')
        self.assertEqual(len(cards(self.store)),1)

    def test_encrypted_backup_roundtrip_wrong_password_tampering_and_exclusive_output(self):
        rid=self.study();save_card(self.store,'Q','A')
        path=self.root/'copy.diolinobak';password='Uma senha de teste 123'
        create_protected_backup(self.store,path,password)
        self.assertNotIn(b'Cardiologia',path.read_bytes());self.assertNotIn(b'SQLite format',path.read_bytes())
        with self.assertRaises(FileExistsError):create_protected_backup(self.store,path,password)
        self.store.delete('study',rid)
        with self.assertRaises(ValueError):restore_protected_backup(self.store,path,'outra senha incorreta')
        self.assertEqual(self.store.rows('study'),[])
        safety=restore_protected_backup(self.store,path,password)
        self.assertTrue(Path(safety).exists());self.assertEqual(len(self.store.rows('study')),1);self.assertEqual(len(cards(self.store)),1)
        broken=bytearray(path.read_bytes());broken[-1]^=1
        modified=self.root/'modified.diolinobak';modified.write_bytes(broken)
        with self.assertRaises(ValueError):decrypt_backup(modified,password)
        with self.assertRaises(ValueError):create_protected_backup(self.store,self.root/'short.diolinobak','curta')

    def test_pdf_text_merge_extract_and_preserve_inputs(self):
        a,b=self.root/'a.pdf',self.root/'b.pdf';self.pdf(a,2);self.pdf(b)
        original=a.read_bytes()
        self.assertIn('Diolino PDF de teste',extract_pdf(a))
        merged=self.root/'merged.pdf';merge_pdfs([a,b],merged)
        self.assertEqual(len(PdfReader(merged).pages),3)
        output=self.root/'pages.pdf';extract_pages(merged,'3,1-2',output)
        self.assertEqual(len(PdfReader(output).pages),3)
        with self.assertRaises(ValueError):page_numbers('0,5',3)
        with self.assertRaises(FileExistsError):extract_pages(a,'1',a)
        self.assertEqual(a.read_bytes(),original)
        protected=self.root/'password.pdf';writer=PdfWriter();writer.add_blank_page(100,100);writer.encrypt('test-password')
        with protected.open('wb') as file:writer.write(file)
        with self.assertRaises(ValueError):extract_pdf(protected)

    def test_real_portuguese_english_ocr_offline(self):
        image=Image.new('RGB',(1500,220),'white');draw=ImageDraw.Draw(image)
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',48)
        draw.text((30,60),'Diolino teste de reconhecimento 2026',font=font,fill='black')
        path=self.root/'ocr.png';image.save(path)
        text=recognize_image(path)
        self.assertIn('Diolino',text);self.assertIn('2026',text)
        self.assertEqual(self.store.conn.execute('SELECT COUNT(*) FROM notebook').fetchone()[0],0)

    def test_ui_panels_do_not_write_personal_records_on_open(self):
        from app import App
        app=App(self.store);app.withdraw()
        try:
            app.show_global_search();app.show_review_cards();app.review_session();app.edit_review_card();app.show_document_tools()
            app.update_idletasks()
            self.assertEqual(cards(self.store),[])
            self.assertEqual(self.store.rows('study'),[])
            app.navigate('data');app.update_idletasks()
            app.navigate('studies');app.update_idletasks()
        finally:app.shutdown()


if __name__=='__main__':unittest.main()
