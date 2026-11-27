"""Inline text tags render as their own elements (Strong, Mark next to B, Em, Span)."""
import re

from upytl import UPYTL, html as h


def test_strong_and_mark_render():
    t = {h.P(): {h.Strong(): 'bold', h.Mark(): 'marked', h.Em(): 'em'}}
    out = re.sub(r'\s+', '', UPYTL().render(t, {}))     # upytl indents; compare the markup only
    assert '<strong>bold</strong>' in out
    assert '<mark>marked</mark>' in out
    assert '<em>em</em>' in out
