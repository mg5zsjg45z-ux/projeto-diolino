"""Transparent adult energy simulation, not a prescription.

Mifflin et al. (1990), PMID 2305711: simplified resting energy equation.
Activity factor is a user-selected assumption, not measured expenditure.
"""
import math

FORMULA_SOURCE = 'https://pubmed.ncbi.nlm.nih.gov/2305711/'
ACTIVITY_SOURCE = 'https://www.niddk.nih.gov/bwp'


def energy_estimate(weight, height, age, coefficient, activity, deficit_pct):
    values = []
    for raw in (weight, height, age, activity, deficit_pct):
        try:
            value = float(str(raw).strip().replace(',', '.'))
        except (TypeError, ValueError):
            raise ValueError('Preencha peso, altura, idade, fator de atividade e déficit com números.') from None
        if not math.isfinite(value):
            raise ValueError('Os valores precisam ser números finitos.')
        values.append(value)
    weight, height, age, activity, deficit_pct = values
    if not 30 <= weight <= 350 or not 100 <= height <= 250:
        raise ValueError('Confira as unidades: peso de 30 a 350 kg e altura de 100 a 250 cm nesta calculadora.')
    if not age.is_integer() or not 18 <= age <= 120:
        raise ValueError('Esta calculadora é para adultos; informe a idade em anos completos (18 a 120).')
    if coefficient not in ('Masculino (+5)', 'Feminino (−161)'):
        raise ValueError('Escolha o coeficiente da equação. Ele não é inferido pelo nome ou pelo perfil.')
    if not 1 <= activity <= 2.5:
        raise ValueError('Use um fator de atividade entre 1,0 e 2,5 para esta simulação.')
    if not 0 <= deficit_pct <= 50:
        raise ValueError('Use um déficit de 0 a 50%. Zero simula manutenção; o limite não é uma recomendação.')
    resting = 10 * weight + 6.25 * height - 5 * age + (5 if coefficient.startswith('Masculino') else -161)
    if resting <= 0:
        raise ValueError('Esses dados não produzem uma estimativa de repouso válida.')
    total = resting * activity
    deficit = total * deficit_pct / 100
    intake = total - deficit
    if intake < 1000:
        raise ValueError('A simulação resultaria em menos de 1.000 kcal/dia. Não será apresentada como meta alimentar; revise os parâmetros com um profissional.')
    return {'resting_kcal': resting, 'total_kcal': total, 'deficit_kcal': deficit,
            'intake_kcal': intake, 'deficit_pct': deficit_pct}
