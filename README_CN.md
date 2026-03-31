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
- **自动保存** — 生成的音频自动保存到本地

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

### 2. 配置 MCP

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

### 3. 使用

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
- **speak** — 用克隆的声音或预设声音生成语音。参数：`text`（必填）、`voice_id`（必填）、`provider`（fish-audio/elevenlabs）、`speed`（0.5-2.0）、`output_path`。
- **list_voices** — 列出平台可用的声音。参数：`provider`（fish-audio/elevenlabs）。

### 音效
- **generate_sfx** — 从文字描述生成音效。参数：`prompt`（必填）、`duration`（秒数）、`output_path`。平台：ElevenLabs。

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
4. 在 MCP 配置中设置 `FISH_AUDIO_API_KEY`

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
4. 在 MCP 配置中设置 `ELEVENLABS_API_KEY`

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

## 相关项目

- [mcp-video-gen](https://github.com/kevinten-ai/mcp-video-gen) — AI 视频生成 MCP 服务器（7 个平台）
- [mcp-image-gen](https://github.com/kevinten-ai/mcp-image-gen) — AI 图片生成 MCP 服务器（Gemini + Imagen）
- [mcp-3d-gen](https://github.com/kevinten-ai/mcp-3d-gen) — AI 3D 模型生成 MCP 服务器

## 许可证

MIT — 详见 [LICENSE](LICENSE)。
