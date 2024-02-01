from dataclasses import field
from functools import partial
from .components import *

@dataclass
class CommonCard:
    room_id: str
    elements: list = field(default_factory=list)

    @property
    def header(self):
        return Header(Text(f'房间{self.room_id}'))
    
    def add_ele(self, *elements):
        self.elements.extend(elements)
        return self

    def to_dict(self):
        return asdict(FsCard(self.header, self.elements))
    
    @staticmethod
    def btn_value(cmd, room_id, **kwargs):
        return {
            "cmd": cmd,
            "room_id": room_id,
            **kwargs
        }
    
    @staticmethod
    def confirm(title, text):
        return Confirm(Text(title), Text(text))


def pick_hero_card(room_id, pos, names):
    btn_value = partial(CommonCard.btn_value, 'pick_hero', room_id)
    confirm = partial(CommonCard.confirm, '确认选择武将')
    card = CommonCard(room_id, [
        Markdown(f'你的位置是 {pos} 号位，你的可选武将有 {len(names)} 个，请选择：')
    ])
    actions = [Action([
        Button(Text(name), 'primary', btn_value(uname=name), confirm(name))
        for name in names[:3]
    ])]
    if len(names) > 3:
        actions.append(Action([
            Button(Text(name), 'default', btn_value(uname=name), confirm(name))
            for name in names[3:]
        ]))
    return card.add_ele(*actions).to_dict()


def simple_card(room_id, cont):
    return CommonCard(room_id, [
        TextBlock(Text(cont))
    ]).to_dict()