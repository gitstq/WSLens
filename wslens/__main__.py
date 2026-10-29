"""允许以 ``python -m wslens`` 或 ``python wslens.pyz`` 两种入口运行。"""

import sys

if __package__ in (None, ""):
    # zipapp 单文件归档场景：归档根目录已在 sys.path 上，直接绝对导入
    from wslens.cli import main
else:
    from .cli import main

if __name__ == "__main__":
    sys.exit(main())
