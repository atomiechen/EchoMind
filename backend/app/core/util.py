import json
from typing import List, Tuple


from app.core.agent.models import Issue
from app.core.parsed_issues import ParsedIssue


def get_max_numbered_parsed_issues(latest_issue_map_path) -> Tuple[List[Issue], str]:
    """
    返回一个元组(parsed_issues:list, topic:str)
    """
    old_parsed_issue = []
    topic = ""
    if latest_issue_map_path.exists():
        files = list(latest_issue_map_path.glob("*.json"))
        max_number = -1
        max_file_path = None
        for file_path in files:
            try:
                number = int(file_path.stem.split("-")[-1])
                if number > max_number:
                    max_number = number
                    max_file_path = file_path
            except ValueError:
                continue  # 如果文件名中的编号不是整数，跳过
        # 输出编号最大的文件路径
        if max_file_path is not None:
            with open(max_file_path, "r") as f:
                issue_map = json.load(f)
                if issue_map:
                    tmp_parsed_issue: ParsedIssue = ParsedIssue(
                        parsed_issue=issue_map["issue_map"]
                    )
                    old_parsed_issue = tmp_parsed_issue.issue_map_list_without_delete
            if old_parsed_issue:
                topic = old_parsed_issue[0].content
        else:
            print("[resume_error] No valid json files found.")
    else:
        print("[resume_error] No issue_map directory found.")

    if old_parsed_issue == []:
        old_parsed_issue = [
            Issue(
                full_id="1",
                content="Unknown",
                type="unconfirmed",
                issue_id=1,
                positions=[],
                source=None,
            )
        ]
    if topic == "":
        topic = "Unknown"

    return old_parsed_issue, topic
