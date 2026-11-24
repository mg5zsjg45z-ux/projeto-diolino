"""Field definitions shared by the desktop UI and SQLite validation."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    type: str = 'text'
    required: bool = False
    choices: tuple = ()
    minimum: float | None = None
    maximum: float | None = None


def F(key, label, type='text', required=False, choices=(), minimum=None, maximum=None):
    return Field(key, label, type, required, tuple(choices), minimum, maximum)


DATE = F('date', 'Data', 'date', True)
TIME = F('time', 'Horário', 'time')
NOTES = F('notes', 'Observações', 'long')
CHECK_GROUPS = (
    ('Higiene bucal', ('brush_1', 'brush_2', 'brush_3')),
    ('Banho', ('bath_1', 'bath_2')),
    ('Checagem da medicação', ('med_1', 'med_2')),
)

MODELS = {
    'plans': ('Planos', [
        F('title', 'Nome do plano', required=True),
        F('area', 'Área', 'choice', True, ['Pessoal', 'Medicina', 'Treinos', 'Bíblia', 'Saúde', 'Outra']),
        F('status', 'Situação', 'choice', True, ['Ativo', 'Pausado', 'Concluído', 'Arquivado']),
        F('priority', 'Prioridade', 'choice', True, ['Baixa', 'Normal', 'Alta']),
        F('start_date', 'Início', 'date'), F('end_date', 'Prazo do plano', 'date'),
        F('objective', 'Objetivo', 'long'), NOTES]),
    'plan_steps': ('Etapas dos planos', [
        F('plan_id', 'Plano associado', 'plan', True),
        F('title', 'Etapa', required=True), F('due_date', 'Prazo', 'date'),
        F('state', 'Situação', 'choice', True, ['A fazer', 'Em andamento', 'Concluído']),
        F('priority', 'Prioridade', 'choice', True, ['Baixa', 'Normal', 'Alta']),
        F('position', 'Ordem', 'integer', minimum=0), NOTES]),
    'agenda': ('Agenda', [DATE, TIME,
        F('duration_min', 'Duração (min)', 'integer', minimum=1, maximum=525600),
        F('title', 'Título', required=True),
        F('category', 'Tipo', 'choice', True, ['Tarefa', 'Compromisso', 'Nota']),
        F('state', 'Situação', 'choice', True, ['Pendente', 'Concluído', 'Cancelado']),
        F('reminder', 'Notificar no Windows?', 'choice', True, ['Sim', 'Não']),
        F('description', 'Descrição / notas', 'long')]),
    'profile': ('Perfil e saúde', [
        F('name', 'Nome', required=True), F('birth_date', 'Nascimento', 'date'),
        F('height_cm', 'Altura (cm)', 'number', minimum=30, maximum=300),
        F('goals', 'Objetivos', 'long'), F('conditions', 'Condições de saúde', 'long'),
        F('allergies', 'Alergias', 'long'), F('surgeries', 'Cirurgias / antecedentes', 'long'),
        F('restrictions', 'Limitações / orientações profissionais', 'long'),
        F('routine', 'Rotina e plantões', 'long'), NOTES]),
    'body': ('Peso e medidas', [DATE, TIME,
        F('weight_kg', 'Peso (kg)', 'number', minimum=1, maximum=600),
        F('waist_cm', 'Cintura (cm)', 'number', minimum=1),
        F('hip_cm', 'Quadril (cm)', 'number', minimum=1),
        F('chest_cm', 'Tórax (cm)', 'number', minimum=1),
        F('arm_cm', 'Braço (cm)', 'number', minimum=1),
        F('thigh_cm', 'Coxa (cm)', 'number', minimum=1),
        F('fat_pct', 'Gordura corporal (%)', 'number', minimum=0, maximum=100),
        F('method', 'Método / equipamento'), F('conditions', 'Condições da medição'), NOTES]),
    'food': ('Alimentação', [DATE, TIME,
        F('meal', 'Refeição', 'choice', True, ['Café da manhã', 'Almoço', 'Jantar', 'Lanche', 'Ceia', 'Outra']),
        F('food_name', 'Alimento / bebida', required=True), F('brand', 'Marca / preparação'),
        F('quantity', 'Quantidade consumida', 'number', True, minimum=0.01),
        F('unit', 'Unidade', 'choice', True, ['g', 'mL', 'unidade', 'porção', 'colher', 'xícara']),
        F('kcal', 'Calorias da quantidade consumida (kcal)', 'number', minimum=0),
        F('protein_g', 'Proteínas da quantidade consumida (g)', 'number', minimum=0),
        F('carbs_g', 'Carboidratos da quantidade consumida (g)', 'number', minimum=0),
        F('fat_g', 'Gorduras da quantidade consumida (g)', 'number', minimum=0),
        F('fiber_g', 'Fibras da quantidade consumida (g)', 'number', minimum=0),
        F('source', 'Fonte dos nutrientes', 'choice', True, ['Rótulo', 'Tabela nutricional', 'TACO (NEPA/UNICAMP)', 'Estimativa', 'Não informado']),
        F('reference', 'Referência / detalhes da estimativa'), NOTES]),
    'hydration': ('Água e cafeína', [DATE, TIME,
        F('drink', 'Bebida', required=True),
        F('is_water', 'É água para a meta diária?', 'choice', choices=['Sim', 'Não']),
        F('volume_ml', 'Volume (mL)', 'number', True, minimum=1),
        F('caffeine_mg', 'Cafeína (mg), se conhecida', 'number', minimum=0), NOTES]),
    'workout': ('Treinos', [DATE, TIME,
        F('name', 'Nome do treino / atividade', required=True),
        F('modality', 'Modalidade', 'choice', True, ['Musculação', 'Caminhada', 'Corrida', 'Bicicleta', 'Natação', 'Outra']),
        F('duration_min', 'Duração efetiva (min)', 'number', True, minimum=0.1, maximum=1440),
        F('effort', 'Esforço percebido (0 a 10)', 'number', minimum=0, maximum=10),
        F('distance_km', 'Distância (km)', 'number', minimum=0), NOTES]),
    'sets': ('Séries de musculação', [
        F('workout_id', 'Treino associado', 'workout', True),
        F('exercise', 'Exercício', required=True), F('equipment', 'Equipamento'),
        F('set_number', 'Número da série', 'integer', True, minimum=1),
        F('load_kg', 'Carga (kg)', 'number', minimum=0),
        F('load_basis', 'Como a carga foi registrada', 'choice', True, ['Total', 'Por halter / lado', 'Máquina', 'Peso corporal', 'Assistência']),
        F('reps', 'Repetições', 'integer', True, minimum=1),
        F('rest_sec', 'Intervalo (seg)', 'integer', minimum=0),
        F('effort', 'Esforço percebido (0 a 10)', 'number', minimum=0, maximum=10),
        F('pain', 'Dor / desconforto'), NOTES]),
    'sleep': ('Sono', [DATE,
        F('start', 'Início do sono (data e hora)', 'datetime', True),
        F('end', 'Fim do sono (data e hora)', 'datetime', True),
        F('awake_min', 'Tempo acordado no intervalo (min)', 'number', True, minimum=0),
        F('type', 'Tipo', 'choice', True, ['Sono principal', 'Cochilo']),
        F('quality', 'Qualidade percebida (1 a 5)', 'integer', minimum=1, maximum=5),
        F('shift', 'Relacionado a plantão?', 'choice', True, ['Não', 'Sim']), NOTES]),
    'medication': ('Uso de medicamentos', [DATE, TIME,
        F('name', 'Medicamento / suplemento', required=True),
        F('prescribed_dose', 'Dose prescrita (texto e unidade)'),
        F('taken_dose', 'Dose efetivamente tomada', 'number', minimum=0),
        F('unit', 'Unidade da dose', 'choice', True, ['mg', 'mcg', 'g', 'mL', 'gota', 'comprimido', 'cápsula', 'UI', 'Outra']),
        F('status', 'Situação', 'choice', True, ['Tomado', 'Não tomado', 'Não informado']),
        F('prescriber', 'Prescritor / referência da prescrição'),
        F('effects', 'Efeitos percebidos', 'long'), NOTES]),
    'health': ('Sinais e bem-estar', [DATE, TIME,
        F('systolic', 'Pressão sistólica (mmHg)', 'integer', minimum=1),
        F('diastolic', 'Pressão diastólica (mmHg)', 'integer', minimum=1),
        F('pulse', 'Frequência cardíaca (bpm)', 'integer', minimum=1),
        F('energy', 'Disposição (1 a 5)', 'integer', minimum=1, maximum=5),
        F('mood', 'Humor (1 a 5)', 'integer', minimum=1, maximum=5),
        F('appetite', 'Apetite (1 a 5)', 'integer', minimum=1, maximum=5),
        F('symptoms', 'Sintomas', 'long'), NOTES]),
    'exams': ('Exames e consultas', [DATE,
        F('name', 'Exame / consulta', required=True),
        F('result', 'Resultado'), F('unit', 'Unidade'), F('reference', 'Intervalo de referência do laboratório'),
        F('professional', 'Profissional / laboratório'),
        F('guidance', 'Orientações recebidas', 'long'), NOTES]),
    'study': ('Estudo médico', [DATE, TIME,
        F('topic', 'Tema', required=True),
        F('duration_min', 'Tempo efetivo (min)', 'number', True, minimum=0.1, maximum=1440),
        F('format', 'Formato', 'choice', True, ['Leitura', 'Vídeo', 'Leitura e vídeo']),
        F('source', 'Material / fonte'), F('learning', 'Aprendizados / revisão', 'long'), NOTES]),
    'bible': ('Estudo bíblico', [DATE, TIME,
        F('passage', 'Livro / capítulo / versículos', required=True),
        F('reflection', 'Estudo e reflexões', 'long'), NOTES]),
    'routine': ('Histórico da checagem', [DATE,
        *[F(key, f'{label} — {index}ª checagem (0 ou 1)', 'integer', minimum=0, maximum=1)
          for label, keys in CHECK_GROUPS for index, key in enumerate(keys, 1)], NOTES]),
    'energy': ('Simulações calóricas', [DATE,
        F('weight_kg', 'Peso usado (kg)', 'number', True, minimum=30, maximum=350),
        F('height_cm', 'Altura usada (cm)', 'number', True, minimum=100, maximum=250),
        F('age_years', 'Idade usada (anos)', 'integer', True, minimum=18, maximum=120),
        F('coefficient', 'Coeficiente da equação', 'choice', True, ['Masculino (+5)', 'Feminino (−161)']),
        F('activity_factor', 'Fator de atividade', 'number', True, minimum=1, maximum=2.5),
        F('deficit_pct', 'Déficit simulado (%)', 'number', True, minimum=0, maximum=50), NOTES]),
    'daily': ('Fechamento do dia', [DATE,
        F('shift', 'Dia de plantão?', 'choice', True, ['Não', 'Sim', 'Não informado']),
        F('medicine_status', 'Medicina', 'choice', True, ['Não informado', 'Realizado', 'Parcial', 'Não realizado']),
        F('exercise_status', 'Exercício', 'choice', True, ['Não informado', 'Realizado', 'Parcial', 'Não realizado']),
        F('bible_status', 'Bíblia', 'choice', True, ['Não informado', 'Realizado', 'Não realizado']),
        F('difficulties', 'Dificuldades / aprendizados', 'long'), NOTES]),
}

HELP = {
    'agenda': 'Data e hora usam o relógio local do Windows. Para receber notificação, informe o horário e mantenha o aplicativo em execução, inclusive minimizado na bandeja.',
    'energy': 'Cenários de Mifflin–St Jeor com os parâmetros usados naquele momento. Na calculadora, use Carregar última simulação para consultar os resultados. Não são prescrições.',
    'food': 'Busque na TACO para calcular nutrientes pela quantidade em gramas de parte comestível, ou registre um alimento manualmente. Escolha a preparação correta (cru, cozido etc.). Campos vazios significam desconhecido.',
    'sets': 'Cadastre o treino primeiro. Registre uma linha por série; use Duplicar para repetir um exercício e ajustar a próxima série.',
    'sleep': 'Use a data em que acordou. Início e fim incluem a data para registrar noites que atravessam a meia-noite. O tempo acordado será descontado.',
    'medication': 'Registre o uso observado e a prescrição separadamente. Exemplo de nome: lisdexanfetamina. O aplicativo não calcula nem recomenda doses.',
    'hydration': 'Marque Sim somente para água. Café e outras bebidas não entram na meta de água. Calorias de bebidas devem ser registradas em Alimentação.',
    'routine': 'Há uma lista por dia. 1 = checado; 0 = desmarcado; vazio = sem informação. Use Checagem secundária para marcar rapidamente.',
    'daily': 'O fechamento é seu relato. O painel também mostra os registros detalhados. Domingo mantém os compromissos diários; a exceção é apenas o lembrete.',
    'body': 'Preencha somente as medidas disponíveis. Registre o método e as condições para comparar avaliações de forma consistente.',
    'profile': 'Seu cadastro e histórico de saúde. Não é necessário preencher tudo para começar.',
}
