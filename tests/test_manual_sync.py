import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from storage import Store
from manual_sync import export_file, load_file, preview, apply_file, snapshot, reconcile
from workspace_data import save_note


class ManualSyncTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir='test-output')
        self.root = Path(self.folder.name)
        self.a, self.b = Store(self.root/'a'), Store(self.root/'b')
        self.sequence = 0

    def tearDown(self):
        self.a.close(); self.b.close(); self.folder.cleanup()

    def exported(self, store):
        self.sequence += 1
        path = self.root/f'file-{self.sequence}.json'
        export_file(store, path)
        return load_file(path)

    def transfer(self, source, target, choices=None):
        data = self.exported(source)
        plan = preview(target, data)
        result = apply_file(target, data, plan['base'], choices)
        self.assertTrue(Path(result['backup']).exists())
        return plan, result

    def study(self, store, topic='Cardiologia', minutes=25):
        return store.save('study', dict(date='2026-11-04',time='10:00',topic=topic,duration_min=minutes,format='Leitura'))

    def test_collision_roundtrip_reference_and_repeat(self):
        self.study(self.a, 'A'); self.study(self.b, 'B')
        plan = self.a.save('plans',dict(title='Plano',area='Medicina',status='Ativo',priority='Normal'))
        self.a.save('plan_steps',dict(plan_id=plan,title='Etapa',state='A fazer',priority='Normal'))
        self.b.save('plans',dict(title='Outro',area='Pessoal',status='Ativo',priority='Normal'))
        self.transfer(self.a,self.b)
        self.assertEqual(len(self.b.rows('study')),2)
        step=self.b.rows('plan_steps')[0]
        self.assertEqual(self.b.get('plans',step['plan_id'])['title'],'Plano')
        self.transfer(self.b,self.a)
        self.transfer(self.a,self.b)
        self.assertEqual(len(self.a.rows('study')),2)
        self.assertEqual(len(self.b.rows('plan_steps')),1)

    def test_conflicts_keep_or_replace_and_stale_preview(self):
        rid=self.study(self.a)
        self.transfer(self.a,self.b)
        self.study(self.b,'Outro')
        self.a.save('study',dict(date='2026-11-04',time='10:00',topic='Cardiologia',duration_min=40,format='Vídeo'),rid)
        data=self.exported(self.a); plan=preview(self.b,data)
        self.assertEqual(plan['counts']['conflicts'],1)
        apply_file(self.b,data,plan['base'])
        self.assertEqual(next(r for r in self.b.rows('study') if r['topic']=='Cardiologia')['duration_min'],25)
        plan=preview(self.b,data)
        apply_file(self.b,data,plan['base'],{plan['conflicts'][0]['key']:'incoming'})
        self.assertEqual(next(r for r in self.b.rows('study') if r['topic']=='Cardiologia')['duration_min'],40)
        plan=preview(self.b,data);self.study(self.b,'Mudança concorrente')
        with self.assertRaisesRegex(ValueError,'mudaram'):
            apply_file(self.b,data,plan['base'])

    def test_notes_text_and_formatting_and_no_resurrection(self):
        rid=save_note(self.a,'Nota','2026-11-04','Texto',[dict(tag='bold',start=0,end=5)],labels='x',favorite=True)
        self.transfer(self.a,self.b)
        self.assertEqual(self.b.conn.execute('SELECT body FROM notebook').fetchone()[0],'Texto')
        self.transfer(self.b,self.a)
        self.assertIn('bold',self.a.conn.execute('SELECT formatting FROM notebook').fetchone()[0])
        data=self.exported(self.a)
        self.b.conn.execute("UPDATE notebook SET deleted_at='2026-11-04' WHERE id=?",(rid,));self.b.conn.commit()
        plan=preview(self.b,data)
        self.assertEqual(plan['counts']['blocked'],1)
        apply_file(self.b,data,plan['base'])
        self.assertIsNotNone(self.b.conn.execute('SELECT deleted_at FROM notebook').fetchone()[0])

    def test_similar_without_link_needs_choice_and_can_be_separate(self):
        self.study(self.a,minutes=25);self.study(self.b,minutes=40)
        data=self.exported(self.a);plan=preview(self.b,data)
        self.assertTrue(plan['conflicts'][0]['possible'])
        apply_file(self.b,data,plan['base'],{plan['conflicts'][0]['key']:'separate'})
        self.assertEqual(len(self.b.rows('study')),2)

    def test_real_repeated_identical_rows_are_not_collapsed(self):
        self.study(self.a);self.study(self.a)
        self.transfer(self.a,self.b)
        self.assertEqual(len(self.b.rows('study')),2)
        self.transfer(self.a,self.b)
        self.assertEqual(len(self.b.rows('study')),2)

    def test_invalid_input_is_atomic_and_credentials_absent(self):
        self.study(self.a)
        data=self.exported(self.a)
        serialized=json.dumps(data)
        self.assertNotIn('pomodoro_v1',serialized)
        bad=copy.deepcopy(data);bad['records']['study'][0]['duration_min']=-1
        with self.assertRaises(ValueError):preview(self.b,bad)
        self.assertEqual(self.b.rows('study'),[])
        bad=copy.deepcopy(data);bad['records']['study'].append(copy.deepcopy(bad['records']['study'][0]))
        with self.assertRaises(ValueError):preview(self.b,bad)

    def test_python_javascript_candidate_parity(self):
        self.study(self.a); self.study(self.b,minutes=40)
        save_note(self.a,'Nota','2026-11-04','Conteúdo',labels='rotina',favorite=True)
        incoming=self.exported(self.a);self.exported(self.b)
        current=snapshot(self.b)
        script="""import {reconcile} from './online/site/lib/manual-sync.mjs';
        let text='';for await(const chunk of process.stdin)text+=chunk;
        const data=JSON.parse(text);process.stdout.write(JSON.stringify(reconcile(data.current,data.incoming)));"""
        process=subprocess.run(['node','--input-type=module','-e',script],input=json.dumps(dict(current=current,incoming=incoming)),text=True,capture_output=True,check=True)
        actual=json.loads(process.stdout)
        self.assertEqual(actual,reconcile(current,incoming))

    def test_failed_audit_rolls_back_all_rows(self):
        from unittest.mock import patch
        self.study(self.a);self.study(self.a,'Outra')
        data=self.exported(self.a);plan=preview(self.b,data)
        with patch.object(self.b,'audit',side_effect=OSError('Falha de teste')):
            with self.assertRaises(OSError):apply_file(self.b,data,plan['base'])
        self.assertEqual(self.b.rows('study'),[])


if __name__=='__main__':unittest.main()
