from upytl import (
    Component, Template, Slot, SlotTemplate, UPYTL, html as h, XTemplate, gtag
)
import upytl.bulma as bm

t = {
    bm.Page(title='{page_title}'): {
        bm.Page.S.scripts(): {
            h.Script(src="https://cdn.jsdelivr.net/npm/vue@2/dist/vue.js"): '',
            h.Script(src='upytl.js'): ''
        },
        bm.Page.S.default(): {
            bm.NavBase(Class='is-primary'): {
                SlotTemplate(Slot='brand'): {
                    bm.NavbarItem(): 'UPYTL'
                }
            },
            bm.Breadcrumb(align='centered', sep='bullet'): {
                bm.BreadcrumbItem(icon='home', text='Home'): None,
                bm.BreadcrumbItem(icon='book', text='Doc', is_active=True): None,
            },
            bm.MenuSection(): None,
            XTemplate(): {
                h.Div(): {
                    h.Text(): 'This is just a div ... but it is rendered by Vue.js!',
                    gtag.NiceNonExistingVueComponent({'@click': 'some_meth'}, Class='class'): ''
                }
            }
        }

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
