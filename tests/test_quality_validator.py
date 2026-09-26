from pathlib import Path
from ai_gif_studio.engines.validator import OutputValidator
def test_rejects_missing_and_wrong_magic(tmp_path:Path):
    p=tmp_path/"x.gif"; p.write_bytes(b"notgif")
    assert not OutputValidator().validate_gif(p,100)
