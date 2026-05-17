"""
ykv2mp4 — 优酷 YKV 视频无损转 MP4 工具

将优酷客户端下载的 .ykv 格式视频无损提取并合并为标准 MP4 文件。
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__license__ = "MIT"

from .converter import YKVConverter, find_ftyp_offsets, extract_segments
