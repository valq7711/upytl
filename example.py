from upytl import (
    Component, Slot, SlotTemplate, UPYTL, html as h
)

# flake8: noqa E226

# Let's define some custom reusable components

class HTMLPage(Component):
    props = dict(
        footer_class='page-footer',
        page_title="This page has no title :(, but it's fixable - just `HTMLPage(page_title='awesome')`"
    )
    template = {
        h.Html(): {
            h.Head():{
                h.Title(): '[[page_title]]',
                h.Meta(charset=b'utf-8'):'',
            },
            h.Body():{
                Slot(SlotName=b'nav'):{h.Div(): '[there is no default nav]'},
                Slot(SlotName=b'content'):{h.Div(): '[there is no default content]'},
                Slot(SlotName=b'footer'):{
                    h.Div(
                        Class='{footer_class}',
                        Style={'margin':'30px', 'font-family':'monospace', 'font-size':'20px'}
                    ): {
                        h.Text(): 'Created using ',
                        h.A(href={'URL()'}): 'UPYTL',
                    }
                },
            },
        },
    }

class Field(Component):
    props = dict(
        name='[no name]',
        value='',
        type='text',
        # for select
        options=[],
    )

    template = {
        h.Label(If='type=="text"'):{
            h.Text():'[[name]]',
            h.Input(name='{name}', value='{value}'):''
        },
        h.Label(Elif='type=="select"'):{
            h.Text():'[[name]]',
            h.Select(name='{name}'):{
                h.Option(For='opt in options', value='{opt[value]}', selected={'opt["value"]==value'}):
                     '[[ opt.get("name", opt["value"]) ]]'
            },
        },
    }

class Form(Component):
    props = dict(
        fields=None
    )
    template = {
        h.Form(If='fields', action='#'):{
            h.Div(For='fld in fields', Style={'margin':'15px'}):{
                Field(
                    name='{fld[name]}',  type={'fld.get("type", "text")'},
                    value={'fld.get("value", "")'},
                    options={'fld.get("options", None)'},
                ):'',
            },
            h.Button(type='submit'): 'Submit'
        },
        h.Div(Else=''): 'Sorry, no fields were passed to this form'
    }


# Now define a specific page template

t = {
    HTMLPage(footer_class='custom-footer'):{
        SlotTemplate(Slot='content'):{
            h.Div():(
                'Hey [[ user_name.title() ]]! How are you?'
            ),
            h.Div():{
                Form(fields={'fields'}):''
            }
        }
    }
}


# Define context

def URL():
    return 'https://github.com/valq7711/upytl'


# Keep in mind, that context (ctx) passed to render upytl.render
# is inaccessible in custom components, since components are similar to imported functions
# and component props and slots are similar to function arguments.
# So there is an optional `global_ctx` argument, which can be passed to UPYTL
# to provide access to desired stuff from anywhere including custom components

upytl = UPYTL(global_ctx=dict(URL=URL))

ctx = dict(
    page_title='UPYTL example',
    user_name = 'john',
    fields=[
        {'name': 'Friend Name', 'value': 'Tom?'},
        {'name': 'Email'},
        {
            'name': 'Favorite Color', 'type': 'select', 'value': '#888888',
            'options': [
                dict(name='red', value='#FF0000'),
                dict(name='geen', value='#00FF00'),
                dict(name='blue', value='#0000FF'),
                dict(name='gray', value='#888888'),
            ],
        }
    ]
)

rendered = upytl.render(t, ctx, indent=2)

print(rendered)

with open('example.html', 'w', encoding='utf8') as out:
    out.write(rendered)

print('\n'*2, '****** rendered with metatags ************')
print(upytl.render(t, ctx, indent=2, debug=True))
