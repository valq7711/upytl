# UPYTL
Ultra Pythonic Template Language (inspired by Vue.js)

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


## About
Default render-behaviour for attributes is `str.format()`, so you can
```Python
h.Div(Class='{header_class}'): 'Header'

# or even
h.Div(Class='{class_map[header]}'): 'Header'

# note that `key` must be is unquoted - see `str.format()` doc

```
If you don't want any processing - just pass `bytes`

```Python
h.Div(Class=b'no-{processing}'): 'Header'
```

To evaluate python expression pass string wrapped in `set`

```Python
h.Button(disabled={'not allow_submit'}): 'Submit'
```

If an attribute value is a Python expression (like one above) and if it is evaluated to a boolean value (`True`/`False`)
then it is rendered without value (`True`) or not rendered at all (`False`).
So in above example if `allow_submit` is falsy i.e. `not allow_submit` is `True` we'll get

```HTML
<button disabled>Submit</button>
```

## `For`-loop, `If`-`Elif`-`Else`

There are special attributes: `For`, `If`, `Elif`, `Else`,
their values are always treated as python expressions except for `Else` - its value is ignored.
Also note that `For`-syntax is a bit trimmed compared to pure python.

```Python
t = {
    h.Template(For='k in range(5)'):{
        h.Div(If='k == 1'): 'This is the div number one',
        h.Div(Elif='k != 3'): 'This is #[[ k ]] div',
        h.Div(Else=''): 'Here should be div #3',
    }
}
```

```HTML
<div>
  This is #0 div
</div>
<div>
  This is the div number one
</div>
<div>
  This is #2 div
</div>
<div>
  Here should be div #3
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
```

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

### Slots

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
Definition component attributes via `props` is suitable for simple cases,
for more complex cases use `__init__` and `SlotsEnum`

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

