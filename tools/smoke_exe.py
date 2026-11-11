"""Smoke: EXE v3.8.2 должен жить 25 с в offscreen без падения."""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
p = subprocess.Popen(
    [os.path.join(ROOT, "dist", "StampRescue", "StampRescue.exe")],
    env=env, cwd=ROOT,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
time.sleep(25)
if p.poll() is None:
    p.terminate()
    print("EXE alive 25s: OK")
    sys.exit(0)
out = p.stdout.read().decode(errors="replace")
print(f"EXE DIED code={p.returncode}\n{out[-2000:]}")
sys.exit(1)
