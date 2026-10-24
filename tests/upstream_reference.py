"""Official e1d17499051c12d59985a333e0f7b5f5304d9b2d references, independent of local release folders."""
from pathlib import Path
REFERENCE = Path(__file__).resolve().parent / "fixtures" / "upstream"
def original_source(relative):
    return (REFERENCE / relative).read_text(encoding="utf-8-sig")
