from enum import Enum, auto

from upytl import (
    Template, Component, Tag as UTag, html as h, Slot, SlotTemplate
)
from upytl.helpers import islice_dict


class ModifierTypeEnum(Enum):

    def _generate_next_value(self, name: str, *args):
        return f"is-{name.lower().replace('_', '-')}"


class BulmaBase(UTag):
    tag_name = 'div'


class Container(BulmaBase):

    class ContainerTypes(ModifierTypeEnum):
        widescreen = auto()
        fullhd = auto()
        max_desktop = auto()
        max_widescreen = auto()

    ident_class = 'container'


# level
class Level(BulmaBase):
    ident_class = 'level'


class LevelLeft(BulmaBase):
    ident_class = 'level-left'


class LevelRight(BulmaBase):
    ident_class = 'level-right'


class LevelItem(BulmaBase):
    ident_class = 'level-item'


# media
class Media(BulmaBase):
    ident_class = 'media'


class MediaLeft(BulmaBase):
    ident_class = 'media-left'


class MediaRight(BulmaBase):
    ident_class = 'media-right'


class MediaContent(BulmaBase):
    ident_class = 'media-item'


# hero
class Hero(BulmaBase):
    ident_class = 'hero'


class HeroHead(BulmaBase):
    ident_class = 'hero-head'


class HeroBody(BulmaBase):
    ident_class = 'hero-body'


class HeroFoot(BulmaBase):
    ident_class = 'hero-foot'


# section
class Section(BulmaBase):
    ident_class = 'section'


# footer
class Footer(BulmaBase):
    ident_class = 'footer'


# elements
class Box(BulmaBase):
    ident_class = 'box'


class Button(BulmaBase):
    ident_class = 'button'
    tag_name = 'button'


class Content(BulmaBase):
    ident_class = 'Content'


class DelButton(BulmaBase):
    ident_class = 'delete'
    tag_name = 'button'


class Icon(Component):

    def __init__(self, icon='home', text='', size='', **kw):
        args = islice_dict(locals().copy(), start=1, stop='kw')
        super().__init__(**dict(args), **kw)

    template = {
        h.Span(Class=[b'icon', ('is-{size}', 'size')]): {
            h.I(Class='fas fa-{icon}'): None
        },
        h.Span(If='text'): {
            h.Text(): '[[text]]'
        }
    }


class IconText(BulmaBase):
    ident_class = 'icon-text'
    tag_name = 'span'


class Image(Component):

    def __init__(self, src='https://bulma.io/images/placeholders/64x64.png', size_or_ratio='64x64', **kw):
        args = islice_dict(locals().copy(), start=1, stop='kw')
        super().__init__(**dict(args), **kw)

    template = {
        h.Figure(Class='image is-{size_or_ratio}'): {
            h.Img(src='{src}'): ''
        }
    }


class Tag(BulmaBase):
    ident_class = 'tag'


class Title(BulmaBase):
    ident_class = 'title'
    tag_name = 'p'


class SubTitle(BulmaBase):
    ident_class = 'subtitle'
    tag_name = 'p'


# notification
class Notification(BulmaBase):
    ident_class = 'notification'


# Nav
class Navbar(BulmaBase):
    ident_class = 'navbar'


class NavbarBrand(BulmaBase):
    ident_class = 'navbar-brand'


class NavbarItem(BulmaBase):
    ident_class = 'navbar-item'
    tag_name = 'a'


class NavbarBurger(Component):
    props = []

    template = {
        h.A(Class='navbar-burger'): {
            h.Span(For='i in range(3)'): ''
        }
    }


class NavbarMenu(BulmaBase):
    ident_class = 'navbar-menu'


class NavbarStart(BulmaBase):
    ident_class = 'navbar-start'


class NavbarEnd(BulmaBase):
    ident_class = 'navbar-end'


class NavbarLink(BulmaBase):
    ident_class = 'navbar-link'
    tag_name = 'a'


class NavbarDropdown(BulmaBase):
    ident_class = 'navbar-dropdown'


class NavbarHR(BulmaBase):
    ident_class = 'navbar-divider'
    tag_name = 'hr'


class NavbarDD(Component):

    def __init__(self, name='More', is_boxed=False, **kw):
        args = islice_dict(locals().copy(), start=1, stop='kw')
        super().__init__(**dict(args), **kw)

    template = {
        NavbarItem(Tag='div', Class='has-dropdown is-hoverable'): {
            NavbarLink(): '[[name]]',
            NavbarDropdown(Class=['is_boxed']): {
                Slot(SlotName='content'): {
                    NavbarItem(For='i in range(3)'): 'content-[[i]]',
                    NavbarHR(): None,
                    NavbarItem(): 'About',
                }
            }
        }
    }


class NavBase(Component):
    props = []

    template = {
        Navbar(): {
            NavbarBrand(): {
                Slot(SlotName='brand'): 'UPYTL',
                NavbarBurger(): '',
            },
            NavbarMenu(): {
                NavbarStart(): {
                    Slot(SlotName='start'): {
                        NavbarItem(For='i in range(3)'): 'start-[[i]]',
                        NavbarDD(): None
                    },
                },
                NavbarEnd(): {
                    Slot(SlotName='end'): '',
                }
            }
        }
    }


class Breadcrumb(Component):
    tag_name = 'nav'

    def __init__(self, align='', sep='', **kw):
        args = islice_dict(locals().copy(), start=1, stop='kw')
        super().__init__(**dict(args), **kw)

    template = {
        h.Nav(Class=[b'breadcrumb', ('is-{align}', 'align'), ('has-{sep}-separator', 'sep')]): {
            h.UL(): {
                Slot(): ''
            }
        }
    }


class BreadcrumbItem(Component):

    def __init__(self, href='#', icon='', text='', is_active=False, **kw):
        args = islice_dict(locals().copy(), start=1, stop='kw')
        super().__init__(**dict(args), **kw)

    template = {
        h.LI(Class=['is_active']): {
            Slot(): {
                h.A(href='{href}'): {
                    Icon(If='icon', icon='{icon}', size='small', text='{text}'): '',
                    h.Text(Else=''): '[[text]]'
                }
            }
        }
    }


class MenuItem(BreadcrumbItem):

    template = {
        h.LI(): {
            Slot(): {
                h.A(Class=[b'icon-text', 'is_active'], href='{href}'): {
                    Icon(If='icon', icon='{icon}', size='small', text='{text}'): '',
                    h.Text(Else=''): '[[text]]'
                }
            },
            Slot(SlotName='menu'): ''
        }
    }


class MenuTag(BulmaBase):
    ident_class = 'menu'
    tag_name = 'aside'


class MenuLabelTag(BulmaBase):
    ident_class = 'menu-label'
    tag_name = 'p'


class MenuSection(Component):
    def __init__(
            self, label='General',
            items=[
                dict(name='Dashboard', href='#', icon='home'),
                dict(name='TODO', href='#', icon='', is_active=True,
                    menu=[
                        dict(name='todo 1', href='#'),
                        dict(name='todo 2', href='#'),
                        dict(name='todo 3', href='#'),
                    ]
                ),
                dict(name='Users', href='#', icon='users'),
            ], **kw
    ):
        args = islice_dict(locals().copy(), start=1, stop='kw')
        super().__init__(**dict(args), **kw)

    template = {
        MenuLabelTag(): '[[ label ]]',
        h.UL(Class='menu-list'): {
            MenuItem(
                For='it in items', text='{it[name]}', icon={'it.get("icon")'}, href={'it.get("href")'},
                is_active={'it.get("is_active")'}
            ): {
                SlotTemplate(If='it.get("menu")', Slot='menu'): {
                    h.UL(): {
                        MenuItem(
                            For='sub_it in it["menu"]', text='{sub_it[name]}',
                            icon={'sub_it.get("icon")'}, href={'sub_it.get("href")'},
                            is_active={'sub_it.get("is_active")'}
                        ): None
                    }
                }
            }
        }
    }


class Page(Component):

    def __init__(self, title: str = 'UPYTL Bulma Page', fixed_navbar: str = '', **kw):
        '''
        Args:
            title: A nice page title
            fixed_navbar: 'top' | 'bottom'
        '''
        args = islice_dict(locals().copy(), start=1, stop='kw')
        super().__init__(**dict(args), **kw)

    template = {
        h.Html(): {
            h.Head(): {
                h.Title(): '[[title]]',
                h.Meta(charset='utf-8'): '',
                h.Meta(name="viewport", content="width=device-width, initial-scale=1"): '',
                h.Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css"): '',
                h.Script(src="https://kit.fontawesome.com/5c105e6ebd.js", crossorigin="anonymous"): '',
                Slot(SlotName='scripts'): '',
            },
            h.Body(
                Class={
                    'has-navbar-fixed-top': 'fixed_navbar=="top"',
                    'has-navbar-fixed-bottom': 'fixed_navbar=="bottom"'
                }
            ): {
                Slot(): {
                    NavBase(Class='is-primary'): {
                        SlotTemplate(Slot='brand'): {
                            NavbarItem(): 'UPYTL'
                        }
                    }
                }
            }
        },
    }
