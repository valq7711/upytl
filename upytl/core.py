import io
import re
import functools
from enum import Enum
from types import SimpleNamespace, CodeType, FunctionType
import inspect
import threading

from typing import Union, Callable, Tuple, List, Iterable, overload, Type, Dict, TypeVar, Optional

from upytl.helpers import AttrsDict, ValueGetter, ValueGettersDict


AUTO_TAG_NAME = object()


class RenderError(Exception):
    def __init__(self, component: 'Tag', orig_exc):
        super().__init__(str(orig_exc))
        self.component = component
        self.orig_exc = orig_exc
        self.html_dump = ''

    def set_html_dump(self, s: str):
        self.html_dump = s

    def __repr__(self):
        return (
            f'Error: {self.orig_exc}\n'
            f'while rendering {self.component}'
        )

    def __str__(self):
        return (
            f'{self.__repr__()}\n'
            f'Rendered dump:\n{self.html_dump}\n'
            f'... [ Error goes here ]'
        )


def catch_errors(fun):

    @functools.wraps(fun)
    def inner(self, *args, **kw):
        try:
            yield from fun(self, *args, **kw)
        except RenderError:
            raise
        except Exception as exc:
            raise RenderError(self, exc) from exc
    return inner


class RenderedTag(SimpleNamespace):
    tag_class: Type['Tag']
    attrs: dict
    tag: Union[str, None]

    @property
    def tag_name(self) -> str:
        name = self.tag
        if name and isinstance(name, str):
            return name

        class_name = self.tag_class.__name__
        if name is AUTO_TAG_NAME:
            class_name = class_name.lower()
        return class_name

    @property
    def is_body_allowed(self) -> bool:
        return self.tag_class.is_body_allowed

    @property
    def is_meta_tag(self) -> bool:
        return self.tag_class.is_meta_tag


def set_info(init):

    @functools.wraps(init)
    def inner(self: 'Tag', *args, **kw):
        if self._info is None:
            frm = inspect.currentframe().f_back
            self._info = {'created_at': f'{frm.f_code.co_filename}:{frm.f_lineno}'}
            del frm
        init(self, *args, **kw)

    return inner


class Tag:

    tag_name: Union[str, object] = AUTO_TAG_NAME

    is_body_allowed = True  # no body - no closing tag
    is_meta_tag = False  # if True expose only body, e.g. Text, Template, MyComponent, Slot
    ident_class = None  # identity non-overridable class

    # instance attributes
    attrs: Dict[str, Union[ValueGetter, Dict[str, ValueGetter]]] = None
    for_loop: tuple  # (var_names, iterable_factory)
    if_cond: Tuple[str, ValueGetter]   # (kword:['If' | 'Elif' | 'Else'] , value:[callable | castable to bool])
    assign_attrs: ValueGetter
    _info: Optional[dict] = None

    @overload
    def __init__(
        self, _: dict = None, *,
        For=None, If=None, Elif=None, Else=None,
        Class=None, xClass=None,
        Style=None, xStyle=None,
        Data=None, xData=None,
        Attrs=None,
        Tag=None,
        **attrs
    ):
        ...

    @set_info
    def __init__(self, _: dict = None, **attrs):
        """
        xClass, xStyle, xData mean eXtend Class or Style or Data
        """
        if _ is not None:
            _.update(attrs)
            attrs = _

        if self.attrs is not None:
            attrs = dict(self.attrs, **attrs)

        self.attrs, self.for_loop, self.if_cond = self._process_attrs(attrs)
        self.assign_attrs = self.attrs.pop('Attrs', ValueGetter({}))

    @staticmethod
    def _compile_for(s: str) -> Tuple[str, CodeType]:
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

    def _process_attrs(self, attrs: dict):
        attrs, for_loop, if_cond = self._parse_attrs(attrs)
        self._wrap_in_getters(attrs)
        return attrs, for_loop, if_cond

    def _wrap_in_getters(self, attrs: dict):
        for k, v in attrs.items():
            if isinstance(v, (list, tuple)):
                # [b'button', 'is_large', ('is-{size}', 'size')] =>
                #       {'button': True, 'is-large': 'is_large', 'is-{size}': 'size'}
                v = dict([
                    it if isinstance(it, tuple)
                    else
                        (it.decode(), True) if isinstance(it, bytes)
                    else
                        (str(it).replace('_', '-'), it)
                    for it in v
                ])

            if isinstance(v, dict):
                attrs[k] = ValueGettersDict([
                    (dk, ValueGetter(dv, force_compile=(k in ['Class', 'xClass']))) for dk, dv in v.items()]
                )
            else:
                attrs[k] = ValueGetter(v, force_compile=(k == 'Attrs'))

    def _parse_attrs(self, attrs: dict):
        for_loop = attrs.pop('For', None)
        if for_loop is not None:
            for_loop = self._compile_for(for_loop)

        if_cond = None
        for kword in ['If', 'Elif', 'Else']:
            v = attrs.pop(kword, None)
            if v is not None:
                if kword != 'Else' and isinstance(v, str) and v:
                    v = ValueGetter(v, force_compile=True)
                else:
                    v = ValueGetter(v)
                if_cond = (kword, v)
                break

        assign_attrs = attrs.get('Attrs', None)
        if isinstance(assign_attrs, dict):
            attrs.update(assign_attrs)
            attrs.pop('Attrs')

        return attrs, for_loop, if_cond

    def resolve_cond(self, ctx):
        if self.if_cond is None:
            return
        kword, v = self.if_cond
        return (kword, v.get(ctx))

    @classmethod
    def _render_attrs(cls, ctx: dict, attrs: AttrsDict):
        attrs.render(ctx)
        return attrs

    @classmethod
    def _make_self_rendered(cls, ctx: dict, attrs: AttrsDict):
        attrs = cls._render_attrs(ctx, attrs)
        ident_class = cls.ident_class
        if ident_class is not None:
            klass = attrs.get('class')
            klass = f'{ident_class} {klass}' if klass else ident_class
            attrs['class'] = klass

        tag_name = attrs.pop('Tag', cls.tag_name)

        ret = RenderedTag(
            tag_class=cls,
            attrs=attrs,
            tag=tag_name
        )
        return ret

    def _merge_attrs(self, ctx: dict, passed_attrs: AttrsDict = None, passed_defaults: AttrsDict = None):
        if passed_defaults is not None:
            attrs = passed_defaults.copy()
            attrs.extend(self.attrs)
        else:
            attrs = AttrsDict(self.attrs)

        attrs.update(self.assign_attrs.get(ctx))
        if passed_attrs is not None:
            attrs.extend(passed_attrs)
        return attrs

    def _render_text_body(self, u: 'UPYTL', body: str, ctx: dict):
        code = u.compile_template(body)
        if code is not None:
            body = eval(code, None, ctx)
        return self.format_text_body(body)

    def _render_dict_body(self, u: 'UPYTL', body: dict, self_ctx: dict, ctx: dict, self_rendered: RenderedTag):
        yield u.START_BODY
        for ch, ch_body, loop_vars in u.iter_body(body, self_ctx):
            ch_ctx = ctx if loop_vars is None else dict(ctx, **loop_vars)
            yield from ch.render(u, ch_ctx, ch_body)
        yield u.END_BODY

    @catch_errors
    def render(
            self, u: 'UPYTL', ctx: dict, body: Union[dict, str, None], passed_attrs: dict = None,
            passed_defaults: dict = None
    ):
        self_ctx = dict(u.global_ctx, **ctx)

        attrs = self._merge_attrs(self_ctx, passed_attrs, passed_defaults)
        self_rendered = self._make_self_rendered(self_ctx, attrs)

        yield self_rendered
        if not body:
            return
        if isinstance(body, str):
            yield self._render_text_body(u, body, self_ctx)
            return
        yield from self._render_dict_body(u, body, self_ctx, ctx, self_rendered)

    def format_text_body(self, body: str):
        """Return formatted/escaped body.

        NOTE: This hook is only invoked if the body is a `string` (i.e. text node).
        """
        return body

    def __repr__(self):
        nm = self.tag_name if isinstance(self.tag_name, str) else self.__class__.__name__
        return f'<{nm}({str(self.attrs)})> {self._info}'


class VoidTag(Tag):
    is_body_allowed = False


class MetaTag(Tag):
    tag_name = None
    is_meta_tag = True


class Template(MetaTag):

    @classmethod
    def _render_attrs(cls, ctx: dict, attrs: AttrsDict):
        attrs.render_values(ctx, render_complex_extendables=True)
        return attrs

    def _render_dict_body(self, u: 'UPYTL', body: dict, self_ctx: dict, ctx: dict, self_rendered: RenderedTag):
        rendered_attrs = self_rendered.attrs
        if 'Is' in rendered_attrs:
            body = body[rendered_attrs.pop('Is')]
        yield u.START_BODY
        for ch, ch_body, loop_vars in u.iter_body(body, self_ctx):
            ch_ctx = ctx if loop_vars is None else dict(ctx, **loop_vars)
            yield from ch.render(u, ch_ctx, ch_body, passed_defaults=rendered_attrs)
        yield u.END_BODY


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
        self_ctx = dict(u.global_ctx, **ctx)
        slots_content_map: dict
        slots_content_map = u.pop_scope()
        slot_name = self.SlotName.get(self_ctx)
        to_slot: Tuple[dict, Tag, dict]
        to_slot = slots_content_map.get(slot_name)
        if to_slot is None:
            # render as regular tag (slot default content)
            yield from super().render(u, ctx, body)
            u.push_scope(slots_content_map)
            return

        del body
        stempl_ctx, stempl, stempl_body = to_slot
        attrs = AttrsDict(self.attrs)
        self_rendered = self._make_self_rendered(self_ctx, attrs)
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

    Slot: ValueGetter
    SlotProps: Union[ValueGetter, None]
    special_attrs = ('Slot', 'SlotProps')

    def _process_attrs(self, attrs: dict):
        tmp = super()._process_attrs(attrs)
        attrs, extra = tmp[0], tmp[1:]
        self.Slot = attrs.pop('Slot', ValueGetter('default'))
        self.SlotProps = attrs.pop('SlotProps', None)
        return [attrs, *extra]

    def render_special(self, spec_attr: str, u: 'UPYTL', ctx: dict):
        assert spec_attr in self.special_attrs
        v: Union[None, ValueGetter] = getattr(self, spec_attr)
        if v is not None:
            ctx = None if v.is_static else dict(u.global_ctx, **ctx)
            return v.get(ctx)


T = TypeVar('T', bound='Component')


class ComponentMeta(type):
    def __init__(cls: Type[T], name, bases, dct):
        super().__init__(name, bases, dct)
        if name == 'Component':
            return

        # parse props
        if 'props' not in dct and '__init__' in dct:
            props = {}
            for i, p in enumerate(inspect.signature(dct['__init__']).parameters.values()):
                if i and p.kind is p.POSITIONAL_OR_KEYWORD:
                    props[p.name] = p.default if p.default is not p.empty else ''
            cls.props = props

        template_processed = cls.__dict__.get('_template_processed', False)
        if not template_processed:
            cls._template_processed = True
            if cls.template is None:
                cls.template = cls.template_factory(cls)


class Component(MetaTag, metaclass=ComponentMeta):

    template: Union[str, dict] = None
    template_factory: Callable
    _template_processed = False

    # instance attrs
    props: Union[list, Dict[str, ValueGetter]]

    @overload
    def __init__(
        self, _: dict = None, *,
        For=None, If=None, Elif=None, Else=None,
        Class=None, xClass=None,
        Style=None, xStyle=None,
        Data=None, xData=None,
        Attrs=None,
        **attrs
    ):
        ...

    @set_info
    def __init__(self, _: dict = None, **attrs):
        if _ is not None:
            _.update(attrs)
            attrs = _
        self.props_set = set()
        super().__init__(**attrs)
        self.slots = set()

    def _parse_attrs(self, attrs: dict):
        attrs, for_loop, if_cond = super()._parse_attrs(attrs)

        if isinstance(self.props, list):
            props = dict.fromkeys(self.props)
        else:
            props = self.props.copy()

        for k, v in props.items():
            props[k] = ValueGetter(v)

        for k in [*attrs]:
            if k in self.props:
                props[k] = ValueGetter(attrs.pop(k))
                self.props_set.add(k)
        self.props = props
        return attrs, for_loop, if_cond

    @classmethod
    def _render_attrs(cls, ctx: dict, attrs: AttrsDict):
        return attrs

    @catch_errors
    def render(
            self, u: 'UPYTL', ctx: dict, body: Union[dict, str, None],
            passed_attrs: AttrsDict = None, passed_defaults: AttrsDict = None
    ):
        self_ctx = u.global_ctx.copy()
        self_ctx.update(ctx)

        passed_attrs, passed_defaults = [
            dct.copy() if dct is not None else AttrsDict() for dct in (passed_attrs, passed_defaults)
        ]

        assign_attrs: dict = self.assign_attrs.get(self_ctx)
        assign_attrs = assign_attrs.copy()

        if isinstance(body, str) or isinstance(body, dict) and not isinstance(next(iter(body), None), SlotTemplate):
            body = {SlotTemplate(): body}
        slots_content: Dict[SlotTemplate, Union[str, dict]] = body
        # save parent cxt as slots content should be rendered in it, not in component context
        out_ctx = ctx

        props_rendered = {}
        # maybe props passed in Attrs or in passed_attrs
        for k, v in self.props.items():
            if k in assign_attrs:
                props_rendered[k] = assign_attrs.pop(k)
            elif k in passed_attrs:
                props_rendered[k] = passed_attrs.pop(k)
            elif k in passed_defaults and k not in self.props_set:
                props_rendered[k] = passed_defaults.pop(k)
            else:
                if k in self.props_set:
                    v = v.get(self_ctx)
                    passed_defaults.pop(k, None)
                elif k in passed_defaults:
                    v = passed_defaults.pop(k)
                else:
                    v = v.get(self_ctx)
                props_rendered[k] = v
        self_ctx.update(props_rendered)

        rendered_attrs = passed_defaults
        rendered_attrs.extend(self.attrs)
        rendered_attrs.render_values(self_ctx, skip=assign_attrs, render_complex_extendables=True)
        rendered_attrs.update(assign_attrs)

        # yeild tag/attrs
        self_rendered = self._make_self_rendered(self_ctx, rendered_attrs)
        yield self_rendered

        yield u.START_BODY
        passed_attrs = rendered_attrs.copy().extend(passed_attrs)
        # resolve for-loop/if-else
        slots_content_map = {}
        if slots_content:
            for st, st_body, loop_vars in u.iter_body(slots_content, {**u.global_ctx, **out_ctx}):
                st: SlotTemplate
                st_ctx = out_ctx if loop_vars is None else {**out_ctx, **loop_vars}
                slots_content_map[st.render_special('Slot', u, st_ctx)] = (st_ctx, st, st_body)
        u.push_scope(slots_content_map)
        # component template context is defined by only component's props
        template_context = self.get_context(props_rendered)
        for ch, ch_body, loop_vars in u.iter_body(self.template, {**u.global_ctx, **template_context}):
            ch_ctx = (
                template_context if loop_vars is None
                else {**template_context, **loop_vars}
            )
            gen = ch.render(u, ch_ctx, ch_body, passed_attrs)
            yield from gen

        yield u.END_BODY
        u.pop_scope()

    def get_context(self, props_rendered: dict) -> dict:
        """Return context for own template.

        This method can be overloaded in a derived class
        to extend the context of own template.
        """
        return props_rendered


class _GenTag:
    def __getattr__(self, name: str) -> Type[Tag]:
        cls = type(name, (Tag,), {'tag_name': name.replace('_', '-')})
        return cls


gtag = _GenTag()


class SlotTemplateFactory:
    def __init__(self, slot: str):
        self.slot = slot

    def __call__(self, **kw) -> SlotTemplate:
        kw['Slot'] = self.slot
        return SlotTemplate(**kw)


class SlotsEnum(Enum):
    def __init__(self):
        self._value_ = SlotTemplateFactory(self.name)

    def slot(self, **kw) -> Slot:
        return Slot(SlotName=self.value.slot, **kw)

    def __call__(self, **kw):
        return self.value(**kw)


class GenericComponent(Tag):

    component_factory: ValueGetter

    def _process_attrs(self, attrs: dict):
        # attrs, *extra = super()._process_attrs(attrs)
        tmp = super()._process_attrs(attrs)
        attrs, extra = tmp[0], tmp[1:]
        self.component_factory = attrs.pop('Is')
        return [attrs, *extra]

    def render(self, u: 'UPYTL', ctx: dict, body: Union[dict, str, None]):
        self_ctx = {**u.global_ctx, **ctx}
        component_factory = self.component_factory.get(self_ctx)
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
        self._local = threading.local()
        self.global_ctx = global_ctx or {}
        self.default_ctx = default_ctx or {}
        self.registered_components = {}

    @property
    def scope(self) -> list:
        return self._local.scope

    @scope.setter
    def scope(self, scope: list):
        self._local.scope = scope

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
        out = HTMLPrinter(indent, debug, doctype)
        try:
            self._render(template, ctx, out)
            return out.buf.getvalue()
        except RenderError as exc:
            exc.set_html_dump(out.buf.getvalue())
            raise

    def _render(self, template: Dict[Tag, dict], ctx: dict, out: 'HTMLPrinter'):
        if self.default_ctx:
            dctx = self.default_ctx.copy()
            dctx.update(ctx)
            ctx = dctx
        self.scope = []
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

    def view(self, template, **defaults):

        from collections.abc import MutableMapping

        def decorator(func):

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                if isinstance(result, (dict, MutableMapping)):
                    tplvars = defaults.copy()
                    tplvars.update(result)
                    return self.render(template, tplvars)
                elif result is None:
                    return self.render(template, defaults)
                return result

            return wrapper

        return decorator


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
            stack = self.stack
            close_tag = stack[-1] if len(stack) else None
            if isinstance(close_tag, str):
                stack.pop()
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
            stack.append(close_tag)
        self.prev_tag = it


class UHelper:

    def __truediv__(self, s: str):
        return s.encode()

    def __mul__(self, s: str):
        return {s}
