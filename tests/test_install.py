from upytl import (
    Component, Slot, SlotTemplate, UPYTL, UHelper, html as h, Tag, SlotsEnum
)

upytl = UPYTL()


t = {
    h.Div(): 'Hello [[ which_world ]] world!'
}


expected = \
"""
<div>
  Hello Python world!
</div>"""


def test_simple():
    rendered = upytl.render(t, ctx={'which_world': 'Python'}, doctype=None)
    assert rendered == expected
