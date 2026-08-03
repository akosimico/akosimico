"""Embedded canonical ASCII portrait used by the SVG renderer."""

from __future__ import annotations

import base64
import hashlib
import zlib
from typing import Final


_PORTRAIT_SHA256: Final[str] = "81f21b4f2ec1a214548fed974a258a15431e7bca0b19f30290dc72bedc956d41"

_PORTRAIT_B85: Final[str] = (
    "c-pm?ZH~ks2!{X9DNKxiBzOQ4lezz?7EoJj{c0ymGTUi8`V@IVx*@EM<a0GtD`(|*m$TD8i|Hxc0fj<CD+6~R^owml_-DUD="
    "$$9LND(|6;EGZC^8|t<2xTw@V#NAhyGqsBGVtZ0P!ViAIf$|t22rDrr_`FE50;CMQ4l;`e)x1#prAm$eoFcryrZr|ju`cMBe"
    "nsGf{Do$cCx7Y0i>Gj#yD;!3Kegvz*KAZ*^0V&bA<PpfmG%QqO@KCSVL}_zZ4J5?(nHBRH*=gx^sOt^_wn;q^x!B%jT@8ORq"
    "*6`7ndr3j`mcw>o=e&c;iUJb`p75F=cRPz=bb;gqq26g>hjQWv5WoFRrWX%{QnA%rRKAXJqejLInSzA>C_QawD}v}7pwNGvH"
    "Y+3hbJr&ZEAtz|RHx<GoCkag;bvjAYTfLYBh`Qlx@O+L;Oh46F=(4q^8Ca0`k-"
    "dh}FzL%}|0pu71JYSmE$^1uX<g5fH;?$Roj8Bt)XO=5H4q~$bLGR}fkF|9upRLUojwGpQ<(rEQf}W`BghUOBAo7<JnDV4XJZ"
    "tW%JuvAj>sXghkVz1J#n^%9=rmuJZ<X%q$f&7%5_lwIg4TH_neQbvA^KA6kzPVB-Bt*OulVAOO@DG_iMO8kZK*dEC36y@?op"
    "mW?gIoOo62Qx<dxDQ9ZPQHzGe$j+Ro~dNt6(vcq1aC%Of3-"
    "9SL{+J}5!DVUUKHy7AjgMp{rpU`$N+O!KCM{muTfYEycY^Wvg4=s{>E#*@NFqc>YF4PG2SyNp7?6nU>G6SnN?Nto*0=tmltu"
    "ciBHZ9=lYp?clxn3QA)?;$&8xY4ut&k$``|JxJpzN8k<A?8O2Xlc>9Wrl>S?p}D})BZS#TAR7AA#Ru@#<aKILud>U%#V;<?r"
    "{Jy*%pwwGP!e6S8(FUPE5?)6RQ@@%#Vd9x98|Aml&9FK(?04Oxz<#@7XY5l#l5_&a0-"
    "cPE)($Q_c?pZbp#C<uQd60yK=qEhwLn(-VsP?{3JbzMPOhj<*g&"
)


def portrait_bytes() -> bytes:
    """Decode the embedded portrait payload without requiring a tracked source asset."""

    return zlib.decompress(base64.b85decode(_PORTRAIT_B85.encode("ascii")))


def _load_portrait() -> tuple[str, ...]:
    try:
        raw = portrait_bytes()
        text = raw.decode("utf-8")
    except (ValueError, zlib.error, UnicodeDecodeError) as exc:
        raise RuntimeError("embedded ASCII portrait payload is invalid") from exc
    if hashlib.sha256(raw).hexdigest() != _PORTRAIT_SHA256:
        raise RuntimeError("embedded ASCII portrait digest does not match the approved artwork")
    lines = tuple(text.splitlines())
    if len(lines) != 55 or any(len(line) != 100 for line in lines):
        raise RuntimeError("embedded ASCII portrait must contain 55 lines of 100 characters")
    return lines


ASCII_PORTRAIT: Final[tuple[str, ...]] = _load_portrait()
