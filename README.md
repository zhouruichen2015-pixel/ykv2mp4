# ykv2mp4

将优酷客户端下载的 `.ykv` 视频文件无损转为标准 `.mp4` 格式。

## 这是什么？

优酷下载的视频是 `.ykv` 格式，普通播放器打不开，也不能剪辑、不能传到别的地方用。  
这个工具能把 `.ykv` **原画质无损** 转成通用的 `.mp4`。

## 快速开始

下面教你从零开始——假设你电脑上**什么都没装**。

---

### 第一步：安装 Python

> 如果已经装了 Python，跳过这步。

1. 打开 https://www.python.org/downloads/
2. 下载 Python 3.11 或更高版本
3. 安装时 **勾选 "Add Python to PATH"**（非常重要！）
4. 安装完成后，打开 PowerShell 验证：
   ```powershell
   python --version
   ```
   应该显示 `Python 3.11.x` 或更高版本

---

### 第二步：安装 ykv2mp4

打开 PowerShell，粘贴以下命令回车：

```powershell
pip install git+https://github.com/zhouruichen2015-pixel/ykv2mp4.git
```

等待安装完成，没有报错即可。  
验证安装：

```powershell
ykv2mp4 --version
```

显示 `ykv2mp4 v0.1.0` 就说明装好了。

---

### 第三步：准备 ffmpeg（可选，推荐）

> 如果 YKV 文件只有 1 个分片，不需要 ffmpeg 也能转。  
> 如果 YKV 文件包含多个分片（大部分情况），需要 ffmpeg 来合并。

**方法一：安装 ffmpeg（推荐）**

1. 打开 https://ffmpeg.org/download.html
2. 找到 Windows 版本下载
3. 解压到 `C:\ffmpeg`
4. 把 `C:\ffmpeg\bin` 添加到系统 PATH（百度搜"Windows 添加环境变量"）
5. 验证：
   ```powershell
   ffmpeg -version
   ```

**方法二：直接用优酷自带的 ffmpeg（最简单）**

如果安装了优酷客户端，工具会自动找到它自带的 ffmpeg，不用额外装任何东西。

---

### 第四步：开始转换

找一个 `.ykv` 文件来试试。

```powershell
# 最简单的用法
ykv2mp4 video.ykv
```

工具会自动查找 ffmpeg，提取所有视频分片，合并成 `video.mp4`。

---

## 完整用法

### 转换单个文件

```powershell
# 直接转（输出到同目录）
ykv2mp4 电影.ykv

# 指定输出路径
ykv2mp4 电影.ykv -o E:/成品/电影.mp4

# 指定 ffmpeg 路径（如果没装到 PATH 里）
ykv2mp4 电影.ykv --ffmpeg C:/ffmpeg/bin/ffmpeg.exe

# 保留中间的分片文件（方便排查问题）
ykv2mp4 电影.ykv --keep-segments
```

### 批量转换

```powershell
# 转换当前目录所有 .ykv
ykv2mp4 *.ykv --output-dir ./成品

# 扫描整个目录及其子目录
ykv2mp4 D:/优酷下载/ -o D:/转好的MP4/

# 同时转多个目录
ykv2mp4 D:/视频1/ D:/视频2/ --output-dir ./输出
```

### 仅提取不合并

如果不用 ffmpeg，可以只把分片提取出来单个播放：

```powershell
ykv2mp4 电影.ykv --no-merge
```

会在同目录生成 `part1.mp4`、`part2.mp4` 等文件。

### 查看详细日志

```powershell
ykv2mp4 电影.ykv -v
```

会显示每个步骤的详细信息，方便排查问题。

### 所有参数一览

```
ykv2mp4 [选项] <YKV文件...>

位置参数:
  input                  YKV 文件路径
                         支持: 文件名、路径、通配符 *.ykv、目录名

选项:
  -o, --output FILE      输出路径（单文件/批量时作为目录）
  --output-dir DIR       批量时的输出目录
  --ffmpeg PATH          指定 ffmpeg.exe 的完整路径
  --no-merge             只提取分片，不合并成单个 MP4
  --keep-segments        保留中间生成的分片文件
  -v, --verbose          显示详细日志
  --version              显示版本号
```

---

## 常见问题

### "找不到 ffmpeg"

- 如果只装了一个 YKV 文件且只有 1 个分片，仍然能转成功
- 如果有多个分片，需要装 ffmpeg（参考上面的第三步）
- 或者用 `--no-merge` 只提取分片

### "YKV 文件不存在"

- 检查文件名是否写对了（Windows 可能隐藏了扩展名）
- 用绝对路径试试：`ykv2mp4 D:\完整\路径\视频.ykv`
- 把文件拖到 PowerShell 窗口会自动补全路径

### "导入错误 / pip 安装失败"

- 确认 Python ≥ 3.10
- 试试手动安装：
  ```powershell
  git clone https://github.com/zhouruichen2015-pixel/ykv2mp4.git
  cd ykv2mp4
  pip install .
  ```

### 转换出来的 MP4 只有一段，没有完整的视频

可能 YKV 包含多个分片，但没装 ffmpeg 导致没有合并。  
安装 ffmpeg 后重新转一遍即可。

---

## 工作原理（不感兴趣可以跳过）

YKV 文件其实没有加密，它只是把多个标准 MP4 片段简单拼接了起来，每个 MP4 片段以 `ftyp` 标记开头。

```
YKV 文件结构:
┌─────────────────────┐
│ [第1段] ftyp ...    │  ← 第一个 MP4 片段
├─────────────────────┤
│ [第2段] ftyp ...    │  ← 第二个 MP4 片段
├─────────────────────┤
│ [第3段] ftyp ...    │  ← 第三个 MP4 片段
└─────────────────────┘

处理过程:
1. 扫描 "ftyp" 标记 → 找到每段的起始位置
2. 按位置切割 → 得到 part1.mp4, part2.mp4, ...
3. ffmpeg 无损合并（-c copy，不重新编码）
4. → 输出最终的完整 output.mp4
```

整个过程**不重新编码**，画质、音质完全不变，等于只是把被拆开的文件重新拼回去。

---

## GitHub Actions 自动转换（给爱折腾的人）

不想装 Python 也可以在 GitHub 云端自动转。

### 方法：手动触发

1. 打开仓库：https://github.com/zhouruichen2015-pixel/ykv2mp4
2. 点 **Actions** → **YKV → MP4 Converter** → **Run workflow**
3. 选择文件来源：
   - **ykv-input**：从仓库目录读取（需要先通过 GitHub 网页上传文件）
   - **latest-release**：从最新 Release 附件读取
4. 选择输出格式
5. 运行完成后，下载生成的 `.mp4` 文件

---

## Python API（给程序员）

```python
from ykv2mp4 import YKVConverter

# 创建转换器
converter = YKVConverter(ffmpeg_path="ffmpeg")

# 单个文件
result = converter.convert("video.ykv", "output.mp4")

# 批量
results = converter.convert_batch(["a.ykv", "b.ykv"], output_dir="./成品")
```

---

## 许可证

MIT
