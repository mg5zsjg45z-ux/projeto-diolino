"""Offline TACO catalogue, accent-insensitive search and explicit gram scaling."""
import copy
import json
import math
import unicodedata
from functools import lru_cache
from pathlib import Path

MACROS = ('kcal', 'protein_g', 'carbs_g', 'fat_g', 'fiber_g')
SOURCE_NAME = 'TACO (NEPA/UNICAMP)'


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value).casefold()) if not unicodedata.combining(c))


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def grams_value(value):
    try:
        grams = float(str(value).strip().replace(',', '.'))
    except (TypeError, ValueError):
        raise ValueError('Informe a quantidade consumida em gramas.') from None
    if not math.isfinite(grams) or not .01 <= grams <= 100000:
        raise ValueError('A quantidade deve estar entre 0,01 e 100.000 g.')
    return grams


def scale(nutrients, grams):
    grams = grams_value(grams)
    return {key: round(value * grams / 100, 6) if numeric(value) else None for key, value in nutrients.items()}


def nutrient_text(raw, grams=100):
    if numeric(raw):
        value = raw * grams_value(grams) / 100
        return f'{value:.3f}'.rstrip('0').rstrip('.').replace('.', ',') if value == 0 or value >= .001 else '< 0,001'
    return {None: 'Não informado', 'Tr': 'Traço', 'NA': 'Não aplicável', '*': 'Em reavaliação'}.get(raw, 'Inconsistência na fonte')


def reference(snapshot):
    meta, food = snapshot['metadata'], snapshot['food']
    return f"{meta['name']} · {meta['edition']} ({meta['year']}) · código {food['code']} · valores por 100 g de parte comestível · {meta['source_url']}"


def validate_snapshot(snapshot):
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get('food'), dict) or not isinstance(snapshot.get('metadata'), dict):
        raise ValueError('Referência nutricional inválida. Selecione o alimento na TACO novamente.')
    food, meta = snapshot['food'], snapshot['metadata']
    if not isinstance(food.get('nutrients'), dict) or not all(key in food['nutrients'] for key in MACROS):
        raise ValueError('Composição nutricional incompleta.')
    if not isinstance(food.get('code'), int) or not food.get('name') or not all(meta.get(k) for k in ('name', 'edition', 'year', 'version', 'source_url', 'sha256')):
        raise ValueError('Identificação da fonte nutricional incompleta.')
    # Ensure the immutable snapshot can be persisted without NaN/Infinity or objects.
    json.dumps(snapshot, allow_nan=False)


class TacoCatalogue:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(__file__).parent / 'data' / 'taco' / 'catalogue.json'
        document = json.loads(self.path.read_text(encoding='utf-8'))
        self.metadata = document['metadata']
        self.fields = document['fields']
        self.foods = document['foods']
        self.by_code = {food['code']: food for food in self.foods}
        if len(self.by_code) != len(self.foods) or len(self.foods) != 597:
            raise ValueError('Catálogo TACO incompleto ou com códigos repetidos.')
        self.categories = list(dict.fromkeys(food['category'] for food in self.foods))
        self.search_text = {food['code']: normalized(f"{food['code']} {food['name']} {food['category']}") for food in self.foods}

    def search(self, query='', category=None):
        tokens = normalized(query).split()
        return [food for food in self.foods if (not category or food['category'] == category)
                and all(token in self.search_text[food['code']] for token in tokens)]

    def snapshot(self, code):
        return copy.deepcopy(dict(metadata=self.metadata, food=self.by_code[int(code)]))


@lru_cache(maxsize=1)
def catalogue():
    return TacoCatalogue()
