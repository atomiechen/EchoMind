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
