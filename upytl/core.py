
import re
from types import SimpleNamespace

from typing import Any, Union, Callable, TypeVar, Generic, Tuple, List, Iterable

T = TypeVar('T', bound='Tag')


class VarRef:
    """To hold a context variable reference"""

    def __init__(self, var_name):
        self.var_name = var_name


class RenderContext:
    def __init__(self, ctx):
        self.ctx = ctx
        self.extra = {}

    def extended(self, ctx) -> 'RenderContext':
        cpy = self.__class__({**self.ctx, **ctx})
        cpy.extra = {**self.extra}
        return cpy


class Tag:

    tag_name: str = None

    is_body_allowed = True  # no body - no closing tag
    is_meta_tag = False  # if True expose only body, e.g. Text, Template, MyComponent, Slot
    is_proto = True  # i.e. it is not copy for render

    # instance attributes
    attrs: dict[str, Union[str, int, bool, Callable, VarRef]]
    body: list  # produced when rendering
    for_loop: tuple  # (var_names, iterable_factory)
    if_cond: tuple   # (kword:['If' | 'Elif' | 'Else'] , value:[callable | VarRef | castable to bool])

    def __init__(self, **attrs):
        self.attrs, self.for_loop, self.if_cond = self._process_attrs(**attrs)
        self.body = None

    @staticmethod
    def _compile_for(s: str):
        """s = 'a, b in some'"""
        # get vars-in part
        vars_s = s.split(' in ')[0].strip()
        # remove parens
        vars_s = re.sub(r'[\(\[\]\)]', '', vars_s)
        var_names = [k.strip() for k in vars_s.split(',') if k.strip()]
        var_names_s = ", ".join(var_names)
        if len(var_names) > 1:
            var_names_s = f'({var_names_s})'
        lst_src = f'[{var_names_s} for {s}]'
        return tuple(var_names), compile(lst_src, '<string>', 'eval')

    def _process_attrs(self, **attrs):

        for_loop = attrs.pop('For', None)
        if for_loop is not None:
            for_loop = self._compile_for(for_loop)

        if_cond = None
        for kword in ['If', 'Elif', 'Else']:
            v = attrs.pop(kword, None)
            if v is not None:
                if kword != 'Else' and isinstance(v, str) and v:
                    code_obj = compile(v, '<string>', 'eval')
                    v = lambda ctx: eval(code_obj, None, ctx)
                if_cond = (kword, v)
                break
        for k, v in attrs.items():
            if isinstance(v, set):
                assert len(v) == 1
                v = [*v][0]
                code_obj = compile(v, '<string>', 'eval')
                attrs[k] = lambda ctx: eval(code_obj, None, ctx)
        return attrs, for_loop, if_cond

    def clone(self: T) -> T:
        cpy = self.__class__()
        cpy.attrs = {**self.attrs}
        cpy.body = self.body
        cpy.for_loop = self.for_loop
        cpy.if_cond = self.if_cond
        cpy.is_proto = False
        return cpy

    @staticmethod
    def _render_attr(attr_value, ctx: dict):
        v = attr_value
        if isinstance(v, str):
            v = v.format(**ctx)
        elif callable(v):
            v = v(ctx)
        elif isinstance(v, VarRef):
            v = ctx.get(v.var_name)
        return v

    def _render_attrs(self, ctx: dict):
        assert not self.is_proto
        attrs = self.attrs
        for a, v in attrs.items():
            attrs[a] = self._render_attr(v, ctx)

    def _resolve_cond(self, ctx):
        if self.if_cond is None:
            return

        kword, v = self.if_cond
        if callable(v):
            v = v(ctx)
        elif isinstance(v, VarRef):
            v = ctx.get(v.var_name)
        return (kword, v)

    def _iter_body(self, body: dict['Tag', dict], ctx: dict) -> Iterable[Tuple[dict, 'Tag', dict]]:
        in_if_block = False
        skip_rest = None
        for tag, tag_body in body.items():
            collect = False
            cond = tag._resolve_cond(ctx)
            if cond is None:
                collect = True
                in_if_block = False
            else:
                kw, v = cond
                if kw == 'If':
                    in_if_block = True
                    if v:
                        collect = True
                        skip_rest = True
                    else:
                        skip_rest = False
                elif kw == 'Elif':
                    if not in_if_block:
                        raise RuntimeError('Elif out of If-block')
                    if not skip_rest and v:
                        collect = True
                        skip_rest = True
                elif kw == 'Else':
                    if not in_if_block:
                        raise RuntimeError('Else out of If-block')
                    if not skip_rest:
                        collect = True
            if collect:
                if tag.for_loop is not None:
                    for item_ctx in tag._iter_for_loop_context(ctx):
                        yield (item_ctx, tag, tag_body)
                else:
                    yield (ctx, tag, tag_body)

    def _iter_for_loop_context(self, ctx) -> dict:
        var_names, code_obj = self.for_loop
        lst = eval(code_obj, None, ctx)
        for var_values in lst:
            if not isinstance(var_values, tuple):
                var_values = [var_values]
            item_ctx = {**ctx, **dict(zip(var_names, var_values))}
            yield item_ctx

    def _process_child(self, child_rctx: RenderContext, child: 'Tag', child_body: dict):
        return child.render(child_rctx, child_body)

    def _render_body(self, body: Union[str, dict['Tag', dict]], rctx: RenderContext):
        ret = []
        for child_ctx, child, child_body in self._iter_body(body, rctx.ctx):
            child_rctx = rctx.extended(child_ctx)
            ret.append(self._process_child(child_rctx, child, child_body))
        return ret

    def render(self, rctx: RenderContext, body: dict):
        me = self.clone()
        me._render_attrs(rctx.ctx)
        if isinstance(body, str):
            if body:
                #body = compile('f"{body}"', '<string>', 'eval')
                body = eval(f'f"{body}"', None, rctx.ctx)
                #body = body.format(**rctx.ctx)
        elif body is not None:
            body = self._render_body(body, rctx)
        me.body = body
        return me

    def __repr__(self):
        return f'<{self.tag_name}({str(self.attrs)})>'


class Slot(Tag):

    tag_name = 'Slot'

    is_meta_tag = True

    parent: 'Component'

    def __init__(self, name='default', **attrs):
        attrs.setdefault('name', name)
        super().__init__(**attrs)
        self.parent = None

    @property
    def name(self):
        return self.attrs['name']

    def clone(self) -> 'Slot':
        cpy = super().clone()
        cpy.parent = self.parent
        return cpy

    def render(self, rctx: RenderContext, body: Union[str, dict[T, dict]]):
        assert self in self.parent.slots
        parent_data = rctx.extra[self.parent]
        slot_name = self._render_attr(self.name, rctx.ctx)
        slot_bus: dict[str, Tuple[RenderContext, SlotTemplate, dict]] = parent_data.slot_bus
        stempl_rctx, stempl, stempl_body = slot_bus.get(slot_name, (None, None, None))
        if stempl is None:
            return super().render(rctx, body)
        else:
            sprops = {}
            if 'SlotProps' in stempl.attrs:
                sprops_name = stempl.attrs['SlotProps']
                sprops = {sprops_name: self.attrs}
            stempl_rctx = stempl_rctx.extended(sprops)
            return stempl.render(stempl_rctx, stempl_body)


class SlotTemplate(Tag):
    is_meta_tag = True

    @property
    def name(self):
        return self.attrs.get('name', 'default')


class Component(Tag):

    _ownbody: Union[str, dict]

    is_meta_tag = True

    props: Union[list, dict]
    slots: set

    def __init__(self, **attrs):
        super().__init__(**attrs)
        self.slots = set()
        self._ownbody = self._clone_body(self._ownbody)


    def _clone_body(self, src):
        if not isinstance(src, dict):
            return src
        cpy = {}
        for t, v in src.items():
            if isinstance(t, Slot):
                t = t.clone()
                t.parent = self
                self.slots.add(t)
            elif isinstance(t, Component):
                t = t.clone()
                t.slots.clear()
                t._ownbody = t._clone_body(t._ownbody)
            cpy[t] = self._clone_body(v)
        return cpy

    def _process_attrs(self, **attrs):
        if isinstance(self.props, list):
            props = dict.fromkeys(self.props)
        else:
            props = {**self.props}
        for k in [*attrs]:
            if k in self.props:
                props[k] = attrs.pop(k)
        self.props = props
        return super()._process_attrs(**attrs)

    def clone(self) -> 'Component':
        cpy = super().clone()
        cpy.props = self.props
        cpy.slots = self.slots
        cpy._ownbody = self._ownbody
        return cpy

    def _render_props(self, ctx: dict):
        render_prop = self._render_attr
        return {k: render_prop(v, ctx) for k, v in self.props.items()}

    def render(self, rctx: RenderContext, body: Union[str, dict['Tag', dict]]):
        assert self not in rctx.extra
        rctx = rctx.extended(self._render_props(rctx.ctx))
        if body and (isinstance(body, str) or not isinstance([*body][0], SlotTemplate)):
            body = {SlotTemplate(): body}

        # the body is the set of templates for slots
        slot_bus = {}
        if isinstance(body, dict):
            for t_ctx, t, t_body in self._iter_body(body, rctx.ctx):
                t_rctx = rctx.extended(t_ctx)
                t: SlotTemplate = t
                slot_bus[t.name] = (t_rctx, t, t_body)
        data = SimpleNamespace(slot_bus=slot_bus)
        rctx.extra[self] = data
        ret = super().render(rctx, self._ownbody)
        del rctx.extra[self]
        return ret

Tag(a=1)
