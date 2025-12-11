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
import subprocess
from datetime import datetime

# 版本号
VERSION = "1.1.0"

# 尝试导入 rich 库用于更好的进度显示
try:
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.console import Console
    from rich.live import Live
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from disk_analyzer.scanner import DiskScanner, parse_size, DuplicateFinder, format_size
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
    
    parser.add_argument(
        '--update',
        action='store_true',
        help='更新工具到最新版本'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='store_true',
        help='显示版本信息'
    )
    
    parser.add_argument(
        '--find-duplicates',
        action='store_true',
        help='检测重复文件（可能耗时较长）'
    )
    
    parser.add_argument(
        '--dup-min-size',
        type=str,
        default='10KB',
        help='重复检测最小文件大小 (默认: 10KB)'
    )
    
    return parser


def do_update():
    """更新工具到最新版本"""
    # 获取工具安装目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"🔄 正在更新 disk-analyzer...")
    print(f"   安装目录: {script_dir}")
    print()
    
    try:
        # 检查是否是 git 仓库
        if not os.path.exists(os.path.join(script_dir, '.git')):
            print("❌ 错误: 当前目录不是 git 仓库，无法更新")
            print("   请使用 git clone 重新安装工具")
            sys.exit(1)
        
        # 获取当前版本
        current_commit = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=script_dir,
            capture_output=True,
            text=True
        ).stdout.strip()
        print(f"   当前版本: {VERSION} ({current_commit})")
        
        # 检查远程更新
        print("   检查远程更新...")
        subprocess.run(['git', 'fetch'], cwd=script_dir, capture_output=True)
        
        # 检查是否有更新
        status = subprocess.run(
            ['git', 'status', '-uno'],
            cwd=script_dir,
            capture_output=True,
            text=True
        ).stdout
        
        if 'Your branch is up to date' in status:
            print("\n✅ 已经是最新版本！")
            return
        
        # 拉取最新代码
        print("   拉取最新代码...")
        result = subprocess.run(
            ['git', 'pull', '--rebase'],
            cwd=script_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ 更新失败: {result.stderr}")
            sys.exit(1)
        
        # 获取新版本
        new_commit = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=script_dir,
            capture_output=True,
            text=True
        ).stdout.strip()
        
        print(f"\n✅ 更新成功！")
        print(f"   新版本: {new_commit}")
        
        # 显示更新日志
        print("\n📝 更新内容:")
        log = subprocess.run(
            ['git', 'log', f'{current_commit}..{new_commit}', '--oneline'],
            cwd=script_dir,
            capture_output=True,
            text=True
        ).stdout.strip()
        
        if log:
            for line in log.split('\n'):
                print(f"   • {line}")
        
    except FileNotFoundError:
        print("❌ 错误: 未找到 git 命令，请先安装 git")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 更新失败: {e}")
        sys.exit(1)


def show_version():
    """显示版本信息"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"disk-analyzer v{VERSION}")
    print(f"macOS 磁盘空间分析工具")
    
    # 获取 git 信息
    try:
        if os.path.exists(os.path.join(script_dir, '.git')):
            commit = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                cwd=script_dir,
                capture_output=True,
                text=True
            ).stdout.strip()
            print(f"Git commit: {commit}")
    except:
        pass
    
    print(f"\n安装路径: {script_dir}")
    print("GitHub: https://github.com/openingax/disk-analyzer")


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
    
    # 处理 --version 参数
    if args.version:
        show_version()
        return
    
    # 处理 --update 参数
    if args.update:
        do_update()
        return
    
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
    
    # 重复文件检测
    if args.find_duplicates:
        print()
        print("=" * 60)
        print("🔍 正在检测重复文件...")
        print("=" * 60)
        
        try:
            dup_min_size = parse_size(args.dup_min_size)
        except ValueError:
            dup_min_size = 10 * 1024  # 默认 10KB
        
        def dup_progress(current, total, stage):
            stage_names = {
                'size_group': '按大小分组',
                'partial_hash': '计算部分哈希',
                'full_hash': '计算完整哈希'
            }
            stage_name = stage_names.get(stage, stage)
            if total > 0:
                sys.stdout.write(f'\r   {stage_name}: {current}/{total} ({current*100//total}%)')
                sys.stdout.flush()
        
        finder = DuplicateFinder(
            min_size=dup_min_size,
            progress_callback=dup_progress
        )
        
        dup_start = datetime.now()
        duplicates = finder.find_duplicates(result.all_files)
        dup_elapsed = datetime.now() - dup_start
        
        # 清除进度行
        sys.stdout.write('\r' + ' ' * 60 + '\r')
        sys.stdout.flush()
        
        if duplicates:
            summary = finder.get_summary(duplicates)
            
            print(f"\n✅ 检测完成! 耗时: {dup_elapsed.total_seconds():.1f} 秒\n")
            print(f"   发现 {summary['total_groups']} 组重复文件")
            print(f"   涉及 {summary['total_files']} 个文件")
            print(f"   💾 可释放空间: {summary['formatted_wasted']}")
            print()
            
            # 显示前 10 组重复文件
            print("📄 最大的重复文件组:")
            print("-" * 60)
            
            for i, group in enumerate(duplicates[:10], 1):
                print(f"\n   {i}. [{group.count} 份] {group.formatted_size} (可释放 {group.formatted_wasted})")
                for j, f in enumerate(group.files[:3]):
                    prefix = "     └── " if j == min(2, len(group.files) - 1) else "     ├── "
                    path_display = f.path
                    if len(path_display) > 50:
                        path_display = '...' + path_display[-47:]
                    print(f"{prefix}{path_display}")
                if len(group.files) > 3:
                    print(f"     └── ... 还有 {len(group.files) - 3} 个文件")
            
            if len(duplicates) > 10:
                print(f"\n   ... 还有 {len(duplicates) - 10} 组重复文件")
            print()
        else:
            print(f"\n✅ 检测完成! 未发现重复文件 (最小检测大小: {format_size(dup_min_size)})\n")


if __name__ == '__main__':
    main()
