#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lyrics_server.py — 用本机轻量模型（faster-whisper）自动识别歌词，并连同「音乐粒子时钟」网页一起启动。

用法（把本文件和 index.html 放在同一个文件夹）：
    python lyrics_server.py                      # 默认 small 模型，自动选 GPU/CPU
    python lyrics_server.py --model medium       # 中文歌建议用 medium（6GB 显存可跑）
    python lyrics_server.py --lang zh --trad     # 指定中文并输出繁体
    python lyrics_server.py --lrc 歌曲.mp3        # 不开网页，只把歌曲识别成同名 .lrc

启动后浏览器会打开 http://127.0.0.1:8765/ ，在页面里选歌曲，歌词会一边识别一边同步显示。
首次运行会自动 pip 安装 faster-whisper，并下载模型到本文件夹的 models/ 里。
"""
import argparse, importlib, os, subprocess, sys, tempfile, threading, webbrowser, json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

HERE = Path(__file__).resolve().parent
PAGE = HERE / "index.html"
VERSION = "v4-av-shim"


def pip_install(*pkgs):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", *pkgs])


def ensure(pkg, mod):
    try:
        importlib.import_module(mod)
    except ImportError:
        print(f"[安装] {pkg} …")
        pip_install(pkg)
        importlib.invalidate_caches()


def check_av():
    """兼容层：PyAV 不认识 metadata_errors 参数时，自动忽略该参数，faster-whisper 照常解码。"""
    try:
        import av
    except Exception:
        return
    orig = av.open

    def _open(*args, **kw):
        try:
            return orig(*args, **kw)
        except TypeError as e:
            if "metadata_errors" in str(e) or "metadata_encoding" in str(e):
                kw.pop("metadata_errors", None)
                kw.pop("metadata_encoding", None)
                return orig(*args, **kw)
            raise

    av.open = _open
    print(f"[PyAV] {getattr(av, '__version__', '?')}  {Path(av.__file__).parent}")


def add_nvidia_dlls():
    """把 pip 安装的 cuBLAS / cuDNN 目录加入 DLL 搜索路径（Windows）。"""
    try:
        import nvidia
    except ImportError:
        return
    for base in list(getattr(nvidia, "__path__", [])):
        for b in Path(base).glob("*/bin"):
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(str(b))
            os.environ["PATH"] = str(b) + os.pathsep + os.environ.get("PATH", "")


class Engine:
    def __init__(self, a):
        self.a, self.lock, self.model, self.device, self.conv = a, threading.Lock(), None, "cpu", None
        if a.trad:
            try:
                ensure("opencc-python-reimplemented", "opencc")
                from opencc import OpenCC
                self.conv = OpenCC("s2twp").convert
            except Exception as e:
                print("[繁体] OpenCC 安装失败，歌词将不转繁体：", e)
        self.load()

    def _make(self, device):
        from faster_whisper import WhisperModel
        ct = "int8_float16" if device == "cuda" else "int8"
        print(f"[模型] 载入 {self.a.model}（{device}/{ct}），首次会自动下载到 {HERE / 'models'} …")
        m = WhisperModel(self.a.model, device=device, compute_type=ct, download_root=str(HERE / "models"))
        try:  # 暖机：让缺少 CUDA 库的问题在这里就暴露
            import numpy as np
            list(m.transcribe(np.zeros(16000, dtype="float32"), beam_size=1)[0])
        except ImportError:
            pass
        return m

    def ask_gpu_libs(self):
        if self.a.device == "auto" and not self.a.yes:
            if input("GPU 不可用，要安装加速库 nvidia-cublas-cu12 / nvidia-cudnn-cu12（约 1GB）吗？[y/N] ").strip().lower() != "y":
                return False
        try:
            pip_install("nvidia-cublas-cu12", "nvidia-cudnn-cu12")
            importlib.invalidate_caches()
            return True
        except Exception as e:
            print("[GPU] 安装失败：", e)
            return False

    def load(self):
        ensure("faster-whisper", "faster_whisper")
        check_av()
        if self.a.device != "cpu":
            for attempt in (1, 2):
                try:
                    add_nvidia_dlls()
                    self.model, self.device = self._make("cuda"), "cuda"
                    return
                except Exception as e:
                    print(f"[GPU] 不可用：{e}")
                    if attempt == 1 and self.ask_gpu_libs():
                        continue
                    break
            print("[GPU] 改用 CPU")
        self.model, self.device = self._make("cpu"), "cpu"

    def segments(self, path, lang):
        a = self.a
        prompt = a.prompt or ("以下是歌曲的繁體中文歌詞。" if a.trad and (lang or "zh").startswith("zh") else None)
        segs, info = self.model.transcribe(path, language=lang, beam_size=5, vad_filter=a.vad,
                                           condition_on_previous_text=False, initial_prompt=prompt)
        yield {"language": info.language}
        last, rep = None, 0
        for s in segs:
            t = s.text.strip()
            if not t:
                continue
            # 过滤纯音乐段落常见的幻觉：低置信、高压缩比、连续重复
            if (s.no_speech_prob > 0.6 and s.avg_logprob < -0.8) or s.avg_logprob < -1.5 or s.compression_ratio > 2.4:
                continue
            rep = rep + 1 if t == last else 0
            last = t
            if rep >= 3:
                continue
            if self.conv:
                t = self.conv(t)
            yield {"start": round(s.start, 2), "end": round(s.end, 2), "text": t}


def make_handler(engine, a):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, *x):
            pass

        def _cors(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            self.send_header("Access-Control-Allow-Private-Network", "true")

        def _json(self, o):
            b = json.dumps(o, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self._cors()
            self.end_headers()
            self.wfile.write(b)

        def do_OPTIONS(self):
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_GET(self):
            p = urlparse(self.path).path
            if p == "/api/ping":
                return self._json({"ok": True, "model": a.model, "device": engine.device})
            if p in ("/", "/index.html"):
                if not PAGE.exists():
                    return self.send_error(404, "找不到 index.html，请和本脚本放在同一文件夹")
                data = PAGE.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            self.send_error(404)

        def do_POST(self):
            u = urlparse(self.path)
            if u.path != "/api/transcribe":
                return self.send_error(404)
            q = parse_qs(u.query)
            name = q.get("name", ["audio"])[0]
            lang = q.get("lang", [a.lang or ""])[0] or None
            n = int(self.headers.get("Content-Length", 0))
            fd, tmp = tempfile.mkstemp(suffix=Path(name).suffix[:8] or ".audio")
            try:
                with os.fdopen(fd, "wb") as f:
                    left = n
                    while left > 0:
                        b = self.rfile.read(min(1 << 20, left))
                        if not b:
                            break
                        f.write(b)
                        left -= len(b)
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self._cors()
                self.end_headers()

                def send(o):
                    self.wfile.write((json.dumps(o, ensure_ascii=False) + "\n").encode("utf-8"))
                    self.wfile.flush()

                with engine.lock:
                    print(f"[识别] {name}")
                    found = None
                    try:
                        for o in engine.segments(tmp, lang):
                            found = o.get("language", found)
                            send(o)
                            if "text" in o:
                                print(f"  {o['start']:7.2f}  {o['text']}")
                        send({"done": True, "language": found})
                    except (BrokenPipeError, ConnectionResetError):
                        print("[识别] 页面已离开，停止")
                    except Exception as e:
                        msg = str(e)
                        if "metadata_errors" in msg:
                            msg += "（PyAV 版本过旧：执行 pip install -U av 后重启本脚本）"
                        print("[识别] 出错：", msg)
                        try:
                            send({"error": msg})
                        except Exception:
                            pass
            finally:
                try:
                    os.remove(tmp)
                except OSError:
                    pass

    return H


def to_lrc(engine, path, lang):
    out = []
    for o in engine.segments(path, lang):
        if "text" in o:
            m, s = divmod(o["start"], 60)
            out.append(f"[{int(m):02d}:{s:05.2f}]{o['text']}")
            print(out[-1])
    dst = Path(path).with_suffix(".lrc")
    dst.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"已写入 {dst}")


def main():
    ap = argparse.ArgumentParser(description="本机歌词识别服务 + 音乐粒子时钟")
    ap.add_argument("--model", default="small", help="tiny / base / small / medium / large-v3（默认 small）")
    ap.add_argument("--lang", default=None, help="语言代码，如 zh、en、ja；不填则自动检测")
    ap.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--trad", action="store_true", help="中文歌词转成繁体")
    ap.add_argument("--vad", action="store_true", help="开启人声检测过滤（纯音乐段落多时可试）")
    ap.add_argument("--prompt", default=None, help="给模型的提示，例如歌手名/歌名/用字习惯")
    ap.add_argument("--lrc", metavar="音频文件", help="只识别这首歌并写出同名 .lrc，然后退出")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("-y", "--yes", action="store_true", help="需要装 GPU 库时不再询问")
    a = ap.parse_args()

    print(f"[版本] lyrics_server {VERSION}  [Python] {sys.executable}")
    eng = Engine(a)
    if a.lrc:
        return to_lrc(eng, a.lrc, a.lang)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(eng, a))
    url = f"http://127.0.0.1:{a.port}/"
    print(f"\n已就绪（{a.model} / {eng.device}）：{url}   按 Ctrl+C 结束")
    if not a.no_browser:
        threading.Timer(1, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
