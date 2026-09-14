# -*- coding: utf-8 -*-
"""跑开发用探针，并且保证玩家存档一根毛都不掉。

dev/ 下面那些探针（tools_probe / ui_shot …）会真的调存档接口、真的写文件，
直接对着玩家的存档跑就是在拿人家的进度做实验。所以这个脚本：

  1. 开跑前把 user:// 下所有存档挪到 _probe_saves/ 里（不是复制，是挪走）；
  2. 跑 Godot；
  3. 不管成功失败，都把探针写出来的档删掉，再把挪走的原档放回去，
     顺便核对哈希，确认和跑之前一模一样。

用法：
    python -X utf8 tools/run_probe.py dev/tools_probe.tscn
"""
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GODOT = r"F:\APP\Godot\Godot.exe"
USERDIR = os.path.join(os.environ["APPDATA"], "Godot", "app_userdata", "同福奇缘")
STASH = os.path.join(ROOT, "_probe_saves")


def saves():
    if not os.path.isdir(USERDIR):
        return []
    return sorted(f for f in os.listdir(USERDIR)
                  if f.startswith("tongfu") and f.endswith(".json"))


def digest(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    if len(sys.argv) < 2:
        raise SystemExit("用法：python tools/run_probe.py dev/xxx.tscn")
    scene = sys.argv[1]

    os.makedirs(STASH, exist_ok=True)
    before = {}
    for f in saves():
        src = os.path.join(USERDIR, f)
        before[f] = digest(src)
        dst = os.path.join(STASH, f)
        if os.path.exists(dst):
            os.remove(dst)
        shutil.move(src, dst)
    print("[探针] 先把玩家存档挪走：%s" % (", ".join(before) or "（一个都没有）"))

    try:
        proc = subprocess.run([GODOT, "--path", os.path.join(ROOT, "game"), scene],
                              cwd=ROOT, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        print(proc.stdout or "", end="")
        print(proc.stderr or "", end="")
        print("[探针] Godot 退出码 %d" % proc.returncode)
    finally:
        for f in saves():                      # 探针自己存出来的档，丢掉
            os.remove(os.path.join(USERDIR, f))
        same = True
        for f, h in before.items():            # 原档放回原位
            shutil.move(os.path.join(STASH, f), os.path.join(USERDIR, f))
            now = digest(os.path.join(USERDIR, f))
            same = same and now == h
            print("[探针] 放回 %s  一致=%s" % (f, now == h))
        # Godot 自己写的临时目录也顺手清掉
        probe_dir = os.path.join(USERDIR, "_probe_backup")
        if os.path.isdir(probe_dir):
            shutil.rmtree(probe_dir)
        print("[探针] 存档已还原，全部一致 = %s" % same)
        if not same:
            raise SystemExit("存档不对劲，别继续了")


if __name__ == "__main__":
    main()
