import struct
import zlib
import pytest
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from academy.decoder import Decoder
from academy.decoder_keys import SCS_AES_KEY
from academy.exceptions import DecodeError


def encrypt(payload=b"SiiNunit { }", declared=None, compressed=None, bad_pad=False):
    data = zlib.compress(payload) if compressed is None else compressed
    pad = padding.PKCS7(128).padder()
    data = pad.update(data) + pad.finalize()
    if bad_pad:
        data = data[:-1] + b"\x00"
    iv = bytes(16)
    enc = Cipher(algorithms.AES(SCS_AES_KEY), modes.CBC(iv)).encryptor()
    return b"ScsC" + bytes(32) + iv + struct.pack("<I", len(payload) if declared is None else declared) + enc.update(data) + enc.finalize()


def test_real(reference):
    raw = reference.read_bytes()
    decoded = Decoder().decode(raw)
    assert decoded.source_format == "ScsC"
    assert decoded.text.startswith("SiiNunit")
    assert decoded.warnings and "HMAC" in decoded.warnings[0]
    assert reference.read_bytes() == raw
    from pathlib import Path
    plain = reference.with_name("academy_book_states%20(2)_decoded.sii")
    if plain.exists():
        assert decoded.text.replace("\r\n","\n") == plain.read_text(encoding="utf-8-sig").replace("\r\n","\n")


def test_decompress():
    assert Decoder().decode(encrypt()).text == "SiiNunit { }"


@pytest.mark.parametrize("raw", [b"", b"ScsC", b"ScsC" + bytes(69), b"BSII", b"nope"])
def test_invalid(raw):
    with pytest.raises(DecodeError):
        Decoder().decode(raw)


@pytest.mark.parametrize("kwargs", [{"bad_pad": True}, {"declared": 500}, {"compressed": b"invalid"}, {"compressed": zlib.compress(b"SiiNunit { }")[:-2]}])
def test_corrupt(kwargs):
    with pytest.raises(DecodeError):
        Decoder().decode(encrypt(**kwargs))


def test_bsii_adapter_uses_private_copy(tmp_path):
    import sys
    script = tmp_path/"fake_decoder.py"
    script.write_text("from pathlib import Path\nimport sys\np=Path(sys.argv[1])\nassert p.read_bytes()==b'BSIItest'\np.write_bytes(b'SiiNunit { }')\n",encoding="utf-8")
    source = tmp_path/"game.sii"
    source.write_bytes(b"BSIItest")
    decoder = Decoder([sys.executable,str(script),"{input}"])
    assert decoder.decode(source.read_bytes()).text == "SiiNunit { }"
    assert source.read_bytes() == b"BSIItest"
    assert decoder.decode(encrypt(payload=b"BSIItest")).text == "SiiNunit { }"
