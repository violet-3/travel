"""容错 JSON 解析 · LLM/Dify 输出格式不完美时的统一修复入口

所有 Agent 与 Dify 客户端共用，避免各写一份解析逻辑。
"""

import json
import re


def fix_truncated_json(text: str) -> str:
    """修复被截断的 JSON —— 补全缺失的字符串引号和闭合方括号/花括号

    原理: 遍历字符，记录是否在字符串内以及括号栈的状态，
    然后按 LIFO 顺序补全缺失的闭合符号。
    """
    text = text.rstrip().rstrip(",").rstrip()

    # 第一遍: 检查字符串是否被截断（未闭合的引号）
    in_string = False
    escape = False
    for ch in text:
        if escape:
            escape = False
        elif ch == "\\" and in_string:
            escape = True
        elif ch == '"':
            in_string = not in_string
    if in_string:
        text += '"'

    # 第二遍: 检查所有括号/花括号是否闭合
    stack = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            escape = False
        elif ch == "\\" and in_string:
            escape = True
        elif ch == '"':
            in_string = not in_string
        elif not in_string:
            if ch in "{[":
                stack.append(ch)
            elif ch == "}":
                if stack and stack[-1] == "{":
                    stack.pop()
            elif ch == "]":
                if stack and stack[-1] == "[":
                    stack.pop()

    closers = {"{": "}", "[": "]"}
    for opener in reversed(stack):
        text += closers[opener]

    return text


def parse_json(text) -> dict | list:
    """容错 JSON 解析，支持对象和数组

    注意: 不做全局单引号→双引号替换，那会破坏内容里的英文撇号（如 don't）。
    """
    if isinstance(text, (dict, list)):
        return text
    if not isinstance(text, str):
        raise ValueError(f"Expected string, got {type(text)}")

    text = text.strip()

    # 尝试 1: 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试 2: 提取 markdown 代码块
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试 3: 找到最外层的 { } 或 [ ]
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

    # 尝试 4: 去尾部逗号后再取最外层
    cleaned = re.sub(r",\s*([}\]])", r"\1", text)
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = cleaned.find(start_char)
        end = cleaned.rfind(end_char)
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                pass

    # 尝试 5: 修复被截断的 JSON（补全缺失的引号和闭合括号）
    try:
        return json.loads(fix_truncated_json(text))
    except json.JSONDecodeError:
        pass

    raise ValueError(f"无法解析 JSON，LLM 原始输出:\n{text[:800]}")
