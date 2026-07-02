import base64
import json
import re
import time
import urllib.request
import urllib.error
import urllib.parse
from io import BytesIO
from typing import Any

import torch
import numpy as np
from PIL import Image

from comfy_api.latest import io, ui


def comfy_image_to_base64_png_url(image: torch.Tensor) -> str:
    """将 ComfyUI 图像张量转换为 base64 PNG URL"""
    i = np.multiply(255., image.cpu().numpy())
    img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    b64_png = base64.b64encode(buffer.getvalue())
    return f"data:image/png;base64,{b64_png.decode('utf-8')}"


def extract_thinking_content(content: str, pattern: str = "```") -> tuple[str, str]:
    """
    从模型响应中提取思考内容
    
    支持多种思考标签格式:
    - DeepSeek/Qwen3: <think>\n...\n</think>\n
    - Claude: ...
    - 自定义标签: ```
    
    返回: (完整内容，思考内容)
    """
    if not content:
        return "", ""
    
    # 尝试匹配不同类型的思考标签
    thinking_patterns = [
        # DeepSeek/Qwen3 格式：<think>\n...\n</think>
        (r'<think>\n(.*?)</think>', re.DOTALL),
        # Claude 格式：...\n...\n...
        (r'</think>\n(.*?)</think>', re.DOTALL),
        # 通用代码块格式：```...```
        (r'`{3,}\w*\n(.*?)`{3,}', re.DOTALL),
    ]
    
    for regex, flags in thinking_patterns:
        match = re.search(regex, content, flags)
        if match:
            thinking = match.group(1).strip()
            # 移除思考标签，保留其他内容
            cleaned = re.sub(regex, '', content, flags=flags).strip()
            return cleaned, thinking
    
    # 如果没有找到思考标签，返回原始内容和空思考
    return content, ""


def openai_chat_completion(
    base_url: str,
    api_key: str | None,
    model: str,
    messages: list[dict],
    temperature: float | None = None,
    seed: int | None = None,
    max_tokens: int | None = None,
    top_p: float | None = None,
    presence_penalty: float | None = None,
    extra_body: dict[str, Any] | None = None,
    n: int = 1,
) -> dict[str, Any]:
    """
    使用 urllib 发送 OpenAI API 请求
    
    返回完整的响应字典
    """
    # 构建请求体
    request_body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "n": n,
    }
    
    # 添加可选参数
    if temperature is not None:
        request_body["temperature"] = temperature
    if seed is not None:
        request_body["seed"] = seed
    if max_tokens is not None:
        request_body["max_tokens"] = max_tokens
    if top_p is not None:
        request_body["top_p"] = top_p
    if presence_penalty is not None:
        request_body["presence_penalty"] = presence_penalty
    if extra_body:
        request_body.update(extra_body)
    
    # 构建请求头
    headers = {
        "Content-Type": "application/json",
    }
    if api_key and api_key != "-":
        headers["Authorization"] = f"Bearer {api_key}"
    
    # 构建请求
    url = f"{base_url.rstrip('/')}/chat/completions"
    data = json.dumps(request_body).encode('utf-8')
    
    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST"
    )
    
    # 发送请求
    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            response_data = json.loads(response.read().decode('utf-8'))
            return response_data
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise Exception(f"API 请求失败 [{e.code}]: {error_body}")
    except urllib.error.URLError as e:
        raise Exception(f"API 连接失败：{e.reason}")
    except Exception as e:
        raise Exception(f"API 请求异常：{str(e)}")


class OpenAIChatCompletion(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="OpenAIChatCompletion",
            display_name="OpenAI Chat Completion",
            category="OpenAI",
            description="使用 OpenAI API 兼容协议进行文本和图片的多模态对话，支持思考模式",
            inputs=[
                # 基础配置
                io.String.Input(
                    id="base_url",
                    display_name="Base URL",
                    tooltip="API 基础 URL",
                    placeholder="https://api.openai.com/v1",
                    default="https://api.openai.com/v1",
                ),
                io.String.Input(
                    id="api_key",
                    display_name="API Key",
                    optional=True,
                    tooltip="API 密钥，不需要时留空",
                    placeholder="sk-...",
                    default="-",
                ),
                io.String.Input(
                    id="model",
                    display_name="Model",
                    tooltip="模型名称",
                    placeholder="gpt-4o",
                    default="gpt-4o",
                ),
                # 提示词（System Prompt 和 Prompt 相邻排列）
                io.String.Input(
                    id="system_prompt",
                    display_name="System Prompt",
                    tooltip="系统提示词（留空表示不使用）",
                    multiline=True,
                    placeholder="You are a helpful assistant.",
                    default="",
                ),
                io.String.Input(
                    id="prompt",
                    display_name="Prompt",
                    tooltip="用户提示词",
                    multiline=True,
                    placeholder="请帮我写一首诗...",
                ),
                # 图像输入
                io.Image.Input(
                    id="images",
                    display_name="Images",
                    optional=True,
                    tooltip="可选的图像输入",
                ),
                # 高级参数
                io.DynamicCombo.Input(
                    id="enable_advanced_params",
                    display_name="Enable Advanced Params",
                    tooltip="启用高级参数（温度、种子、采样等）",
                    options=[
                        io.DynamicCombo.Option(
                            "启用",
                            [
                                io.Float.Input(
                                    id="temperature",
                                    display_name="Temperature",
                                    tooltip="温度参数，控制随机性",
                                    default=1.0,
                                    min=0.0,
                                    max=2.0,
                                    step=0.1,
                                    display_mode=io.NumberDisplay.number,
                                ),
                                io.Int.Input(
                                    id="seed",
                                    display_name="Seed",
                                    tooltip="随机种子",
                                    default=42,
                                    min=0,
                                    max=2147483647,
                                    control_after_generate=False,
                                    display_mode=io.NumberDisplay.number,
                                ),
                                io.Int.Input(
                                    id="top_k",
                                    display_name="Top K",
                                    tooltip="Top-K 采样参数",
                                    default=0,
                                    min=0,
                                    max=1000,
                                    display_mode=io.NumberDisplay.number,
                                ),
                                io.Float.Input(
                                    id="top_p",
                                    display_name="Top P",
                                    tooltip="Top-P 采样参数",
                                    default=1.0,
                                    min=0.0,
                                    max=1.0,
                                    step=0.01,
                                    display_mode=io.NumberDisplay.number,
                                ),
                                io.Float.Input(
                                    id="min_p",
                                    display_name="Min P",
                                    tooltip="最小概率阈值",
                                    default=0.0,
                                    min=0.0,
                                    max=1.0,
                                    step=0.01,
                                    display_mode=io.NumberDisplay.number,
                                ),
                                io.Int.Input(
                                    id="max_tokens",
                                    display_name="Max Tokens",
                                    tooltip="最大输出 token 数",
                                    default=512,
                                    min=1,
                                    max=1000000,
                                    display_mode=io.NumberDisplay.number,
                                ),
                                io.Float.Input(
                                    id="repetition_penalty",
                                    display_name="Repetition Penalty",
                                    tooltip="重复惩罚",
                                    default=1.0,
                                    min=0.0,
                                    max=5.0,
                                    step=0.05,
                                    display_mode=io.NumberDisplay.number,
                                ),
                                io.Float.Input(
                                    id="presence_penalty",
                                    display_name="Presence Penalty",
                                    tooltip="存在惩罚",
                                    default=0.0,
                                    min=-2.0,
                                    max=2.0,
                                    step=0.1,
                                    display_mode=io.NumberDisplay.number,
                                ),
                                io.String.Input(
                                    id="thinking_tag",
                                    display_name="Thinking Tag",
                                    tooltip="思考标签模式，用于提取思考内容",
                                    default="```",
                                ),
                            ]
                        ),
                        io.DynamicCombo.Option(
                            "禁用",
                            []
                        ),
                    ],
                ),
                # 选项
                io.Boolean.Input(
                    id="force_regen",
                    display_name="Force Regen",
                    tooltip="强制重新生成（禁用缓存）",
                    default=False,
                ),
                io.Boolean.Input(
                    id="enable_thinking",
                    display_name="Enable Thinking",
                    tooltip="启用思考模式（某些模型支持 extended thinking）",
                    default=False,
                ),
                io.Boolean.Input(
                    id="debug_mode",
                    display_name="Debug Mode",
                    tooltip="调试模式：在控制台打印 HTTP 请求和响应",
                    default=False,
                ),
                io.Boolean.Input(
                    id="passthrough",
                    display_name="Passthrough",
                    tooltip="绕过 API 调用，直接将提示词透传到 content 输出",
                    default=False,
                ),
            ],
            outputs=[
                io.String.Output(
                    id="content",
                    display_name="Content",
                    tooltip="过滤掉思考后的内容",
                ),
                io.String.Output(
                    id="full_content",
                    display_name="Full Content",
                    tooltip="模型完整响应（包含思考内容）",
                ),
            ],
        )

    @classmethod
    def fingerprint_inputs(cls, **kwargs) -> str:
        """
        控制节点缓存行为
        - force_regen=True 时返回时间戳，强制重新生成
        - 否则返回输入内容的哈希，相同输入使用缓存结果
        """
        if kwargs.get("force_regen"):
            return str(time.time())  # 使用时间戳强制刷新
        else:
            # 移除 force_regen 后序列化剩余输入作为缓存键
            kwargs.pop("force_regen", None)
            return json.dumps(kwargs, sort_keys=True, separators=(",", ":"))

    @classmethod
    def execute(cls,
                base_url: str,
                model: str,
                prompt: str,
                api_key: str | None = None,
                system_prompt: str | None = None,
                images: list[torch.Tensor] | None = None,
                enable_advanced_params: dict | None = None,
                force_regen: bool = False,
                enable_thinking: bool = False,
                debug_mode: bool = False,
                passthrough: bool = False,
                ) -> io.NodeOutput:
        # Passthrough 模式：跳过 API 调用，直接透传提示词
        if passthrough:
            return io.NodeOutput(prompt, prompt)
        
        # 验证必要参数
        if not model or (isinstance(model, str) and model.strip() == ""):
            raise Exception("错误：必须指定模型名称\n请检查模型输入是否已正确连接")
        if not prompt or (isinstance(prompt, str) and prompt.strip() == ""):
            raise Exception("错误：必须提供用户提示词\n请检查提示词输入是否已正确连接，或直接在节点中输入提示词")
        
        # 从 DynamicCombo 字典中提取高级参数
        enabled = enable_advanced_params is not None and enable_advanced_params.get("enable_advanced_params") == "启用"
        
        # 提取高级参数值，如果未启用则使用默认值
        temperature = enable_advanced_params.get("temperature", 1.0) if enabled else None
        seed = enable_advanced_params.get("seed", 42) if enabled else None
        top_k = enable_advanced_params.get("top_k", 0) if enabled else None
        top_p = enable_advanced_params.get("top_p", 1.0) if enabled else None
        min_p = enable_advanced_params.get("min_p", 0.0) if enabled else None
        max_tokens = enable_advanced_params.get("max_tokens", 512) if enabled else None
        repetition_penalty = enable_advanced_params.get("repetition_penalty", 1.0) if enabled else None
        presence_penalty = enable_advanced_params.get("presence_penalty", 0.0) if enabled else None
        thinking_tag = enable_advanced_params.get("thinking_tag", "```") if enabled else "```"
        # 构建消息
        messages = []
        
        # 添加系统提示
        if system_prompt and system_prompt.strip():
            messages.append({
                "role": "system",
                "content": system_prompt.strip()
            })
        
        # 构建用户消息
        if images is not None and len(images) > 0:
            # 多模态消息
            content = []
            for image in images:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": comfy_image_to_base64_png_url(image)
                    }
                })
            content.append({
                "type": "text",
                "text": prompt
            })
            messages.append({
                "role": "user",
                "content": content
            })
        else:
            # 纯文本消息
            messages.append({
                "role": "user",
                "content": prompt
            })
        
        # 构建请求参数
        extra_body: dict[str, Any] = {}
        
        # 仅在启用高级参数时传递采样和惩罚参数
        if enabled:
            if top_k is not None and top_k > 0:
                extra_body["top_k"] = top_k
            if min_p is not None and min_p > 0.0:
                extra_body["min_p"] = min_p
            if repetition_penalty is not None and repetition_penalty != 1.0:
                extra_body["repetition_penalty"] = repetition_penalty
        
        # 处理思考模式（始终显式传递 enable_thinking）
        if "chat_template_kwargs" not in extra_body:
            extra_body["chat_template_kwargs"] = {}
        extra_body["chat_template_kwargs"]["enable_thinking"] = enable_thinking
        
        # 构建 API 调用参数
        api_kwargs: dict[str, Any] = {
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
            "messages": messages,
            "extra_body": extra_body,
            "n": 1,
        }
        
        # 仅在启用高级参数时传递温度、种子、max_tokens、top_p、presence_penalty
        if enabled:
            if temperature is not None:
                api_kwargs["temperature"] = temperature
            if seed is not None:
                api_kwargs["seed"] = seed
            if max_tokens is not None:
                api_kwargs["max_tokens"] = max_tokens
            if top_p is not None:
                api_kwargs["top_p"] = top_p
            if presence_penalty is not None:
                api_kwargs["presence_penalty"] = presence_penalty
        
        # Debug 模式：打印请求信息
        if debug_mode:
            print("\n" + "="*60)
            print("[OpenAI Chat] HTTP 请求")
            print("="*60)
            print(f"URL: {api_kwargs['base_url']}/chat/completions")
            print(f"Model: {api_kwargs['model']}")
            print(f"Messages: {json.dumps(api_kwargs['messages'], ensure_ascii=False, indent=2)}")
            if api_kwargs.get('extra_body'):
                print(f"Extra Body: {json.dumps(api_kwargs['extra_body'], ensure_ascii=False, indent=2)}")
            print("="*60 + "\n")
        
        # 发送请求
        response_data = openai_chat_completion(**api_kwargs)
        
        # Debug 模式：打印响应信息
        if debug_mode:
            print("\n" + "="*60)
            print("[OpenAI Chat] HTTP 响应")
            print("="*60)
            print(json.dumps(response_data, ensure_ascii=False, indent=2))
            print("="*60 + "\n")
        
        # 检查响应
        if "choices" not in response_data or len(response_data["choices"]) == 0:
            raise Exception("API 响应中没有返回 choices")
        
        # 获取响应内容
        message = response_data["choices"][0].get("message", {})
        response_content = message.get("content") or ""
        
        # 检查是否有 reasoning_content 字段（某些 API 返回的思考内容）
        reasoning_content = message.get("reasoning_content") or ""
        
        # 确定最终内容
        if reasoning_content:
            # 如果 API 返回了 reasoning_content，使用它作为思考内容
            # full_content 包含思考内容，content 不包含
            full_content = response_content + "\n\n" + reasoning_content if response_content else reasoning_content
            cleaned_content = response_content
        else:
            # 否则从 content 中提取思考内容（支持 thinking 标签格式）
            full_content = response_content
            cleaned_content = response_content
        
        # 返回两个输出：content, full_content
        return io.NodeOutput(
            cleaned_content,
            full_content,
        )
