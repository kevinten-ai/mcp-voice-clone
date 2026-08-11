# mcp-voice-clone

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
  <a href="https://modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP-compatible-green.svg" alt="MCP"></a>
  <img src="https://img.shields.io/badge/version-1.0.0-blue.svg" alt="Version 1.0.0">
</p>

<p align="center">
  <strong>语音克隆与高级 TTS MCP 服务器。</strong><br>
  从音频样本克隆声音，用克隆的声音生成语音，生成音效。<br>
  支持 Claude Code、Claude Desktop、Cursor 及所有 MCP 兼容客户端。
</p>

<p align="center">
  <a href="README.md">English</a>
</p>

## 特性

- **声音克隆** — 从一段音频样本克隆任意声音（Fish Audio + ElevenLabs）
- **高级 TTS** — 用克隆的声音或预设声音生成语音
- **音效生成** — 从文字描述生成音效（ElevenLabs）
- **最佳中文声音克隆** — Fish Audio 中文声音克隆效果极好，价格实惠
- **优质英文语音** — ElevenLabs 提供自然、富有表现力的英文语音
- **灵活切换** — 通过 `provider` 参数每次请求选择最优平台
- **安全自动保存** — MP3 使用微秒级文件名，绝不覆盖已有文件
- **媒体大小门禁** — 克隆样本上限 25 MiB，Provider 音频响应上限 50 MiB
- **请求校验** — TTS 语速、音效时长、文本长度、格式和 Provider 错误在 Schema 与运行时同时受限

## 支持的平台

| 平台 | 能力 | 适用场景 | 价格 | 环境变量 |
|---|---|---|---|---|
| **Fish Audio** | 声音克隆、TTS | 中文声音克隆 | 约 ¥0.07/次 | `FISH_AUDIO_API_KEY` |
| **ElevenLabs** | 声音克隆、TTS、音效 | 英文 TTS、音效生成 | 免费额度 + 付费 | `ELEVENLABS_API_KEY` |

### 平台选择指南

```
需要声音克隆？
  ├─ 中文声音？
  │   └─ fish-audio ✅（中文克隆最佳，价格实惠）
  │
  ├─ 英文声音？
  │   └─ elevenlabs ✅（优质品质，自然音色）
  │
  └─ 需要音效？
      └─ elevenlabs（文字描述生成音效）
```

## 快速开始

### 1. 克隆 & 安装

```bash
git clone https://github.com/kevinten-ai/mcp-voice-clone.git
cd mcp-voice-clone
uv sync
```

### 2. 使用 Codex 任务 Profile

本地服务器默认注册但禁用。按任务启动一个只启用语音能力的新 Codex 会话：

```bash
codex-mcp run voice -- --cd /path/to/project
```

Profile 只影响新会话，不会修改 Codex 基础配置。Provider Key 应保存在已注册的
本地服务器配置中，不要写入仓库文件或命令历史。

### 3. 兼容客户端配置

只需配置你要使用的平台，至少配置一个。

<details>
<summary><b>Claude Code（命令行）— 推荐</b></summary>

```bash
# 仅 Fish Audio（中文声音克隆）
claude mcp add -s user mcp-voice-clone \
  --env FISH_AUDIO_API_KEY=你的key \
  -- uv --directory /path/to/mcp-voice-clone run voice-clone

# 仅 ElevenLabs（英文 TTS + 音效）
claude mcp add -s user mcp-voice-clone \
  --env ELEVENLABS_API_KEY=你的key \
  -- uv --directory /path/to/mcp-voice-clone run voice-clone

# 两个平台都用（全部功能）
claude mcp add -s user mcp-voice-clone \
  --env FISH_AUDIO_API_KEY=你的fish_key \
  --env ELEVENLABS_API_KEY=你的elevenlabs_key \
  -- uv --directory /path/to/mcp-voice-clone run voice-clone
```

</details>

<details>
<summary><b>Claude Desktop / Cursor（JSON 配置）</b></summary>

```json
{
  "mcpServers": {
    "mcp-voice-clone": {
      "command": "uv",
      "args": ["--directory", "/path/to/mcp-voice-clone", "run", "voice-clone"],
      "env": {
        "FISH_AUDIO_API_KEY": "你的fish_key",
        "ELEVENLABS_API_KEY": "你的elevenlabs_key"
      }
    }
  }
}
```

</details>

### 4. 使用

克隆声音并生成语音：

```
"从 /path/to/sample.mp3 克隆声音，命名为'我的声音'"
"用'我的声音'说'大家好，这是声音克隆的测试'"
"生成一段雷鸣的音效"
```

## 工具说明（共 5 个）

### 声音克隆
- **clone_voice** — 从音频样本克隆声音。参数：`audio_path`（必填）、`name`（必填）、`description`、`provider`（fish-audio/elevenlabs）。返回 voice_id 用于 `speak`。

### 语音
- **speak** — 用克隆声音或预设声音生成语音。参数：`text`（必填，最多 10,000 字符）、`voice_id`（必填）、`provider`、`speed`（0.7-1.2）、`output_path`（只能是新的 `.mp3`）。
- **list_voices** — 列出平台可用的声音。参数：`provider`（fish-audio/elevenlabs）。

### 音效
- **generate_sfx** — 从文字描述生成音效。参数：`prompt`（必填，最多 2,000 字符）、`duration`（0.5-30 秒）、`output_path`（只能是新的 `.mp3`）。平台：ElevenLabs。

### 工具
- **list_providers** — 列出所有已配置的声音克隆、TTS、音效平台。

## API Key 注册指南

<details>
<summary><b>1. Fish Audio — 最佳中文声音克隆</b></summary>

| 项目 | 详情 |
|---|---|
| 平台 | Fish Audio |
| 网址 | https://fish.audio |
| 价格 | 非常实惠，约 ¥0.07/次 |
| 环境变量 | `FISH_AUDIO_API_KEY` |

**步骤：**
1. 访问 https://fish.audio → 注册
2. 进入 **API Keys**：https://fish.audio/account/api-keys
3. 点击 "Create API Key" → 复制
4. 创建权限尽可能小的专用 Key，并在本地 MCP 配置中设置 `FISH_AUDIO_API_KEY`

**声音克隆技巧：**
- 上传 10-30 秒的清晰音频样本效果最好
- 单声道音频比立体声效果好
- 尽量减少样本中的背景噪音
- 支持 MP3、WAV、FLAC、M4A 格式

</details>

<details>
<summary><b>2. ElevenLabs — 优质英文 TTS + 音效</b></summary>

| 项目 | 详情 |
|---|---|
| 平台 | ElevenLabs |
| 网址 | https://elevenlabs.io |
| 免费额度 | 每月 10,000 字符 |
| 环境变量 | `ELEVENLABS_API_KEY` |

**步骤：**
1. 访问 https://elevenlabs.io → 注册
2. 进入 **Profile + API Key**：https://elevenlabs.io/app/settings/api-keys
3. 点击 "Create API Key" → 复制
4. 创建仅允许所需语音能力的受限 Key，并在本地 MCP 配置中设置 `ELEVENLABS_API_KEY`

**功能：**
- 从短音频样本即时克隆声音（付费方案）
- 支持 29+ 种语言
- 从文字描述生成音效
- 免费额度可使用高品质预设声音

</details>

## 环境变量

| 变量 | 平台 | 说明 |
|---|---|---|
| `FISH_AUDIO_API_KEY` | Fish Audio（声音克隆 + TTS） | 至少配置 |
| `ELEVENLABS_API_KEY` | ElevenLabs（TTS + 克隆 + 音效） | 一个平台 |
| `AUDIO_OUTPUT_DIR` | 输出目录 | 可选，默认 `./output` |

## 常见问题排查

### 通用错误

| 错误 | 根因 | 解决方案 |
|---|---|---|
| `No providers configured` | 没设置任何 API Key | 至少设置一个 API Key |
| `Unknown provider` | 拼写错误或平台未配置 | 用 `list_providers` 查看可用选项 |
| `Audio file not found` | audio_path 无效 | 检查文件路径是否存在且可访问 |
| `Output file already exists` | 输出会覆盖已有文件 | 选择新的 `.mp3` 路径，或由用户明确删除旧文件 |
| `Unsupported audio sample format` | 克隆样本格式不支持 | 使用 MP3、WAV、FLAC、OGG、M4A、AAC 或 WebM |
| `Audio sample is too large` | 样本超过本地 25 MiB 安全上限 | 克隆前裁剪或压缩样本 |
| `Provider response is too large` | 生成音频超过 50 MiB 上限 | 缩短文本或生成时长 |

### 平台特定错误

| 错误 | 平台 | 解决方案 |
|---|---|---|
| `HTTP 401` | Fish Audio | 检查 `FISH_AUDIO_API_KEY` 是否有效 |
| `HTTP 401` | ElevenLabs | 检查 `ELEVENLABS_API_KEY` 是否有效 |
| `HTTP 422` | Fish Audio | 音频格式不支持或文件过大 |
| `quota_exceeded` | ElevenLabs | 免费额度用尽，升级方案或等待重置 |
| `voice_not_found` | 两者 | voice_id 无效，用 `list_voices` 检查 |

### 使用技巧

- **Fish Audio** 的中文声音克隆成本远低于 ElevenLabs
- **ElevenLabs** 免费额度包含每月 10,000 字符 TTS 和预设声音
- **声音克隆**效果很大程度取决于音频样本质量 — 使用清晰、干净的录音
- **音效生成**接受自然语言描述，描述越具体效果越好
- 自定义输出只能使用 `.mp3`，且不能指向已有文件；输出冲突会在可能计费的 Provider 请求前被拒绝。
- Provider 音频采用流式读取并限制为 50 MiB；JSON 元数据和错误预览同样有大小边界。

## 项目结构

```
src/voice_clone/
├── __init__.py
├── __main__.py
├── server.py              # MCP 服务器 + 工具定义
└── providers/
    ├── __init__.py        # 基类（BaseTTSProvider、BaseVoiceCloningProvider、BaseSFXProvider）+ 注册机制
    ├── fish_audio.py      # Fish Audio — 中文声音克隆 + TTS
    └── elevenlabs.py      # ElevenLabs — 英文 TTS + 声音克隆 + 音效
```

### 添加新平台

1. 创建 `src/voice_clone/providers/your_provider.py`
2. 实现相关基类：`BaseTTSProvider`、`BaseVoiceCloningProvider` 或 `BaseSFXProvider`
3. 在 `server.py:_init_providers()` 中注册，通过环境变量控制启用
4. 新平台自动出现在工具和 `list_providers` 中

## 本地开发

```bash
git clone https://github.com/kevinten-ai/mcp-voice-clone.git
cd mcp-voice-clone
uv sync

# 直接运行
uv run voice-clone

# MCP Inspector 调试
npx @modelcontextprotocol/inspector uv --directory . run voice-clone
```

## 相关媒体工作流

图片生成、图片编辑和视频生成默认使用 AnyCap CLI，图片/视频 MCP 仅用于兼容测试。
只有代理推理过程中确实需要声音克隆、TTS、声音查询或音效生成时，才通过 `voice` Profile 启用本 MCP。

## 许可证

MIT — 详见 [LICENSE](LICENSE)。
