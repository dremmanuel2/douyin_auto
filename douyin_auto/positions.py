# 抖音按钮位置配置（从 positions.txt 自动加载）
import os

POSITIONS = {}

_positions_txt = os.path.join(os.path.dirname(__file__), "positions.txt")
if os.path.exists(_positions_txt):
    with open(_positions_txt, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and ":" in line and not line.startswith("#"):
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if value.startswith("(") and value.endswith(")"):
                    value = value[1:-1]
                    parts = value.split(",")
                    if len(parts) == 2:
                        try:
                            x = float(parts[0].strip())
                            y = float(parts[1].strip())
                            POSITIONS[key] = (x, y)
                        except ValueError:
                            pass
