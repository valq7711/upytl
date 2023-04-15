# UPYTL
### The Ultra Pythonic Templating Language

UPYTL is a lightweight, fully fucntional, self contained python package, designed to enable rapid generation and rendering of feature rich context driven `HTML` pages in a structured, Pythonic manner totally eliminating code repetition.

The `Slot`, `Template`, `Component` architecture, (similar in both functionality AND flexibilty to their `Vue.Js` equivalents), allows development of multiple, re-usable, self contained components that can be used throughout your project with no risk whatsoever of `DOM` contamination or conflicts.

UPYTL can be used standalone or easily integrated into any `context driven framework` in order to render stunning, feature rich, HTML pages dynamically. 

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
- pythonic component pre-processor with `get_context()` function

## General
UPYTL supports all standard HTML `tags` and `tag attributes` as standard and as can be seen from the above example the syntax for defining `tags` and `attributes` is ```h.<tag-name capitalised>(<attribute capatilised>, <attribute capatilised>, ... ): '',``` 

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

UPYTL provides a number of `special` attributes namely : `For`, `If`, `Elif`, `Else`. Their values are always treated as python expressions except for `Else` - its value is ignored.
Also note that `For`-syntax is a bit lighter when compared to pure python.

```Python
t = {
    h.Template(For='k in range(5)'):{
        h.Div(If='k == 1'): 'This is div number one',
        h.Div(Elif='k != 3'): 'This is #[[ k ]] div',
        h.Div(Else=''): 'This will be div #3',
    }
}
```

##### Note:- the use of the `h.Template()` tag above. This is the recommended way to declare conditional `same level` tags

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
Components form the backbone of the underlying design philosophy behind `UPYTL`. A UPYTL component can be anything from a fully functioning autonomous code block to a specifc `tag` or element of another component. In order to better understnd the power and felxibilty of `components` lets take a look at a real life use case:

One of the most important functions of any interactive application is the ability to produce notifications of events and request actions from the end user. This can range from requesting login credentials (if the user is not logged in) to notificaiton of invalid or failed verification of payment details. The html `notification` class is commonly used for this purpose so let us take a look at how we can create a `multi-purpose` custom notification `component` that can be used to process any notifications produced by our application without the need to code seperate code blocks for each condition.

## Custom Components - Markup Extension

```Python
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
The first thing to note is that our component uses `props = { ... }`. If no `props` are passed to the component we render using `default` values of the props.

This allows us to design our component with default characteristics and attributes that will be `overriddedn` by any valid `props` passed in.

The other thing to note is the difference in syntax between ```'{ ... }'``` and ```'[[ ... ]]'``` and their uses.

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

Slots are a convenient way of passing through specific properties to components whist maintaining component attributes if required.

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


### Better IDE Support
Defining component attributes via `props` is suitable for most cases.
For more complex cases we can use `__init__` and `SlotsEnum`

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

    # If component has more than one slot, we should specify in which slot we want to insert
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
Occasionally it is necessary provide more complex `manipulations` at the component level than `For If, Eleif, Else ...`. For these situations UPYYTL has a convenience fucntoon that allows us to perform all of the above and more.
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

## The Script Tag
Including `JS` or `Jquery` functionality in our components is facilitated by the use of the `h.Script` tag.

A classic example or use case would be the `navbar burger` functionality required by most html pages in order to make them responsive.

```python
## Example Navbar Component using Bulma

from . my_componets import NavBarItem
 
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
Provided that the appropriate `NavBarItem` component is available this component when included in any template render as expected and have a fully functional navbar-burger button which will either show or hide the navbar in responsive mode.

#### make sure you have the appropriate JQuery library loaded in the parent template.

The other thing to note is the use of `funny attributes` as in ```**{'aria-label':'menu', 'aria-expanded':"false"}```. These are necessary for html attributes with a '-'.

## Putting it all together
Now that we have seen power of `Components` and how they interact with `Templates` and how both can facilitate the use of `Slots` to provide maximum flexibilty and functionality lets take a look at a typical use case.

Our application will consist of a number of `Pages`. Each `Page` will consist of a number of distinct `Components`. In our case lets have a Header/Navbar, Notification area, a Body (which dsiplays the page content) and a footer. Pretty much that standard anatomy of a page.

So far we have created a `Notify` component, a `NavBar` component and the `Body` or `Content` will be whatever we want it to be. So lets create a HTLPage componet with uses all the above.

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

Here we define out HTMLPage component which we can use throughout our application givng us complete uniformity of "look and feel" irrespectrive of content being displyed. For the sake of simplicity we have defined the footer in the page component but equally as well we could have created a seperate `PageFooter` component.


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

## Next Steps
The real power of `UPYTL` is the ability to build re-useable compoents. We strongly reccomend adding all new componenets you develop to a `component library` file which can easliy be uploaded to PyPI and shared amongst team members, colleques and any other collaborators.



