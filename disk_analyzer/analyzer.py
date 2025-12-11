"""
数据分析模块
提供空间占用统计和分析功能
"""

from collections import defaultdict
from typing import Dict, List, Tuple
from dataclasses import dataclass

from .scanner import ScanResult, FileInfo, DirInfo, format_size


@dataclass
class ExtensionStats:
    """扩展名统计"""
    extension: str
    total_size: int
    file_count: int
    
    @property
    def formatted_size(self) -> str:
        return format_size(self.total_size)


class SpaceAnalyzer:
    """空间分析器"""
    
    def __init__(self, scan_result: ScanResult):
        """
        初始化分析器
        
        Args:
            scan_result: 扫描结果
        """
        self.scan_result = scan_result
    
    def get_top_directories(self, n: int = 20) -> List[DirInfo]:
        """
        获取占用空间最大的 N 个目录
        
        Args:
            n: 返回的目录数量
            
        Returns:
            按大小降序排列的目录列表
        """
        # 收集所有目录
        all_dirs = [self.scan_result.root] + self.scan_result.all_dirs
        
        # 按大小排序
        sorted_dirs = sorted(all_dirs, key=lambda d: d.total_size, reverse=True)
        
        return sorted_dirs[:n]
    
    def get_top_files(self, n: int = 20) -> List[FileInfo]:
        """
        获取最大的 N 个文件
        
        Args:
            n: 返回的文件数量
            
        Returns:
            按大小降序排列的文件列表
        """
        sorted_files = sorted(
            self.scan_result.all_files, 
            key=lambda f: f.size, 
            reverse=True
        )
        return sorted_files[:n]
    
    def get_extension_stats(self) -> List[ExtensionStats]:
        """
        获取按扩展名分组的统计
        
        Returns:
            按总大小降序排列的扩展名统计列表
        """
        ext_data: Dict[str, Dict[str, int]] = defaultdict(lambda: {'size': 0, 'count': 0})
        
        for file in self.scan_result.all_files:
            ext_data[file.extension]['size'] += file.size
            ext_data[file.extension]['count'] += 1
        
        stats = [
            ExtensionStats(
                extension=ext,
                total_size=data['size'],
                file_count=data['count']
            )
            for ext, data in ext_data.items()
        ]
        
        return sorted(stats, key=lambda s: s.total_size, reverse=True)
    
    def get_directory_tree(self, max_depth: int = 3) -> Dict:
        """
        获取目录树结构（用于可视化）
        
        Args:
            max_depth: 最大深度
            
        Returns:
            嵌套的目录树字典
        """
        def build_tree(dir_info: DirInfo, current_depth: int) -> Dict:
            tree = {
                'name': dir_info.name,
                'path': dir_info.path,
                'size': dir_info.total_size,
                'formatted_size': format_size(dir_info.total_size),
                'file_count': dir_info.file_count,
                'children': []
            }
            
            if current_depth < max_depth:
                # 按大小排序子目录
                sorted_subdirs = sorted(
                    dir_info.subdirs.values(),
                    key=lambda d: d.total_size,
                    reverse=True
                )
                
                for subdir in sorted_subdirs:
                    tree['children'].append(build_tree(subdir, current_depth + 1))
            
            return tree
        
        return build_tree(self.scan_result.root, 0)
    
    def get_summary(self) -> Dict:
        """
        获取扫描摘要
        
        Returns:
            包含统计信息的字典
        """
        return {
            'root_path': self.scan_result.root.path,
            'total_size': self.scan_result.total_size,
            'formatted_size': format_size(self.scan_result.total_size),
            'total_files': self.scan_result.total_files,
            'total_dirs': self.scan_result.total_dirs,
            'errors_count': len(self.scan_result.errors)
        }
    
    def get_size_distribution(self) -> Dict[str, Dict[str, int]]:
        """
        获取文件大小分布
        
        Returns:
            按大小区间分组的统计
        """
        ranges = [
            ('<1 KB', 0, 1024),
            ('1 KB - 100 KB', 1024, 100 * 1024),
            ('100 KB - 1 MB', 100 * 1024, 1024 * 1024),
            ('1 MB - 10 MB', 1024 * 1024, 10 * 1024 * 1024),
            ('10 MB - 100 MB', 10 * 1024 * 1024, 100 * 1024 * 1024),
            ('100 MB - 1 GB', 100 * 1024 * 1024, 1024 * 1024 * 1024),
            ('>1 GB', 1024 * 1024 * 1024, float('inf'))
        ]
        
        distribution = {name: {'count': 0, 'total_size': 0} for name, _, _ in ranges}
        
        for file in self.scan_result.all_files:
            for name, min_size, max_size in ranges:
                if min_size <= file.size < max_size:
                    distribution[name]['count'] += 1
                    distribution[name]['total_size'] += file.size
                    break
        
        return distribution
    
    def get_media_stats(self) -> Dict[str, Dict[str, any]]:
        """
        获取媒体文件统计
        
        Returns:
            按媒体类型分组的统计 {type: {count, total_size, files}}
        """
        from .scanner import MEDIA_TYPES
        
        stats = {}
        for media_type in MEDIA_TYPES.keys():
            stats[media_type] = {
                'count': 0,
                'total_size': 0,
                'files': [],
                'formatted_size': '0 B'
            }
        stats['other'] = {'count': 0, 'total_size': 0, 'files': [], 'formatted_size': '0 B'}
        
        for file in self.scan_result.all_files:
            media_type = file.media_type or 'other'
            if media_type in stats:
                stats[media_type]['count'] += 1
                stats[media_type]['total_size'] += file.size
                # 只保留最大的20个文件
                if len(stats[media_type]['files']) < 20:
                    stats[media_type]['files'].append(file)
                else:
                    # 找到最小的文件替换
                    min_idx = min(range(len(stats[media_type]['files'])), 
                                  key=lambda i: stats[media_type]['files'][i].size)
                    if file.size > stats[media_type]['files'][min_idx].size:
                        stats[media_type]['files'][min_idx] = file
        
        # 格式化大小并排序文件
        for media_type in stats:
            stats[media_type]['formatted_size'] = format_size(stats[media_type]['total_size'])
            stats[media_type]['files'].sort(key=lambda f: f.size, reverse=True)
        
        return stats
    
    def get_cleanable_suggestions(self) -> Dict[str, Dict[str, any]]:
        """
        获取可清理文件建议
        
        Returns:
            按清理类型分组的统计
        """
        from .scanner import CLEANABLE_PATTERNS
        
        suggestions = {}
        for clean_type in CLEANABLE_PATTERNS.keys():
            suggestions[clean_type] = {
                'count': 0,
                'total_size': 0,
                'items': [],
                'formatted_size': '0 B'
            }
        
        # 统计可清理文件
        for file in self.scan_result.all_files:
            if file.cleanable_type:
                clean_type = file.cleanable_type
                if clean_type in suggestions:
                    suggestions[clean_type]['count'] += 1
                    suggestions[clean_type]['total_size'] += file.size
                    if len(suggestions[clean_type]['items']) < 10:
                        suggestions[clean_type]['items'].append({
                            'path': file.path,
                            'size': file.size,
                            'formatted_size': format_size(file.size),
                            'type': 'file'
                        })
        
        # 统计可清理目录
        for dir_info in self.scan_result.all_dirs:
            from .scanner import is_cleanable
            import os
            clean_type = is_cleanable(dir_info.path, os.path.basename(dir_info.path))
            if clean_type and clean_type in suggestions:
                suggestions[clean_type]['count'] += 1
                suggestions[clean_type]['total_size'] += dir_info.total_size
                if len(suggestions[clean_type]['items']) < 10:
                    suggestions[clean_type]['items'].append({
                        'path': dir_info.path,
                        'size': dir_info.total_size,
                        'formatted_size': format_size(dir_info.total_size),
                        'type': 'directory'
                    })
        
        # 格式化大小
        for clean_type in suggestions:
            suggestions[clean_type]['formatted_size'] = format_size(suggestions[clean_type]['total_size'])
        
        return suggestions
    
    def get_treemap_data(self, max_depth: int = 3) -> Dict:
        """
        获取 Treemap 图表数据
        
        Args:
            max_depth: 最大深度
            
        Returns:
            ECharts treemap 格式的数据
        """
        def build_treemap_node(dir_info: DirInfo, current_depth: int) -> Dict:
            import os
            node = {
                'name': dir_info.name or os.path.basename(dir_info.path) or dir_info.path,
                'value': dir_info.total_size,
                'path': dir_info.path,
            }
            
            if current_depth < max_depth and dir_info.subdirs:
                # 过滤掉太小的目录
                min_size = dir_info.total_size * 0.01  # 至少占1%
                children = []
                for subdir in sorted(dir_info.subdirs.values(), 
                                     key=lambda d: d.total_size, reverse=True):
                    if subdir.total_size >= min_size or len(children) < 5:
                        children.append(build_treemap_node(subdir, current_depth + 1))
                    if len(children) >= 15:  # 限制子节点数量
                        break
                
                if children:
                    node['children'] = children
            
            return node
        
        return build_treemap_node(self.scan_result.root, 0)
    
    def get_old_files(self, days: int = 365, n: int = 20) -> List[FileInfo]:
        """
        获取超过指定天数未修改的大文件
        
        Args:
            days: 天数阈值
            n: 返回文件数量
            
        Returns:
            按大小降序排列的旧文件列表
        """
        import time
        threshold = time.time() - (days * 24 * 60 * 60)
        
        old_files = [f for f in self.scan_result.all_files if f.mtime < threshold]
        old_files.sort(key=lambda f: f.size, reverse=True)
        
        return old_files[:n]
