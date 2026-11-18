"""静态扫描：.vue 模板中引用的事件处理/方法是否在 script 中有声明。

抓取 @event="handler"、v-on、:prop 绑定里的标识符，检查 script setup 中
是否有对应声明（function/const/let/import/props/emit）。防止
「模板调用了不存在的函数，编译静默通过、运行静默失败」这类错误。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "frontend-mp" / "src"

# 模板中 @click="open(item)" / @open="openMedia" / :src="thumbUrl(x)" 等
BINDING_RE = re.compile(r'(?:@[\w.:-]+|v-on:[\w.:-]+|:(?:src|url|path)|v-if|v-for|v-show)\s*=\s*"([^"]+)"')
IDENT_RE = re.compile(r'\b([a-zA-Z_$][\w$]*)\s*(?:\(|\b)')

# script 中可认为是声明的模式
DECL_PATTERNS = [
    r'(?:async\s+)?function\s+([a-zA-Z_$][\w$]*)',
    r'(?:const|let|var)\s+([a-zA-Z_$][\w$]*)',
    r'import\s+(?:\{[^}]*\}|([a-zA-Z_$][\w$]*))',
    r'import\s*\{([^}]*)\}',
    r'(?:const|let)\s*\{([^}]*)\}\s*=',
]
IGNORE = {
    "true", "false", "null", "undefined", "item", "index", "entry", "group",
    "store", "emit", "props", "uni", "wx", "Math", "Date", "JSON", "Object",
    "Array", "String", "Number", "Boolean", "Promise", "setTimeout", "setInterval",
    "clearTimeout", "clearInterval", "console", "encodeURIComponent", "decodeURIComponent",
    "parseInt", "parseFloat", "isNaN", "navigateTo", "requireAuth", "dayjs",
}


def declared_names(script):
    names = set()
    # defineProps({...}) / defineProps([...]) 的 prop 名
    for pm in re.finditer(r'defineProps\s*(?:<[^>]*>)?\s*\(\s*(\{[^)]*\}|\[[^)]*\])', script):
        body = pm.group(1)
        for name in re.findall(r'([a-zA-Z_$][\w$]*)\s*:', body):
            names.add(name)
        for name in re.findall(r'["\']([a-zA-Z_$][\w$]*)["\']', body):
            names.add(name)
    for pattern in DECL_PATTERNS:
        for m in re.finditer(pattern, script):
            for group in m.groups():
                if not group:
                    continue
                for part in group.split(","):
                    part = part.strip()
                    name = part.split(":")[0].split(" as ")[-1].strip()
                    if name and re.match(r'^[a-zA-Z_$][\w$]*$', name):
                        names.add(name)
    return names


def template_identifiers(template):
    """只提取函数调用形式的标识符（前面不是 . 的），属性访问和 v-for 变量不报。"""
    ids = set()
    for m in BINDING_RE.finditer(template):
        expr = m.group(1)
        # v-for 循环变量声明（"item in items" / "(item, i) in items"）
        for vf in re.finditer(r'\(?([\w$, ()]+?)\)?\s+in\s+', expr):
            for var in vf.group(1).replace("(", "").replace(")", "").split(","):
                ids.discard(var.strip())
        for im in re.finditer(r'(?<![.\w$])([a-zA-Z_$][\w$]*)\s*\(', expr):
            ident = im.group(1)
            if ident not in IGNORE and not ident[0].isupper():
                ids.add(ident)
        # @event="handler" 裸标识符处理器（无括号）
        bare = re.fullmatch(r'\s*([a-zA-Z_$][\w$]*)\s*', expr)
        if bare and bare.group(1) not in IGNORE and not bare.group(1)[0].isupper():
            ids.add(bare.group(1))
    return ids


def main():
    problems = []
    for vue in sorted(ROOT.rglob("*.vue")):
        text = vue.read_text()
        tpl = re.search(r"<template>([\s\S]*?)</template>", text)
        script = re.search(r"<script setup>([\s\S]*?)</script>", text)
        if not tpl or not script:
            continue
        declared = declared_names(script.group(1))
        used = template_identifiers(tpl.group(1))
        missing = used - declared
        if missing:
            problems.append((vue.relative_to(ROOT), sorted(missing)))
    if problems:
        print("发现未声明的模板引用：")
        for path, missing in problems:
            print(f"  {path}: {', '.join(missing)}")
        sys.exit(1)
    print("所有模板绑定均有声明，未发现悬空引用")


if __name__ == "__main__":
    main()
