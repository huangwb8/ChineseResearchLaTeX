#!/usr/bin/env python3
"""兼容旧参数的只读输出检查入口；不再通过 S 编号判断科学关联。"""
import sys
sys.dont_write_bytecode = True
from run import main
if __name__ == "__main__":
    raise SystemExit(main(["check", *sys.argv[1:]]))
