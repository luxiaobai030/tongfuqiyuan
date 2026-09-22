# -*- coding: utf-8 -*-
"""只把安卓导出模板里用得着的那几十 MB 抠下来。

官方模板包 Godot_v<版本>_export_templates.tpz 有一个多 G，安卓导出其实
只用得到里面那一个 apk。.tpz 本身就是个 zip，而 zip 的目录在文件末尾，
所以可以只用 HTTP Range 请求把文件尾巴那段读出来、照着目录里的偏移量
只下要的那一条 —— 剩下的一个 G 连碰都不用碰。

下好的模板直接放进 %APPDATA%/Godot/export_templates/<版本>/，
和用编辑器「安装模板」出来的效果一模一样。

用法（墙内一般得挂代理，走环境变量或 --proxy）：
    python -X utf8 tools/fetch_android_template.py --proxy http://127.0.0.1:7897
"""
import argparse
import collections
import io
import os
import sys
import urllib.request
import zipfile

REPO = "https://github.com/godotengine/godot-builds/releases/download"
## 每次 Range 请求光「开始传」就得等一两秒（GitHub 的 CDN 就这样），
## 所以块开大点、少求几次 —— 一块 1 MB 能磨掉好几倍的时间。
BLOCK = 16 << 20
KEEP_BLOCKS = 3               # 手上最多留几块，别把整个包堆在内存里


class HttpFile(io.RawIOBase):
    """把一个 URL 包装成可随机读的文件对象：底下按块缓存、按 Range 取。"""

    def __init__(self, url, proxy=None):
        super().__init__()
        self.url = url
        handlers = []
        if proxy:
            handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
        self._opener = urllib.request.build_opener(*handlers)
        self._blocks = collections.OrderedDict()
        self._pos = 0
        self.size = self._probe_size()

    def _request(self, start, end):
        req = urllib.request.Request(self.url, headers={"Range": "bytes=%d-%d" % (start, end)})
        with self._opener.open(req) as resp:
            return resp.read()

    def _probe_size(self):
        """顺手要一个字节，从 Content-Range 里读出整包多大。"""
        req = urllib.request.Request(self.url, headers={"Range": "bytes=0-0"})
        with self._opener.open(req) as resp:
            rng = resp.headers.get("Content-Range", "")
            if "/" in rng:
                return int(rng.rsplit("/", 1)[1])
            return int(resp.headers["Content-Length"])

    def _block(self, idx):
        if idx in self._blocks:
            self._blocks.move_to_end(idx)
            return self._blocks[idx]
        start = idx * BLOCK
        end = min(start + BLOCK, self.size) - 1
        print("[模板]   下第 %d 块（%.0f–%.0f MB）" % (idx, start / 2 ** 20, end / 2 ** 20), flush=True)
        self._blocks[idx] = self._request(start, end)
        while len(self._blocks) > KEEP_BLOCKS:
            self._blocks.popitem(last=False)
        return self._blocks[idx]

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self._pos

    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_SET:
            self._pos = offset
        elif whence == io.SEEK_CUR:
            self._pos += offset
        else:
            self._pos = self.size + offset
        return self._pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self._pos
        out = bytearray()
        while n > 0 and self._pos < self.size:
            idx, off = divmod(self._pos, BLOCK)
            chunk = self._block(idx)[off:off + n]
            if not chunk:
                break
            out += chunk
            self._pos += len(chunk)
            n -= len(chunk)
        return bytes(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="4.7-stable")
    ap.add_argument("--what", default="android_release.apk",
                    help="要抠出来的模板名，逗号分隔（默认只要安卓 release）")
    ap.add_argument("--proxy",
                    default=os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY"),
                    help="HTTP 代理，例如 http://127.0.0.1:7897")
    ap.add_argument("--dir", default=None, help="装到哪儿，默认 Godot 的模板目录")
    args = ap.parse_args()

    url = "%s/%s/Godot_v%s_export_templates.tpz" % (REPO, args.version, args.version)
    ## Godot 认的模板目录名是版本号那套写法（4.7.stable），
    ## 不是 GitHub 标签那套（4.7-stable）—— 差一个字符它就当没装过。
    dest = args.dir or os.path.join(os.environ["APPDATA"], "Godot", "export_templates",
                                    args.version.replace("-", "."))
os.makedirs(dest, exist_ok=True)

    print("[模板] 打开 %s" % url)
    src = HttpFile(url, args.proxy)
    print("[模板] 整包 %.1f MB —— 只下要的那几条" % (src.size / 2 ** 20))
    with zipfile.ZipFile(src) as z:
        names = {os.path.basename(n): n for n in z.namelist()}
        for w in [x.strip() for x in args.what.split(",") if x.strip()]:
            if w not in names:
                raise SystemExit("模板包里没有 %s" % w)
            info = z.getinfo(names[w])
            out = os.path.join(dest, w)
            print("[模板] 取 %s（压缩后 %.1f MB）" % (w, info.compress_size / 2 ** 20))
            with z.open(info) as fin, open(out + ".part", "wb") as fout:
                while True:
                    buf = fin.read(1 << 20)
                    if not buf:
                        break
                    fout.write(buf)
            os.replace(out + ".part", out)
            print("[模板]   → %s（%.1f MB）" % (out, os.path.getsize(out) / 2 ** 20))
    print("[模板] 装好了：%s" % dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
