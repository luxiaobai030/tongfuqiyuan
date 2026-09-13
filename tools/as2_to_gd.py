# -*- coding: utf-8 -*-
"""把原版 AS2 子集转成 GDScript"""
import os, re, io, sys, json

## 原版根舞台上“会自己播动画的角色”的名字（剧本里会点名让它们播某一段动画）
CLIP_NAMES = {"datang", "dr_boos", "laobai_yuehui", "xy_zhandou", "zhandou_GSYL"}

# ---------------- 词法 ----------------
TOKEN = re.compile(r"""
    (?P<ws>\s+)
  | (?P<num>\d+\.\d+|\d+)
  | (?P<str>"(?:[^"\\]|\\.)*")
  | (?P<op>\+=|-=|\*=|/=|<=|>=|==|!=|&&|\|\||[-+*/%<>=(){};,&|!.])
  | (?P<id>[A-Za-z_$][A-Za-z_0-9]*)
""", re.X)

def lex(src):
    toks = []
    i = 0
    while i < len(src):
        m = TOKEN.match(src, i)
        if not m:
            raise SyntaxError("bad char at %d: %r" % (i, src[i:i+20]))
        i = m.end()
        if m.lastgroup == "ws":
            continue
        toks.append((m.lastgroup, m.group()))
    toks.append(("eof", ""))
    return toks

# ---------------- 语法 ----------------
class Parser:
    def __init__(self, toks):
        self.t = toks; self.i = 0
    def peek(self, k=0): return self.t[min(self.i+k, len(self.t)-1)]
    def next(self):
        v = self.t[self.i]; self.i += 1; return v
    def accept(self, val):
        if self.t[self.i][1] == val:
            self.i += 1; return True
        return False
    def expect(self, val):
        if not self.accept(val):
            raise SyntaxError("expected %r got %r" % (val, self.peek()))
    def program(self):
        out = []
        while self.peek()[0] != "eof" and self.peek()[1] != "}":
            out.append(self.stmt())
        return out
    def block(self):
        if self.accept("{"):
            out = []
            while not self.accept("}"):
                if self.peek()[0] == "eof": raise SyntaxError("unterminated block")
                out.append(self.stmt())
            return ("block", out)
        return ("block", [self.stmt()])
    def stmt(self):
        t = self.peek()
        if t[1] == "if":
            self.next()
            self.expect("(")
            cond = self.expr()
            self.expect(")")
            then = self.block()
            els = None
            if self.peek()[1] == "else":
                self.next()
                if self.peek()[1] == "if":
                    els = ("block", [self.stmt()])
                else:
                    els = self.block()
            else:
                self.accept(";")
            return ("if", cond, then, els)
        if t[1] in ("stop", "play", "stopAllSounds", "nextFrame", "prevFrame", "unloadMovie", "loadMovie", "trace",
                    "gotoAndPlay", "gotoAndStop", "getURL", "tellTarget", "gotoAndStopIf"):
            self.next()
            args = []
            if self.accept("("):
                if not self.accept(")"):
                    while True:
                        args.append(self.expr())
                        if self.accept(")"): break
                        self.expect(",")
            self.accept(";")
            return ("call", t[1], args)
        # 赋值 / 表达式语句
        e = self.expr()
        if self.peek()[1] in ("=", "+=", "-=", "*=", "/="):
            op = self.next()[1]
            rhs = self.expr()
            self.accept(";")
            return ("assign", op, e, rhs)
        self.accept(";")
        return ("expr", e)
    def expr(self): return self.or_expr()
    def or_expr(self):
        left = self.and_expr()
        while self.peek()[1] in ("or", "||"):
            self.next(); right = self.and_expr()
            left = ("bin", "or", left, right)
        return left
    def and_expr(self):
        left = self.cmp_expr()
        while self.peek()[1] in ("and", "&&", "&"):
            self.next(); right = self.cmp_expr()
            left = ("bin", "and", left, right)
        return left
    def cmp_expr(self):
        left = self.add_expr()
        ops = []
        while self.peek()[1] in ("<", ">", "<=", ">=", "==", "!="):
            op = self.next()[1]
            ops.append((op, self.add_expr()))
        if not ops:
            return left
        return ("chain", left, ops)
    def add_expr(self):
        left = self.mul_expr()
        while self.peek()[1] in ("+", "-"):
            op = self.next()[1]; right = self.mul_expr()
            left = ("bin", op, left, right)
        return left
    def mul_expr(self):
        left = self.unary()
        while self.peek()[1] in ("*", "/", "%"):
            op = self.next()[1]; right = self.unary()
            left = ("bin", op, left, right)
        return left
    def unary(self):
        if self.peek()[1] == "-":
            self.next(); return ("neg", self.unary())
        if self.peek()[1] == "!":
            self.next(); return ("not", self.unary())
        return self.primary()
    def primary(self):
        t = self.next()
        if t[0] == "num":
            return ("num", float(t[1]) if "." in t[1] else int(t[1]))
        if t[0] == "str":
            return ("str", t[1][1:-1])
        if t[1] == "(":
            e = self.expr(); self.expect(")"); return e
        if t[0] == "id":
            name = t[1]
            # 成员访问 _root.x / this.x
            while self.peek()[1] == ".":
                self.next()
                sub = self.next()
                name = sub[1] if name in ("_root", "this", "_parent", "_level0") else name + "." + sub[1]
            if self.peek()[1] == "(":
                self.next()
                args = []
                if not self.accept(")"):
                    while True:
                        args.append(self.expr())
                        if self.accept(")"): break
                        self.expect(",")
                return ("call", name, args)
            return ("var", name)
        raise SyntaxError("unexpected token %r" % (t,))

# ---------------- 生成 GDScript ----------------
def gd_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

def emit_expr(e):
    k = e[0]
    if k == "num":
        return repr(e[1])
    if k == "str":
        return gd_str(e[1])
    if k == "var":
        n = e[1]
        if n in ("true", "false"): return n
        if n in ("undefined", "null", "NaN"): return "null"
        return 'V("%s")' % n
    if k == "neg":
        return "(-_num(%s))" % emit_expr(e[1])
    if k == "not":
        return "(not _truth(%s))" % emit_expr(e[1])
    if k == "bin":
        op, a, b = e[1], e[2], e[3]
        if op in ("and", "or"):
            return "(_truth(%s) %s _truth(%s))" % (emit_expr(a), op, emit_expr(b))
        fn = {"+": "_add", "-": "_sub", "*": "_mul", "/": "_div", "%": "_mod"}.get(op)
        if fn:
            return "%s(%s, %s)" % (fn, emit_expr(a), emit_expr(b))
        return "(" + emit_expr(a) + " " + op + " " + emit_expr(b) + ")"
    if k == "chain":
        parts = []
        left = e[1]
        for op, rhs in e[2]:
            a = emit_expr(left) if not parts else ("_num(%s)" % parts[-1])
            fn = {"==": "_eq", "!=": "_ne", "<": "_lt", ">": "_gt", "<=": "_le", ">=": "_ge"}[op]
            parts.append("%s(%s, %s)" % (fn, a, emit_expr(rhs)))
            left = rhs
        return parts[-1]
    if k == "call":
        name, args = e[1], e[2]
        if "." in name:
            return "0"
        a = ", ".join(emit_expr(x) for x in args)
        if name == "random":
            return "randi_range(0, int(_num(%s)) - 1)" % a
        if name == "int":
            return "int(_num(%s))" % a
        if name in ("String",):
            return "str(%s)" % a
        if name == "Number":
            return "_num(%s)" % a
        if name == "substring":
            return "(%s).substr(%s)" % (emit_expr(args[0]), ", ".join(emit_expr(x) for x in args[1:]))
        if name == "getTimer":
            return "0"
        if name in ("stopAllSounds", "play", "stop"):
            return "0"
        return "unknown_call(%s, [%s])" % (gd_str(name), a)
    raise SyntaxError("emit %r" % (e,))

def emit_stmt(s, ind):
    pad = "\t" * ind
    k = s[0]
    if k == "block":
        return "".join(emit_stmt(x, ind) for x in s[1])
    if k == "if":
        out = pad + "if " + emit_expr(s[1]) + ":\n"
        body = emit_stmt(s[2], ind+1) or (pad + "\tpass\n")
        out += body
        if s[3]:
            out += pad + "else:\n" + emit_stmt(s[3], ind+1)
        return out
    if k == "assign":
        op, target, rhs = s[1], s[2], s[3]
        if target[0] != "var":
            return pad + "pass # %s assign to non-var\n" % op
        name = target[1]
        rhs_code = emit_expr(rhs)
        if op == "=":
            return pad + 'setv("%s", %s)\n' % (name, rhs_code)
        fn = {"+=": "_add", "-=": "_sub", "*=": "_mul", "/=": "_div"}[op]
        return pad + 'setv("%s", %s(V(%s), %s))\n' % (name, fn, gd_str(name), rhs_code)
    if k == "call":
        name, args = s[1], s[2]
        if "." in name:
            owner, meth = name.rsplit(".", 1)
            if owner in CLIP_NAMES and meth in ("gotoAndPlay", "gotoAndStop", "play", "stop"):
                if meth == "play":
                    return pad + 'clip_play(%s)\n' % gd_str(owner)
                if meth == "stop":
                    return pad + 'clip_stop(%s)\n' % gd_str(owner)
                if args:
                    return pad + 'clip_go(%s, %s)\n' % (gd_str(owner), emit_expr(args[0]))
        if name == "gotoAndPlay":
            if not args: return pad + "pass\n"
            return pad + 'G(%s)\n' % emit_expr(args[0])
        if name in ("gotoAndStop", "gotoAndStopIf"):
            if not args: return pad + "pass\n"
            return pad + 'G(%s)\n' % emit_expr(args[0])
        if name == "stop":
            return pad + "halt_mm()\n"
        if name == "play":
            return pad + "resume_mm()\n"
        if name == "stopAllSounds":
            return pad + "stop_sounds()\n"
        if name == "getURL":
            return pad + "pass\n"
        return pad + "pass\n"
    if k == "expr":
        # 语句位置上的成员调用：就是把角色动画点名播放（dr_boos.gotoAndPlay(24)）
        if s[1][0] == "call" and "." in s[1][1]:
            return emit_stmt(("call", s[1][1], s[1][2]), ind)
        return pad + "pass\n"
    return pad + "pass\n"

def convert(src):
    """把 on(release){...} 或普通脚本转成 GDScript 函数体"""
    body = src.strip()
    m = re.match(r'''on\s*\((?:[^()]|"[^"]*")*\)\s*''', body, re.S)
    if m and m.start() == 0:
        body = body[m.end():]
    if body.startswith("{"):
        body = body[1:]
        if body.rstrip().endswith("}"):
            body = body.rstrip()[:-1]
    toks = lex(body)
    ast = Parser(toks).program()
    code = "".join(emit_stmt(s, 1) for s in ast)
    return code or "\tpass\n"

if __name__ == "__main__":
    S = sys.argv[1]
    ok = fail = 0
    errs = {}
    for root, _, files in os.walk(os.path.join(S, "scripts")):
        for fn in files:
            p = os.path.join(root, fn)
            src = io.open(p, encoding="utf-8").read()
            try:
                convert(src)
                ok += 1
            except Exception as e:
                fail += 1
                key = str(e)[:80]
                errs.setdefault(key, []).append(os.path.relpath(p, S))
    print("ok", ok, "fail", fail)
    for k, v in list(errs.items())[:20]:
        print(" ", k, "->", v[:3])
