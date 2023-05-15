from pyntree import Node
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Card:
    front: str
    back: str
    crtime: datetime
    mdtime: datetime