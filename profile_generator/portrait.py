"""Embedded canonical ASCII portrait used by the SVG renderer."""

from __future__ import annotations

import base64
import hashlib
import zlib
from typing import Final


_PORTRAIT_SHA256: Final[str] = "03a5d683e2d29b0a05bf62d76b567f21e620fe9585e607d5e403f92a13261f82"

_PORTRAIT_B85: Final[str] = (
    "c-pO5TW%yF4E*O5Eus0r!UwQ~l>47*ZSyiTbTiqYjgnO|RQpvfyRU0?@cPT+{_b)-1^MDie22mR1^LEy_iIDc6f6eeAA*#7r}OGb_l-"
    "B?M&c9uLFzd6^1(oN?j6h+h<tZy2ja6?TM*n~L_&&;V?gB8>kSH?y9@Kb^@&Lxmh?-"
    "#c5RGt$Bx<_zMsSzYB1l{37#FcCDAT0=$^f`yitE8IVPEwuVzzx>VYYKJ_5Pc2&f1ekrW_+1cV@zxa<RuhZqVVbpjClryZY&QD_x*tRUDDX~Lj"
    ";lrx4!$S@QkQh$^I%smvygrR{@2ys^MegulJ4gEt*28@ygRE~thPcYEZVD_0ii+V|@e2IQz9Pl4TX+Y`DE(`9$El7z_J+(MukZAaf)4WB8ER5D"
    "&&3g@_Jpu^~h}$4~A3Fu$8F%4@WOLHm(Tr9cu9cK+BEvM6>)pPsRW_P1$UY_(m=HMKIP^X1Uo62PChdu7bXO&5q5aR#&yVLX2@BmY(1MKQX>!*"
    "BRDZPxk=7yrf&&0aS$|dW&su?EEsk1?gaZbEqJ)?P1yb=bZp9tW2|R)1o~S@<VCldf#GH^)Zp?IC@wQnQS51w#qDbuvbWViHV-"
    "N0{Sn&Y_q!@pEB&#;=AjXBcVJsBZ1Bev-Pc@`v{R<0sCMgAJk~pqG*pL`$qlw%XjWNz3Mc}1^5$CRjzfvo4X$mk#inAq8JszLc#0rJ^Bx4Y*#i"
    "V;314e`*O$H3eUL#8qgWKG8x@poRb8UH4t#-"
    "sNRIM<=wfLT!7Ea!5jU!ih<1TGkLIJU%PdyPIxC`^6R}(H=6$>j9ZwpjCMMk$Cq;QipE9s?y2OkY(3d~KOU3+(}Mymc}krC3LylNBTv?{#33wj"
    "2@9m%f*yxdu&ke3dXjhRK@{J?HE6<$^ib`&ApiUNWXf#{}XC%?F3t(_Byl0ga53FS-LVUrzpDlQ=ST7r5+yA$6^6go<fh6@l=C6!KI_|O@*avl"
    "N;_aLey`hG$XQ_L)^W91PG+uqYb*a&r1&_0+kyms|mjg?tms2&F~HRMbb5Cplm>uevm<!Vf75>s4`zq=GBoBWbgoUl<HR6*oF9}RjPes8i4UzP"
    "=pa>X7tBgiubJv}7w(aLX+bF1g6$KwOP^IXN=M_ClG?15n7E^}OcnyYcqBpWsx2}>oUJR*{vr)W{V1tkbb2qts4dym&4h%$;!ojevw1~gkZ(Ly"
    "3SE-W#2BX*~*!n7gx5D*0qH7=6PF!Yk$0%wvJIE{>@XFzF)jN-"
    "c~>_@InBFl9T?!s#~Uzf&IY~#3u?l2}4U)$n!6OIc7xt)C*NEwEBvVsC5+Yab0d57YTq%h`bL2r^IP6Z`O;*Cn;M!|bY)LdM|NW`}L5}JgR%aU"
    "{2=lNa9@#^j5MAc6ni^$02C|sN*#f1O)du{iv>s)U$BaXgm{L;#le-"
    "=_?e+9k2X1Wd~(xB&I4qq(Mk1sZ=NlXB(_r{I1U8)^`;O!SW8!D4=y~kwtglm>`?|pHhC&gc~59FDe65W?>QyRHzr-"
    "?RulG<QEhIUy#GZ}QrmGgI=v0vP^=%=+G^N~)d`E5qC)r8=73$^E+b#@t$1|;?2XZ^>!-O6V9dJVgXvJfn>KYZ(O8-kxc*__EJ^Izh-S~-"
    "6O(?s+8OB&p6I*(p)tqsO=OAg*J9em1tcjGT#0saFnrCa|"
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
    if len(lines) != 72 or any(len(line) != 100 for line in lines):
        raise RuntimeError("embedded ASCII portrait must contain 72 lines of 100 characters")
    return lines


ASCII_PORTRAIT: Final[tuple[str, ...]] = _load_portrait()
