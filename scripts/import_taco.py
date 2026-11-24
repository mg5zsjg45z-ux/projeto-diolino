"""Rebuild the offline catalogue from the official NEPA spreadsheet.

Run with the bundled Python (openpyxl). No personal database is accessed.
"""
import argparse
import hashlib
import json
import math
from datetime import date
from pathlib import Path
from urllib.request import urlopen

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://nepa.unicamp.br/wp-content/uploads/sites/27/2023/10/Taco-4a-Edicao.xlsx'
PAGE = 'https://nepa.unicamp.br/tabela-brasileira-de-composicao-de-alimentos-4a-edicao/'

CORE = [
    (2, 'moisture_g', 'Umidade', 'g'), (3, 'kcal', 'Energia', 'kcal'),
    (4, 'energy_kj', 'Energia', 'kJ'), (5, 'protein_g', 'Proteínas', 'g'),
    (6, 'fat_g', 'Gorduras totais', 'g'), (7, 'cholesterol_mg', 'Colesterol', 'mg'),
    (8, 'carbs_g', 'Carboidratos', 'g'), (9, 'fiber_g', 'Fibra alimentar', 'g'),
    (10, 'ash_g', 'Cinzas', 'g'), (11, 'calcium_mg', 'Cálcio', 'mg'),
    (12, 'magnesium_mg', 'Magnésio', 'mg'), (14, 'manganese_mg', 'Manganês', 'mg'),
    (15, 'phosphorus_mg', 'Fósforo', 'mg'), (16, 'iron_mg', 'Ferro', 'mg'),
    (17, 'sodium_mg', 'Sódio', 'mg'), (18, 'potassium_mg', 'Potássio', 'mg'),
    (19, 'copper_mg', 'Cobre', 'mg'), (20, 'zinc_mg', 'Zinco', 'mg'),
    (21, 'retinol_mcg', 'Retinol', 'µg'), (22, 're_mcg', 'Equivalentes de retinol (RE)', 'µg'),
    (23, 'rae_mcg', 'Equivalentes de atividade de retinol (RAE)', 'µg'),
    (24, 'thiamine_mg', 'Tiamina (B1)', 'mg'), (25, 'riboflavin_mg', 'Riboflavina (B2)', 'mg'),
    (26, 'pyridoxine_mg', 'Piridoxina (B6)', 'mg'), (27, 'niacin_mg', 'Niacina (B3)', 'mg'),
    (28, 'vitamin_c_mg', 'Vitamina C', 'mg'),
]
FATTY = [(2, 'saturated_g', 'Gorduras saturadas', 'g'),
         (3, 'monounsaturated_g', 'Gorduras monoinsaturadas', 'g'),
         (4, 'polyunsaturated_g', 'Gorduras poli-insaturadas', 'g')]
FATTY += [(col, 'fatty_' + name.replace(':', '_').replace(' ', '_').replace('-', '_'),
           'Ácido graxo ' + name, 'g') for col, name in zip(
               [*range(5, 12), *range(13, 25)],
               ['12:0', '14:0', '16:0', '18:0', '20:0', '22:0', '24:0',
                '14:1', '16:1', '18:1', '20:1', '18:2 n-6', '18:3 n-3', '20:4',
                '20:5', '22:5', '22:6', '18:1t', '18:2t'])]
AMINO = [(col, 'amino_' + key + '_g', label, 'g') for col, key, label in zip(
    [*range(2, 11), *range(12, 21)],
    ['tryptophan', 'threonine', 'isoleucine', 'leucine', 'lysine', 'methionine', 'cystine',
     'phenylalanine', 'tyrosine', 'valine', 'arginine', 'histidine', 'alanine', 'aspartic',
     'glutamic', 'glycine', 'proline', 'serine'],
    ['Triptofano', 'Treonina', 'Isoleucina', 'Leucina', 'Lisina', 'Metionina', 'Cistina',
     'Fenilalanina', 'Tirosina', 'Valina', 'Arginina', 'Histidina', 'Alanina',
     'Ácido aspártico', 'Ácido glutâmico', 'Glicina', 'Prolina', 'Serina'])]


def build(download=False):
    folder = ROOT / 'data' / 'taco'
    original = folder / 'taco-oficial.xlsx'
    if download:
        with urlopen(SOURCE, timeout=45) as response:
            content = response.read()
        if not content.startswith(b'PK'):
            raise ValueError('A fonte não retornou uma planilha XLSX.')
        original.write_bytes(content)
    workbook = openpyxl.load_workbook(original, read_only=True, data_only=True)
    fields = []
    foods = {}
    warnings = []
    counts = {}
    for sheet_index, (group, mapping) in enumerate([
        ('Composição, minerais e vitaminas', CORE), ('Ácidos graxos', FATTY), ('Aminoácidos', AMINO)
    ]):
        sheet = workbook.worksheets[sheet_index]
        fields.extend(dict(key=key, label=label, unit=unit, group=group) for _, key, label, unit in mapping)
        category = None
        seen = set()
        for row_number, row in enumerate(sheet.values, 1):
            if isinstance(row[0], str) and row[1] is None and row[0] not in ('Alimento', 'Número do'):
                category = row[0].strip()
            if not isinstance(row[0], (int, float)) or not isinstance(row[1], str):
                continue
            code = int(row[0])
            assert row[0] == code and code not in seen
            seen.add(code)
            if sheet_index == 0:
                foods[code] = dict(code=code, name=row[1].strip(), category=category, nutrients={})
            assert code in foods
            # The second half of each printed table repeats its code column.
            repeat_column = (13, 12, 11)[sheet_index]
            assert row[repeat_column] == code
            for column, key, _, _ in mapping:
                value = row[column]
                if isinstance(value, str):
                    value = value.strip() or None
                if isinstance(value, (int, float)):
                    assert math.isfinite(value), (code, key, value)
                    if value < 0:
                        warnings.append(dict(code=code, nutrient=key, raw=value, sheet=sheet.title,
                                             cell=f'{openpyxl.utils.get_column_letter(column+1)}{row_number}'))
                elif value not in (None, 'Tr', 'NA', '*'):
                    warnings.append(dict(code=code, nutrient=key, raw=value, sheet=sheet.title,
                                         cell=f'{openpyxl.utils.get_column_letter(column+1)}{row_number}'))
                foods[code]['nutrients'][key] = value
        counts[group] = len(seen)
    workbook.close()
    assert sorted(foods) == list(range(1, 598))
    assert len(fields) == len({f['key'] for f in fields})
    for food in foods.values():
        for field in fields:
            food['nutrients'].setdefault(field['key'], None)
    metadata = dict(name='TACO — NEPA/UNICAMP', edition='4ª edição revisada e ampliada',
                    year=2011, version='TACO-4-2011', checked_on=date.today().isoformat(),
                    source_url=SOURCE, page_url=PAGE,
                    sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
                    basis='100 g de parte comestível', sheet_counts=counts,
                    permission='Reprodução permitida com citação da fonte (NEPA/UNICAMP, 2011).',
                    warnings=warnings)
    result = dict(metadata=metadata, fields=fields, foods=list(foods.values()))
    (folder / 'catalogue.json').write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    print(json.dumps(dict(foods=len(foods), nutrients=len(fields), categories=len({f['category'] for f in foods.values()}),
                          sheet_counts=counts, warnings=warnings, sha256=metadata['sha256']), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--download', action='store_true', help='Baixar novamente da fonte oficial antes de gerar o catálogo')
    build(parser.parse_args().download)
