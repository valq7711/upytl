from upytl import (
    Component, Template, Slot, SlotTemplate, UPYTL, html as h
)
import upytl.bulma as bm

t = {
    bm.Page(title='{page_title}'): {
        bm.NavBase(Class='is-primary'): {
            SlotTemplate(Slot='brand'): {
                bm.NavbarItem(): 'UPYTL'
            }
        },
        bm.Breadcrumb(align='centered', sep='bullet'): {
            bm.BreadcrumbItem(icon='home', text='Home'): None,
            bm.BreadcrumbItem(icon='book', text='Doc', is_active=True): None,
        },
        bm.MenuSection(): None

    }
}


u = UPYTL()


@u.view(t)
def demo():
    return dict(page_title='UPYTL Bulma')


rendered = demo()

print(rendered)

from pathlib import Path

Path('bulma_demo.html').write_text(rendered, encoding='utf8')
