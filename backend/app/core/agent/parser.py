import datetime
import re
from typing import Dict, List

from app.core.agent.models import Issue


def parse_summary(new_summary_output: str) -> List[str]:
    """
    输入:
    - ${summary content}
    - ${summary content 2}
    输出：
    [
        "summary content",
        "summary content 2"
    ]
    """
    lines = new_summary_output.strip().split("\n")
    summary_pattern = r"^- (.*)"
    summary_list = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        summary_match = re.match(summary_pattern, line)
        if summary_match:
            summary_list.append(summary_match.group(1))
    return summary_list


def issue_map_to_str(issues: List[Issue]) -> str:
    result = []
    beijing_time = datetime.datetime.now()
    result.append(f"Issue Map at {beijing_time}:")
    for issue in issues:
        result.append(f"{issue.full_id} issue: {issue.content}")
        for pos in issue.positions:
            result.append(f"- position {pos.full_id}: {pos.content}")
            # for arg in pos.pros:
            #     result.append(f'  - {arg.full_id} pro: {arg.content}')
            # for arg in pos.cons:
            #     result.append(f'  - {arg.full_id} con: {arg.content}')
        if issue.source:
            result.append("- from:")
            result.append(
                f"  - {issue.source.target_id} {issue.source.target_type}: {issue.source.target_content} <- {issue.source.content}"
            )
        else:
            result.append("- from: None")
        result.append("")
    return "\n".join(result)


"""
下面的三个函数：parse_new_position, parse_final_issue, parse_suggest_position
是meeting agent gamma版本中处理agent生成的数据的函数
"""


def gamma_parse_new_position(new_position: str) -> List[Dict]:
    """
    输入：
    1.1 position {position1 content}
    // {note 1 content}
    1.3 position {position 2 content}
    // {note 2 content}
    输出：
    [
        {
            "order_id": 1,
            "position": "position1 content",
            "note": "note 1 content"
        },
        {
            "order_id": 2,
            "position": "position 2 content",
            "note": "note 2 content"
        }
    ]
    """
    result = []
    position_pattern = r"(\d+\.\d+)\s*position\s*[:：]?\s*(.*)"
    note_pattern = r"//\s*(.*)"

    current_dict = {}
    lines = new_position.strip().split("\n")
    # if len(lines) == 1 and lines[0] == "None":
    #     return []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        position_match = re.search(position_pattern, line)
        note_match = re.search(note_pattern, line)
        if position_match:
            if current_dict:
                result.append(current_dict)
                current_dict = {}
            current_dict["order_id"] = position_match.group(1).strip()
            current_dict["position"] = position_match.group(2).strip()
        elif note_match:
            current_dict["note"] = note_match.group(1)
    if current_dict:
        result.append(current_dict)

    return result


def gamma_parse_new_issue(new_issue: str) -> List[str]:
    """
        输入：
    ${The number of the position to be split}. ${Original position text}
    - ${Issue number, starting from 1 within each position}.${Content of the split issue}
    - ${Issue number, starting from 1 within each position}.${Content of the split issue}
    1.1 position xxx
    1.1.1 sub_issue xxx
        输出：
        [
            {
                "position_id": 1.1
                "position_content": "Original position text",
                "sub_issues": [
                    "Content of the split issue",
                    "Content of the split issue"
                ]
            }
        ]
    """
    result = []

    # Regular expression patterns
    position_pattern = r"^(\d+\.\d+)\s+position\s*[:：]?\s*(.*)"
    sub_issue_pattern = r"^-?\s*(\d+(\.\d+)*)\s+(sub_issue)?\s*[:：]?\s*(.*)"

    lines = new_issue.strip().split("\n")

    current_position = None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        position_match = re.match(position_pattern, line.strip())
        sub_issue_match = re.match(sub_issue_pattern, line)

        if position_match:
            position_full_id = position_match.group(1).strip()
            position_content = position_match.group(2).strip()
            current_position = {
                "position_id": position_full_id,
                "position_content": position_content,
                "sub_issues": [],
            }
            result.append(current_position)

        elif sub_issue_match and current_position is not None:
            sub_issue_content = sub_issue_match.group(4)
            current_position["sub_issues"].append(sub_issue_content)
    return result
