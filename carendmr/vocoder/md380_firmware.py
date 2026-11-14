"""Auspacken der Original-Firmware-Datei des Tytera MD-380 (Version 2.32).

Tytera verteilt Firmware-Updates als "verpackte" Dateien: 256 Byte Kopf,
danach das Programmabbild, verschlüsselt mit einem zyklisch wiederholten,
festen 1024-Byte-XOR-Schlüssel, am Ende 256 Byte Fuß. Format und Schlüssel
stammen aus md380tools (md380_fw.py, Klasse MD380FW) von Travis Goodspeed
KK4VCZ und Mitwirkenden; Lizenz laut dessen README: „licensed in exchange
for two liters of India Pale Ale“. Dieselbe Datei liegt auch in
md380_vocoder_dynarmic (firmware/md380-fw.py, GPL) und wird dort beim Bauen
genauso verwendet.

CarenDMR enthält damit KEINE Firmware, nur das Verfahren, um eine vom Nutzer
bezogene Update-Datei auszupacken.
"""
from __future__ import annotations

import hashlib
import io
import struct
import zipfile

# Bezugsquellen und Prüfsummen wie in md380_vocoder_dynarmic/firmware/download.sh
# (Commit 55c9a2c6d502567380c7dfaf4a2e3cc4dd6d1dd5).
FIRMWARE_ZIP_URL = "https://md380.org/firmware/orig/TYT-Tytera-MD-380-FW-v232.zip"
FIRMWARE_ZIP_MEMBER = "Firmware 2.32/MD-380-D2.32(AD).bin"
WRAPPED_SHA256 = "e1a1a11a84d9afd2d2ceed61be8395e32a8034785abd0be0236478f7d8609f43"
# Ergebnis des Auspackens (am 14.11.2026 aus dem verifizierten Download ermittelt).
UNWRAPPED_SHA256 = "c0351f250a834660641bca3b06be931c80cc1ed0ef808356c550b99cd0f4c632"

# RAM-Abbild aus md380tools/cores (identisch mit md380_vocoder_dynarmic/firmware).
CORE_URL = "https://raw.githubusercontent.com/travisgoodspeed/md380tools/master/cores/d02032-core.img"
CORE_SHA256 = "d40398183e9aa8db6288a62d9a0e0c233cb143ef5633680abd829cc03c719f66"
CORE_SIZE = 0x20000

WRAPPED_MAGIC = b"OutSecurityBin"
_HEADER = struct.Struct("<16s7s9s16s33s47sLL120s")
_JST = b"JST51"
BASE_ADDRESS = 0x0800C000
# Die Bridge stellt 1 MiB ab 0x0800C000 bereit.
MAX_FIRMWARE_BYTES = 0x100000

KEY = bytes.fromhex(
    "2edf40b5bdda91352142e3e26da90b9031303afa4f0574640a29447e6077ad8c"
    "9ae263c421fe3cf793c2e174168cc92aed65680c4986a3ba611c885dc4493cd2"
    "ee6b340c1aa0a8b3588a4511df4f232fa4e4f63b2c8c882d9e9b67ab1c80da29"
    "53021a5451cabfb19722798170fc00e981364e4fa01c0b07ea2f492f0f2571d7"
    "f1307d666e8368387913e38c709a4a9ea9e2d6104f40148e6c5e96b2463ee825"
    "ef7cc50818d48b9226e3edfa8832e8974770f846deff8b0c4db3b6fc69d6275b"
    "766f5b03f7c31105c51dfe925fcbc21c81691bb8f86258c7b4b311d51ff216c1"
    "ad8fa51eb45be0da7f467d1d9e6dc0747f54a62f436f6408cae80f05109c9d9f"
    "bd670c23f7a1e1597be8d464ec20cae96ab9037367309516b6d91953e5dba43c"
    "cd7cf9d8679ffcc9e28a6a2cf2edc8c16a20994c0dadd43ba10e958846b813e1"
    "0658d207ad5c1a74dbb5a74057dba245a612d082dded0abdb310ed6cda39d2d6"
    "9082007671e021a08ff0f367c4f340bd471610dc7ef81de5136687c74a69c963"
    "9282ecee5a34fb9625c3b668e13c8a7174b5c12399d6f7fbea98cd613d4de1d0"
    "34e1fd36105f8e9ec6b6580c55be69a856764b1fd5907e475f2f25025cef0064"
    "a0269a183c69c4ff9a52411bc981c3ac15e11798db2c9c109bb2f9714f560f68"
    "fbd92d5a865b8303c81eda5de48e82c3d87e8b5652b538a0c6a9b077bd8af724"
    "70821dc5953cb5f079a389994fec8c36c7d61020e330393d079cb2dc4f949ee0"
    "24aad2211214410fd467b799b1a3cb4d0c700fc036a7893086146768ac7beee4"
    "42d8b436a4eb0fa802f4cd23b3bc254fccd4eefcf2210fc16c9937e27c47ce77"
    "f0952bcbf4ca07032ad23100fd3e8486328b179dbfa7b337e1b18a14690025e3"
    "56689faaa9b8116775874df83631cf38631cf06b47405ddc0ce6c8c419afdd6e"
    "9ed978996cbe151e0b9d88d2069deeae8a0fe32d2ff4f5f616bf59bb345cdd61"
    "ed701e61e5e3fb6e139c4958178bc830cded56ad22cb63ce26c4a5c1630d0d04"
    "6eb6f9cabb2faba0b50afa500e024705543db3b1c6ce8fac657e159e4ecc559e"
    "4632719b97aa0dfb1b710283960b527748876102c30462d7fb740f199ca09d79"
    "a06def9e205d0ac96a58c9b955add1ccd154c868c276c2990f2efcfbf592cddb"
    "a2edd999ff4f8850cd48b7b9f3f0ad4d162a50aa6b2a9838c935450c03a8cd0d"
    "743c9955db8870da6ac8344d19dccc4240946192652acdfd521050146bec8557"
    "3fe2959a5d11abad6960a83b6f7a17f3761763e6597e4730d24787dbd866de00"
    "2b65372f2df12011f3987b4c9cd176a7e13dbe6fee2cf01970635128f01dbe52"
    "5f4fe6def230b65030f9154849e9d2a8a98ddaf5cd3eaf0055eb15c55b190f93"
    "0427096d54d757b1470adef71dcb113cf58f20409dbb6b2ca9673d78c262b70c"
)
KEY_SHA256 = "5254139c6b596d9413d106e6b7c0685ec245d69555cb28df98f061d6b879c4cd"


class FirmwareFormatError(ValueError):
    """Die Datei ist keine passende MD-380-Firmware 2.32."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _xor_cyclic(data: bytes, key: bytes) -> bytes:
    if not data:
        return b""
    repeats = len(data) // len(key) + 1
    stream = (key * repeats)[: len(data)]
    value = int.from_bytes(data, "big") ^ int.from_bytes(stream, "big")
    return value.to_bytes(len(data), "big")


def unwrap(image: bytes) -> bytes:
    """Entschlüsselt eine verpackte MD-380-Update-Datei."""
    if len(image) < 512 or not image.startswith(WRAPPED_MAGIC):
        raise FirmwareFormatError("Keine verpackte Tytera-Update-Datei.")
    header = _HEADER.unpack(image[:256])
    if not header[1].startswith(_JST):
        raise FirmwareFormatError("Die Update-Datei ist nicht für das MD-380 bestimmt.")
    app_len = header[7]
    if app_len != len(image) - 512 or app_len > MAX_FIRMWARE_BYTES:
        raise FirmwareFormatError("Die Längenangabe der Update-Datei passt nicht.")
    return _xor_cyclic(image[256 : 256 + app_len], KEY)


def wrap(app: bytes, start: int = BASE_ADDRESS) -> bytes:
    """Gegenstück zu unwrap(); nur für Tests (keine Firmware nötig)."""
    pad = (512 - len(app) % 512) % 512
    app = app + b"\xff" * pad
    header = _HEADER.pack(
        WRAPPED_MAGIC, _JST, b"\xff" * 9, b"\x30\x02\x00\x30\x00\x40\x00\x47",
        bytes([1, 13]) + bytes(range(2, 33)), b"\xff" * 47, start, len(app), b"\xff" * 120,
    )
    footer = b"\xff" * 240 + b"OutputBinDataEnd"
    return header + _xor_cyclic(app, KEY) + footer


def firmware_from_bytes(data: bytes) -> tuple[bytes, str]:
    """Liefert das ausgepackte Abbild D002.032 und die Herkunftsprüfung.

    Akzeptiert das Original-ZIP von md380.org, die verpackte Update-Datei
    MD-380-D2.32(AD).bin oder ein bereits ausgepacktes D002.032.bin.
    Alle drei Wege werden über feste SHA-256-Prüfsummen geprüft.
    Rückgabe: (Abbild, "verified").
    """
    if data[:4] == b"PK\x03\x04":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = archive.namelist()
                member = FIRMWARE_ZIP_MEMBER if FIRMWARE_ZIP_MEMBER in names else next(
                    (n for n in names if n.endswith("MD-380-D2.32(AD).bin")), None
                )
                if member is None:
                    raise FirmwareFormatError(
                        "Im ZIP fehlt die Datei MD-380-D2.32(AD).bin (Firmware 2.32)."
                    )
                data = archive.read(member)
        except zipfile.BadZipFile as error:
            raise FirmwareFormatError("Das ZIP-Archiv ist beschädigt.") from error
    if data.startswith(WRAPPED_MAGIC):
        if sha256(data) != WRAPPED_SHA256:
            raise FirmwareFormatError(
                "Das ist eine andere Firmware-Version. Benötigt wird MD-380 Version 2.32 (D002.032)."
            )
        image = unwrap(data)
        if sha256(image) != UNWRAPPED_SHA256:
            raise FirmwareFormatError("Die Firmware ließ sich nicht korrekt auspacken.")
        return image, "verified"
    if sha256(data) == UNWRAPPED_SHA256:
        return data, "verified"
    raise FirmwareFormatError(
        "Die Datei ist keine MD-380-Firmware 2.32 (weder Original-ZIP noch Update-Datei "
        "noch ein passendes D002.032.bin)."
    )


def check_core(data: bytes) -> None:
    if len(data) != CORE_SIZE or sha256(data) != CORE_SHA256:
        raise FirmwareFormatError(
            "Das RAM-Abbild passt nicht. Benötigt wird d02032-core.img aus md380tools (131072 Byte)."
        )
