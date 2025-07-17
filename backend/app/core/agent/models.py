from typing import List, Literal, Optional, Union
from pydantic import BaseModel


class Sentence(BaseModel):
    spk: str
    sentence_id: int
    content: str


class SpeakerBlock(BaseModel):
    spk: str
    block: List[Sentence]


class SummaryBlock(BaseModel):
    title: str
    block_summary: str
    object_relation: str


class NodeElement(BaseModel):
    full_id: str
    content: str
    type: Literal["confirmed", "deleted", "unconfirmed"] = "unconfirmed"


class Argument(NodeElement):
    argument_id: str
    ref: Optional[str] = None


class Position(NodeElement):
    position_id: int
    ref: Optional[str] = None
    pros: List[Argument]
    cons: List[Argument]
    note: Optional[str] = None
    generated_issue: bool = False  # 标记当前的内容是否生成过 issue , 如果 position 内容变化了,需要将这个值置为 False


class Relation(BaseModel):
    target_id: str
    target_type: str
    target_content: str
    content: str


class Issue(NodeElement):
    issue_id: int
    positions: List[Position]
    source: Optional[Relation] = None


class Operation(BaseModel):
    full_id: str


class AddOperation(Operation):
    op: Literal["ADD"] = "ADD"
    data: Union[Issue, Position, Argument]
    parent_full_id: Optional[str] = None


class DeleteOperation(Operation):
    op: Literal["DELETE"] = "DELETE"


class ModifyOperation(Operation):
    op: Literal["MODIFY"] = "MODIFY"
    new_content: str
