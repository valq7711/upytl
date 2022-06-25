# UPYTL
Ultra Pythonic Template Language

```python
from upytl import UPYTL, html as h

t = {
  h.Div(): 'Hello [[ which_world ]] world!'
}

upytl = UPYTL()

rendered = upytl.render(t, ctx={'which_world':'Python'}, doctype=None)
print(rendered)
```

```html
<div>
  Hello Python world!
</div>
```

## Features Supported:

- for-loop
- if-elif-else
- custom components with slots

