import io
import re
from enum import Enum
from types import SimpleNamespace

from typing import Union, Callable, Tuple, List, Iterable, overload, Type, Dict


AUTO_TAG_NAME = object()


class VarRef:
    """To hold a context variable reference"""

    def __init__(self, var_name):
        self.var_name = var_name


class RenderedTag(SimpleNamespace):
    tag_class: Type['Tag']
    attrs: dict

    @property
    def tag_name(self):
        name = self.tag_class.tag_name
        if name and isinstance(name, str):
            return name

        class_name = self.tag_class.__name__
        if name is AUTO_TAG_NAME:
            class_name = class_name.lower()
        return class_name

    @property
    def is_body_allowed(self):
        return self.tag_class.is_body_allowed

    @property
    def is_meta_tag(self):
        return self.tag_class.is_meta_tag


class Tag:

    tag_name: Union[str, object] = AUTO_TAG_NAME

    is_body_allowed = True  # no body - no closing tag
    is_meta_tag = False  # if True expose only body, e.g. Text, Template, MyComponent, Slot

    # instance attributes
    attrs: Dict[str, Union[str, int, bool, Callable, VarRef]]
    for_loop: tuple  # (var_names, iterable_factory)
    if_cond: tuple   # (kword:['If' | 'Elif' | 'Else'] , value:[callable | VarRef | castable to bool])

    @overload
    def __init__(
        self, *,
        For=None, If=None, Elif=None, Else=None,
        Class=None, xClass=None,
        Style=None, xStyle=None,
        Attrs=None,
        **attrs
    ):
        ...

    def __init__(self, **attrs):
        """
        xClass, xStyle mean eXtend Class or Style
        They have special meaning if only they are dicts or lists/tuples,
        in other cases it will be treat as regular attrs.
        """
        self.attrs, self.for_loop, self.if_cond = self._process_attrs(attrs)

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

    @staticmethod
    def _make_value_render(v, force_eval=False):
        if force_eval:
            if isinstance(v, str):
                code_obj = compile(v, '<string>', 'eval')

                def render(ctx: dict):
                    return eval(code_obj, None, ctx)
                return render
            return v

        render = v
        if isinstance(v, bytes):
            render = v.decode()

        elif isinstance(v, str):
            try:
                v.format_map({})
                # if we're here it is just string
                # do nothing
            except KeyError:
                render = v.format_map

        elif isinstance(v, VarRef):
            var_name = v.var_name

            def render(ctx: dict):
                return ctx.get(var_name)

        elif isinstance(v, set):
            assert len(v) == 1
            v = [*v][0]
            code_obj = compile(v, '<string>', 'eval')

            def render(ctx: dict):
                return eval(code_obj, None, ctx)

        return render

    def _process_attrs(self, attrs: dict):
        for_loop = attrs.pop('For', None)
        if for_loop is not None:
            for_loop = self._compile_for(for_loop)

        if_cond = None
        for kword in ['If', 'Elif', 'Else']:
            v = attrs.pop(kword, None)
            if v is not None:
                if kword != 'Else' and isinstance(v, str) and v:
                    v = self._make_value_render(v, force_eval=True)
                if_cond = (kword, v)
                break

        for k, v in attrs.items():
            if isinstance(v, dict):
                dct = {**v}
                for dk, dv in dct.items():
                    if isinstance(dv, bytes):
                        dct[dk] = dv.decode()
                    else:
                        dct[dk] = self._make_value_render(dv)
                attrs[k] = dct
            else:
                force_eval = k == 'Attrs'
                attrs[k] = self._make_value_render(v, force_eval)
        return attrs, for_loop, if_cond

    @classmethod
    def _render_value(cls, attr_value, ctx: dict):
        if callable(attr_value):
            attr_value = attr_value(ctx)
        return attr_value

    @classmethod
    def _class_render(cls, name, raw_enabled, ctx):
        """Render html class of a tag."""
        if cls._render_value(raw_enabled, ctx):
            return name

    @classmethod
    def _style_render(cls, k, raw_v, ctx):
        """Render html style of a tag."""
        v = cls._render_value(raw_v, ctx)
        if not v:
            return
        return f'{k}:{v}'

    @classmethod
    def _render_attrs(cls, attrs: dict, ctx: dict):
        ret = {}
        attrs_assignment = None
        render_value = cls._render_value
        for a, v in attrs.items():
            v = render_value(v, ctx)
            if a == 'Attrs':
                attrs_assignment = v
            else:
                ret[a] = v

        if attrs_assignment is not None:
            ret.update(attrs_assignment)

        args = [
            ('Class', 'exClass', ' ', cls._class_render),
            ('Style', 'exStyle', ';', cls._style_render)
        ]
        for a, exa, sep, item_render in args:
            merged = cls._render_merge_special_attrs(ret, a, exa, sep=sep, item_render=item_render, ctx=ctx)
            ret.pop(a, None)
            ret.pop(exa, None)
            if merged:
                ret[a.lower()] = merged

        return ret

    @classmethod
    def _render_merge_special_attrs(
            cls, attrs: dict, attr_name, extra_name,
            *, sep: str, ctx: dict, item_render
    ):
        attr = attrs.get(attr_name)
        extra = attrs.get(extra_name, None)
        if extra is not None and attr is None:
            attr = extra
            extra = None

        if isinstance(attr, dict):
            if isinstance(extra, dict):
                attr.update(extra)
                extra = None
            rendered = [item_render(k, v, ctx) for k, v in attr.items()]
            attr = sep.join([v for v in rendered if v])
        if extra:
            if isinstance(extra, dict):
                rendered = [item_render(k, v, ctx) for k, v in extra.items()]
                extra = sep.join([v for v in rendered if v])
            if extra:
                attr = f'{attr}{sep}{extra}'
        return attr

    def resolve_cond(self, ctx):
        if self.if_cond is None:
            return
        kword, v = self.if_cond
        return (kword, self._render_value(v, ctx))

    def render_self(self, ctx):
        ret = RenderedTag(
            tag_class=self.__class__,
            attrs=self._render_attrs(self.attrs, ctx),
        )
        return ret

    def render(self, u: 'UPYTL', ctx: dict, body: Union[dict, str, None]):
        self_ctx = {**u.global_ctx, **ctx}
        self_rendered = self.render_self(self_ctx)
        yield self_rendered
        if not body:
            return
        if not isinstance(body, dict):
            code = u.compile_template(body)
            if code is not None:
                yield eval(code, None, self_ctx)
            else:
                # no code found in body
                yield body
            return

        yield u.START_BODY
        for ch, ch_body, loop_vars in u.iter_body(body, self_ctx):
            ch_ctx = ctx if loop_vars is None else {**ctx, **loop_vars}
            yield from ch.render(u, ch_ctx, ch_body)
        yield u.END_BODY

    def __repr__(self):
        nm = self.tag_name or self.__class__.__name__
        return f'<{nm}({str(self.attrs)})>'


class VoidTag(Tag):
    is_body_allowed = False


class MetaTag(Tag):
    tag_name = None
    is_meta_tag = True


class Template(MetaTag):
    pass


class Slot(MetaTag):

    @overload
    def __init__(
        self, *,
        SlotName='default',
        For=None, If=None, Elif=None, Else=None,
        **attrs
    ):
        ...

    def __init__(self, SlotName='default', **attrs):
        attrs.setdefault('SlotName', SlotName)
        super().__init__(**attrs)

    @property
    def SlotName(self):
        return self.attrs['SlotName']

    def render(self, u: 'UPYTL', ctx: dict, body: Union[dict, str, None]):
        self_ctx = {**u.global_ctx, **ctx}
        slots_content_map: dict
        slots_content_map = u.pop_scope()
        slot_name = self._render_value(self.SlotName, self_ctx)
        to_slot: Tuple[dict, Tag, dict]
        to_slot = slots_content_map.get(slot_name)
        if to_slot is None:
            # render as regular tag (slot default content)
            yield from super().render(u, ctx, body)
            u.push_scope(slots_content_map)
            return

        del body
        stempl_ctx, stempl, stempl_body = to_slot
        self_rendered = self.render_self(self_ctx)
        yield self_rendered

        # inject slot props
        stempl: SlotTemplate
        sprops_name = stempl.render_special('SlotProps', u, ctx)
        if sprops_name:
            stempl_ctx = {**stempl_ctx, **{sprops_name: self_rendered.attrs}}

        yield u.START_BODY
        yield from stempl.render(u, stempl_ctx, stempl_body)
        yield u.END_BODY
        u.push_scope(slots_content_map)


class SlotTemplate(MetaTag):

    Slot: Union[str, Callable]
    SlotProps: Union[str, Callable, None]
    special_attrs = {'Slot', 'SlotProps'}

    def _process_attrs(self, attrs: dict):
        #attrs, *extra = super()._process_attrs(attrs)
        tmp = super()._process_attrs(attrs)
        attrs, extra = tmp[0], tmp[1:]
        self.Slot = attrs.pop('Slot', 'default')
        self.SlotProps = attrs.pop('SlotProps', None)
        return attrs, *extra

    def render_special(self, spec_attr: str, u: 'UPYTL', ctx: dict):
        assert spec_attr in self.special_attrs
        v = getattr(self, spec_attr)
        if callable(v):
            return self._render_value(v, {**u.global_ctx, **ctx})
        return v


class Component(MetaTag):

    template: Union[str, dict]

    # instance attrs
    props: Union[list, dict]
    has_root: bool

    @overload
    def __init__(
        self, *,
        For=None, If=None, Elif=None, Else=None,
        Class=None, xClass=None,
        Style=None, xStyle=None,
        Attrs=None,
        **attrs
    ):
        ...

    def __init__(self, **attrs):
        super().__init__(**attrs)
        self.slots = set()
        # if we have root - pass down attrs
        self.has_root = (
            isinstance(self.template, dict)
            and len(self.template) == 1
            and not isinstance([*self.template][0], Slot)
        )

    def _process_attrs(self, attrs: dict):
        if isinstance(self.props, list):
            props = dict.fromkeys(self.props)
        else:
            props = {**self.props}
        for k in [*attrs]:
            if k in self.props:
                props[k] = attrs.pop(k)
        #props, *_ = super()._process_attrs(props)
        tmp = super()._process_attrs(props)
        props = tmp[0]
        self.props = props
        return super()._process_attrs(attrs)

    def _render_props(self, ctx: dict):
        render_prop = self._render_value
        return {k: render_prop(v, ctx) for k, v in self.props.items()}

    def render(self, u: 'UPYTL', ctx: dict, body: Union[dict, str, None]):
        if isinstance(body, str):
            body = {SlotTemplate(): body}
        slots_content: Dict[SlotTemplate, Union[str, dict]] = body
        # save parent cxt as slots content should be rendered in it, not in component context
        out_ctx = ctx
        props_context = {**u.global_ctx, **ctx}
        props_rendered = self._render_props(props_context)
        self_ctx = {**props_context, **props_rendered}
        # yeild tag/attrs
        self_rendered = self.render_self(self_ctx)
        yield self_rendered
        yield u.START_BODY
        # resolve for-loop/if-else
        slots_content_map = {}
        if slots_content:
            for st, st_body, loop_vars in u.iter_body(slots_content, {**u.global_ctx, **out_ctx}):
                st: SlotTemplate
                st_ctx = out_ctx if loop_vars is None else {**out_ctx, **loop_vars}
                slots_content_map[st.render_special('Slot', u, st_ctx)] = (st_ctx, st, st_body)
        u.push_scope(slots_content_map)
        is_first = True
        # component template context is defined by only component's props
        template_context = self.get_context(props_rendered)
        for ch, ch_body, loop_vars in u.iter_body(self.template, {**u.global_ctx, **template_context}):
            ch_ctx = (
                template_context if loop_vars is None
                else {**template_context, **loop_vars}
            )
            gen = ch.render(u, ch_ctx, ch_body)
            if is_first and self.has_root:
                it = next(gen, None)
                if not issubclass(it.tag_class, Slot):
                    # pass down attrs
                    it.attrs.update(self_rendered.attrs)
                yield it
            yield from gen

        yield u.END_BODY
        u.pop_scope()

    def get_context(self, props_rendered: dict) -> dict:
        """Return context for own template.

        This method can be overloaded in a derived class
        to extend the context of own template.
        """
        return props_rendered


class GenericComponent(Tag):

    component_factory: Union[str, Type[Tag]]

    def _process_attrs(self, attrs: dict):
        # attrs, *extra = super()._process_attrs(attrs)
        tmp = super()._process_attrs(attrs)
        attrs, extra = tmp[0], tmp[1:]
        self.component_factory = attrs.pop('Is')
        return attrs, *extra

    def render(self, u: 'UPYTL', ctx: dict, body: Union[dict, str, None]):
        self_ctx = {**u.global_ctx, **ctx}
        component_factory = self.component_factory
        if component_factory.__qualname__.startswith(Tag._make_value_render.__qualname__):
            component_factory = self._render_value(self.component_factory, self_ctx)
        if isinstance(component_factory, str):
            component_factory = u.get_component_factory(component_factory)
        assert issubclass(component_factory, Tag)
        component = component_factory(**self.attrs)
        return component.render(u, ctx, body)


class Punc(Enum):
    START = 'start'
    END = 'end'


class UPYTL:
    START_BODY = Punc.START
    END_BODY = Punc.END

    compiled_templates_cache = {}

    registered_components: Dict[str, Tag]

    def __init__(self, *, global_ctx: dict = None, default_ctx: dict = None):
        self.global_ctx = global_ctx or {}
        self.default_ctx = default_ctx or {}
        self.scope = None
        self.registered_components = {}

    def get_component_factory(self, name: str) -> Type[Tag]:
        return self.registered_components[name]

    @classmethod
    def compile_template(cls, body: str, delimiters: List[str] = None):
        if delimiters is None:
            delimiters = ['[[', ']]']

        cache_key = (tuple(delimiters), body)
        ret = cls.compiled_templates_cache.get(cache_key)
        if ret is not None:
            return ret

        dleft, dright = delimiters
        dleft, dright = [re.escape(d) for d in [dleft, dright]]
        split_re = re.compile(f'({dleft}.*?{dright})')
        body_split = split_re.split(body)
        if len(body_split) == 1:
            # no code
            cls.compiled_templates_cache[cache_key] = None
            return None

        iter_body = iter(body_split)
        fstr = []
        while True:
            s = next(iter_body, None)
            if s:
                s = s.replace('{', '{{').replace('}', '}}')
                fstr.append(s)
            code = next(iter_body, None)
            if code is None:
                break
            # remove delimiters [2:-2]
            fstr.append(f'{{ {code[2:-2]} }}')
        fstr = ''.join(fstr)
        fstr = f"f'''{fstr}'''"
        ret = compile(fstr, '<string>', 'eval')
        cls.compiled_templates_cache[cache_key] = ret
        return ret

    @classmethod
    def iter_body(cls, body: Dict[Tag, dict], ctx: dict) -> Iterable[Tuple[Tag, dict, dict]]:
        in_if_block = False
        skip_rest = None
        for tag, tag_body in body.items():
            collect = False
            cond = tag.resolve_cond(ctx)
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
                    for loop_vars in cls._iter_for_loop(tag.for_loop, ctx):
                        yield (tag, tag_body, loop_vars)
                else:
                    yield (tag, tag_body, None)

    @classmethod
    def _iter_for_loop(cls, for_loop: Tuple, ctx) -> dict:
        var_names, code_obj = for_loop
        lst = eval(code_obj, None, ctx)
        for var_values in lst:
            if not isinstance(var_values, tuple):
                var_values = [var_values]
            yield dict(zip(var_names, var_values))

    def push_scope(self, it):
        self.scope.append(it)

    def pop_scope(self) -> Dict[str, Tuple[dict, Tag, Dict[Tag, dict]]]:
        return self.scope.pop()

    def render(self, template: Dict[Tag, dict], ctx, *, indent=2, debug=False, doctype='html'):
        ctx = {**self.default_ctx, **ctx}
        self.scope = []
        out = HTMLPrinter(indent, debug, doctype)
        # wrap in Template to ensure foo-loop/if-else will be processed properly
        template = {Template(): template}
        for k, v in template.items():
            for it in k.render(self, ctx, v):
                if it is self.START_BODY:
                    out.start_body()
                elif it is self.END_BODY:
                    out.end_body()
                else:
                    out.print(it)
        return out.buf.getvalue()


class HTMLPrinter:

    def __init__(self, indent=0, debug=False, doctype='html'):
        self.indent = ' ' * indent
        self.cur_indent = ''
        self.debug = debug
        self.buf = io.StringIO()
        if doctype:
            self.buf.write(f'<!DOCTYPE {doctype}>')

        self.prev_tag = None
        self.stack = []

    def indent_inc(self):
        if self.indent:
            self.cur_indent = f'{self.indent}{self.cur_indent}'

    def indent_dec(self):
        step = len(self.indent)
        if step:
            self.cur_indent = self.cur_indent[:-step]

    def start_body(self):
        assert isinstance(self.prev_tag, RenderedTag)
        self.stack.append(Punc.START)
        if self.debug or not self.prev_tag.tag_class.is_meta_tag:
            self.indent_inc()

    def end_body(self):
        # it can be prev close-tag
        it = self.stack.pop()
        if isinstance(it, str):
            self._print(it)
            it = self.stack.pop()
        assert it is Punc.START
        close_tag = self.stack.pop()
        if close_tag:
            self.indent_dec()
            self._print_with_indent(close_tag)

    def _print(self, s):
        if s:
            self.buf.write(s)

    def _print_with_indent(self, s: str):
        if not s:
            return
        if self.indent:
            s = f'\n{self.cur_indent}{s}'
        self._print(s)

    def print(self, it: Union[RenderedTag, str]):
        if isinstance(it, str):
            # this is text-body
            self.start_body()
            self._print_with_indent(it)
            self.end_body()
        else:
            close_tag = self.stack and self.stack[-1]
            if isinstance(close_tag, str):
                self.stack.pop()
                self._print(close_tag)
            if not self.debug and it.tag_class.is_meta_tag:
                tag_def = None
                close_tag = ''
            else:
                tag_name = it.tag_name
                attrs = ' '.join([
                    f'''{aname}{'' if v is True else f'="{str(v)}"' }'''
                    for aname, v in it.attrs.items() if v is not False
                ])
                sep = ' ' if attrs else ''
                end_tag_def, close_tag = ['', f'</{tag_name}>'] if it.is_body_allowed else [' /', '']
                tag_def = f'<{tag_name}{sep}{attrs}{end_tag_def}>'
            self._print_with_indent(tag_def)
            self.stack.append(close_tag)
        self.prev_tag = it


class UHelper:
    def __getattr__(self, name):
        return VarRef(name)

    def __truediv__(self, s: str):
        return s.encode()

    def __mul__(self, s: str):
        return {s}
