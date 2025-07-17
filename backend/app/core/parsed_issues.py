from typing import List, Literal, Optional, Tuple
from pydantic import BaseModel
from app.core.utils_echo import judge_node_type_by_full_id
from app.core.agent.models import Issue, Relation, Position
import copy


class ParsedIssue(BaseModel):
    parsed_issue: List[Issue]

    @property
    def issue_map_list_without_delete(self):
        result: List[Issue] = []
        parsed_issue_tmp = copy.deepcopy(self.parsed_issue)
        for issue in parsed_issue_tmp:
            if issue.type == "deleted":
                continue
            pos_list: List[Position] = []
            for pos in issue.positions:
                if pos.type == "deleted":
                    continue
                pos_list.append(pos)
            issue.positions = pos_list
            result.append(issue)
        return result

    def get_position_by_full_id(self, full_id: str) -> Optional[Position]:
        father_issue_id = int(full_id.split(".")[0])
        position_id = int(full_id.split(".")[1])
        return self.parsed_issue[father_issue_id - 1].positions[position_id - 1]

    def get_issue_map_dict(self):
        # res_dict = {}
        # for issue in self.parsed_issue:
        #     res_dict[str(issue.issue_id)] = issue.model_dump()
        # return res_dict
        res_list = []
        for issue in self.parsed_issue:
            res_list.append(issue.model_dump())
        return {"issue_map": res_list}

    def delete_position_self(self, position_full_id: str) -> None:
        """
        删除position：
        - 删除position本身
        - 删除position下的所有argument
        - 将所有指向这个position的issue的source置空
        """
        print("delete_position_self", position_full_id)
        father_issue_id = int(position_full_id.strip().split(".")[0])
        chosen_position_id = int(position_full_id.strip().split(".")[1])
        position = self.parsed_issue[father_issue_id - 1].positions[
            chosen_position_id - 1
        ]
        position.type = "deleted"  # 标记position为无效

        # 标记所有关联的pros和cons为无效
        for pro in position.pros:
            pro.type = "deleted"
        for con in position.cons:
            con.type = "deleted"

        # 将所有指向这个position的issue的source置空
        for issue in self.parsed_issue:
            if issue.source and issue.source.target_id == position_full_id:
                issue.source = None
                issue.type = "deleted"

    def delete_issue_self(self, issue_full_id: str) -> None:
        """
        删除issue：
        - 删除issue本身
        - 删除issue下的所有position及其argument
        - 将所有指向这些position的issue的source置空
        """
        chosen_issue_id = int(issue_full_id)
        issue = self.parsed_issue[chosen_issue_id - 1]
        issue.type = "deleted"  # 标记issue为无效

        # 删除所有一层position，将所有指向这些position的issue的source置空
        for position in issue.positions:
            self.delete_position_self(position.full_id)

    def delete_position_family(self, position_full_id: str):
        """
        删除position及其family：
        - 删除position本身
        - 删除position下的所有argument
        - 删除position长出的所有issue及其family
        """
        self.delete_position_self(position_full_id)
        # 1. 找到所有长出的issue
        # 2. 删除这些issue
        # 3. 递归删除这些issue下的所有position及其family
        for issue in self.parsed_issue:
            if issue.source and issue.source.target_id == position_full_id:
                self.delete_issue_self(issue.full_id)
                for pos in issue.positions:
                    self.delete_position_family(pos.full_id)

    def user_delete_node(self, full_id: str):
        node_type = judge_node_type_by_full_id(full_id)
        if node_type == "issue":
            self.delete_issue_self(full_id)
        elif node_type == "position":
            self.delete_position_self(full_id)
        return full_id

    def confirm_node_fathers(self, node_full_id: str):
        """
        将节点及其所有直系父辈的type改为confirmed
        """
        node_type = judge_node_type_by_full_id(node_full_id)
        if node_type == "issue":
            self.parsed_issue[int(node_full_id) - 1].type = "confirmed"
            source = self.parsed_issue[int(node_full_id) - 1].source
            if source is not None:
                self.confirm_node_fathers(source.target_id)
        elif node_type == "position":
            father_issue_id = int(node_full_id.split(".")[0])
            father_position_id = int(node_full_id.split(".")[1])
            self.parsed_issue[father_issue_id - 1].positions[
                father_position_id - 1
            ].type = "confirmed"
            self.confirm_node_fathers(f"{father_issue_id}")

    def user_add_node(
        self,
        node_type: Optional[Literal["ISSUE", "POSITION"]],
        father_id: str,
        content: str,
    ) -> str:
        """
        添加node
        - 在对应的位置加上node
        - 改变其所有父辈的返回新节点的full_id
        """
        if node_type == "ISSUE":
            father_position_4_father_issue_id = father_id.split(".")[0]
            father_position_id = father_id.split(".")[1]
            issue_full_id = str(len(self.parsed_issue) + 1)
            self.parsed_issue.append(
                Issue(
                    full_id=issue_full_id,
                    content=content,
                    type="confirmed",
                    issue_id=len(self.parsed_issue) + 1,
                    positions=[],
                    source=Relation(
                        target_id=father_id,
                        target_type="position",
                        target_content=self.parsed_issue[
                            int(father_position_4_father_issue_id) - 1
                        ]
                        .positions[int(father_position_id) - 1]
                        .content,
                        content="",
                    ),
                )
            )
            self.confirm_node_fathers(father_id)
            return issue_full_id
        elif node_type == "POSITION":
            father_issue_id = father_id
            position_id = len(self.parsed_issue[int(father_issue_id) - 1].positions) + 1
            position_full_id = f"{father_issue_id}.{position_id}"
            self.parsed_issue[int(father_issue_id) - 1].positions.append(
                Position(
                    full_id=position_full_id,
                    content=content,
                    type="confirmed",
                    position_id=position_id,
                    pros=[],
                    cons=[],
                )
            )
            self.confirm_node_fathers(position_full_id)
            return position_full_id
        else:
            return "0"

    def agent_modify_node(self, full_id: str, new_content: str) -> bool:
        """
        修改node
        返回: 是否修改成功
        """
        node_type = judge_node_type_by_full_id(full_id)
        if node_type == "issue":
            self.parsed_issue[int(full_id) - 1].content = new_content
        elif node_type == "position":
            position = self.get_position_by_full_id(full_id)
            if position:
                if position.content != new_content:
                    position.generated_issue = False
                position.content = new_content
            else:
                return False
            # 修改所有指向这个position的issue的source.target_content
            for issue in self.parsed_issue:
                if issue.source and issue.source.target_id == full_id:
                    issue.source.target_content = new_content
        return True

    def user_modify_node(self, full_id: str, new_content: str):
        """
        修改node
        """
        node_type = judge_node_type_by_full_id(full_id)
        if node_type == "issue":
            self.parsed_issue[int(full_id) - 1].content = new_content
        elif node_type == "position":
            position = self.get_position_by_full_id(full_id)
            if position:
                if position.content != new_content:
                    position.generated_issue = False
                position.content = new_content
            # 修改所有指向这个position的issue的source.target_content
            for issue in self.parsed_issue:
                if issue.source and issue.source.target_id == full_id:
                    issue.source.target_content = new_content
        self.confirm_node_fathers(full_id)
        return full_id

    def i2p_current_positions(self, issue_id: int) -> Tuple[str, List[Position]]:
        """
        输出：
        - 返回 issue 所有存在的 position 及其 type，编号为对应的full_id
        - 返回list记录所有传入的 full_id 与 content 的dict{"full_id": content}
        """
        positions: List[Position] = self.parsed_issue[issue_id - 1].positions
        positions_str_list = []
        input_positions: List[Position] = []
        for pos_id, position in enumerate(positions):
            if position.type == "deleted":
                continue
            position_str = f"{position.full_id} position: {position.content}"
            if position.type == "confirmed":
                position_str += "\n- unmodifiable"
            elif position.type == "unconfirmed":
                position_str += "\n- modifiable"
            position_str += "\n// " + position.note if position.note else ""
            positions_str_list.append(position_str)
            input_positions.append(position)
        return "\n".join(positions_str_list), input_positions

    def get_position_4_sub_issue(self, position_full_id: str) -> List[Issue]:
        sub_issues: List[Issue] = []
        for issue in self.parsed_issue:
            if (
                issue.source
                and issue.source.target_id == position_full_id
                and issue.type != "deleted"
            ):
                sub_issues.append(issue)
        return sub_issues

    def p2i_parse_positions(self, issue_id: int) -> str:
        """
        将当前 issue 下 所有【存在】、【没有生成过 issue】 【没有sub_issue】的 position 输出字符串
        """
        p2i_str = ""
        for position in self.parsed_issue[issue_id - 1].positions:
            if (
                position.type != "deleted"
                and (not position.generated_issue)
                and self.get_position_4_sub_issue(position.full_id) == []
            ):
                p2i_str += f"{position.full_id} position: {position.content}\n"
        return p2i_str

    def add_new_positions(
        self, new_positions: List, chosen_id: int, input_positions: List
    ) -> List[Position]:
        """
        输入：
        [
            {
                "order_id": "1.1",
                "position": "position1 content",
                "note": "note 1 content"
            },
            {
                "order_id": "1.3",
                "position": "position 2 content",
                "note": "note 2 content"
            }
        ]
        流程：
        for agent的输出position：
         - 如果full_id可以和已有的full_id对上:
            - 原有的 position 是 deleted: raise valueerror
            - 原有的 position 是 confirmed: continue
            - 原有的 position 是 unconfirmed: 修改原有的 position
        - 如果对不上:
            - 新的编号小于等于当前的最大编号: raise valueerror
            - 作为新的节点加入
        输出:
        - 传给生成 p2i agent 的 List[Position]
        """
        # 获取实际有效的position: List[Position]
        valid_positions: List[Position] = []
        valid_full_ids = []
        for position in self.parsed_issue[chosen_id - 1].positions:
            if position.type != "deleted":
                valid_positions.append(position)
                valid_full_ids.append(position.full_id)
        if valid_full_ids == []:
            max_position_full_id = ""
        else:
            max_position_full_id = valid_full_ids[-1]

        # 传给issue的输入: List[Position]
        i2p_postions: List[Position] = []

        for new_position in new_positions:
            # 如果在有效的position中
            if new_position["order_id"] in valid_full_ids:
                valid_position = [
                    position
                    for position in valid_positions
                    if position.full_id == new_position["order_id"]
                ][0]
                # 如果是deleted就报错
                if valid_position.type == "deleted":
                    raise ValueError("[i2p_rror] 原来的position已经被删除了")
                # 如果是confirmed就不修改
                elif valid_position.type == "confirmed":
                    continue
                # 如果是unconfirmed就修改
                elif valid_position.type == "unconfirmed":
                    if (
                        valid_position.content != new_position["position"]
                        and new_position["position"] != "None"
                    ):
                        self.agent_modify_node(
                            new_position["order_id"], new_position["position"]
                        )
                        i2p_postions.append(valid_position)
            # 如果不在有效的position中
            else:
                # 如果新的position的full_id没有当前最大的节点大，就报错
                if max_position_full_id != "" and (
                    new_position["order_id"].split(".")[0]
                    != max_position_full_id.split(".")[0]
                    or int(new_position["order_id"].split(".")[1])
                    <= int(max_position_full_id.split(".")[1])
                ):
                    raise ValueError(
                        f"[i2p_error] 新增的position的编号{new_position['order_id']}不大于当前最大的编号{max_position_full_id}"
                    )
                position_id = len(self.parsed_issue[chosen_id - 1].positions) + 1
                position_full_id = f"{chosen_id}.{position_id}"
                self.parsed_issue[chosen_id - 1].positions.append(
                    Position(
                        full_id=position_full_id,
                        content=new_position["position"],
                        position_id=position_id,
                        pros=[],
                        cons=[],
                        type="unconfirmed",
                        note=new_position["note"],
                    )
                )
                i2p_postions.append(self.parsed_issue[chosen_id - 1].positions[-1])
        return i2p_postions

    def add_new_issues(self, new_issues: List, chosen_id: int):
        """
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
        流程：
        - 如果当前的 position 是 deleted , 就continue
        - 如果当前的 position 是 confirmed, 就continue
        - 如果当前的 position 是 unconfirmed, 就加入新的 issue
        """

        for new_issue in new_issues:
            father_position = self.get_position_by_full_id(new_issue["position_id"])
            if father_position:
                if father_position.type == "deleted":
                    continue
                else:
                    for sub_issue in new_issue["sub_issues"]:
                        issue_id = len(self.parsed_issue) + 1
                        self.parsed_issue.append(
                            Issue(
                                full_id=str(issue_id),
                                content=sub_issue,
                                type="unconfirmed",
                                issue_id=issue_id,
                                positions=[],
                                source=Relation(
                                    target_id=father_position.full_id,
                                    target_type="position",
                                    target_content=father_position.content,
                                    content="",
                                ),
                            )
                        )

    def issue_chain(self, chosen_issue_id: int) -> str:
        issue_chain = []
        current_issue = self.parsed_issue[chosen_issue_id - 1]
        issue_chain.append(current_issue.content)
        source = current_issue.source
        while source is not None:
            father_position_full_id = source.target_id
            father_position_id = father_position_full_id.split(".")[1]
            father_issue_id = father_position_full_id.split(".")[0]
            father_issue = self.parsed_issue[int(father_issue_id) - 1]
            if father_issue.type == "deleted":
                break
            # add position content
            issue_chain.append(
                father_issue.positions[int(father_position_id) - 1].content
            )
            # add issue content
            issue_chain.append(father_issue.content)
            source = father_issue.source
        return " -> ".join(issue_chain[::-1])
