"""Launch a local Ollama service when available, then open the study app."""
import json, os, shutil, subprocess, sys, time, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def models():
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open('http://127.0.0.1:11434/api/tags',timeout=2) as r:
            return [m['name'] for m in json.load(r)['models']]
    except Exception:return None

binary=shutil.which('ollama')
if binary and models() is None:
    env=dict(os.environ,OLLAMA_HOST='127.0.0.1:11434',OLLAMA_NO_CLOUD='1',OLLAMA_NUM_PARALLEL='1',OLLAMA_MAX_LOADED_MODELS='1')
    logdir=ROOT/'data';logdir.mkdir(exist_ok=True)
    with (logdir/'ollama.log').open('ab') as log:
        proc=subprocess.Popen([binary,'serve'],cwd=ROOT,env=env,stdout=log,stderr=log,start_new_session=True)
    for _ in range(30):
        if models() is not None:break
        if proc.poll() is not None:break
        time.sleep(.5)
found=models()
if found is None:print('本地 Ollama 未启动；请安装并启动 Ollama，页面仍可使用资料检索。',flush=True)
elif found:print(f'已连接本地 Ollama，发现 {len(found)} 个已下载模型。请在网页中选择适合本机的模型。',flush=True)
else:print('已连接本地 Ollama，但未发现已下载模型。请先完成模型选择与下载。',flush=True)
port=os.environ.get('STUDY_PORT','8765')
try:
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(f'http://127.0.0.1:{port}/api/version',timeout=2) as r:
        running=json.load(r)
except Exception:
    os.execv(sys.executable,[sys.executable,str(ROOT/'app.py')])
else:
    if running.get('product')!='keban-ai':
        print(f'端口 {port} 已被其他程序使用。请关闭该程序，或设置 STUDY_PORT 后重试。',flush=True)
        sys.exit(1)
    import webbrowser
    webbrowser.open(f'http://127.0.0.1:{port}')
    print('已打开正在运行的课程助手。')
