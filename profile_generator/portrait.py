"""Embedded canonical ASCII portrait used by the SVG renderer."""

from __future__ import annotations

import base64
import hashlib
import zlib
from typing import Final

_PORTRAIT_SHA256: Final[str] = (
    "1b1a4d1be28da8809d9cb1719ac4897ea99449e1d7eedc98c9d419653885f948"
)
_PORTRAIT_B85: Final[str] = (
    "c%1E6TaMc>4E*0y7!dp;fjj^K0=fUG${{6NO6<h)KECRrX?Cq@G<*)VEWiJJ{Q<^*kpCbP592TMFM{wgvHcy8ps-<GMVn>PECmD>"
    "`?IjfPlGrU*%)-x0$n7KZ-Ts<#`oO6b322-=$GFOVKFliQD7JrsVcoL`W^`TwrVf{DE271?S@5_-YuWl8Exa7)9O#MC+7^%%B)*`"
    "lL<&<+j&hH5D)*b$G@grK##ZMTn5>qh20TmB`vU(7?+}J)|72$yfL#GCj*kO-3@awQ#)n*4Kd|JT~>000a3SX21E|>j>V3y2WzQY"
    "`Wa+9k;rbejSd&{NZAl~qTErr&ZKS3?)GZ+Ma=oB#2bkh)Yi>|v>XPD_L%iZEy@bDbHg9)G`qpBf{b-yahs{)15AWVHfp>t=H6ge"
    "LEPnCac4xal}b&PAQoOy*6jHYf(S1AY7r)LAf6(~4b&0jyLkdgNJ=<Jk|(07CrXYVBv2-*FxMi5ghMf@3Fqw06A7uG@zSe|Cw}$)"
    "WM^d0G~cK6>4p<{C5zk#-L72Tsa+ssC(T`H7tWaqYGn@a=$^|w2>Su6*)n1(0>MxX;IWpHqCQryZxK1w8ND~z4sdtzjS5_C4uG%I"
    "ihtc@?vRD&n-<q1i~s@)1Zs3dj{}Qfg{#8rp7%l1%E1MYu28{Xh*9O1GFk{mQlSW|=wF}`3+zzWm~1KNm61x`YKRhY5qo-riQrBF"
    "0)x3?x@@ir<AMiG)}YKOh#=e26Sa6(1f8`uWwVpaWqgOlUbaX!4HTg)FjsWOWTBRIZzz*_5*v5ba*(RlI3o(5<k7TD?RAea3Ncg*"
    "4C=gVnWvIHo$(w^oNA?2_jkCyz)#OD;TA{$8H874kL0LlMRgDvQ$79!XZ%rK81N5(d_08w1<2npxhd|@051-3EcZbc?-Q3m_&&(u"
    ">HHanhoSG*=%9K&i#Fl6ux=XpUNX`qM$a%H$?_xJslpwMp1`=E2`1k6`94Stbb3^%V$5F9G!up|`c|GeOh5lrjMkZ@Bp>k#2gnie"
    "cOlgJ6@@1471%bt@S@3w$u$ii<9z&%1-AiS(FW7dq6B3NWkq6A&H0O8LAd|n>}dn8*^Gt;$w*g|7)6#A8(+hiIRUb_znU{HEg|Wk"
    "$Gl;_io33@?w2I*Q9?`X>!8W3H)^hq;`}62+w$kDi+51s(@K>VR@Fl1Wmk9hK?LRB=gEO<hBt>;W)=5`Qrv-<C~_5<T}GPGl4bp>"
    "JxH@sbz-M_dguX73bq#vr#5kAGt@3r4PX3<N2yOn9(R2<*%2ARmV%71q!VpZR#A7nuCD(1DC1u@Jr4yO-araI<LbzjuwPR#*-KhZ"
    "R6W1?f8^Rdwx_=d3=q)3z*K5@c=-%+wi}<mNNy(c0K4|u9t3z!`Ud2X-th{8f+sS2Rar?5g}FG0ysN@zHhY4xkwkHklSU9QDQJ$O"
    "Gax54*)jxCg(+SgM&pW&7l7C#GdnsQ{gV7vq7IIgO5DDY`O4(@#p}WMFvaKJ<QI~b81bM7TMVPIeZBqPpI^m$6suJ4J8j4+?IwqP"
    "+CEIiSqwy2T;9Yz?!)<nWXVYWAJW3ZJ&V<2BPJe(iedF1Sl#$7"
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
        raise RuntimeError(
            "embedded ASCII portrait digest does not match the approved artwork"
        )

    lines = tuple(text.splitlines())
    if len(lines) != 72 or any(len(line) != 100 for line in lines):
        raise RuntimeError(
            "embedded ASCII portrait must contain 72 lines of 100 characters"
        )

    return lines


ASCII_PORTRAIT: Final[tuple[str, ...]] = _load_portrait()
