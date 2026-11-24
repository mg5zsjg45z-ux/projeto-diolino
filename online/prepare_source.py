"""Copy public application definitions only; never read the personal database."""
import json
import sys
from dataclasses import asdict
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from models import MODELS, CHECK_GROUPS
from planning import TEMPLATES
from bible_library import VERSIONS, BOOKS
from nutrition import catalogue
site = root / 'online/site'
(site/'lib').mkdir(exist_ok=True)
(site/'public/mobile').mkdir(parents=True, exist_ok=True)
schema = {k:dict(label=label, fields=[asdict(f) for f in fields]) for k,(label,fields) in MODELS.items()}
for f in schema['agenda']['fields']:
    if f['key']=='reminder': f['label']='Lembrete registrado (sem notificação automática na web)'
definitions=dict(schema=schema,groups=CHECK_GROUPS,templates=TEMPLATES,versions=VERSIONS,books=BOOKS)
(site/'lib/definitions.json').write_text(json.dumps(definitions,ensure_ascii=False),encoding='utf-8')
(site/'lib/taco.json').write_bytes((root/'data/taco/catalogue.json').read_bytes())
html=(root/'mobile/index.html').read_text(encoding='utf-8')
start=html.index('<section id="login">');end=html.index('</section>',start)+len('</section>')
html=html[:start]+'''<section id="login"><div class="eyebrow">Controle pessoal · acesso privado</div><div class="brand">Diolino.</div><p>Rotina, saúde e planejamento.</p><a href="/signin-with-chatgpt?return_to=/" target="_top">Entrar com ChatGPT</a><p class="muted">Seus registros online ficam disponíveis no PC e no iPhone. Requer internet.</p><form id="login-form" hidden><input id="code"></form></section>'''+html[end:]
html=html.replace('Constância, todos os dias','Controle pessoal · online')
html=html.replace('Registro salvo no Diolino deste PC.','Registro salvo na sua conta online.')
html=html.replace('Falha de conexão. Confira se o PC está ligado e na mesma rede.','Falha de conexão. Verifique sua internet e tente novamente.')
html=html.replace("$('logout').onclick=async()=>", "$('logout').onclick=async()=>")
lines=html.splitlines()
for i,line in enumerate(lines):
    if line.startswith("$('logout').onclick"):
        lines[i]="$('logout').onclick=()=>{location.href='/signout-with-chatgpt?return_to=/'};"
html='\n'.join(lines)
html=html.replace("initialize().catch(","window.addEventListener('load',()=>initialize().catch(")
html=html.replace("console.debug('Aguardando autenticação.')});", "console.debug('Aguardando autenticação.')}));")
html=html.replace('</body>', '<script src="/mobile/online.js"></script></body>')
html=html.replace('</head>', '<link rel="stylesheet" href="/mobile/refinement.css"></head>')
html=html.replace('</body>', '<script src="/mobile/refinement.js"></script></body>')
(site/'lib/document.json').write_text(json.dumps(html,ensure_ascii=False),encoding='utf-8')
for name in ('modern.css','planning.js'):
    (site/'public/mobile'/name).write_bytes((root/'mobile'/name).read_bytes())
manifest=json.loads((site/'.openai/hosting.json').read_text(encoding='utf-8-sig'))
manifest['d1']='DB'
(site/'.openai/hosting.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
