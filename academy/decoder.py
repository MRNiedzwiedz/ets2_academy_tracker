from dataclasses import dataclass
import logging
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from academy.decoder_keys import SCS_AES_KEY
from academy.exceptions import DecodeError

MAX_SIZE = 64 * 1024 * 1024
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Decoded:
    text: str
    source_format: str
    warnings: tuple[str, ...] = ()


class Decoder:
    def __init__(self, bsii_command: list[str] | None = None):
        self.bsii_command = bsii_command

    def decode(self, raw: bytes) -> Decoded:
        if len(raw) > MAX_SIZE:
            raise DecodeError("Plik przekracza limit 64 MiB")
        source = raw[:4].decode("ascii", errors="replace")
        warnings = []
        if raw.startswith(b"ScsC"):
            if len(raw) < 72 or (len(raw) - 56) % 16:
                raise DecodeError("Niepełny lub niewyrównany ScsC")
            expected = struct.unpack_from("<I", raw, 52)[0]
            if expected > MAX_SIZE:
                raise DecodeError("Zadeklarowany rozmiar przekracza limit")
            try:
                decryptor = Cipher(algorithms.AES(SCS_AES_KEY), modes.CBC(raw[36:52])).decryptor()
                padded = decryptor.update(raw[56:]) + decryptor.finalize()
                unpadder = padding.PKCS7(128).unpadder()
                compressed = unpadder.update(padded) + unpadder.finalize()
            except ValueError as exc:
                raise DecodeError("Błędne dopełnienie AES PKCS#7") from exc
            try:
                stream = zlib.decompressobj()
                raw = stream.decompress(compressed, MAX_SIZE + 1)
                if len(raw) > MAX_SIZE or not stream.eof or stream.unused_data or stream.unconsumed_tail:
                    raise DecodeError("Niepełny, nadmiarowy lub zbyt duży strumień zlib")
            except zlib.error as exc:
                raise DecodeError("Błąd dekompresji zlib") from exc
            if len(raw) != expected:
                raise DecodeError(f"Niezgodna długość ScsC: {len(raw)} zamiast {expected}")
            warnings.append("HMAC ScsC niezweryfikowany — konstrukcja MAC i klucz niepotwierdzone")
            log.warning(warnings[-1])
            log.info("ScsC decoding successful")
        if raw.startswith(b"BSII"):
            raw = self._bsii(raw)
        if not raw.startswith(b"SiiN"):
            raise DecodeError("Nieznany format: oczekiwano ScsC, BSII lub SiiN")
        try:
            return Decoded(raw.decode("utf-8-sig"), source, tuple(warnings))
        except UnicodeDecodeError as exc:
            raise DecodeError("Niepoprawny tekst UTF-8") from exc

    def _bsii(self, raw: bytes) -> bytes:
        if not self.bsii_command:
            raise DecodeError("BSII wymaga zewnętrznego dekodera. Ustaw bsii_command.")
        # Decoder receives a private copy only, even if it overwrites its input.
        with tempfile.TemporaryDirectory(prefix="academy-bsii-") as folder:
            src, dst = Path(folder) / "input.sii", Path(folder) / "output.sii"
            src.write_bytes(raw)
            command = [arg.replace("{input}", str(src)).replace("{output}", str(dst))
                       for arg in self.bsii_command]
            if not any("{input}" in arg for arg in self.bsii_command):
                raise DecodeError("Polecenie BSII musi zawierać {input}")
            try:
                subprocess.run(command, check=True, timeout=30, capture_output=True,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                output = dst if dst.exists() else src
                if output.stat().st_size > MAX_SIZE:
                    raise DecodeError("Wynik BSII przekracza limit")
                return output.read_bytes()
            except (OSError, subprocess.SubprocessError) as exc:
                raise DecodeError("Zewnętrzny dekoder BSII nie zakończył pracy poprawnie") from exc
