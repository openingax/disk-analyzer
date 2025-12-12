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
    """HTML 报告生成器 - 增强版"""
    
    def __init__(self, scan_result: ScanResult):
        self.scan_result = scan_result
        self.analyzer = SpaceAnalyzer(scan_result)
    
    def _generate_chart_data(self) -> dict:
        """生成图表所需的数据"""
        import json
        
        # 文件类型分布饼图数据
        ext_stats = self.analyzer.get_extension_stats()[:10]
        pie_data = [{'name': s.extension, 'value': s.total_size} for s in ext_stats]
        
        # 媒体类型统计
        media_stats = self.analyzer.get_media_stats()
        media_pie_data = [
            {'name': k, 'value': v['total_size']} 
            for k, v in media_stats.items() if v['total_size'] > 0
        ]
        
        # 文件大小分布
        size_dist = self.analyzer.get_size_distribution()
        size_bar_data = {
            'categories': list(size_dist.keys()),
            'counts': [v['count'] for v in size_dist.values()],
            'sizes': [v['total_size'] for v in size_dist.values()]
        }
        
        # Treemap 数据
        treemap_data = self.analyzer.get_treemap_data(max_depth=4)
        
        return {
            'pieData': pie_data,
            'mediaPieData': media_pie_data,
            'sizeBarData': size_bar_data,
            'treemapData': treemap_data
        }
    
    def _build_interactive_tree(self, dir_info: DirInfo, total_size: int, depth: int = 0, max_depth: int = 5) -> str:
        """构建可交互的目录树 HTML"""
        import os
        
        if depth > max_depth:
            return ""
        
        size_str = format_size(dir_info.total_size)
        percentage = (dir_info.total_size / total_size * 100) if total_size > 0 else 0
        name = dir_info.name or os.path.basename(dir_info.path) or dir_info.path
        
        # 过滤并排序子目录
        min_size = total_size * 0.005
        subdirs = [d for d in dir_info.subdirs.values() if d.total_size >= min_size]
        subdirs.sort(key=lambda d: d.total_size, reverse=True)
        
        has_children = len(subdirs) > 0 and depth < max_depth
        collapsed = 'collapsed' if depth > 1 else ''
        
        html = f'''
        <div class="tree-item {collapsed}">
            <div class="tree-header" onclick="toggleTree(this)">
                <span class="tree-toggle">{('▶' if has_children else '•')}</span>
                <span class="tree-icon">{'📂' if has_children else '📁'}</span>
                <span class="tree-name" title="{dir_info.path}">{name}</span>
                <span class="tree-meta">
                    <span class="tree-size">{size_str}</span>
                    <span class="tree-percent">{percentage:.1f}%</span>
                    <div class="tree-bar"><div class="tree-bar-fill" style="width: {min(percentage, 100)}%"></div></div>
                </span>
            </div>'''
        
        if has_children:
            html += '<div class="tree-children">'
            for subdir in subdirs[:15]:
                html += self._build_interactive_tree(subdir, total_size, depth + 1, max_depth)
            if len(subdirs) > 15:
                html += f'<div class="tree-more">... 还有 {len(subdirs) - 15} 个目录</div>'
            html += '</div>'
        
        html += '</div>'
        return html
    
    def generate_report(self, output_path: str, duplicates=None):
        """生成 HTML 报告
        
        Args:
            output_path: 输出文件路径
            duplicates: 可选的重复文件组列表 (List[DuplicateGroup])
        """
        import json
        
        summary = self.analyzer.get_summary()
        top_dirs = self.analyzer.get_top_directories(20)
        top_files = self.analyzer.get_top_files(20)
        ext_stats = self.analyzer.get_extension_stats()[:15]
        media_stats = self.analyzer.get_media_stats()
        cleanable = self.analyzer.get_cleanable_suggestions()
        chart_data = self._generate_chart_data()
        
        # 计算可清理总量
        total_cleanable = sum(v['total_size'] for v in cleanable.values())
        total_cleanable_str = format_size(total_cleanable)
        
        # 构建目录树
        tree_html = self._build_interactive_tree(self.scan_result.root, summary['total_size'])
        
        # 媒体类型图标映射
        media_icons = {
            'video': '🎬', 'audio': '🎵', 'image': '🖼️', 
            'document': '📄', 'archive': '📦', 'code': '💻', 'other': '📎'
        }
        
        # 可清理类型图标映射
        clean_icons = {
            'cache': '🗑️', 'logs': '📋', 'temp': '⏱️', 'build': '🔧', 'ide': '💼'
        }
        
        # Pre-build duplicates HTML
        duplicates_html = ''
        duplicates_summary_html = ''
        has_duplicates = duplicates and len(duplicates) > 0
        
        if has_duplicates:
            total_wasted = sum(g.wasted_size for g in duplicates)
            total_dup_files = sum(g.count for g in duplicates)
            
            duplicates_summary_html = f'''
            <div class="stat-card danger">
                <div class="stat-icon">🔄</div>
                <div class="stat-value">{format_size(total_wasted)}</div>
                <div class="stat-label">重复文件可释放</div>
            </div>'''
            
            for i, group in enumerate(duplicates, 1):
                files_html = ''
                for f in group.files:
                    path_display = f.path
                    if len(path_display) > 60:
                        path_display = '...' + path_display[-57:]
                    files_html += f'''
                    <div class="dup-file">
                        <span class="dup-file-icon">📄</span>
                        <span class="dup-file-path" title="{f.path}">{path_display}</span>
                    </div>'''
                
                duplicates_html += f'''
                <div class="dup-group">
                    <div class="dup-group-header">
                        <span class="dup-group-num">#{i}</span>
                        <span class="dup-group-info">{group.count} 份相同文件</span>
                        <span class="dup-group-size">{group.formatted_size}</span>
                        <span class="dup-group-wasted">可释放 {group.formatted_wasted}</span>
                    </div>
                    <div class="dup-group-files">{files_html}</div>
                </div>'''
        
        # Pre-build media cards HTML
        media_cards_html = ''
        for k, v in media_stats.items():
            if v['count'] > 0:
                icon = media_icons.get(k, '📎')
                count_str = "{:,}".format(v['count'])
                media_cards_html += f'''
                <div class="media-card">
                    <div class="media-icon">{icon}</div>
                    <div class="media-type">{k}</div>
                    <div class="media-size">{v['formatted_size']}</div>
                    <div class="media-count">{count_str} 个文件</div>
                </div>'''
        
        # Pre-build cleanup cards HTML
        cleanup_cards_html = ''
        for k, v in cleanable.items():
            if v['total_size'] > 0:
                icon = clean_icons.get(k, '🗑️')
                cleanup_cards_html += f'''
                <div class="cleanup-card">
                    <div class="cleanup-header">
                        <span class="cleanup-icon">{icon}</span>
                        <span class="cleanup-type">{k}</span>
                    </div>
                    <div class="cleanup-size">{v['formatted_size']}</div>
                    <div class="cleanup-count">{v['count']} 个项目</div>
                </div>'''
        
        # Pre-build top dirs table HTML
        total_size = summary['total_size']
        dirs_table_html = ''
        for i, d in enumerate(top_dirs):
            pct = (d.total_size / total_size * 100) if total_size > 0 else 0
            dirs_table_html += f'''
                        <tr>
                            <td class="rank">{i+1}</td>
                            <td class="size">{format_size(d.total_size)}</td>
                            <td class="bar-cell">
                                <div class="mini-bar"><div class="mini-bar-fill" style="width:{pct:.1f}%"></div></div>
                                <span class="percent">{pct:.1f}%</span>
                            </td>
                            <td class="path" title="{d.path}">{d.path}</td>
                        </tr>'''
        
        # Pre-build top files table HTML
        files_table_html = ''
        for i, f in enumerate(top_files):
            files_table_html += f'''
                        <tr>
                            <td class="rank">{i+1}</td>
                            <td class="size">{format_size(f.size)}</td>
                            <td class="path" title="{f.path}">{f.path}</td>
                        </tr>'''
        
        # Pre-build extension stats table HTML
        types_table_html = ''
        for s in ext_stats:
            pct = (s.total_size / total_size * 100) if total_size > 0 else 0
            count_str = "{:,}".format(s.file_count)
            types_table_html += f'''
                        <tr>
                            <td><code style="color: var(--info);">{s.extension}</code></td>
                            <td class="size">{s.formatted_size}</td>
                            <td class="bar-cell">
                                <div class="mini-bar"><div class="mini-bar-fill" style="width:{pct:.1f}%"></div></div>
                                <span class="percent">{pct:.1f}%</span>
                            </td>
                            <td>{count_str}</td>
                        </tr>'''
        
        # Format summary values
        total_files_str = "{:,}".format(summary['total_files'])
        total_dirs_str = "{:,}".format(summary['total_dirs'])
        chart_data_json = json.dumps(chart_data, ensure_ascii=False)
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>磁盘空间分析报告</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #6366f1;
            --primary-light: #818cf8;
            --primary-dark: #4f46e5;
            --accent: #a855f7;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --info: #06b6d4;
            --bg-dark: #0a0a0f;
            --bg-card: #12121a;
            --bg-card-hover: #1a1a24;
            --bg-elevated: #1e1e2d;
            --border: rgba(255,255,255,0.08);
            --text: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-dim: #64748b;
            --gradient-primary: linear-gradient(135deg, #6366f1, #a855f7);
            --gradient-success: linear-gradient(135deg, #10b981, #06b6d4);
            --gradient-warning: linear-gradient(135deg, #f59e0b, #f97316);
            --gradient-danger: linear-gradient(135deg, #ef4444, #ec4899);
            --shadow-glow: 0 0 40px rgba(99, 102, 241, 0.15);
            --shadow-card: 0 4px 24px rgba(0,0,0,0.4);
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-dark);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        /* Header */
        .header {{
            text-align: center;
            margin-bottom: 3rem;
            padding: 3rem 0;
            background: linear-gradient(180deg, rgba(99,102,241,0.1) 0%, transparent 100%);
            border-radius: 24px;
            position: relative;
            overflow: hidden;
        }}
        
        .header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 200px;
            height: 2px;
            background: var(--gradient-primary);
        }}
        
        .header h1 {{
            font-size: 3rem;
            font-weight: 700;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
            letter-spacing: -0.02em;
        }}
        
        .header .subtitle {{
            color: var(--text-secondary);
            font-size: 1rem;
        }}
        
        .header .scan-path {{
            margin-top: 1rem;
            padding: 0.75rem 1.5rem;
            background: var(--bg-card);
            border-radius: 50px;
            display: inline-block;
            font-family: monospace;
            font-size: 0.875rem;
            color: var(--text-dim);
            border: 1px solid var(--border);
        }}
        
        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
        }}
        
        .stat-card:hover {{
            background: var(--bg-card-hover);
            transform: translateY(-2px);
            box-shadow: var(--shadow-card);
        }}
        
        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--gradient-primary);
            opacity: 0;
            transition: opacity 0.3s;
        }}
        
        .stat-card:hover::before {{ opacity: 1; }}
        
        .stat-icon {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}
        
        .stat-value {{
            font-size: 2rem;
            font-weight: 700;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .stat-card.success .stat-value {{
            background: var(--gradient-success);
            -webkit-background-clip: text;
            background-clip: text;
        }}
        
        .stat-card.warning .stat-value {{
            background: var(--gradient-warning);
            -webkit-background-clip: text;
            background-clip: text;
        }}
        
        .stat-label {{
            color: var(--text-secondary);
            font-size: 0.875rem;
            margin-top: 0.25rem;
        }}
        
        /* Section Card */
        .section {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: var(--shadow-card);
        }}
        
        .section-header {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }}
        
        .section-icon {{
            font-size: 1.5rem;
        }}
        
        .section-title {{
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text);
        }}
        
        /* Charts Grid */
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        
        .chart-container {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 1.5rem;
            box-shadow: var(--shadow-card);
        }}
        
        .chart-title {{
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .chart {{
            height: 300px;
            width: 100%;
        }}
        
        .chart-large {{
            height: 400px;
        }}
        
        /* Tables */
        .table-wrapper {{
            overflow-x: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th, td {{
            padding: 0.875rem 1rem;
            text-align: left;
        }}
        
        th {{
            color: var(--text-dim);
            font-weight: 500;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--border);
        }}
        
        tr {{
            border-bottom: 1px solid var(--border);
            transition: background 0.2s;
        }}
        
        tr:hover {{
            background: var(--bg-elevated);
        }}
        
        tr:last-child {{
            border-bottom: none;
        }}
        
        .rank {{
            color: var(--text-dim);
            font-weight: 600;
            font-size: 0.875rem;
        }}
        
        .size {{
            color: var(--success);
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
        }}
        
        .path {{
            color: var(--text-secondary);
            font-size: 0.875rem;
            max-width: 400px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        
        .bar-cell {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        
        .mini-bar {{
            width: 80px;
            height: 6px;
            background: rgba(255,255,255,0.1);
            border-radius: 3px;
            overflow: hidden;
        }}
        
        .mini-bar-fill {{
            height: 100%;
            background: var(--gradient-primary);
            border-radius: 3px;
            transition: width 0.5s ease;
        }}
        
        .percent {{
            color: var(--text-dim);
            font-size: 0.8rem;
            min-width: 45px;
        }}
        
        /* Tree */
        .tree-container {{
            max-height: 600px;
            overflow-y: auto;
            padding-right: 0.5rem;
        }}
        
        .tree-container::-webkit-scrollbar {{
            width: 6px;
        }}
        
        .tree-container::-webkit-scrollbar-track {{
            background: var(--bg-elevated);
            border-radius: 3px;
        }}
        
        .tree-container::-webkit-scrollbar-thumb {{
            background: var(--primary);
            border-radius: 3px;
        }}
        
        .tree-item {{
            margin: 2px 0;
        }}
        
        .tree-item.collapsed > .tree-children {{
            display: none;
        }}
        
        .tree-item.collapsed .tree-toggle {{
            transform: rotate(0deg);
        }}
        
        .tree-header {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 0.75rem;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .tree-header:hover {{
            background: var(--bg-elevated);
        }}
        
        .tree-toggle {{
            color: var(--text-dim);
            font-size: 0.7rem;
            width: 12px;
            transition: transform 0.2s;
            transform: rotate(90deg);
        }}
        
        .tree-icon {{
            font-size: 1rem;
        }}
        
        .tree-name {{
            color: var(--warning);
            font-weight: 500;
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        
        .tree-meta {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        
        .tree-size {{
            color: var(--success);
            font-family: monospace;
            font-size: 0.85rem;
            min-width: 70px;
            text-align: right;
        }}
        
        .tree-percent {{
            color: var(--text-dim);
            font-size: 0.8rem;
            min-width: 45px;
        }}
        
        .tree-bar {{
            width: 60px;
            height: 4px;
            background: rgba(255,255,255,0.1);
            border-radius: 2px;
            overflow: hidden;
        }}
        
        .tree-bar-fill {{
            height: 100%;
            background: var(--gradient-primary);
            border-radius: 2px;
        }}
        
        .tree-children {{
            margin-left: 1.5rem;
            border-left: 1px solid var(--border);
            padding-left: 0.5rem;
        }}
        
        .tree-more {{
            color: var(--text-dim);
            font-size: 0.85rem;
            padding: 0.5rem 0.75rem;
            font-style: italic;
        }}
        
        /* Media Cards */
        .media-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
        }}
        
        .media-card {{
            background: var(--bg-elevated);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            text-align: center;
            transition: all 0.3s ease;
        }}
        
        .media-card:hover {{
            transform: translateY(-2px);
            border-color: var(--primary);
        }}
        
        .media-icon {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }}
        
        .media-type {{
            font-weight: 600;
            text-transform: capitalize;
            margin-bottom: 0.25rem;
        }}
        
        .media-size {{
            color: var(--success);
            font-weight: 700;
            font-size: 1.25rem;
        }}
        
        .media-count {{
            color: var(--text-dim);
            font-size: 0.85rem;
        }}
        
        /* Cleanup Section */
        .cleanup-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
        }}
        
        .cleanup-card {{
            background: var(--bg-elevated);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            transition: all 0.3s ease;
        }}
        
        .cleanup-card:hover {{
            border-color: var(--danger);
        }}
        
        .cleanup-header {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.75rem;
        }}
        
        .cleanup-icon {{
            font-size: 1.5rem;
        }}
        
        .cleanup-type {{
            font-weight: 600;
            text-transform: capitalize;
        }}
        
        .cleanup-size {{
            color: var(--danger);
            font-weight: 700;
            font-size: 1.5rem;
            margin-bottom: 0.25rem;
        }}
        
        .cleanup-count {{
            color: var(--text-dim);
            font-size: 0.85rem;
        }}
        
        /* Duplicates Section */
        .dup-container {{
            max-height: 600px;
            overflow-y: auto;
        }}
        
        .dup-group {{
            background: var(--bg-elevated);
            border: 1px solid var(--border);
            border-radius: 12px;
            margin-bottom: 1rem;
            overflow: hidden;
        }}
        
        .dup-group-header {{
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1rem 1.25rem;
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(239, 68, 68, 0.05));
            border-bottom: 1px solid var(--border);
        }}
        
        .dup-group-num {{
            background: var(--danger);
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
        }}
        
        .dup-group-info {{
            color: var(--text);
            font-weight: 500;
        }}
        
        .dup-group-size {{
            color: var(--warning);
            font-family: monospace;
            font-weight: 600;
        }}
        
        .dup-group-wasted {{
            color: var(--danger);
            font-weight: 600;
            margin-left: auto;
        }}
        
        .dup-group-files {{
            padding: 0.75rem 1.25rem;
        }}
        
        .dup-file {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.4rem 0;
            border-bottom: 1px solid var(--border);
        }}
        
        .dup-file:last-child {{
            border-bottom: none;
        }}
        
        .dup-file-icon {{
            font-size: 0.9rem;
        }}
        
        .dup-file-path {{
            color: var(--text-dim);
            font-size: 0.85rem;
            font-family: monospace;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        
        .dup-summary {{
            display: flex;
            gap: 2rem;
            margin-bottom: 1.5rem;
            padding: 1rem 1.5rem;
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(239, 68, 68, 0.05));
            border-radius: 12px;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }}
        
        .dup-summary-item {{
            text-align: center;
        }}
        
        .dup-summary-value {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--danger);
        }}
        
        .dup-summary-label {{
            color: var(--text-dim);
            font-size: 0.85rem;
        }}
        
        /* Tabs */
        .tabs {{
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.5rem;
        }}
        
        .tab {{
            padding: 0.5rem 1rem;
            border-radius: 8px;
            cursor: pointer;
            color: var(--text-secondary);
            transition: all 0.2s;
            font-weight: 500;
        }}
        
        .tab:hover {{
            color: var(--text);
            background: var(--bg-elevated);
        }}
        
        .tab.active {{
            color: var(--primary-light);
            background: rgba(99,102,241,0.1);
        }}
        
        .tab-content {{
            display: none;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        /* Footer */
        .footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-dim);
            font-size: 0.875rem;
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}
            
            .header h1 {{
                font-size: 2rem;
            }}
            
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
            
            .chart {{
                height: 250px;
            }}
        }}
        
        /* Animations */
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .section, .chart-container, .stat-card {{
            animation: fadeIn 0.5s ease forwards;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <h1>📊 磁盘空间分析报告</h1>
            <p class="subtitle">扫描完成于 {current_time}</p>
            <div class="scan-path">📁 {summary['root_path']}</div>
        </header>
        
        <!-- Stats Overview -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon">💾</div>
                <div class="stat-value">{summary['formatted_size']}</div>
                <div class="stat-label">总占用空间</div>
            </div>
            <div class="stat-card success">
                <div class="stat-icon">📄</div>
                <div class="stat-value">{total_files_str}</div>
                <div class="stat-label">文件数量</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">📂</div>
                <div class="stat-value">{total_dirs_str}</div>
                <div class="stat-label">目录数量</div>
            </div>
            <div class="stat-card warning">
                <div class="stat-icon">🧹</div>
                <div class="stat-value">{total_cleanable_str}</div>
                <div class="stat-label">可清理空间</div>
            </div>
        </div>
        
        <!-- Charts Row -->
        <div class="charts-grid">
            <div class="chart-container">
                <div class="chart-title">📊 文件类型分布</div>
                <div id="pieChart" class="chart"></div>
            </div>
            <div class="chart-container">
                <div class="chart-title">🎬 媒体文件占比</div>
                <div id="mediaPieChart" class="chart"></div>
            </div>
        </div>
        
        <!-- Treemap -->
        <div class="chart-container" style="margin-bottom: 1.5rem;">
            <div class="chart-title">🗺️ 空间占用地图（点击可下钻）</div>
            <div id="treemapChart" class="chart chart-large"></div>
        </div>
        
        <!-- Size Distribution -->
        <div class="chart-container" style="margin-bottom: 1.5rem;">
            <div class="chart-title">📈 文件大小分布</div>
            <div id="sizeBarChart" class="chart"></div>
        </div>
        
        <!-- Media Files Analysis -->
        <div class="section">
            <div class="section-header">
                <span class="section-icon">🎬</span>
                <h2 class="section-title">媒体文件分析</h2>
            </div>
            <div class="media-grid">
                {media_cards_html}
            </div>
        </div>
        
        <!-- Cleanup Suggestions -->
        <div class="section">
            <div class="section-header">
                <span class="section-icon">🧹</span>
                <h2 class="section-title">可清理空间建议</h2>
            </div>
            <div class="cleanup-grid">
                {cleanup_cards_html}
            </div>
        </div>
        
        <!-- Duplicate Files Section -->
        {'<div class="section"><div class="section-header"><span class="section-icon">🔄</span><h2 class="section-title">重复文件检测</h2></div><div class="dup-container">' + duplicates_html + '</div></div>' if has_duplicates else ''}
        
        <!-- Directory Tree -->
        <div class="section">
            <div class="section-header">
                <span class="section-icon">🌳</span>
                <h2 class="section-title">目录结构</h2>
            </div>
            <div class="tree-container">
                {tree_html}
            </div>
        </div>
        
        <!-- Top Items Tabs -->
        <div class="section">
            <div class="tabs">
                <div class="tab active" onclick="switchTab('dirs')">📂 最大目录</div>
                <div class="tab" onclick="switchTab('files')">📄 最大文件</div>
                <div class="tab" onclick="switchTab('types')">📊 文件类型</div>
            </div>
            
            <div id="tab-dirs" class="tab-content active">
                <div class="table-wrapper">
                    <table>
                        <tr><th>#</th><th>大小</th><th>占比</th><th>路径</th></tr>
                        {dirs_table_html}
                    </table>
                </div>
            </div>
            
            <div id="tab-files" class="tab-content">
                <div class="table-wrapper">
                    <table>
                        <tr><th>#</th><th>大小</th><th>文件路径</th></tr>
                        {files_table_html}
                    </table>
                </div>
            </div>
            
            <div id="tab-types" class="tab-content">
                <div class="table-wrapper">
                    <table>
                        <tr><th>扩展名</th><th>大小</th><th>占比</th><th>文件数</th></tr>
                        {types_table_html}
                    </table>
                </div>
            </div>
        </div>
        
        <!-- Footer -->
        <footer class="footer">
            <p>由 macOS 磁盘空间分析工具生成 | {current_time}</p>
        </footer>
    </div>
    
    <script>
        // Chart Data
        const chartData = {chart_data_json};
        
        // Format size helper
        function formatSize(bytes) {{
            const units = ['B', 'KB', 'MB', 'GB', 'TB'];
            let i = 0;
            while (bytes >= 1024 && i < units.length - 1) {{
                bytes /= 1024;
                i++;
            }}
            return bytes.toFixed(1) + ' ' + units[i];
        }}
        
        // Pie Chart - File Types
        const pieChart = echarts.init(document.getElementById('pieChart'));
        pieChart.setOption({{
            tooltip: {{
                trigger: 'item',
                formatter: (params) => `${{params.name}}<br/>大小: ${{formatSize(params.value)}}<br/>占比: ${{params.percent}}%`,
                backgroundColor: 'rgba(30,30,45,0.95)',
                borderColor: 'rgba(99,102,241,0.3)',
                textStyle: {{ color: '#f1f5f9' }}
            }},
            legend: {{
                orient: 'vertical',
                right: '5%',
                top: 'center',
                textStyle: {{ color: '#94a3b8' }}
            }},
            series: [{{
                type: 'pie',
                radius: ['45%', '75%'],
                center: ['35%', '50%'],
                avoidLabelOverlap: false,
                itemStyle: {{
                    borderRadius: 8,
                    borderColor: '#12121a',
                    borderWidth: 2
                }},
                label: {{ show: false }},
                emphasis: {{
                    label: {{ show: true, fontSize: 14, fontWeight: 'bold' }}
                }},
                labelLine: {{ show: false }},
                data: chartData.pieData,
                color: ['#6366f1', '#a855f7', '#ec4899', '#f43f5e', '#f97316', '#eab308', '#22c55e', '#14b8a6', '#06b6d4', '#3b82f6']
            }}]
        }});
        
        // Media Pie Chart
        const mediaPieChart = echarts.init(document.getElementById('mediaPieChart'));
        mediaPieChart.setOption({{
            tooltip: {{
                trigger: 'item',
                formatter: (params) => `${{params.name}}<br/>大小: ${{formatSize(params.value)}}<br/>占比: ${{params.percent}}%`,
                backgroundColor: 'rgba(30,30,45,0.95)',
                borderColor: 'rgba(99,102,241,0.3)',
                textStyle: {{ color: '#f1f5f9' }}
            }},
            legend: {{
                orient: 'vertical',
                right: '5%',
                top: 'center',
                textStyle: {{ color: '#94a3b8' }}
            }},
            series: [{{
                type: 'pie',
                radius: ['45%', '75%'],
                center: ['35%', '50%'],
                roseType: 'radius',
                itemStyle: {{
                    borderRadius: 8,
                    borderColor: '#12121a',
                    borderWidth: 2
                }},
                label: {{ show: false }},
                emphasis: {{
                    label: {{ show: true, fontSize: 14, fontWeight: 'bold' }}
                }},
                data: chartData.mediaPieData,
                color: ['#f43f5e', '#a855f7', '#06b6d4', '#22c55e', '#f97316', '#6366f1', '#64748b']
            }}]
        }});
        
        // Treemap Chart
        const treemapChart = echarts.init(document.getElementById('treemapChart'));
        treemapChart.setOption({{
            tooltip: {{
                formatter: (info) => {{
                    const value = info.value;
                    return `<strong>${{info.name}}</strong><br/>大小: ${{formatSize(value)}}`;
                }},
                backgroundColor: 'rgba(30,30,45,0.95)',
                borderColor: 'rgba(99,102,241,0.3)',
                textStyle: {{ color: '#f1f5f9' }}
            }},
            series: [{{
                type: 'treemap',
                data: [chartData.treemapData],
                width: '100%',
                height: '100%',
                roam: false,
                nodeClick: 'zoomToNode',
                breadcrumb: {{
                    show: true,
                    height: 26,
                    itemStyle: {{
                        color: '#1e1e2d',
                        borderColor: 'rgba(255,255,255,0.1)',
                        textStyle: {{ color: '#94a3b8' }}
                    }}
                }},
                label: {{
                    show: true,
                    formatter: (params) => {{
                        return params.name + '\\n' + formatSize(params.value);
                    }},
                    fontSize: 11,
                    color: '#f1f5f9'
                }},
                itemStyle: {{
                    borderColor: '#0a0a0f',
                    borderWidth: 2,
                    gapWidth: 2
                }},
                levels: [
                    {{ itemStyle: {{ borderWidth: 0, gapWidth: 5 }} }},
                    {{ colorSaturation: [0.3, 0.6], itemStyle: {{ borderColorSaturation: 0.7, gapWidth: 2, borderWidth: 2 }} }},
                    {{ colorSaturation: [0.3, 0.5], itemStyle: {{ borderColorSaturation: 0.6, gapWidth: 1 }} }},
                    {{ colorSaturation: [0.3, 0.5] }}
                ],
                color: ['#6366f1', '#a855f7', '#ec4899', '#f43f5e', '#f97316', '#eab308', '#22c55e', '#14b8a6', '#06b6d4']
            }}]
        }});
        
        // Size Distribution Bar Chart
        const sizeBarChart = echarts.init(document.getElementById('sizeBarChart'));
        sizeBarChart.setOption({{
            tooltip: {{
                trigger: 'axis',
                axisPointer: {{ type: 'shadow' }},
                formatter: (params) => {{
                    const data = params[0];
                    const sizeData = chartData.sizeBarData.sizes[data.dataIndex];
                    return `${{data.name}}<br/>文件数: ${{data.value}}<br/>总大小: ${{formatSize(sizeData)}}`;
                }},
                backgroundColor: 'rgba(30,30,45,0.95)',
                borderColor: 'rgba(99,102,241,0.3)',
                textStyle: {{ color: '#f1f5f9' }}
            }},
            grid: {{
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            }},
            xAxis: {{
                type: 'category',
                data: chartData.sizeBarData.categories,
                axisLine: {{ lineStyle: {{ color: 'rgba(255,255,255,0.1)' }} }},
                axisLabel: {{ color: '#94a3b8', fontSize: 11 }}
            }},
            yAxis: {{
                type: 'value',
                axisLine: {{ show: false }},
                axisLabel: {{ color: '#94a3b8' }},
                splitLine: {{ lineStyle: {{ color: 'rgba(255,255,255,0.05)' }} }}
            }},
            series: [{{
                data: chartData.sizeBarData.counts,
                type: 'bar',
                barWidth: '60%',
                itemStyle: {{
                    borderRadius: [6, 6, 0, 0],
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        {{ offset: 0, color: '#a855f7' }},
                        {{ offset: 1, color: '#6366f1' }}
                    ])
                }},
                emphasis: {{
                    itemStyle: {{
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            {{ offset: 0, color: '#c084fc' }},
                            {{ offset: 1, color: '#818cf8' }}
                        ])
                    }}
                }}
            }}]
        }});
        
        // Resize handler
        window.addEventListener('resize', () => {{
            pieChart.resize();
            mediaPieChart.resize();
            treemapChart.resize();
            sizeBarChart.resize();
        }});
        
        // Tab switching
        function switchTab(tabName) {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('tab-' + tabName).classList.add('active');
        }}
        
        // Tree toggle
        function toggleTree(element) {{
            const treeItem = element.closest('.tree-item');
            treeItem.classList.toggle('collapsed');
        }}
    </script>
</body>
</html>'''
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"📊 HTML 报告已保存到: {output_path}")
