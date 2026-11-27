from upytl import SlotsEnum


class S(SlotsEnum):
    scripts = ()
    default = ()
    footer = ()


def test_members_are_not_aliased():
    # Members all declared as `()` must stay distinct: on Python 3.13+ Enum
    # aliases members whose values compare equal at class creation.
    assert [m.name for m in S] == ['scripts', 'default', 'footer']
    assert S.default is not S.scripts and S.footer is not S.scripts


def test_each_member_targets_its_own_slot():
    assert S.default.value.slot == 'default'
    assert S.footer.value.slot == 'footer'
