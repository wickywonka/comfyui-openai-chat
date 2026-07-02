from typing_extensions import override
from comfy_api.latest import ComfyExtension, io

from .nodes import OpenAIChatCompletion


class OpenAIChatExtension(ComfyExtension):
    @override
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [
            OpenAIChatCompletion,
        ]


async def comfy_entrypoint() -> OpenAIChatExtension:
    return OpenAIChatExtension()
