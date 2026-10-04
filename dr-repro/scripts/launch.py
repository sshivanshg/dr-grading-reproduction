"""Start the training queue in its own session so it survives the launching shell being killed."""
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
log = open(root / "logs" / "queue.log", "a")
p = subprocess.Popen(["bash", str(root / "scripts" / "run_stage3.sh")], cwd=root, stdout=log, stderr=log,
                     stdin=subprocess.DEVNULL, start_new_session=True)
print("queue pid", p.pid)
