"""Per-step training throughput on the local accelerator for a given backbone/size/batch."""
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.model import DRNet  # noqa: E402

backbone, size, bs, amp = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4] == "1"
d = torch.device("mps")
m = DRNet(backbone).to(d).to(memory_format=torch.channels_last)
opt = torch.optim.Adam(m.parameters(), 1e-3)
x = torch.randn(bs, 3, size, size, device=d).to(memory_format=torch.channels_last)
y = torch.randint(0, 5, (bs,), device=d)
times = []
for i in range(8):
    t = time.time()
    with torch.autocast("mps", dtype=torch.float16, enabled=amp):
        loss = torch.nn.functional.cross_entropy(m(x).float(), y)
    opt.zero_grad()
    loss.backward()
    opt.step()
    torch.mps.synchronize()
    times.append(time.time() - t)
    print(f"step {i}: {times[-1]:.2f}s", flush=True)
dt = sum(times[3:]) / len(times[3:])
print(f"{backbone} {size}px bs{bs} amp={amp}: {bs/dt:.1f} img/s, epoch(2562) ~{2562*dt/bs:.0f}s, "
      f"mps mem {torch.mps.driver_allocated_memory()/2**30:.2f} GB")
