"""Main areas and their subordinate pages; MDL2 glyphs from Microsoft Learn."""
AREAS = [
    ('home', 'Visão geral', '\ue80f'),
    ('checklist', 'Checagem diária', '\ue9d5'),
    ('planning', 'Planos', '\ue8fd'),
    ('health_overview', 'Saúde', '\ueb51'),
    ('training', 'Treinos', '\ue805'),
    ('studies', 'Estudos', '\ue8f1'),
    ('bible_library', 'Bíblia', '\ue82d'),
    ('agenda', 'Agenda', '\ue787'),
    ('notebook', 'Anotações diárias', '\ue8a5'),
    ('data', 'Dados e backup', '\ue713'),
    ('printing', 'Relatórios / Imprimir', '\ue749'),
    ('appearance', 'Configurações', '\ue790'),
]
TABS = {
    'appearance': [('appearance', 'Aparência e Temas'), ('modules', 'Gerenciamento de Módulos')],
    'planning': [('planning', 'Meus planos'), ('plans', 'Editar planos'), ('plan_steps', 'Todas as etapas')],
    'agenda': [('agenda', 'Agenda'), ('icloud', 'iCloud e iPhone')],
    'checklist': [('checklist', 'Hoje'), ('daily', 'Fechamentos'), ('routine', 'Hábitos: histórico'), ('adherence', 'Constância')],
    'health_overview': [('health_overview', 'Resumo'), ('body', 'Medidas'), ('sleep', 'Sono'), ('food', 'Alimentação'),
                        ('hydration', 'Água'), ('medication', 'Medicação'), ('health', 'Sinais'), ('exams', 'Exames'),
                        ('profile', 'Perfil'), ('calculator', 'Calculadora'), ('energy', 'Simulações'), ('trends', 'Gráficos')],
    'training': [('training', 'Resumo'), ('workout', 'Atividades'), ('sets', 'Séries e cargas')],
    'studies': [('studies', 'Resumo'), ('study', 'Medicina')],
    'bible_library': [('offline_bible', 'Leitura offline'), ('bible_online', 'Versões online'), ('bible', 'Registros de estudo')],
}


def area_for(page):
    for area, pages in TABS.items():
        if any(key == page for key, _ in pages):
            return area
    return page
