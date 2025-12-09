#!/usr/bin/env python3
"""
macOS 磁盘空间分析工具
递归扫描文件系统，分析空间占用情况
"""

import argparse
import sys
import os
import webbrowser
import tempfile
from datetime import datetime

# 尝试导入 rich 库用于更好的进度显示
try:
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.console import Console
    from rich.live import Live
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from disk_analyzer.scanner import DiskScanner, parse_size
from disk_analyzer.analyzer import SpaceAnalyzer
from disk_analyzer.reporter import TerminalReporter, JSONReporter, HTMLReporter


def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog='disk-analyzer',
        description='macOS 磁盘空间分析工具 - 帮助你找出占用空间的文件和目录',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python main.py ~                      # 分析用户主目录
  python main.py / --depth 3            # 分析根目录，限制深度为3
  python main.py . --top 30             # 显示前30个最大项
  python main.py ~/Downloads --min-size 10MB   # 只统计大于10MB的文件
  python main.py / --exclude node_modules,.git # 排除特定目录
  python main.py . --output report.html        # 生成 HTML 报告
  python main.py . --json report.json          # 生成 JSON 报告
        '''
    )
    
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='要分析的目录路径 (默认: 当前目录)'
    )
    
    parser.add_argument(
        '--depth', '-d',
        type=int,
        default=None,
        help='最大扫描深度 (默认: 无限制)'
    )
    
    parser.add_argument(
        '--top', '-n',
        type=int,
        default=15,
        help='显示前 N 个最大项 (默认: 15)'
    )
    
    parser.add_argument(
        '--min-size', '-m',
        type=str,
        default='0',
        help='最小文件大小，支持单位如 1KB, 10MB, 1GB (默认: 0)'
    )
    
    parser.add_argument(
        '--exclude', '-e',
        type=str,
        default='',
        help='要排除的目录，用逗号分隔 (如: node_modules,.git,__pycache__)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='输出 HTML 报告到指定文件 (默认自动生成临时文件)'
    )
    
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='不自动在浏览器中打开报告'
    )
    
    parser.add_argument(
        '--no-html',
        action='store_true',
        help='不生成 HTML 报告（仅终端输出）'
    )
    
    parser.add_argument(
        '--json', '-j',
        type=str,
        default=None,
        help='输出 JSON 报告到指定文件'
    )
    
    parser.add_argument(
        '--tree-depth',
        type=int,
        default=2,
        help='目录树显示深度 (默认: 2)'
    )
    
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='禁用彩色输出'
    )
    
    parser.add_argument(
        '--follow-symlinks',
        action='store_true',
        help='跟随符号链接 (默认: 不跟随)'
    )
    
    parser.add_argument(
        '--show-errors',
        action='store_true',
        help='显示所有扫描错误'
    )
    
    return parser


def print_progress_simple(current_path: str, files: int, dirs: int):
    """简单的进度显示"""
    # 截断过长的路径
    if len(current_path) > 50:
        display_path = '...' + current_path[-47:]
    else:
        display_path = current_path.ljust(50)
    
    sys.stdout.write(f'\r正在扫描: {files:,} 文件, {dirs:,} 目录 | {display_path}')
    sys.stdout.flush()


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 解析路径
    target_path = os.path.abspath(os.path.expanduser(args.path))
    
    if not os.path.exists(target_path):
        print(f"错误: 路径不存在: {target_path}", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.isdir(target_path):
        print(f"错误: 不是目录: {target_path}", file=sys.stderr)
        sys.exit(1)
    
    # 解析参数
    try:
        min_size = parse_size(args.min_size)
    except ValueError:
        print(f"错误: 无效的大小格式: {args.min_size}", file=sys.stderr)
        sys.exit(1)
    
    exclude_patterns = set()
    if args.exclude:
        exclude_patterns = set(p.strip() for p in args.exclude.split(','))
    
    # 打印开始信息
    print()
    print("🔍 macOS 磁盘空间分析工具")
    print("=" * 50)
    print(f"   扫描路径: {target_path}")
    if args.depth:
        print(f"   最大深度: {args.depth}")
    if min_size > 0:
        print(f"   最小文件: {args.min_size}")
    if exclude_patterns:
        print(f"   排除目录: {', '.join(exclude_patterns)}")
    print("=" * 50)
    print()
    
    # 创建扫描器
    scanner = DiskScanner(
        exclude_patterns=exclude_patterns,
        min_size=min_size,
        max_depth=args.depth,
        follow_symlinks=args.follow_symlinks,
        progress_callback=print_progress_simple
    )
    
    # 开始扫描
    start_time = datetime.now()
    print("开始扫描...")
    
    try:
        result = scanner.scan(target_path)
    except KeyboardInterrupt:
        print("\n\n扫描被用户中断")
        sys.exit(1)
    except PermissionError:
        print(f"\n错误: 无法访问目录 {target_path}，请检查权限", file=sys.stderr)
        sys.exit(1)
    
    # 清除进度行
    sys.stdout.write('\r' + ' ' * 80 + '\r')
    sys.stdout.flush()
    
    elapsed = datetime.now() - start_time
    print(f"✅ 扫描完成! 耗时: {elapsed.total_seconds():.1f} 秒")
    print()
    
    # 生成终端报告
    use_colors = not args.no_color and sys.stdout.isatty()
    reporter = TerminalReporter(result, use_colors=use_colors)
    reporter.print_full_report(tree_depth=args.tree_depth)
    
    # 生成 HTML 报告
    if not args.no_html:
        html_reporter = HTMLReporter(result)
        
        if args.output:
            html_path = args.output
        else:
            # 生成临时文件
            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            html_path = os.path.join(temp_dir, f'disk_report_{timestamp}.html')
        
        html_reporter.generate_report(html_path)
        
        # 自动打开浏览器
        if not args.no_browser:
            print(f"🌐 正在浏览器中打开报告...")
            webbrowser.open(f'file://{os.path.abspath(html_path)}')
    
    # 生成 JSON 报告
    if args.json:
        json_reporter = JSONReporter(result)
        json_reporter.generate_report(args.json)
    
    # 显示错误
    if args.show_errors and result.errors:
        print("\n所有扫描错误:")
        for error in result.errors:
            print(f"  • {error}")


if __name__ == '__main__':
    main()
