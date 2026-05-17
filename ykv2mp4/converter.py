"""
YKV 格式解析与 MP4 转换核心逻辑。

YKV 文件本质上是多个标准 MP4 分片简单拼接而成。
每个 MP4 分片以 'ftyp' box 开头（前 4 字节为 box length）。
本模块通过扫描 'ftyp' 标记定位分片边界，提取分片，
再调用 ffmpeg 无损合并为完整 MP4。
"""

import subprocess
import logging
import shutil
from pathlib import Path
from typing import List

logger = logging.getLogger("ykv2mp4")

FTYP_MARKER = b"ftyp"


def find_ftyp_offsets(data: bytes) -> List[int]:
    """
    在二进制数据中查找所有 MP4 分片的起始偏移。

    YKV 中每个分片是标准 MP4 box，结构为：
        [box_length: 4字节] [box_type: "ftyp"] [box_data...]

    因此找到 "ftyp" 后需要向前回溯 4 字节得到 box 的起始位置。
    """
    offsets: List[int] = []
    pos = 0
    while True:
        idx = data.find(FTYP_MARKER, pos)
        if idx == -1:
            break
        # box 起始 = ftyp 位置 - 4（box length 字段）
        start = idx - 4
        if start >= 0:
            offsets.append(start)
        pos = idx + 4
    return offsets


def extract_segments(
    data: bytes,
    offsets: List[int],
    output_dir: str | Path,
    prefix: str = "part",
) -> List[str]:
    """
    根据分片偏移位置，提取每个 MP4 分片并写入磁盘。

    Args:
        data: YKV 文件原始二进制数据
        offsets: 分片起始偏移列表
        output_dir: 输出目录
        prefix: 分片文件名前缀

    Returns:
        分片文件路径列表（按顺序）
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 最后一个分片终点为文件末尾
    boundaries = sorted(set(offsets))
    boundaries.append(len(data))

    segment_files: List[str] = []
    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        seg_path = output_dir / f"{prefix}{i + 1}.mp4"
        seg_path.write_bytes(data[start:end])
        segment_files.append(str(seg_path.resolve()))
        logger.info("提取分片 %s (%d 字节)", seg_path.name, end - start)

    return segment_files


def merge_segments(
    segment_files: List[str],
    output_path: str | Path,
    ffmpeg_path: str = "ffmpeg",
) -> str:
    """
    使用 ffmpeg concat demuxer 无损合并多个 MP4 分片。

    Args:
        segment_files: 分片文件路径列表（有序）
        output_path: 合并后 MP4 输出路径
        ffmpeg_path: ffmpeg 可执行文件路径

    Returns:
        合并后文件的绝对路径

    Raises:
        RuntimeError: ffmpeg 未找到或执行失败
    """
    output_path = Path(output_path).resolve()

    # 检查 ffmpeg 是否存在
    ffmpeg = shutil.which(ffmpeg_path) or (
        Path(ffmpeg_path).resolve() if Path(ffmpeg_path).is_file() else None
    )
    if not ffmpeg:
        raise RuntimeError(
            f"找不到 ffmpeg（已查找: {ffmpeg_path}）。"
            f"请安装 ffmpeg 或通过 --ffmpeg 参数指定路径。"
            f"如果不想合并，可以使用 --no-merge 仅提取分片。"
        )

    # 生成 ffmpeg concat file list
    list_dir = output_path.parent
    list_file = list_dir / "_ykv_filelist.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for seg in segment_files:
            # ffmpeg concat 要求路径转义或使用安全路径
            escaped = str(Path(seg).resolve()).replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")

    cmd = [
        ffmpeg_path,
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_path),
    ]

    logger.info("执行: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg 合并失败 (code={result.returncode}):\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    logger.info("合并完成 → %s", output_path)

    # 清理临时文件
    if list_file.exists():
        list_file.unlink()

    return str(output_path)


class YKVConverter:
    """
    YKV → MP4 转换器。

    Usage:
        converter = YKVConverter(ffmpeg_path="ffmpeg")
        result = converter.convert("video.ykv", "output.mp4")
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    def convert(
        self,
        ykv_path: str | Path,
        output_path: str | Path | None = None,
        keep_segments: bool = False,
        temp_dir: str | Path | None = None,
    ) -> str:
        """
        将单个 YKV 文件转换为 MP4。

        Args:
            ykv_path: 输入的 .ykv 文件路径
            output_path: 输出 .mp4 路径（留空则自动生成）
            keep_segments: 是否保留中间的分片文件
            temp_dir: 临时分片目录（留空自动创建）

        Returns:
            输出 MP4 文件的绝对路径
        """
        ykv_path = Path(ykv_path)
        if not ykv_path.exists():
            raise FileNotFoundError(f"YKV 文件不存在: {ykv_path}")

        if output_path is None:
            output_path = ykv_path.with_suffix(".mp4")
        output_path = Path(output_path)

        if temp_dir is None:
            temp_dir = output_path.parent / f".ykv_temp_{ykv_path.stem}"

        logger.info("开始转换: %s", ykv_path)

        # 1. 读取 YKV 二进制数据
        data = ykv_path.read_bytes()
        logger.info("读取 YKV 文件: %s (%d 字节)", ykv_path.name, len(data))

        # 2. 扫描 ftyp 标记定位分片
        offsets = find_ftyp_offsets(data)
        if not offsets:
            # 检查文件头，判断是不是新版 YKV 格式
            if data[:2] == b"YK":
                raise ValueError(
                    f"该文件是优酷新版 YKV 格式（YK\" 容器），非旧版 ftyp 拼接格式，"
                    f"当前工具暂不支持。\n"
                    f"建议使用优酷客户端直接播放，或搜索商业转码工具。"
                )
            raise ValueError(f"未找到任何 MP4 分片 (ftyp 标记): {ykv_path}")
        logger.info("发现 %d 个 MP4 分片", len(offsets))

        # 3. 提取分片
        segment_files = extract_segments(data, offsets, temp_dir)
        logger.info("提取完成: %d 个分片", len(segment_files))

        try:
            if len(segment_files) == 1:
                # 只有一个分片，直接拷贝（用 copy2 保留 keep_segments 的效果）
                shutil.copy2(segment_files[0], output_path)
                logger.info("单分片，直接拷贝 → %s", output_path)
            else:
                # 多个分片，用 ffmpeg 合并
                merge_segments(segment_files, output_path, self.ffmpeg_path)
        finally:
            # 4. 清理（即使转换失败也要清理 temp 目录）
            if not keep_segments:
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info("清理临时目录: %s", temp_dir)

        return str(output_path.resolve())

    def convert_batch(
        self,
        ykv_paths: List[str | Path],
        output_dir: str | Path | None = None,
        keep_segments: bool = False,
    ) -> List[str]:
        """
        批量转换多个 YKV 文件。

        Args:
            ykv_paths: YKV 文件路径列表
            output_dir: 输出目录（留空则与源文件同目录）
            keep_segments: 是否保留中间分片

        Returns:
            输出 MP4 文件路径列表
        """
        results: List[str] = []
        for ykv in ykv_paths:
            ykv = Path(ykv)
            out = (
                Path(output_dir) / ykv.with_suffix(".mp4").name
                if output_dir
                else None
            )
            result = self.convert(ykv, output_path=out, keep_segments=keep_segments)
            results.append(result)
        return results
