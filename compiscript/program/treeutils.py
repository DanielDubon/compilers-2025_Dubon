from antlr4.tree.Tree import TerminalNodeImpl

def _escape(s: str) -> str:
    return s.replace('"', r'\"')

def tree_to_pretty_text(tree, rule_names, level=0) -> str:
   
    indent = "  " * level
    if isinstance(tree, TerminalNodeImpl):
        return f"{indent}TOKEN({tree.getText()})\n"

    
    rule_name = rule_names[tree.getRuleIndex()]
    s = f"{indent}{rule_name}\n"
    if hasattr(tree, "children") and tree.children:
        for ch in tree.children:
            s += tree_to_pretty_text(ch, rule_names, level + 1)
    return s

def tree_to_dot(tree, parser) -> str:
    
    counter = {"i": 0}
    lines = [
        "digraph ParseTree {",
        '  node [shape=box, fontsize=10];',
        "  rankdir=TB;"
    ]

    def new_id():
        i = counter["i"]
        counter["i"] += 1
        return f"n{i}"

    def walk(t):
        nid = new_id()
        if isinstance(t, TerminalNodeImpl):
            label = _escape(t.getText())
        else:
            label = _escape(parser.ruleNames[t.getRuleIndex()])
        lines.append(f'  {nid} [label="{label}"];')

        if hasattr(t, "children") and t.children:
            for ch in t.children:
                cid = walk(ch)
                lines.append(f"  {nid} -> {cid};")
        return nid

    walk(tree)
    lines.append("}")
    return "\n".join(lines)
