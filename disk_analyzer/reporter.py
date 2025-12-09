"""
报告生成模块
提供终端输出和文件报告生成功能
"""

import json
from typing import List, Optional
from datetime import datetime

from .scanner import ScanResult, format_size, FileInfo, DirInfo
from .analyzer import SpaceAnalyzer, ExtensionStats


# 终端颜色代码
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


class TerminalReporter:
    """终端报告生成器"""
    
    # 用于绘制树的字符
    TREE_CHARS = {
        'branch': '├── ',
        'last': '└── ',
        'pipe': '│   ',
        'space': '    '
    }
    
    def __init__(self, scan_result: ScanResult, use_colors: bool = True):
        """
        初始化报告生成器
        
        Args:
            scan_result: 扫描结果
            use_colors: 是否使用颜色
        """
        self.scan_result = scan_result
        self.analyzer = SpaceAnalyzer(scan_result)
        self.use_colors = use_colors
    
    def _color(self, text: str, color: str) -> str:
        """添加颜色"""
        if self.use_colors:
            return f"{color}{text}{Colors.RESET}"
        return text
    
    def print_summary(self):
        """打印扫描摘要"""
        summary = self.analyzer.get_summary()
        
        print()
        print(self._color("=" * 60, Colors.CYAN))
        print(self._color("  磁盘空间分析报告", Colors.BOLD + Colors.CYAN))
        print(self._color("=" * 60, Colors.CYAN))
        print()
        
        print(f"  📁 扫描路径: {self._color(summary['root_path'], Colors.YELLOW)}")
        print(f"  💾 总大小:   {self._color(summary['formatted_size'], Colors.GREEN + Colors.BOLD)}")
        print(f"  📄 文件数:   {summary['total_files']:,}")
        print(f"  📂 目录数:   {summary['total_dirs']:,}")
        
        if summary['errors_count'] > 0:
            print(f"  ⚠️  错误数:   {self._color(str(summary['errors_count']), Colors.RED)}")
        
        print()
    
    def print_top_directories(self, n: int = 15):
        """打印最大的目录"""
        dirs = self.analyzer.get_top_directories(n)
        total = self.scan_result.total_size
        
        print(self._color("📂 最大的目录", Colors.BOLD + Colors.BLUE))
        print(self._color("-" * 60, Colors.DIM))
        
        for i, dir_info in enumerate(dirs, 1):
            size_str = format_size(dir_info.total_size)
            percentage = (dir_info.total_size / total * 100) if total > 0 else 0
            
            # 进度条
            bar_length = 20
            filled = int(percentage / 100 * bar_length)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            path_display = dir_info.path
            if len(path_display) > 40:
                path_display = '...' + path_display[-37:]
            
            print(f"  {i:2}. {self._color(size_str.rjust(10), Colors.GREEN)} "
                  f"[{self._color(bar, Colors.CYAN)}] "
                  f"{percentage:5.1f}%  {path_display}")
        
        print()
    
    def print_top_files(self, n: int = 15):
        """打印最大的文件"""
        files = self.analyzer.get_top_files(n)
        
        print(self._color("📄 最大的文件", Colors.BOLD + Colors.BLUE))
        print(self._color("-" * 60, Colors.DIM))
        
        for i, file_info in enumerate(files, 1):
            size_str = format_size(file_info.size)
            
            path_display = file_info.path
            if len(path_display) > 45:
                path_display = '...' + path_display[-42:]
            
            print(f"  {i:2}. {self._color(size_str.rjust(10), Colors.GREEN)}  {path_display}")
        
        print()
    
    def print_extension_stats(self, n: int = 15):
        """打印文件类型统计"""
        stats = self.analyzer.get_extension_stats()[:n]
        total = self.scan_result.total_size
        
        print(self._color("📊 按文件类型", Colors.BOLD + Colors.BLUE))
        print(self._color("-" * 60, Colors.DIM))
        
        for stat in stats:
            percentage = (stat.total_size / total * 100) if total > 0 else 0
            
            # 进度条
            bar_length = 15
            filled = int(percentage / 100 * bar_length)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            ext_display = stat.extension.ljust(15)
            
            print(f"  {ext_display} {self._color(stat.formatted_size.rjust(10), Colors.GREEN)} "
                  f"[{self._color(bar, Colors.YELLOW)}] "
                  f"{percentage:5.1f}%  ({stat.file_count:,} 个文件)")
        
        print()
    
    def print_size_distribution(self):
        """打印文件大小分布"""
        distribution = self.analyzer.get_size_distribution()
        
        print(self._color("📈 文件大小分布", Colors.BOLD + Colors.BLUE))
        print(self._color("-" * 60, Colors.DIM))
        
        total_files = self.scan_result.total_files
        
        for range_name, data in distribution.items():
            count = data['count']
            size = data['total_size']
            percentage = (count / total_files * 100) if total_files > 0 else 0
            
            bar_length = 20
            filled = int(percentage / 100 * bar_length)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            print(f"  {range_name.ljust(15)} "
                  f"{self._color(str(count).rjust(8), Colors.CYAN)} 个文件  "
                  f"[{bar}] {percentage:5.1f}%  "
                  f"({format_size(size)})")
        
        print()
    
    def print_directory_tree(self, max_depth: int = 2, min_size_percent: float = 1.0):
        """
        打印目录树
        
        Args:
            max_depth: 最大显示深度
            min_size_percent: 最小显示占比（百分比）
        """
        print(self._color("🌳 目录结构", Colors.BOLD + Colors.BLUE))
        print(self._color("-" * 60, Colors.DIM))
        
        total = self.scan_result.total_size
        min_size = total * min_size_percent / 100
        
        def print_tree(dir_info: DirInfo, prefix: str = "", depth: int = 0):
            if depth > max_depth:
                return
            
            size_str = format_size(dir_info.total_size)
            percentage = (dir_info.total_size / total * 100) if total > 0 else 0
            
            name = dir_info.name or dir_info.path
            print(f"{prefix}{self._color(name, Colors.YELLOW)} "
                  f"({self._color(size_str, Colors.GREEN)}, {percentage:.1f}%)")
            
            # 过滤并排序子目录
            subdirs = [
                d for d in dir_info.subdirs.values() 
                if d.total_size >= min_size
            ]
            subdirs.sort(key=lambda d: d.total_size, reverse=True)
            
            for i, subdir in enumerate(subdirs):
                is_last = (i == len(subdirs) - 1)
                new_prefix = prefix + (self.TREE_CHARS['space'] if is_last else self.TREE_CHARS['pipe'])
                connector = self.TREE_CHARS['last'] if is_last else self.TREE_CHARS['branch']
                
                print_tree(subdir, prefix + connector, depth + 1)
        
        print_tree(self.scan_result.root)
        print()
    
    def print_errors(self, max_errors: int = 10):
        """打印错误信息"""
        errors = self.scan_result.errors
        if not errors:
            return
        
        print(self._color(f"⚠️  扫描过程中的错误 ({len(errors)} 个)", Colors.BOLD + Colors.RED))
        print(self._color("-" * 60, Colors.DIM))
        
        for error in errors[:max_errors]:
            print(f"  • {self._color(error, Colors.DIM)}")
        
        if len(errors) > max_errors:
            print(f"  ... 还有 {len(errors) - max_errors} 个错误未显示")
        
        print()
    
    def print_full_report(self, tree_depth: int = 2):
        """打印完整报告"""
        self.print_summary()
        self.print_top_directories()
        self.print_top_files()
        self.print_extension_stats()
        self.print_size_distribution()
        self.print_directory_tree(max_depth=tree_depth)
        self.print_errors()


class JSONReporter:
    """JSON 报告生成器"""
    
    def __init__(self, scan_result: ScanResult):
        self.scan_result = scan_result
        self.analyzer = SpaceAnalyzer(scan_result)
    
    def generate_report(self, output_path: str):
        """生成 JSON 报告"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': self.analyzer.get_summary(),
            'top_directories': [
                {
                    'path': d.path,
                    'size': d.total_size,
                    'formatted_size': format_size(d.total_size),
                    'file_count': d.file_count
                }
                for d in self.analyzer.get_top_directories(50)
            ],
            'top_files': [
                {
                    'path': f.path,
                    'size': f.size,
                    'formatted_size': format_size(f.size),
                    'extension': f.extension
                }
                for f in self.analyzer.get_top_files(50)
            ],
            'extension_stats': [
                {
                    'extension': s.extension,
                    'total_size': s.total_size,
                    'formatted_size': s.formatted_size,
                    'file_count': s.file_count
                }
                for s in self.analyzer.get_extension_stats()
            ],
            'size_distribution': self.analyzer.get_size_distribution(),
            'directory_tree': self.analyzer.get_directory_tree(max_depth=5),
            'errors': self.scan_result.errors[:100]  # 最多 100 个错误
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"JSON 报告已保存到: {output_path}")


class HTMLReporter:
    """HTML 报告生成器"""
    
    def __init__(self, scan_result: ScanResult):
        self.scan_result = scan_result
        self.analyzer = SpaceAnalyzer(scan_result)
    
    def generate_report(self, output_path: str):
        """生成 HTML 报告"""
        summary = self.analyzer.get_summary()
        top_dirs = self.analyzer.get_top_directories(30)
        top_files = self.analyzer.get_top_files(30)
        ext_stats = self.analyzer.get_extension_stats()[:20]
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>磁盘空间分析报告</title>
    <style>
        :root {{
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --bg: #0f172a;
            --bg-card: #1e293b;
            --text: #f1f5f9;
            --text-dim: #94a3b8;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{
            font-size: 2.5rem;
            background: linear-gradient(135deg, var(--primary), #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}
        .subtitle {{ color: var(--text-dim); margin-bottom: 2rem; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
        .stat-card {{
            background: var(--bg-card);
            padding: 1.5rem;
            border-radius: 1rem;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .stat-value {{ font-size: 2rem; font-weight: bold; color: var(--success); }}
        .stat-label {{ color: var(--text-dim); font-size: 0.875rem; }}
        .section {{
            background: var(--bg-card);
            padding: 1.5rem;
            border-radius: 1rem;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .section h2 {{ margin-bottom: 1rem; font-size: 1.25rem; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }}
        th {{ color: var(--text-dim); font-weight: 500; }}
        .size {{ color: var(--success); font-family: monospace; }}
        .path {{ color: var(--text-dim); font-size: 0.875rem; word-break: break-all; }}
        .bar-container {{ width: 100px; height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden; }}
        .bar {{ height: 100%; background: linear-gradient(90deg, var(--primary), #a855f7); border-radius: 4px; }}
        .percent {{ color: var(--text-dim); font-size: 0.875rem; min-width: 50px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 磁盘空间分析报告</h1>
        <p class="subtitle">扫描路径: {summary['root_path']} | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="grid">
            <div class="stat-card">
                <div class="stat-value">{summary['formatted_size']}</div>
                <div class="stat-label">总占用空间</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{summary['total_files']:,}</div>
                <div class="stat-label">文件数量</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{summary['total_dirs']:,}</div>
                <div class="stat-label">目录数量</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{summary['errors_count']}</div>
                <div class="stat-label">扫描错误</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📂 最大的目录</h2>
            <table>
                <tr><th>排名</th><th>大小</th><th>占比</th><th>路径</th></tr>
                {''.join(f"""
                <tr>
                    <td>{i+1}</td>
                    <td class="size">{format_size(d.total_size)}</td>
                    <td>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <div class="bar-container"><div class="bar" style="width:{d.total_size/summary['total_size']*100:.1f}%"></div></div>
                            <span class="percent">{d.total_size/summary['total_size']*100:.1f}%</span>
                        </div>
                    </td>
                    <td class="path">{d.path}</td>
                </tr>""" for i, d in enumerate(top_dirs))}
            </table>
        </div>
        
        <div class="section">
            <h2>📄 最大的文件</h2>
            <table>
                <tr><th>排名</th><th>大小</th><th>文件路径</th></tr>
                {''.join(f"""
                <tr>
                    <td>{i+1}</td>
                    <td class="size">{format_size(f.size)}</td>
                    <td class="path">{f.path}</td>
                </tr>""" for i, f in enumerate(top_files))}
            </table>
        </div>
        
        <div class="section">
            <h2>📊 按文件类型</h2>
            <table>
                <tr><th>扩展名</th><th>大小</th><th>占比</th><th>文件数</th></tr>
                {''.join(f"""
                <tr>
                    <td><code>{s.extension}</code></td>
                    <td class="size">{s.formatted_size}</td>
                    <td>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <div class="bar-container"><div class="bar" style="width:{s.total_size/summary['total_size']*100:.1f}%"></div></div>
                            <span class="percent">{s.total_size/summary['total_size']*100:.1f}%</span>
                        </div>
                    </td>
                    <td>{s.file_count:,}</td>
                </tr>""" for s in ext_stats)}
            </table>
        </div>
    </div>
</body>
</html>'''
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"HTML 报告已保存到: {output_path}")
