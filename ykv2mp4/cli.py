"""
ykv2mp4 CLI — 命令行入口。

Usage:
    # 基本转换（自动寻找 ffmpeg）
    ykv2mp4 video.ykv

    # 指定输出路径
    ykv2mp4 video.ykv -o output.mp4

    # 批量转换
    ykv2mp4 *.ykv --output-dir ./mp4

    # 保留中间分片文件
    ykv2mp4 video.ykv --keep-segments

    # 指定 ffmpeg 路径
    ykv2mp4 video.ykv --ffmpeg D:/tools/ffmpeg.exe

    # 不合并（仅提取分片）
    ykv2mp4 video.ykv --no-merge
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .converter import YKVConverter, find_ftyp_offsets, extract_segments


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def check_ffmpeg(ffmpeg_path: str) -> bool:
    """检测 ffmpeg 是否可用。"""
    import shutil
    resolved = shutil.which(ffmpeg_path) or (
        Path(ffmpeg_path).resolve() if Path(ffmpeg_path).exists() else None
    )
    if resolved:
        return True
    return False


def find_ffmpeg_in_youku() -> Optional[str]:
    """尝试在优酷客户端目录下找到自带的 ffmpeg。"""
    candidates = [
        r"C:\Program Files (x86)\YouKu\YoukuClient\nplayer\ffmpeg.exe",
        r"C:\Program Files\YouKu\YoukuClient\nplayer\ffmpeg.exe",
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    return None


def gather_ykv_files(paths: List[str]) -> List[Path]:
    """收集要转换的 YKV 文件（支持通配符后的展开）。"""
    files: List[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_file() and path.suffix.lower() == ".ykv":
            files.append(path.resolve())
        elif path.is_dir():
            files.extend(sorted(Path(path).rglob("*.ykv")))
    return files


def run_no_merge(ykv_path: Path, output_dir: Path):
    """仅提取分片，不合并。"""
    logger = logging.getLogger("ykv2mp4")
    data = ykv_path.read_bytes()
    offsets = find_ftyp_offsets(data)
    if not offsets:
        logger.error("未找到 MP4 分片: %s", ykv_path)
        return
    logger.info("发现 %d 个分片", len(offsets))
    segments = extract_segments(data, offsets, output_dir)
    logger.info("已提取 %d 个分片到 %s", len(segments), output_dir)


def main():
    parser = argparse.ArgumentParser(
        prog="ykv2mp4",
        description="优酷 YKV 视频无损转 MP4 工具",
        epilog="示例: ykv2mp4 video.ykv -o output.mp4 --ffmpeg D:/ffmpeg/bin/ffmpeg.exe",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "input",
        nargs="+",
        help="YKV 文件路径（支持通配符 *.ykv 和目录扫描）",
    )
    parser.add_argument(
        "-o", "--output",
        help="输出文件路径（单文件时有效，批量时作为目录）",
    )
    parser.add_argument(
        "--output-dir",
        help="输出目录（批量转换时使用）",
    )
    parser.add_argument(
        "--ffmpeg",
        help="ffmpeg 可执行文件路径（默认自动查找）",
    )
    parser.add_argument(
        "--no-merge",
        action="store_true",
        help="仅提取分片 MP4，不合并",
    )
    parser.add_argument(
        "--keep-segments",
        action="store_true",
        help="保留中间分片文件",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细日志输出",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"ykv2mp4 v{__version__}",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger("ykv2mp4")

    # 收集 YKV 文件
    files = gather_ykv_files(args.input)
    if not files:
        logger.error("未找到任何 .ykv 文件")
        sys.exit(1)

    logger.info("找到 %d 个 YKV 文件", len(files))

    # 处理 ffmpeg 路径
    ffmpeg_path = args.ffmpeg or os.environ.get("YKV_FFMPEG_PATH") or "ffmpeg"
    has_ffmpeg = check_ffmpeg(ffmpeg_path)

    if not has_ffmpeg:
        # 尝试优酷自带的 ffmpeg
        youku_ffmpeg = find_ffmpeg_in_youku()
        if youku_ffmpeg:
            ffmpeg_path = youku_ffmpeg
            has_ffmpeg = True
            logger.info("使用优酷自带 ffmpeg: %s", ffmpeg_path)

    if not has_ffmpeg:
        logger.warning(
            "未找到 ffmpeg，多分片文件将无法合并。"
            "请安装 ffmpeg 或通过 --ffmpeg 指定路径。"
        )

    converter = YKVConverter(ffmpeg_path=ffmpeg_path if has_ffmpeg else "ffmpeg")

    # 单文件转换
    if len(files) == 1 and not args.output_dir:
        ykv = files[0]

        if args.no_merge:
            out_dir = Path(args.output) if args.output else ykv.parent
            run_no_merge(ykv, Path(out_dir))
            return

        out_path = args.output or None  # None = 自动生成
        try:
            result = converter.convert(
                ykv,
                output_path=str(out_path) if out_path else None,
                keep_segments=args.keep_segments,
            )
            logger.info("✅ 转换完成: %s", result)
        except Exception as e:
            logger.error("❌ 转换失败: %s", e)
            sys.exit(1)

    # 批量转换
    else:
        out_dir = args.output_dir or args.output or "./converted"
        Path(out_dir).mkdir(parents=True, exist_ok=True)

        success = 0
        fail = 0

        for ykv in files:
            try:
                if args.no_merge:
                    seg_dir = Path(out_dir) / ykv.stem
                    run_no_merge(ykv, seg_dir)
                else:
                    out_path = Path(out_dir) / ykv.with_suffix(".mp4").name
                    converter.convert(
                        ykv,
                        output_path=str(out_path),
                        keep_segments=args.keep_segments,
                    )
                success += 1
                logger.info("✅ [%d/%d] %s", success + fail, len(files), ykv.name)
            except Exception as e:
                fail += 1
                logger.error("❌ [%d/%d] %s — %s", success + fail, len(files), ykv.name, e)

        logger.info("批量转换完成: %d 成功, %d 失败", success, fail)


if __name__ == "__main__":
    main()
