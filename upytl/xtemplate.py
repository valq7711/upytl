import uuid
from typing import TypeVar, Type

from . import html as h
from .core import Component, Slot, Tag


class XTemplate(Component):
    props = []

    def get_context(self, props_rendered: dict) -> dict:
        if 'id' not in props_rendered:
            props_rendered['id'] = f'_{uuid.uuid4()}'
        return props_rendered

    template = {
        h.Script(type='text/x-template', id='{id}'): {
            Slot(): ''
        },
        h.Script(): 'upytl.mount_component("[[id]]")'
    }

