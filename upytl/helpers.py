from typing import Union, Callable, Dict, Any
import itertools


class AttrsDict(dict):
    extendables = ('Class', 'Style', 'Data')
    extendables_sources = tuple([f'x{_}' for _ in extendables])

    def extend(self, other: dict):
        self_xsources = {k: self.pop(k, None) for k in self.extendables_sources}
        self.update(other)
        for k, v in self_xsources.items():
            if v is None:
                continue
            oth_v = self.get(k)
            if oth_v is None:
                self[k] = v
                continue
            if isinstance(oth_v, dict) and isinstance(v, dict):
                v = v.copy()
                v.update(oth_v)
                self[k] = v
        return self

    def copy(self):
        return AttrsDict(self)

    def remove(self, *keys):
        for k in keys:
            try:
                del self[k]
            except KeyError:
                pass

    def render_values(self, ctx: dict, *, skip=(), render_complex_extendables=False):
        for a, v in self.items():
            if a in skip:
                continue
            if isinstance(v, ValueGetter):
                v = v.get(ctx)
            elif isinstance(v, ValueGettersDict):
                if render_complex_extendables or a not in self.extendables:
                    v = v.render(ctx)
            self[a] = v
        return self

    def render(self, ctx: dict):
        self.render_values(ctx)
        self._merge_extendables(ctx)

    def _process_extendable(self, name: str, dict_mapper: Callable[[dict], Any], ctx: dict):
        extra = self.pop(f'x{name}', None)
        attr = self.pop(name, None)

        if isinstance(attr, dict):
            if isinstance(extra, dict):
                attr = attr.copy()
                attr.update(extra)
                extra = None
            if isinstance(attr, ValueGettersDict):
                attr = attr.render(ctx)
            attr = dict_mapper(attr)

        if isinstance(extra, dict):
            extra = dict_mapper(extra)

        if attr is None:
            attr = extra
            extra = None
        return attr, extra

    @staticmethod
    def _make_str(it: Union[dict, list, Any], sep: str):
        if isinstance(it, list):
            return sep.join(it)
        elif isinstance(it, dict):
            return sep.join([f'{k}:{v}' for k, v in it.items()])
        return str(it)

    def _merge_extendables(self, ctx: dict):
        for name in self.extendables:
            name_lower = name.lower()
            attr, extra = self._process_extendable(name, getattr(self, f'_{name_lower}_render'), ctx)
            if attr is None:
                continue

            if name == 'Data':
                if extra is not None:
                    raise TypeError('Data, xData attrs must be type of dict')
                self.update(attr)
            else:
                sep = ';' if name == 'Style' else ' '
                attr = self._make_str(attr, sep)
                if extra:
                    extra = self._make_str(extra, sep)
                    attr = f'{attr}{sep}{extra}'
                self[name_lower] = attr

    def _data_render(self, dct: dict):
        return {f'data-{k}': v for k, v in dct.items() if v is not None}

    def _class_render(self, dct: dict):
        """Render html class of a tag."""
        return [klass for klass, enabled in dct.items() if enabled]

    def _style_render(cls, dct: dict):
        """Render html style of a tag."""
        return [f'{prop}:{value}' for prop, value in dct.items() if value]


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
            elif isinstance(v, bytes):
                return v.decode()
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
            k.format_map(ctx): v.get(ctx) if isinstance(v, ValueGetter) else v
            for k, v in self.items()
        }

    def copy(self):
        return ValueGettersDict(self)


def islice_dict(dct: dict, start: Union[str, int] = None, stop: Union[str, int] = None):
    keys = None
    if start is not None and not isinstance(start, int):
        keys = [*dct]
        start = keys.index(start)
    if stop is not None and not isinstance(stop, int):
        if keys is None:
            keys = [*dct]
        stop = keys.index(stop)

    return itertools.islice(dct.items(), start, stop)
