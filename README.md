# UPYTL
### The Ultra Pythonic Templating Language

UPYTL is a lightweight, fully fucntional, self contained python package, designed to enable rapid generation and rendering of feature rich context driven `HTML` pages in a structured, Pythonic manner totally eliminating code repetition.

The `Slot`, `Template`, `Component` architecture, (similar in both functionality AND flexibilty to their `Vue.Js` equivalents), allows development of multiple, re-useable, self contained components that can be used throughout your project or across multiple projects with no risk whatsoever of `DOM` contamination or conflicts.

UPYTL can be used standalone or easily integrated into any `context driven application framework` in order to render stunning, feature rich, HTML pages dynamically. 

## Installation And Usage
`python -m pip install upytl`


```Python
from upytl import UPYTL, html as h

t = {
  h.Div(): 'Hello [[ which_world ]] world!'
}

upytl = UPYTL()

rendered = upytl.render(t, ctx={'which_world':'Python'}, doctype=None)
print(rendered)
```

```HTML
<div>
  Hello Python world!
</div>
```

## Features Supported:

- `For`-loop
- `If`-`Elif`-`Else`
- component selector `Is`
- custom components with `Slot`(s)
- extending component context via `get_context()`
- recursive component templates using `template_factory()`

## Overview
UPYTL supports all standard HTML `tags` and `tag attributes` as standard and as can be seen from the above example it uses native python `dict` for defining template structure, where `dict`-keys are used to hold `tags` with their `attributes` and `dict`-values are used to hold tag-content.
So the general syntax is:
```python
some_template = {
    SomeTagClass(attr1='attr-value', attr2='attr-value', ...): {
        AnotherTagClass(attr1='attr-value', ...): 'text content'
    }
}
```

The `default` render-behaviour for `attributes` is `str.format()`, so you can
```Python
h.Div(Class='{header_class}'): 'Header'

# or even
h.Div(Class='{class_map[header]}'): 'Header'

# note that `key` must be unquoted - see `str.format()` doc

```
If you don't want any processing - just pass `bytes`

```Python
h.Div(Class=b'no-{processing}'): 'Header'
```

To evaluate python expressions pass string wrapped in `set`

```Python
h.Button(disabled={'not allow_submit'}): 'Submit'
```

If an attribute value is a Python expression (like the one above) and if it is evaluated to a boolean value (`True`/`False`)
then it is rendered without the value (`True`) or not rendered at all if (`False`).
So in the above example if `allow_submit` is falsy i.e. `not allow_submit` is `True` we'll get

```HTML
<button disabled>Submit</button>
```

## `For`-loop, `If`-`Elif`-`Else`

UPYTL provides a number of `special` attributes namely : `For`, `If`, `Elif`, `Else`. Their values are always treated as `python` expressions except for `Else` - its value is ignored.
Also note that `For`-syntax is a bit lighter when compared to pure python `for`.

```Python
t = {
    h.Template(For='k in range(5)'):{
        h.Div(If='k == 1'): 'This is div number one',
        h.Div(Elif='k != 3'): 'This is #[[ k ]] div',
        h.Div(Else=''): 'This will be div #3',
    }
}
```
##### Note: the use of the `h.Template()` tag above - `h.Template()` is meta-tag, it is not rendered in the output and is intended to organize template logic. 

```HTML
<div>
  This is #0 div
</div>
<div>
  This is div number one
</div>
<div>
  This is #2 div
</div>
<div>
  This will be div #3
</div>
<div>
  This is #4 div
</div>
```

## `Is`-selector

```Python
t = {
    h.Template(For="key in ['inline', 'block']", Is='{key}'): {
        'block': {
            h.Div(): 'key: [[key]]'
        },
        'inline': {
            h.Span(): 'key: [[key]]'
        }
    }
}
```

```HTML
<span>
  key: inline
</span>
<div>
  key: block
</div>
```

## Components
Components form the backbone of the underlying design philosophy behind `UPYTL`. A UPYTL component can be anything from a fully functioning autonomous block to a specifc `tag` or element of another component. In order to better understnd the power and flexability of `components` lets take a look at a real life use case:

One of the most important functions of any interactive application is the ability to provide notifications of events and request actions from the end user. The html `notification` class is commonly used for this purpose so let us take a look at how we can create a `multi-purpose` custom notification `component` that can be used to process any notifications of any state with any message produced by our application without the need to code seperate code blocks for each condition.

## Custom Components - Markup Extension

```Python

## my_components.py

from upytl import Component, UPYTL, html as h

class Notify(Component):
    props = {
        'note': 'If you see this, please open an issue',
        'status': 'info',
    }

    template = {
        h.Div(Class='notification-{status}'): '[[ note ]]'
    }


t = {
    Notify(): None,
    Notify(note='Today is Monday :('): None,
    Notify(note='Something went wrong!', status='error'): None,
}
````
The first thing to note is that our component uses `props = { ... }` - this is the simple way to define component-specific arguments. 
##### Note: Components are rendered in its own context defined by props. 
If no `props` are passed to the component we render using `default` values of the props.
This allows us to design our component with default characteristics and attributes that will be `overriddedn` by any valid `props` passed in.

The other thing to note is the difference in syntax between `'{ ... }'` and `'[[ ... ]]'` and their uses. We use `[[ ... ]]` delimiters in text-body to avoid overlapping with front-end (e.g. vue.js) templates, that use `{{ ... }}`.

```HTML
<div class="notification-info">
  If you see this, please open an issue
</div>
<div class="notification-info">
  Today is Monday :(
</div>
<div class="notification-error">
  Something went wrong!
</div>
```

In order to make our `custom component` even more `flexible` we can use `Slots`  

### Slots

Slots are a convenient way of passing content to components through specific tags (slots).

```Python
from upytl import Component, UPYTL, html as h, Slot

class Notify(Component):
    props = {
        'status': 'info',
    }

    template = {
        h.Div(Class='notification-{status}'): {
            Slot(): 'If you see this, please open an issue'
        }
    }

t = {
    # ! pass `None` to get default slot content rendered, any other stuff
    # e.g. empty string, will be treated as slot content
    Notify(): None,
    Notify(status='error'): 'Something went wrong!',
}
```

```HTML
<div class="notification-info">
  If you see this, please open an issue
</div>
<div class="notification-error">
  Something went wrong!
</div>
```

### Typical `Slot` use case
One of the most common uses for `Slots` that demonstrates the power of combining `Slots` and `Components` is a typical `Page`. As we will be usng any number of `Pages` in our app lets define a simple re-useable, configurable `HTMLPage` componenet.

```python

## components.py
## simple customisable page component

class HTMLPage(Component):
    props = dict(
        page_title="Some Nice Title"
        footer_class='page-footer',
    )
    template = {
        h.Html(): {
            h.Head():{
                h.Title(): '[[page_title]]',
                h.Meta(charset=b'utf-8'):'',
                Slot(SlotName='head_extra'): '',  # to allow to pass css/scripts 
            },
            h.Body():{
                Slot(SlotName='nav'): {h.Div(): 'there is no default nav'},
                Slot(SlotName='content'): {h.Div(): 'there is no default content'},
                Slot(SlotName='footer'): {
                    h.Div(
                        Class='{footer_class}',
                        Style={'margin':'30px', 'font-family':'monospace', 'font-size':'20px'}
                    ): {
                        h.Text(): 'Created using ',
                        h.A(href={'URL()'}): 'UPYTL',  # assuming that `URL()` is accessible globally
                    }
                },
            },
        },
    }
```

By utilizing `Slots` in our components we immediatley have a components that provides all the sections that each of our pages will have. 
Including this component now in any template will render the default values of the `Slot's`

### Better IDE Support
Defining component attributes via `props` is suitable in most cases.
For more complex cases however, we can use `__init__` and `SlotsEnum`

```python
from upytl import Component, UPYTL, html as h, Slot, SlotsEnum

class Notify(Component):

    # by typing `Notify.S.` we can get which slots component has
    class S(SlotsEnum):
        title = ()
        default = ()

    def __init__(self, status='info', **kw):
        '''This component is rendered as `<div class='notification-{status}>`
        Args:
            status: info | warning | error
        '''
        super().__init__(status=status, **kw)

    template = {
        h.Div(Class='notification-{status}'): {
            h.Div(Class='title'): {
                S.title.slot(): 'Notification',
            },
            S.default.slot(): 'If you see this, please open an issue',
        }
    }

t = {
    # By default, content passed to the component goes into the `default` slot (if there is one)
    Notify(): 'All good',

    # If the component has more than one slot, we should specify the slot we wish to insert our content into.
    Notify(status='error'): {
        Notify.S.title(): 'Error',
        Notify.S.default(): 'Something went wrong!'
    }
}
```

```HTML
<div class="notification-info">
  <div class="title">
    Notification
  </div>
  All good
</div>
<div class="notification-error">
  <div class="title">
    Error
  </div>
  Something went wrong!
</div>
```

## Component Context Helper - get_context()
Occasionally it is necessary for more complex `logic` at the component level than tha standard `For If, Eleif, Else ...`. For these situations UPYYTL has a convenience method that allows us to perform complex functions using standard `python` fucntions or even using functionality from imported external libraries. In fact the `For If, Eleif, Else ...` logic needed by the component could be moved completely into the `get_context method` with the same result.

```Python
from upytl import Component, UPYTL, html as h

class Notify(Component):
    props = {
        'note': 'If you see this, please open an issue',
        'status': 'info',
        'notification : ''
    }

    template = {
        h.Div(Class='notification-{status}'): '[[ notification ]]'
    }
    
    def get_context(self, rprops):
        if rprops['status'] == 'error':
            notification = rprops['note'].upper()
        else:
            notification = rprops['note']
        
        return{ **rprops, 'notification':notification }


t = {
    Notify(): None,
    Notify(note='Today is Monday :('): None,
    Notify(note='Something went wrong!', status='error'): None,
}
````

```HTML
<div class="notification-info">
  If you see this, please open an issue
</div>
<div class="notification-info">
  Today is Monday :(
</div>
<div class="notification-error">
  SOMETHING WENT WRONG!
</div>
```

## The Template Factory - template_factory()
The `template_factory` is another convenience method which allows recursive use of the same component in a template. In order to demonstrate this letst create a simple component 

```python
class TreeView(Component):
    """
    This component demonstrates the use of the `template_factory` method
    which allows recursive use of a single component in its template.
    """
    props = dict(
        tree=[],
        depth=0
    )

    @staticmethod
    def template_factory(cls):
        TreeView = cls
        return {
            h.Div(For='it in tree', Style={'margin-left': {'f"{depth * 4}px"'} }): {
                h.Div(): '[[ it["name"] ]]',
                TreeView(If='"nodes" in it', depth={'depth+1'}, tree={'it["nodes"]'}): ''
            },
        }
```
Now lets use it in a simple template
```python
t = {
    h.Div():{
        h.H4():'Tree-view example:',
        TreeView(tree={'tree'}):{}
    }
}

## Set up our `Context` with the values to render

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
    tree=[
        {
            'name': 'Top',
            'nodes': [
                {'name': 'child-1'},
                {
                    'name': 'child-2',
                    'nodes': [
                        {'name': '2-child-1'},
                        {'name': '2-child-2'},
                        {
                            'name': '2-child-3',
                            'nodes': [
                                {'name': '2-child-3/#1'},
                                {'name': '2-child-3/#2'},
                            ]
                        },
                    ]
                },
                {'name': 'child-3'},
            ]
        },
    ]
)

rendered = upytl.render(tree, ctx, indent=2)

print(rendered)
```

```HTML
<!DOCTYPE html>
<div>
  <h4>
    Tree-view example:
  </h4>
  <div style="margin-left:0px">
    <div>
      Top
    </div>
    <div style="margin-left:4px">
      <div>
        child-1
      </div>
    </div>
    <div style="margin-left:4px">
      <div>
        child-2
      </div>
      <div style="margin-left:8px">
        <div>
          2-child-1
        </div>
      </div>
      <div style="margin-left:8px">
        <div>
          2-child-2
        </div>
      </div>
      <div style="margin-left:8px">
        <div>
          2-child-3
        </div>
        <div style="margin-left:12px">
          <div>
            2-child-3/#1
          </div>
        </div>
        <div style="margin-left:12px">
          <div>
            2-child-3/#2
          </div>
        </div>
      </div>
    </div>
    <div style="margin-left:4px">
      <div>
        child-3
      </div>
    </div>
  </div>
</div>
```

## The Script Tag
Including `JS` or `Jquery` functionality in our components is facilitated by the use of the `h.Script` tag.

A classic example or use case would be the `navbar burger` functionality required by most contemporary html pages in order to make them `responsive` or moblie friendly.

```python
## Example Navbar Component using Bulma

from . my_components import NavBarItem
 
class NavBar(Component):
    props = dict(
        menu = [],
        user = '',
        buttons=[]
    )
    template = {
        h.Nav(Class='navbar is-light', Role='navigation'): {
            h.Div(Class='navbar-brand'): {
                h.A(Class='navbar-item', href={'URL("index")'}):{
                    h.Img(src={'URL("static/upytl.png")'}, height="100"):'',
                },
                h.A(
                    **{'aria-label':'menu', 'aria-expanded':"false"},
                    **{'data-target':"navbarStandard"},
                    role="button",
                    Class="navbar-burger is-active" 
                ):{
                    h.Span(**{'aria-hidden':'true'}):'',
                    h.Span(**{'aria-hidden':'true'}):'',
                    h.Span(**{'aria-hidden':'true'}):'',
                }

            },
            h.Div(Id="navbarStandard", Class="navbar-menu is-active"):{
                h.Div(Class='navbar-start'):{
                    h.Template(For='item in menu'):{
                        NavBarItem(
                            item = {'item'},
                        ):'',
                    },
                },
                h.Div(Class='navbar-end'): {
                    h.Div(Class='navbar-item'): {
                        h.Div(): 'Welcome [[ user ]]',
                    },
                    h.Div(Class='navbar-item'): {
                        h.Template(If = 'not buttons'):{
                            h.Div(): '',
                        },
                        h.Template(Else = ''):{
                            h.Div(Class='buttons'):{
                                h.A(For = 'b in buttons',Class={'b.get("class", "button")'}, Href={'b.get("href", "index")'}):'[[ b["name"] ]]',
                            }
                        }        
                    }
                }
            },
            h.Script(): 
            '''
            $(document).ready(function() {
                // Check for click events on the navbar burger icon
                $(".navbar-burger").click(function() {
                    // Toggle the "is-active" class on both the "navbar-burger" and the "navbar-menu"
                    $(".navbar-burger").toggleClass("is-active");
                    $(".navbar-menu").toggleClass("is-active");
                });
            });
            '''
        }
    }
```
Provided that the appropriate `NavBarItem` component is available this component will render as expected and have a fully functional collapsible navbar-burger button which will either show or hide the navbar in responsive mode.

#### make sure you have the appropriate JQuery library loaded in the parent template.

The other thing to note is the use of `funny attributes` as in ```**{'aria-label':'menu', 'aria-expanded':"false"}```. These are necessary for html attributes with a '-'.

## Putting it all together
Now that we have seen power of `Components` and how they interact with `Templates` and how both can facilitate the use of `Slots` to provide maximum flexibilty and functionality lets take a look at a typical use case.

Our application will consist of a number of `Pages`. Each `Page` will consist of a number of distinct `Components`. In our case lets have a Header/Navbar, Notification area, a Body (which dsiplays the page content) and a footer. Pretty much the standard anatomy of a page.

So far we have created a `Notify` component, a `NavBar` component and the `Body` or `Content` will be whatever we want it to be. So lets create a HTMLPage component which ties all this together.

```Python
## file my_components.py
## A typical simplified page component 

class HTMLPage(Component):
    props = dict(
        footer_class='page-footer',
        page_title="This is the page_title placeholder",
        nav = "This is our navbar placeholder"
    )
    template = {
        h.Html(): {
            h.Head():{
                h.Title(): '[[page_title]]',
                h.Meta(charset=b'utf-8'):'',
                },
                
            h.Body():{
                h.Link(rel='stylesheet', href='https://cdnjs.cloudflare.com/ajax/libs/bulma/0.9.4/css/bulma.min.css'):None,
                
                h.Script(src="https://code.jquery.com/jquery-3.5.1.js"):None,
    
                Slot(SlotName=b'nav'):{
                    h.Div():'[ No NavBar passed to the page ]'
                },
                
                Slot(SlotName=b'notification'):{
                    h.Div():'[ No Flash Message passed to the page ]'
                },
                
                Slot(SlotName=b'content'):{
                    h.Div(): '[ No default content ]'
                },
                
                Slot(SlotName=b'footer'):{
                    h.Footer(Class="footer is-small"):{
                        h.Div(Class= "content has-text-centered"):{
                            h.Template():{
                                h.P(): 'Powered by UPYTL (c) 2023',
                            }    
                        }
                    }
                }
            }
        }
    }
```

Here we define out HTMLPage component which we can use throughout our application givng us complete uniformity or "look and feel" irrespectrive of content being displyed. For the sake of simplicity we have defined the footer in the page component but equally as well we could have created a seperate `PageFooter` component.


and the corresponding template:

```python

## file my_templates.py
## Make sure all components referenced have been defined and are imported 
## Best practice is to store components is a seperate file or files that can be imported as such

from . my_components import StandardNavBar, Notify


t = {
    HTMLPage(footer_class='custom-footer'):{
        SlotTemplate(Slot='nav'):{
            StandardNavBar( menu={'menu'}, user={'user'}, butons={'buttons'})): '',
        },
        
        SlotTemplate(Slot='flash'):{
            Notify(status='success'): 'Hello and Welcome',
        },
        
        SlotTemplate(Slot='content'):{
            h.Template():{
                h.Div(Class='box'):{
                    h.Div():'This will be the content and could be anything you want',
                }
            }
        }
    }
}
```
The `footer will atumatically be displyed as defined in the `HTMPage` component.

#### We leave it up to you as an excercise to design and implement the `NavBarItem` component.

## Conclusion
The real power of `UPYTL` is the ability to build re-useable compoents. We strongly reccomend adding all new componenets you develop to a `component library` file which can easliy be uploaded to PyPI and shared amongst team members, colleques and any other collaborators.

UPYTL provides all the tools needed to develop fully functional, flexible and responsive  `DRY - Dont Repeat Yourself` applications. 



