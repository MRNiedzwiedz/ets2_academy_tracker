"""Small scanner + structural parser; unknown SII scalar forms remain strings."""
import ast
import re
from academy.exceptions import ParseError
from academy.models import SiiObject

TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/|#[^\n]*|[{}:\[\]()]|[^\s"{}:\[\]()]+', re.S)


def scalar(raw: str):
    if raw == "nil":
        return None
    if raw in ("true", "false"):
        return raw == "true"
    if raw.startswith('"') and raw.endswith('"'):
        try:
            return ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            return raw
    if re.fullmatch(r"[+-]?\d+", raw):
        return int(raw)
    if re.fullmatch(r"[+-]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][+-]?\d+)?", raw):
        return float(raw)
    return raw


def parse_sii(text: str) -> dict[str, SiiObject]:
    tokens = []
    scanned = 0
    for match in TOKEN.finditer(text):
        if text[scanned:match.start()].strip():
            raise ParseError("Niepoprawny lub niedomknięty tekst SII")
        scanned = match.end()
        if not match.group().startswith(("//", "/*", "#")):
            tokens.append(match.group())
    if text[scanned:].strip():
        raise ParseError("Niepełny token SII")
    pos = 0

    def take(expected: str | None = None) -> str:
        nonlocal pos
        if pos >= len(tokens):
            raise ParseError("Niepełna struktura SII")
        token = tokens[pos]
        pos += 1
        if expected is not None and token != expected:
            raise ParseError(f"Oczekiwano {expected}, otrzymano {token}")
        return token

    take("SiiNunit")
    take("{")
    objects = {}
    while pos < len(tokens) and tokens[pos] != "}":
        typ = take()
        take(":")
        oid = take()
        take("{")
        fields, raw_fields = {}, {}
        while pos < len(tokens) and tokens[pos] != "}":
            key = take()
            if pos < len(tokens) and tokens[pos] == "[":
                take("[")
                index = take()
                if not index.isdigit():
                    raise ParseError("Niepoprawny indeks tablicy")
                take("]")
                key += f"[{index}]"
            take(":")
            value = take()
            if value == "(":
                parts, depth = [value], 1
                while depth:
                    item = take()
                    if item in ("{", "}"):
                        raise ParseError("Niepełna wartość złożona")
                    depth += (item == "(") - (item == ")")
                    parts.append(item)
                value = " ".join(parts)
            elif value in ("{", "}", ":", "[", "]"):
                raise ParseError("Brak wartości pola")
            if key in fields:
                raise ParseError(f"Powtórzone pole {key}")
            fields[key], raw_fields[key] = scalar(value), value
        take("}")
        if oid in objects:
            raise ParseError("Powtórzony identyfikator obiektu")
        objects[oid] = SiiObject(typ, oid, fields, raw_fields)
    take("}")
    if pos != len(tokens):
        raise ParseError("Nadmiarowe dane po kontenerze SII")
    return objects


def array_values(obj: SiiObject, name: str) -> list:
    count = obj.fields.get(name, 0)
    if not isinstance(count, int) or count < 0 or count > 1_000_000:
        raise ParseError(f"Niepoprawna długość {name}")
    try:
        return [obj.fields[f"{name}[{i}]"] for i in range(count)]
    except KeyError as exc:
        raise ParseError(f"Niepełna tablica {name}") from exc
