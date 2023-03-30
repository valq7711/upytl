import io
import re
from enum import Enum
from types import SimpleNamespace, CodeType

from typing import Union, Callable, Tuple, List, Iterable, overload, Type, Dict, Any, TypeVar


AUTO_TAG_NAME = object()


class RenderedTag(SimpleNamespace):
    tag_class: Type['Tag']
    attrs: dict

    @property
    def tag_name(self) -> str:
        name = self.tag_class.tag_name
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


class ValueGetter:
    is_static = True

    def __init__(self, value, *, force_compile=False, is_static=False):
        if is_static:
            self._value_gtter = value
            assert not callable(value)
        else:
            self._value_gtter = self._make_value_getter(value, force_compile)

        if callable(self._value_gtter):
            self.get = self._value_gtter
            self.is_static = False
        else:
            self.get = self._get_static_value_method

    def get(self, ctx):
        '''See `__init__`'''
        pass

    def _get_static_value_method(self, ctx: dict):
        return self._value_gtter

    @staticmethod
    def _make_value_getter(v, force_compile) -> Union[str, Callable[[dict], Any]]:
        if force_compile:
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

        elif isinstance(v, set):
            assert len(v) == 1
            v = [*v][0]
            code_obj = compile(v, '<string>', 'eval')

            def render(ctx: dict):
                return eval(code_obj, None, ctx)

        return render


class ValueGettersDict(dict):

    def render(self: Dict[str, ValueGetter], ctx: dict):
        return {
            k: v.get(ctx) if isinstance(v, ValueGetter) else v
            for k, v in self.items()
        }

    def copy(self):
        return ValueGettersDict(super().copy())


class Tag:

    tag_name: Union[str, object] = AUTO_TAG_NAME

    is_body_allowed = True  # no body - no closing tag
    is_meta_tag = False  # if True expose only body, e.g. Text, Template, MyComponent, Slot

    # instance attributes
    attrs: Dict[str, Union[ValueGetter, Dict[str, ValueGetter]]]
    for_loop: tuple  # (var_names, iterable_factory)
    if_cond: Tuple[str, ValueGetter]   # (kword:['If' | 'Elif' | 'Else'] , value:[callable | castable to bool])
    assign_attrs: ValueGetter

    @overload
    def __init__(
        self, *,
        For=None, If=None, Elif=None, Else=None,
        Class=None, xClass=None,
        Style=None, xStyle=None,
        Data=None, xData=None,
        Attrs=None,
        **attrs
    ):
        ...

    def __init__(self, **attrs):
        """
        xClass, xStyle, xData mean eXtend Class or Style or Data
        """
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
            if isinstance(v, dict):
                attrs[k] = ValueGettersDict([(dk, ValueGetter(dv)) for dk, dv in v.items()])
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

    @classmethod
    def _class_render(cls, dct: dict):
        """Render html class of a tag."""
        return [klass for klass, enabled in dct.items() if enabled]

    @classmethod
    def _style_render(cls, dct: dict):
        """Render html style of a tag."""
        return [f'{prop}:{value}' for prop, value in dct.items() if value]

    @classmethod
    def _render_attrs(
            cls, attrs: Dict[str, Union[ValueGetter, dict]], ctx: dict,
            *, skip: dict = None, render_nested=False
    ) -> Dict[str, Any]:
        if skip is None:
            skip = {}
        ret = {}
        for a, v in attrs.items():
            if a in skip:
                continue
            if isinstance(v, ValueGetter):
                v = v.get(ctx)
            elif render_nested and isinstance(v, ValueGettersDict):
                v = v.render(ctx)
            ret[a] = v
        return ret

    @classmethod
    def _render_attrs_postproc(cls, attrs: dict, ctx: dict):
        args = [
            ('Class', 'xClass', ' ', cls._class_render),
            ('Style', 'xStyle', ';', cls._style_render)
        ]
        for a, exa, sep, dict_mapper in args:
            merged = cls._render_merge_special_attrs(attrs, a, exa, sep=sep, dict_mapper=dict_mapper, ctx=ctx)
            attrs.pop(a, None)
            attrs.pop(exa, None)
            if merged:
                attrs[a.lower()] = merged
        cls._render_data_attrs(attrs, ctx)

    @classmethod
    def _render_data_attrs(cls, attrs: dict, ctx: dict):
        name, extra_name = 'Data', 'xData'
        data: Dict[str, ValueGetter]
        data, xdata = cls._resolve_extendable_attrs(attrs, name, extra_name, ctx)
        attrs.pop(name, None)
        attrs.pop(extra_name, None)
        if data is None:
            return
        for a, v in data.items():
            attrs[f'data-{a}'] = v

    @classmethod
    def _resolve_extendable_attrs(cls, attrs: Dict[str, Union[Any, dict]], name, extra_name, ctx: dict):
        attr = attrs.get(name)
        extra = attrs.get(extra_name, None)
        if extra is not None and attr is None:
            attr = extra
            extra = None

        if isinstance(extra, ValueGettersDict):
            extra = extra.render(ctx)

        if isinstance(attr, dict):
            if isinstance(extra, dict):
                attr = attr.copy()
                attr.update(extra)
                extra = None
            if isinstance(attr, ValueGettersDict):
                attr = attr.render(ctx)

        return attr, extra

    @classmethod
    def _render_merge_special_attrs(
            cls, attrs: dict, attr_name, extra_name,
            *, sep: str, ctx: dict, dict_mapper
    ):
        attr, extra = cls._resolve_extendable_attrs(attrs, attr_name, extra_name, ctx)
        if attr is None:
            return

        if isinstance(attr, dict):
            attr = sep.join(dict_mapper(attr))

        if isinstance(extra, dict):
            extra = sep.join(dict_mapper(extra))

        if extra:
            attr = f'{attr}{sep}{extra}'
        return attr

    def resolve_cond(self, ctx):
        if self.if_cond is None:
            return
        kword, v = self.if_cond
        return (kword, v.get(ctx))

    @classmethod
    def _make_self_rendered(cls, attrs):
        ret = RenderedTag(
            tag_class=cls,
            attrs=attrs,
        )
        return ret

    def render_self(self, ctx, passed_attrs: Dict[str, Union[ValueGetter, dict]] = None):
        attrs = self.attrs.copy()
        attrs.update(self.assign_attrs.get(ctx))
        if passed_attrs is not None:
            attrs.update(passed_attrs)

        rendered_attrs = self._render_attrs(attrs, ctx)
        self._render_attrs_postproc(rendered_attrs, ctx)
        return self._make_self_rendered(rendered_attrs)

    def render(self, u: 'UPYTL', ctx: dict, body: Union[dict, str, None], passed_attrs: dict = None):
        self_ctx = {**u.global_ctx, **ctx}
        self_rendered = self.render_self(self_ctx, passed_attrs)
        yield self_rendered
        if not body:
            return
        if isinstance(body, str):
            code = u.compile_template(body)
            if code is not None:
                body = eval(code, None, self_ctx)
            yield self.format_text_body(body)
            return

        yield u.START_BODY
        for ch, ch_body, loop_vars in u.iter_body(body, self_ctx):
            ch_ctx = ctx if loop_vars is None else {**ctx, **loop_vars}
            yield from ch.render(u, ch_ctx, ch_body)
        yield u.END_BODY

    def format_text_body(self, body: str):
        """Return formatted/escaped body.

        NOTE: This hook is only invoked if the body is a `string` (i.e. text node).
        """
        return body

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

    Slot: ValueGetter
    SlotProps: Union[ValueGetter, None]
    special_attrs = {'Slot', 'SlotProps'}

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
            ctx = None if v.is_static else {**u.global_ctx, **ctx}
            return v.get(ctx)


T = TypeVar('T', bound='Component')


class ComponentMeta(type):
    def __init__(cls: Type[T], name, bases, dct):
        super().__init__(name, bases, dct)
        if name == 'Component':
            return
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
        self, *,
        For=None, If=None, Elif=None, Else=None,
        Class=None, xClass=None,
        Style=None, xStyle=None,
        Data=None, xData=None,
        Attrs=None,
        **attrs
    ):
        ...

    def __init__(self, **attrs):
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
        self.props = props
        return attrs, for_loop, if_cond

    def _merge_attrs(self, trg: dict, src: dict):
        trg = trg.copy()
        extendable_attrs = ['xClass', 'xStyle', 'xData']
        extendables = {k: trg.pop(k, None) for k in extendable_attrs}
        trg.update(src)
        for k, v in extendables.items():
            if v is None:
                continue
            trg_v = trg.get(k)
            if trg_v is None:
                trg[k] = v
                continue
            if isinstance(trg_v, dict) and isinstance(v, dict):
                v = v.copy()
                v.update(trg_v)
                trg[k] = v
        return trg

    def render(
            self, u: 'UPYTL', ctx: dict, body: Union[dict, str, None],
            passed_attrs: Dict[str, Union[Any, dict]] = None
    ):
        self_ctx = {**u.global_ctx, **ctx}
        if passed_attrs is None:
            passed_attrs = {}
        else:
            passed_attrs = passed_attrs.copy()

        assign_attrs: dict = self.assign_attrs.get(self_ctx)
        assign_attrs = assign_attrs.copy()

        if isinstance(body, str):
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
            else:
                props_rendered[k] = v.get(self_ctx)
        self_ctx.update(props_rendered)
        rendered_attrs = self._render_attrs(
            self.attrs, self_ctx, skip=assign_attrs, render_nested=True
        )
        rendered_attrs.update(assign_attrs)
        passed_attrs = self._merge_attrs(rendered_attrs, passed_attrs)

        # yeild tag/attrs
        self_rendered = self._make_self_rendered(rendered_attrs)

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
