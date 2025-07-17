from app.core.agent.models import Sentence
from typing import Dict, List


def parse_sentences_to_dialog(sentences: List[Sentence], speker: Dict[str, str]) -> str:
    """
    将sentences转换为dialog
    Sentence:
        spk: str
        sentence_id: int
        content: str
    diaglog: str
        {sentence_id}. {spk_nickname}： {sentence.content}
    """
    dialogs_list = []
    for sentence in sentences:
        spk = speker[sentence.spk]
        dialogs_list.append(f"{sentence.sentence_id}. {spk}：{sentence.content}")
    return "\n".join(dialogs_list)


def judge_node_type_by_full_id(full_id: str) -> str:
    """
    根据full_id判断节点类型
    """
    if "." not in full_id:
        return "issue"
    elif "." in full_id and full_id.count(".") == 1:
        return "position"
    elif "." in full_id and full_id.count(".") == 2:
        return "argument"
    else:
        return "unknown"
