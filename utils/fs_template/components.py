from dataclasses import asdict, dataclass
import json
from typing import Literal


@dataclass
class Text:
    content: str
    tag: str = 'plain_text'


@dataclass
class Header:
    title: Text
    template: str = 'blue'


@dataclass
class Markdown(Text):
    tag: str = 'markdown'


@dataclass
class TextBlock:
    text: Text
    tag: str = 'div'


@dataclass
class Action:
    actions: list
    tag: str = 'action'

    @classmethod
    def frm(cls, *actions):
        return cls(actions)
    

@dataclass
class Confirm:
    title: Text
    text: Text

@dataclass
class Button:
    text: Text
    type: Literal['primary', 'default', 'danger']
    value: dict
    confirm: Confirm
    tag: str = 'button'


@dataclass
class FsCard:
    header: Header
    elements: list


if __name__ == '__main__':
    btn_value = {
        "cmd": "pick_hero",
        "room_id": "${room_id}",
        "uname": "${m1}"
    }
    confirm = lambda x: Confirm(Text('确认'), Text(x))
    c = FsCard(
        Header(Text('fj111')), [
            Markdown('你的位置是'),
            Action.frm(
                Button(Text('a'), 'primary', btn_value, confirm('a')),
                Button(Text('b'), 'primary', btn_value, confirm('b')),
            )
        ]
    )
    print(json.dumps(asdict(c)))