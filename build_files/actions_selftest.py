"""Самотест «Быстрых действий» при сборке образа.

python3 actions_selftest.py /usr/lib/astramars-actions
- синтаксис каждой команды каждого шага проверяется через `bash -n`;
- безопасные действия по-настоящему выполняются в образе;
- свои действия правильно разбираются из текста.
"""

import os
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
from astramars_actions import actions, runner  # noqa: E402

failed = 0
for a in actions.BUILTIN:
    for step in a["steps"]:
        p = subprocess.run(["bash", "-n", "-c", step["run"]], capture_output=True, text=True)
        if p.returncode != 0:
            print(f"FAIL синтаксис {a['id']} / {step['title']}: {p.stderr.strip()}")
            failed += 1
print(f"синтаксис: {sum(len(a['steps']) for a in actions.BUILTIN)} команд проверено")

# Безопасные действия выполняются по-настоящему
if not os.path.isdir(os.environ.get("HOME", "")):
    os.environ["HOME"] = tempfile.mkdtemp()   # в контейнере сборки домашней папки может не быть
r = runner.Runner()
for action_id in ("space", "sysinfo"):
    a = next(x for x in actions.BUILTIN if x["id"] == action_id)
    for step in a["steps"]:
        ok, out = r.run_step(step)
        first = out.splitlines()[0] if out else ""
        print(f"{'ok  ' if ok else 'FAIL'} {action_id} / {step['title']}: {first[:90]}")
        if not ok and not step.get("optional"):
            failed += 1

custom = actions.make_custom("Тест", "# комментарий\necho один\n\necho два\n", False)
assert [s["run"] for s in custom["steps"]] == ["echo один", "echo два"], custom
assert custom["subtitle"].startswith("2 команды"), custom["subtitle"]
ok, out = r.run_step(custom["steps"][0])
assert ok and out == "один", (ok, out)
print("свои действия: OK")

print(f"Итого ошибок: {failed}")
sys.exit(1 if failed else 0)
