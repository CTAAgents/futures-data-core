#!/usr/bin/env python3
"""Data-Core 命令行工具。"""
import sys
from datacore import UnifiedDataProvider, __version__


def cmd_quote(args):
    dc = UnifiedDataProvider()
    for sym in args.symbols:
        payload = dc.get(sym, "quote")
        print(f"{sym}: {payload}")


def cmd_list(args):
    dc = UnifiedDataProvider()
    for s in dc.list_symbols():
        print(f"  {s['symbol']:8s} {s['name']:10s} [{s['market']}]")


def cmd_status(args):
    dc = UnifiedDataProvider()
    print(f"Data-Core v{__version__}")
    print(f"注册表: {len(dc.list_symbols())} 个标的")
    for src_name in ["tdx_lc", "tencent", "eastmoney"]:
        print(f"  {src_name}: 待探测")


def main():
    if len(sys.argv) < 2:
        print(f"Data-Core v{__version__}")
        print("用法:")
        print("  datacore list             列出所有标的")
        print("  datacore status           查看状态")
        print("  datacore quote <symbol>   查询行情")
        return
    cmd = sys.argv[1]
    if cmd == "list":
        cmd_list(sys.argv[2:])
    elif cmd == "status":
        cmd_status(sys.argv[2:])
    elif cmd == "quote" and len(sys.argv) >= 3:
        cmd_quote(type("args", (), {"symbols": sys.argv[2:]})())
    else:
        print(f"未知命令: {cmd}")


if __name__ == "__main__":
    main()
