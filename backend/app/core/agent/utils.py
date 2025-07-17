from typing import List, Optional

from handyllm import ChatPrompt

from app.core.agent.models import Sentence, SpeakerBlock


def extract_xml_tag(text: str, tag: str):
    # extract text between <tag> and </tag>
    start_tag = f"<{tag}>"
    end_tag = f"</{tag}>"
    start = text.find(start_tag)
    if start == -1:
        return ""
    start += len(start_tag)
    end = text.find(end_tag)
    if end == -1:
        end = len(text)
    return text[start:end]


def parse_sub_issue_list(sub_issue_list: str):
    """
    <sub_issue_list>
    - xxx
    - xxx
    - xxx
    </sub_issue_list>
    """
    sub_issues = []
    for line in sub_issue_list.split("\n"):
        if line.startswith("-"):
            sub_issues.append(line[1:].strip())
    return sub_issues


def sentence_ids_to_blocks(
    sentence_ids: List[int], speaker_blocks: List[SpeakerBlock]
) -> List[SpeakerBlock]:
    # find the sentence_ids in speaker_blocks
    selected_blocks = []
    for speaker_block in speaker_blocks:
        selected_sentences = []
        for sentence in speaker_block.block:
            if sentence.sentence_id in sentence_ids:
                selected_sentences.append(sentence)
        if selected_sentences:
            selected_block = SpeakerBlock(
                spk=speaker_block.spk, block=selected_sentences
            )
            selected_blocks.append(selected_block)
    return selected_blocks


def sentences_to_blocks(sentences: List[Sentence]):
    speaker_blocks: List[SpeakerBlock] = []
    cur_block: Optional[SpeakerBlock] = None
    # print(f"-----get sentences {sentences} -----")
    for sentence in sentences:
        if cur_block is None or cur_block.spk != sentence.spk:
            cur_block = SpeakerBlock(spk=sentence.spk, block=[])
            speaker_blocks.append(cur_block)
        cur_block.block.append(sentence)
    # print(f"-----get speaker_blocks {speaker_blocks} -----")
    return speaker_blocks


def str_delete_tag(text: str, tag: str) -> str:
    start_tag = f"<{tag}>"
    end_tag = f"</{tag}>"
    start = text.find(start_tag)
    if start == -1:
        return ""
    start += len(start_tag)
    end = text.find(end_tag)
    if end == -1:
        end = len(text)
    return text[:start_tag] + text[end_tag:]


def prompt_delete_tag(prompt: ChatPrompt, tag: str) -> ChatPrompt:
    for i in range(len(prompt.messages)):
        prompt_str = prompt.messages[i]["content"]
        tag_str = extract_xml_tag(prompt_str, tag)
        print("进入循环")
        while tag_str != "":
            start_tag = f"<{tag}>"
            end_tag = f"</{tag}>"
            start = prompt_str.find(start_tag)
            if start == -1:
                continue
            end = prompt_str.find(end_tag)
            if end == -1:
                end = len(prompt_str)
            else:
                end += len(end_tag)
            prompt_str = prompt_str[:start] + prompt_str[end:]
            tag_str = extract_xml_tag(prompt_str, tag)
        print("循环结束")
        prompt.messages[i]["content"] = prompt_str

    # prompt_str = prompt.result_str
    # start_tag = f'<{tag}>'
    # end_tag = f'</{tag}>'
    # start = prompt_str.find(start_tag)
    # if start == -1:
    #     return prompt
    # start += len(start_tag)
    # end = prompt_str.find(end_tag)
    # if end == -1:
    #     end = len(prompt_str)
    # prompt.messages[-1]['content'] = prompt_str[:start_tag] + prompt_str[end_tag:]
    return prompt


def only_save_tag(prompt: ChatPrompt, tag: str) -> ChatPrompt:
    for i in range(len(prompt.messages)):
        prompt_str = prompt.messages[i]["content"]
        new_prompt_str = ""

        prompt.messages[i]["content"] = new_prompt_str
    return prompt


# def parse_issue_chain(parsed_issues: List[Issue], chosen_node_index)->str:
#     '''
#     从parsed_issues中解析出issue chain
#     ！！！注意：issue map是从1开始的！！！
#     '''
#     current_issue = parsed_issues[chosen_node_index-1]
#     issue_chain = [current_issue.content]
#     while current_issue.source is not None:
#         current_issue = parsed_issues[int(current_issue.source.target_id)-1]
#         issue_chain.append(current_issue.content)
#     issue_chain.reverse()
#     return ' -> '.join(issue_chain)

# def parse_new_positions(text_data:str)->List[Position]:
#     positions = []
#     current_position = None
#     current_pros = []
#     current_cons = []
#     for line in text_data.split("\n"):
#         line = line.strip()
#         if line.startswith('-') and 'position' in line:
#             if current_position is not None:
#                 # 保存上一个position
#                 positions.append(Position(**current_position, pros=current_pros, cons=current_cons))
#             current_pros = []
#             current_cons = []
#             parts = line.split(' ', 2)
#             full_id = parts[1].strip()
#             content = ' '.join(parts[2].split(':')[1:]).strip()  # 修正获取content的方法
#             position_id = int(full_id.split('.')[1])
#             current_position = {"full_id": full_id, "content": content, "position_id": position_id}
#         elif current_position is not None:  # 确保current_position已初始化
#             if 'ref' in line:
#                 parts = line.split(':')
#                 current_position['ref'] = parts[1].strip()
#             elif 'pro' in line:
#                 parts = line.split(':', 1)
#                 argument_id = parts[0].split()[-1]
#                 content = parts[1].strip()
#                 full_id = parts[0].split()[1]
#                 current_pros.append(Argument(full_id=full_id, content=content, argument_id=argument_id))
#             elif 'con' in line:
#                 parts = line.split(':', 1)
#                 argument_id = parts[0].split()[-1]
#                 content = parts[1].strip()
#                 full_id = parts[0].split()[1]
#                 current_cons.append(Argument(full_id=full_id, content=content, argument_id=argument_id))

#     # 添加最后一个position
#     if current_position is not None:
#         positions.append(Position(**current_position, pros=current_pros, cons=current_cons))

#     return positions
