# ComfyUI OpenAI Chat Completion

一个 ComfyUI 自定义节点，使用 OpenAI API 兼容协议进行文本和图片的多模态对话，支持思考模式。

## 功能特性

- ✅ OpenAI API 兼容协议（支持 OpenAI、Ollama、vLLM、TGI 等）
- ✅ 支持文本和图片输入（多模态）
- ✅ System Prompt 和 Prompt 紧邻排列，方便使用
- ✅ 可选的高级参数控制（温度、种子、采样参数等）
- ✅ 智能缓存机制
- ✅ 思考模式开关（Enable Thinking）
- ✅ 思考内容自动提取
- ✅ Debug 模式：打印 HTTP 请求和响应到控制台

## 输入参数

### 基础参数
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| Base URL | String | `https://api.openai.com/v1` | API 基础 URL |
| API Key | String | `-` | API 密钥，不需要时留空 |
| Model | String | `gpt-4o` | 模型名称 |
| System Prompt | String | `""`（空） | 系统提示词，留空不使用 |
| Prompt | String | - | 用户提示词 |
| Images | Image | - | 可选的图像输入（多模态） |

### 控制参数
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| Enable Advanced Params | Combo | `禁用` | 启用/禁用高级参数 |
| Force Regen | Boolean | `False` | 强制重新生成（禁用缓存） |
| Enable Thinking | Boolean | `False` | 启用思考模式 |
| Debug Mode | Boolean | `False` | 在控制台打印 HTTP 请求和响应 |
| Passthrough | Boolean | `False` | 绕过 API 调用，直接将提示词透传到 content 输出 |

### 高级参数（需启用 Enable Advanced Params）
| 参数 | 类型 | 默认值 | 范围 | 说明 |
|------|------|--------|------|------|
| Temperature | Float | `1.0` | 0.0–2.0 | 控制随机性 |
| Seed | Int | `42` | 0–2147483647 | 随机种子 |
| Top K | Int | `0` | 0–1000 | Top-K 采样参数 |
| Top P | Float | `1.0` | 0.0–1.0 | Top-P 采样参数 |
| Min P | Float | `0.0` | 0.0–1.0 | 最小概率阈值 |
| Max Tokens | Int | `512` | 1–1000000 | 最大输出 token 数 |
| Repetition Penalty | Float | `1.0` | 0.0–5.0 | 重复惩罚 |
| Presence Penalty | Float | `0.0` | -2.0–2.0 | 存在惩罚 |
| Thinking Tag | String | `` ``` `` | - | 思考标签模式，用于提取思考内容 |

## 输出参数

| 端口 | 类型 | 说明 |
|------|------|------|
| Content | String | 过滤掉思考后的内容 |
| Full Content | String | 模型完整响应（包含思考内容） |

## 缓存机制

节点内置智能缓存机制：

- **默认行为**：当输入参数不变时，使用上次结果，不重新调用 API
- **强制重新生成**：启用 `Force Regen` 开关时，每次都会重新调用 API

### 工作原理
- `force_regen=False`：返回输入内容的哈希作为缓存键，相同输入使用缓存
- `force_regen=True`：返回时间戳作为缓存键，强制重新生成

## Passthrough 模式

启用 `Passthrough` 后，节点跳过 API 调用，直接将 `Prompt` 内容原样输出到 `Content` 和 `Full Content`。
适用于：
- 临时调试工作流
- 需要保持连接但不想调用 API
- 作为 bypass 替代方案（即使节点被执行，也不会产生 API 费用）

## 思考模式

启用 `Enable Thinking` 后，会向 API 传递 `chat_template_kwargs.enable_thinking: true` 参数，用于支持某些模型的 extended thinking 功能。

- 当 `Enable Thinking = false` 时，仍然显式传递 `enable_thinking: false`，确保 API 明确知晓意图
- 思考内容自动提取：结果中会过滤掉模型返回的思考内容，分别从 `Content` 和 `Full Content` 端口输出

## 支持的思考标签格式

节点支持自动提取以下思考标签格式：

- **DeepSeek / Qwen3**: `<think>\n...\n</think>`
- **Claude**: `</think>\n...\n</think>`
- **自定义标签**: 通过高级参数中的 `Thinking Tag` 配置

## 使用示例

### 基础文本对话
```
1. 设置 Base URL 和 API Key
2. 选择模型（如 gpt-4o）
3. 可选：输入 System Prompt
4. 输入 Prompt
5. 点击生成
```

### 多模态对话（带图片）
```
1. 连接图像输入到 Images 端口
2. 输入 Prompt（描述图片内容或提问）
3. 点击生成
```

### 使用思考模式
```
1. 启用 Enable Thinking
2. 输入 Prompt
3. 两个输出端口分别获取：
   - Content: 过滤后的回答
   - Full Content: 完整响应（含思考内容）
```

## 兼容性

- ✅ OpenAI API (api.openai.com)
- ✅ Ollama
- ✅ vLLM
- ✅ TGI (Text Generation Inference)
- ✅ LM Studio
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
- `Enable Thinking` 参数始终显式传递（true 或 false），不受 `Enable Advanced Params` 控制
- System Prompt 留空时不会添加到请求中
- 使用本地部署的推理服务时，确保服务支持 OpenAI API 格式
- 部分参数（如 `top_k`、`min_p`、`repetition_penalty`）需要通过 `extra_body` 传递，兼容性取决于 API 服务端

## 许可证

MIT License
