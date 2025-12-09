"""
文件系统扫描器模块
递归遍历目录树，收集文件和目录的大小信息
"""

import os
import stat
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Generator
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


@dataclass
class FileInfo:
    """文件信息"""
    path: str
    size: int
    mtime: float
    extension: str
    
    @property
    def name(self) -> str:
        return os.path.basename(self.path)


@dataclass
class DirInfo:
    """目录信息"""
    path: str
    total_size: int = 0
    file_count: int = 0
    dir_count: int = 0
    files: List[FileInfo] = field(default_factory=list)
    subdirs: Dict[str, 'DirInfo'] = field(default_factory=dict)
    error: Optional[str] = None
    
    @property
    def name(self) -> str:
        return os.path.basename(self.path) or self.path


@dataclass
class ScanResult:
    """扫描结果"""
    root: DirInfo
    total_size: int = 0
    total_files: int = 0
    total_dirs: int = 0
    errors: List[str] = field(default_factory=list)
    all_files: List[FileInfo] = field(default_factory=list)
    all_dirs: List[DirInfo] = field(default_factory=list)


class DiskScanner:
    """磁盘扫描器"""
    
    # macOS 系统目录，通常需要跳过
    DEFAULT_EXCLUDES = {
        '.Spotlight-V100',
        '.fseventsd',
        '.Trashes',
        '.DocumentRevisions-V100',
        '.TemporaryItems',
        '.vol',
        'System/Volumes/Data/.Spotlight-V100',
        # iCloud 相关目录（扫描会卡住）
        'Library/Mobile Documents',
        'iCloud Drive',
        'CloudStorage',
        '.iCloud',
    }
    
    def __init__(
        self,
        exclude_patterns: Optional[Set[str]] = None,
        min_size: int = 0,
        max_depth: Optional[int] = None,
        follow_symlinks: bool = False,
        progress_callback=None
    ):
        """
        初始化扫描器
        
        Args:
            exclude_patterns: 要排除的目录名或路径模式
            min_size: 忽略小于此大小的文件（字节）
            max_depth: 最大扫描深度，None 表示无限制
            follow_symlinks: 是否跟随符号链接
            progress_callback: 进度回调函数 (current_path, files_scanned, dirs_scanned)
        """
        self.exclude_patterns = self.DEFAULT_EXCLUDES.copy()
        if exclude_patterns:
            self.exclude_patterns.update(exclude_patterns)
        self.min_size = min_size
        self.max_depth = max_depth
        self.follow_symlinks = follow_symlinks
        self.progress_callback = progress_callback
        
        # 统计信息
        self._files_scanned = 0
        self._dirs_scanned = 0
        self._lock = threading.Lock()
    
    def scan(self, path: str) -> ScanResult:
        """
        扫描指定路径
        
        Args:
            path: 要扫描的目录路径
            
        Returns:
            ScanResult 扫描结果
        """
        path = os.path.abspath(os.path.expanduser(path))
        
        if not os.path.exists(path):
            raise ValueError(f"路径不存在: {path}")
        
        if not os.path.isdir(path):
            raise ValueError(f"不是目录: {path}")
        
        result = ScanResult(
            root=DirInfo(path=path),
            all_files=[],
            all_dirs=[]
        )
        
        self._files_scanned = 0
        self._dirs_scanned = 0
        
        # 递归扫描
        self._scan_directory(result.root, 0, result)
        
        # 更新统计
        result.total_size = result.root.total_size
        result.total_files = self._files_scanned
        result.total_dirs = self._dirs_scanned
        
        return result
    
    def _should_exclude(self, path: str, name: str) -> bool:
        """检查是否应该排除此路径"""
        if name in self.exclude_patterns:
            return True
        for pattern in self.exclude_patterns:
            if pattern in path:
                return True
        return False
    
    def _scan_directory(self, dir_info: DirInfo, depth: int, result: ScanResult):
        """递归扫描目录"""
        if self.max_depth is not None and depth > self.max_depth:
            return
        
        try:
            with os.scandir(dir_info.path) as entries:
                for entry in entries:
                    try:
                        # 检查是否排除
                        if self._should_exclude(entry.path, entry.name):
                            continue
                        
                        # 检查是否为符号链接
                        if entry.is_symlink() and not self.follow_symlinks:
                            continue
                        
                        if entry.is_file(follow_symlinks=self.follow_symlinks):
                            self._process_file(entry, dir_info, result)
                        elif entry.is_dir(follow_symlinks=self.follow_symlinks):
                            self._process_directory(entry, dir_info, depth, result)
                            
                    except PermissionError:
                        result.errors.append(f"权限被拒绝: {entry.path}")
                    except OSError as e:
                        result.errors.append(f"访问错误 {entry.path}: {e}")
                        
        except PermissionError:
            dir_info.error = "权限被拒绝"
            result.errors.append(f"权限被拒绝: {dir_info.path}")
        except OSError as e:
            dir_info.error = str(e)
            result.errors.append(f"访问错误 {dir_info.path}: {e}")
        
        # 进度回调
        if self.progress_callback:
            self.progress_callback(dir_info.path, self._files_scanned, self._dirs_scanned)
    
    def _process_file(self, entry, dir_info: DirInfo, result: ScanResult):
        """处理文件"""
        try:
            stat_info = entry.stat(follow_symlinks=self.follow_symlinks)
            size = stat_info.st_size
            
            # 检查最小大小
            if size < self.min_size:
                return
            
            # 获取扩展名
            _, ext = os.path.splitext(entry.name)
            ext = ext.lower() if ext else '(无扩展名)'
            
            file_info = FileInfo(
                path=entry.path,
                size=size,
                mtime=stat_info.st_mtime,
                extension=ext
            )
            
            dir_info.files.append(file_info)
            dir_info.total_size += size
            dir_info.file_count += 1
            
            result.all_files.append(file_info)
            
            with self._lock:
                self._files_scanned += 1
                
        except (OSError, IOError):
            pass
    
    def _process_directory(self, entry, parent_dir: DirInfo, depth: int, result: ScanResult):
        """处理子目录"""
        subdir_info = DirInfo(path=entry.path)
        
        # 递归扫描
        self._scan_directory(subdir_info, depth + 1, result)
        
        # 更新父目录信息
        parent_dir.subdirs[entry.name] = subdir_info
        parent_dir.total_size += subdir_info.total_size
        parent_dir.dir_count += 1
        
        result.all_dirs.append(subdir_info)
        
        with self._lock:
            self._dirs_scanned += 1


def format_size(size: int) -> str:
    """将字节大小格式化为人类可读的形式"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if abs(size) < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} EB"


def parse_size(size_str: str) -> int:
    """解析大小字符串（如 '100MB'）为字节数"""
    size_str = size_str.strip().upper()
    
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
    }
    
    for unit, multiplier in units.items():
        if size_str.endswith(unit):
            number = size_str[:-len(unit)].strip()
            return int(float(number) * multiplier)
    
    # 默认为字节
    return int(size_str)
