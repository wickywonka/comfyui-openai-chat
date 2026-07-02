# ComfyUI OpenAI Chat Completion

一个 ComfyUI 自定义节点，使用 OpenAI API 兼容协议进行文本和图片的多模态对话，支持思考模式。

## 功能特性

- ✅ OpenAI API 兼容协议
- ✅ 支持文本和图片输入（多模态）
- ✅ 可选的高级参数控制
- ✅ 智能缓存机制
- ✅ 思考模式支持（off/low/medium/high）
- ✅ 思考内容自动提取
- ✅ 三个输出端口：完整内容、过滤后内容、思考内容

## 输入参数

### 基础参数
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| Base URL | String | `https://api.openai.com/v1` | API 基础 URL |
| API Key | String | `-` | API 密钥，不需要时留空 |
| Model | String | `gpt-4o` | 模型名称 |
| System Prompt | String | - | 系统提示词（可选） |
| Prompt | String | - | 用户提示词 |
| Images | Image | - | 可选的图像输入 |

### 控制参数
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| Enable Advanced Params | Boolean | `False` | 启用高级参数开关 |
| Force Regen | Boolean | `False` | 强制重新生成（禁用缓存） |

### 高级参数（需启用开关）
| 参数 | 类型 | 默认值 | 范围 | 说明 |
|------|------|--------|------|------|
| Temperature | Float | `1.0` | 0.0-2.0 | 温度参数，控制随机性 |
| Seed | Int | `42` | 0-2147483647 | 随机种子 |
| Top K | Int | `0` | 0-1000 | Top-K 采样参数 |
| Top P | Float | `1.0` | 0.0-1.0 | Top-P 采样参数 |
| Min P | Float | `0.0` | 0.0-1.0 | 最小概率阈值 |
| Max Tokens | Int | `512` | 1-1000000 | 最大输出 token 数 |
| Repetition Penalty | Float | `1.0` | 0.0-5.0 | 重复惩罚 |
| Presence Penalty | Float | `0.0` | -2.0-2.0 | 存在惩罚 |

### 思考模式
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| Thinking Mode | Combo | `off` | 思考模式：off/low/medium/high |
| Thinking Tag | String | ` ``` ` | 思考标签模式，用于提取思考内容 |

## 输出参数

| 端口 | 类型 | 说明 |
|------|------|------|
| Full Content | String | 模型完整响应（包含思考内容） |
| Content | String | 过滤掉思考后的纯内容 |
| Thinking | String | 提取的思考内容 |

## 缓存机制

节点内置智能缓存机制：

- **默认行为**：当输入参数不变时，使用上次结果，不重新调用 API
- **强制重新生成**：启用 `Force Regen` 开关时，每次都会重新调用 API

### 工作原理
- `force_regen=False`：返回输入内容的哈希作为缓存键，相同输入使用缓存
- `force_regen=True`：返回时间戳作为缓存键，强制重新生成

## 支持的思考标签格式

节点支持自动提取以下思考标签格式：

- **DeepSeek/Qwen3**: `<think>\n...\n</think>\n`
- **Claude**: `</think>\n...\n</think>`
- **自定义标签**: 通过 `Thinking Tag` 参数配置

## 使用示例

### 基础文本对话
```
1. 设置 Base URL 和 API Key
2. 选择模型（如 gpt-4o）
3. 输入 Prompt
4. 点击生成
```

### 多模态对话（带图片）
```
1. 连接图像输入到 Images 端口
2. 输入 Prompt（描述图片内容或提问）
3. 点击生成
```

### 使用思考模式
```
1. 设置 Thinking Mode 为 high（或其他级别）
2. 输入 Prompt
3. 三个输出端口分别获取：
   - Full Content: 完整响应
   - Content: 过滤后的回答
   - Thinking: 模型的思考过程
```

### 精确控制采样参数
```
1. 启用 Enable Advanced Params
2. 设置 Temperature、Top P 等参数
3. 点击生成
```

## 兼容性

- ✅ OpenAI API (api.openai.com)
- ✅ Ollama
- ✅ vLLM
- ✅ TGI (Text Generation Inference)
- ✅ 其他 OpenAI API 兼容服务

## 依赖项

```
numpy>=1.25.0
Pillow
```

**无需额外依赖**：使用标准库的 `urllib` 发送 HTTP 请求，无需安装 openai 库。

## 安装

1. 将 `comfyui-openai-chat` 文件夹放入 ComfyUI 的 `custom_nodes` 目录
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 重启 ComfyUI

## 注意事项

- 当 `Enable Advanced Params` 关闭时，高级参数（温度、种子、采样等）不会传递给 API
- 思考模式参数 `thinking_mode` 始终生效，不受 `Enable Advanced Params` 控制
- 使用本地部署的推理服务时，确保服务支持 OpenAI API 格式
- 部分参数（如 `top_k`、`min_p`、`repetition_penalty`）需要通过 `extra_body` 传递，兼容性取决于 API 服务端

## 许可证

MIT License
