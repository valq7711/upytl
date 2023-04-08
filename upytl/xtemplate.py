import uuid
from typing import TypeVar, Type, Union
import json

from . import html as h
from .core import Component, Slot, Tag


class XTemplate(Component):

    def __init__(self, data: Union[dict, str] = b'{}', id: str = '', **kw):
        super().__init__(data=data, id=id, **kw)

    def get_context(self, props_rendered: dict) -> dict:

        if not props_rendered['id']:
            props_rendered['id'] = f'_{uuid.uuid4()}'
        data = props_rendered['data']
        if isinstance(data, dict):
            props_rendered['data'] = json.dumps(data, ensure_ascii=False, default=str, separators=(',', ':'))
        return props_rendered

    template = {
        h.Script(type='text/x-template', id='{id}'): {
            Slot(): ''
        },
        h.Script(): 'upytl.mount_component("[[id]]", [[data]])'
    }
