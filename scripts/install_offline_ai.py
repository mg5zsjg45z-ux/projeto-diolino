import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_assets import install
install(progress=lambda message: print(message, flush=True))
