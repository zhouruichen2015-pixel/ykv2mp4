# ykv2mp4 🚀

将优酷客户端下载的 `.ykv` 格式视频**无损**转为标准 MP4。

YKV 是优酷的私有格式，但其实只是把多个标准 MP4 片段简单拼接在了一起。  
本工具通过扫描 `ftyp` 标记定位每个 MP4 分片，提取出来后用 ffmpeg 无损合并（`-c copy`，不重新编码），**画质零损失**。

## 快速开始

### 安装

```bash
# pip 安装
pip install ykv2mp4

# 或者克隆仓库直接运行
pip install git+https://github.com/zhouruichen2015-pixel/ykv2mp4.git

# 或者克隆仓库
git clone https://github.com/zhouruichen2015-pixel/ykv2mp4.git
cd ykv2mp4
pip install .
```

### 转换一个文件

```bash
ykv2mp4 video.ykv
```

自动在同目录生成 `video.mp4`。

### 指定 ffmpeg 路径

```bash
ykv2mp4 video.ykv --ffmpeg D:/tools/ffmpeg/bin/ffmpeg.exe
```

> 💡 如果安装了优酷客户端，工具会自动检测优酷自带的 ffmpeg。

## 完整用法

```
ykv2mp4 [选项] <YKV文件...>

位置参数:
  input                  YKV 文件路径（支持通配符 *.ykv 和目录扫描）

选项:
  -o, --output FILE      输出文件/目录
  --output-dir DIR       输出目录（批量时使用）
  --ffmpeg PATH          指定 ffmpeg 路径
  --no-merge             仅提取 MP4 分片，不合并
  --keep-segments        保留中间分片文件
  -v, --verbose          详细日志
  --version              显示版本号
```

### 示例

```bash
# 批量转换
ykv2mp4 *.ykv --output-dir ./mp4

# 扫描整个目录
ykv2mp4 ./videos/ -o ./converted

# 仅提取分片（方便调试）
ykv2mp4 video.ykv --no-merge

# 保留中间文件
ykv2mp4 video.ykv --keep-segments
```

## GitHub Actions 自动化

本仓库包含一个完整的 GitHub Actions 工作流，支持：

### 方式一：手动触发

1. 把 `.ykv` 文件放到仓库的 `ykv-input/` 目录并推送
2. 去 **Actions** → **YKV → MP4 Converter** → **Run workflow**
3. 下载生成的 MP4 Artifact

### 方式二：推送自动转换

把 `.ykv` 文件推送到 `ykv-input/` 目录，工作流自动触发，转换结果上传为 Artifact。

### 方式三：Release 集成

发布 Release 时，如果附件包含 `.ykv` 文件，自动转换并上传 MP4 到同一 Release。

## 工作原理

```
.YKV 文件
  │
  ├── [box_len:4B] [ftyp:4B] [MP4数据]  ← 分片 1
  ├── [box_len:4B] [ftyp:4B] [MP4数据]  ← 分片 2
  ├── [box_len:4B] [ftyp:4B] [MP4数据]  ← 分片 3
  └── ...
        │
        ▼
  扫描 "ftyp" → 回溯4字节 → 定位每个分片起始位置
        │
        ▼
  提取为 part1.mp4, part2.mp4, ...
        │
        ▼
  ffmpeg concat 无损合并（-c copy）
        │
        ▼
  output.mp4 ✅
```

- 不重新编码，画质无损
- 只需 ffmpeg 一个外部依赖
- 支持单分片（直接拷贝）和多分片（ffmpeg 合并）

## 依赖

- **Python ≥ 3.10**
- **ffmpeg**（可选，单分片不需要，多分片合并必选）
  - 可通过 `--ffmpeg` 参数指定路径
  - 会自动检测优酷客户端自带的 ffmpeg

## Python API

也可作为库使用：

```python
from ykv2mp4 import YKVConverter

# 单文件
converter = YKVConverter(ffmpeg_path="ffmpeg")
result = converter.convert("video.ykv", "output.mp4")

# 批量
results = converter.convert_batch(["a.ykv", "b.ykv"], output_dir="./mp4s")
```

## 许可证

MIT
