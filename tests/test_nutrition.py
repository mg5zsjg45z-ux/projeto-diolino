import copy
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from nutrition import catalogue, scale, grams_value, nutrient_text, SOURCE_NAME
from storage import Store, SCHEMA_VERSION


class CatalogueTests(unittest.TestCase):
    def test_official_catalogue_coverage_and_provenance(self):
        c = catalogue()
        self.assertEqual(sorted(c.by_code), list(range(1, 598)))
        self.assertEqual(len(c.categories), 15)
        self.assertEqual(len(c.fields), 66)
        self.assertEqual(c.metadata['year'], 2011)
        original = Path(__file__).resolve().parents[1] / 'data/taco/taco-oficial.xlsx'
        self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), c.metadata['sha256'])
        self.assertEqual(c.metadata['sheet_counts']['Ácidos graxos'], 423)
        self.assertEqual(c.metadata['sheet_counts']['Aminoácidos'], 26)

    def test_search_accent_category_and_preparation(self):
        c = catalogue()
        self.assertEqual(c.search('feijao preto cozido')[0]['code'], 567)
        self.assertEqual(c.search('FEIJÃO preto COZIDO')[0]['code'], 567)
        self.assertNotEqual(c.search('arroz tipo 1 cozido')[0]['code'], c.search('arroz tipo 1 cru')[0]['code'])
        self.assertEqual(c.search('feijao', 'Cereais e derivados'), [])

    def test_scaling_and_non_numeric_values(self):
        nutrients = catalogue().by_code[3]['nutrients']
        self.assertEqual(scale(nutrients, '150,5')['kcal'], round(128.25848566666664 * 1.505, 6))
        self.assertIsNone(scale(catalogue().by_code[42]['nutrients'], 100)['fat_g'])
        self.assertEqual(nutrient_text('Tr', 200), 'Traço')
        self.assertEqual(nutrient_text('NA'), 'Não aplicável')
        self.assertEqual(nutrient_text('*'), 'Em reavaliação')
        self.assertEqual(nutrient_text(None), 'Não informado')
        self.assertEqual(nutrient_text(0), '0')
        self.assertIsNone(scale(catalogue().by_code[288]['nutrients'], 100)['carbs_g'])
        self.assertEqual(catalogue().by_code[373]['nutrients']['pyridoxine_mg'], ',0,02')
        for value in ('', 'NaN', 'inf', -1, 0, 100001):
            with self.assertRaises(ValueError):
                grams_value(value)


class FoodSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def values(self, **kwargs):
        return dict(date='2026-10-16', meal='Almoço', food_name='Arroz', quantity=150,
                    unit='g', source=SOURCE_NAME) | kwargs

    def test_atomic_portion_snapshot_and_historical_stability(self):
        snapshot = catalogue().snapshot(3)
        rid = self.store.save('food', self.values(kcal=999), nutrition=snapshot)
        row = self.store.get('food', rid)
        self.assertEqual(row['kcal'], 192.387728)
        self.assertEqual(row['food_name'], 'Arroz, tipo 1, cozido')
        self.assertEqual(row['_nutrition']['grams'], 150)
        self.assertEqual(row['_nutrition']['metadata']['version'], 'TACO-4-2011')
        snapshot['food']['nutrients']['kcal'] = 0
        self.assertEqual(self.store.get('food', rid)['kcal'], 192.387728)
        self.store.close()
        self.store = Store(self.temp.name)
        old = self.store.get('food', rid)
        self.store.save('food', self.values(quantity=200), rid, nutrition=old['_nutrition'])
        self.assertEqual(self.store.get('food', rid)['kcal'], 256.516971)
        self.assertEqual(len(self.store.history('food', rid)), 2)
        with self.assertRaises(ValueError):
            self.store.save('food', self.values(unit='mL'), nutrition=old['_nutrition'])
        self.assertEqual(len(self.store.rows('food')), 1)

    def test_manual_mode_backup_restore_export(self):
        rid = self.store.save('food', self.values(), nutrition=catalogue().snapshot(42))
        self.assertIsNone(self.store.get('food', rid)['fat_g'])
        backup = self.store.backup()
        archive = Path(self.temp.name) / 'export.zip'
        self.store.export(archive)
        with zipfile.ZipFile(archive) as bundle:
            exported = bundle.read('food_nutrition.csv').decode('utf-8-sig')
            self.assertIn('TACO-4-2011', exported)
            self.assertIn('361.366', exported)
        self.store.save('food', self.values(source='Rótulo', kcal=120), rid)
        self.assertIsNone(self.store.get('food', rid)['_nutrition'])
        self.store.restore(backup)
        self.assertEqual(self.store.get('food', rid)['_nutrition']['food']['code'], 42)
        self.store.delete('food', rid)
        self.assertEqual(self.store.rows('food'), [])
        self.assertIn('TACO-4-2011', self.store.history('food', rid)[0]['before_json'])

    def test_legacy_v4_migrates_and_restores_without_rewriting_food(self):
        rid = self.store.save('food', self.values(source='Rótulo', kcal=123, quantity=1, unit='porção'))
        with self.store.conn:
            self.store.conn.execute('DROP TABLE food_nutrition')
            self.store.conn.execute('PRAGMA user_version=4')
        legacy = self.store.backup()
        self.store.close()
        self.store = Store(self.temp.name)
        self.assertEqual(self.store.conn.execute('PRAGMA user_version').fetchone()[0], SCHEMA_VERSION)
        self.assertEqual(self.store.get('food', rid)['kcal'], 123)
        self.assertEqual(self.store.get('food', rid)['unit'], 'porção')
        self.store.restore(legacy)
        self.assertIsNone(self.store.get('food', rid)['_nutrition'])
        self.assertEqual(self.store.get('food', rid)['kcal'], 123)


class FoodEditorTests(unittest.TestCase):
    def setUp(self):
        from app import App
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name)
        self.app = App(self.store)
        self.app.withdraw()

    def tearDown(self):
        self.app.update()
        self.app.shutdown()
        self.temp.cleanup()

    def test_apply_edit_quantity_save_reopen_and_manual(self):
        from app import Editor
        editor = Editor(self.app, 'food')
        editor.withdraw()
        editor.vars['meal'].set('Almoço')
        editor.apply_taco(catalogue().snapshot(3), 100)
        editor.vars['quantity'].set('150')
        self.assertEqual(editor.vars['kcal'].get(), '192,387728')
        self.assertEqual(str(editor.field_widgets['kcal'].cget('state')), 'readonly')
        editor.save()
        row = self.store.get('food', self.store.rows('food')[0]['id'])
        editor = Editor(self.app, 'food', row)
        editor.withdraw()
        self.assertEqual(editor.nutrition_snapshot['food']['code'], 3)
        editor.unlink_taco()
        self.assertEqual(str(editor.field_widgets['kcal'].cget('state')), 'normal')
        editor.vars['kcal'].set('180')
        editor.save()
        self.assertEqual(self.store.get('food', row['id'])['kcal'], 180)
        self.assertIsNone(self.store.get('food', row['id'])['_nutrition'])

    def test_picker_search_portion_and_no_stale_selection(self):
        from nutrition_ui import TacoPicker
        results = []
        self.app.deiconify()
        self.app.update_idletasks()
        picker = TacoPicker(self.app, lambda snapshot, grams: results.append((snapshot, grams)))
        picker.geometry('900x620')
        picker.update()
        self.assertTrue(picker.apply_button.winfo_ismapped())
        self.assertLessEqual(picker.apply_button.winfo_rooty() + picker.apply_button.winfo_height(), picker.winfo_rooty() + picker.winfo_height())
        picker.withdraw()
        self.app.withdraw()
        picker.query.set('arroz tipo 1 cozido')
        self.assertEqual(picker.foods_tree.get_children(), ('3',))
        picker.foods_tree.selection_set('3')
        picker.select_food()
        picker.grams.set('150')
        self.assertEqual(len(picker.nutrients_tree.get_children()), 66)
        picker.query.set('nenhum alimento com este nome')
        self.assertIsNone(picker.snapshot)
        self.assertIn('disabled', picker.apply_button.state())
        picker.query.set('feijao preto cozido')
        picker.foods_tree.selection_set('567')
        picker.select_food()
        picker.apply()
        self.assertEqual(results[0][0]['food']['code'], 567)
        self.assertEqual(results[0][1], 150)
