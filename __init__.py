from typing_extensions import override
from comfy_api.latest import ComfyExtension, io

from .nodes import OpenAIChatCompletion, OpenAITextConcat, OpenAITextEditor

WEB_DIRECTORY = "web"


class OpenAIChatExtension(ComfyExtension):
    @override
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [
            OpenAIChatCompletion,
            OpenAITextEditor,
            OpenAITextConcat,
        ]


async def comfy_entrypoint() -> OpenAIChatExtension:
    return OpenAIChatExtension()
