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
            ('< 1 KB', 0, 1024),
            ('1 KB - 100 KB', 1024, 100 * 1024),
            ('100 KB - 1 MB', 100 * 1024, 1024 * 1024),
            ('1 MB - 10 MB', 1024 * 1024, 10 * 1024 * 1024),
            ('10 MB - 100 MB', 10 * 1024 * 1024, 100 * 1024 * 1024),
            ('100 MB - 1 GB', 100 * 1024 * 1024, 1024 * 1024 * 1024),
            ('> 1 GB', 1024 * 1024 * 1024, float('inf'))
        ]
        
        distribution = {name: {'count': 0, 'total_size': 0} for name, _, _ in ranges}
        
        for file in self.scan_result.all_files:
            for name, min_size, max_size in ranges:
                if min_size <= file.size < max_size:
                    distribution[name]['count'] += 1
                    distribution[name]['total_size'] += file.size
                    break
        
        return distribution
