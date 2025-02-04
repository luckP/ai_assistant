from typing import Type
from .AgentTool import AgentTool
from .PythonTool import PythonTool
from .BashTool import BashTool

class AgentToolFactory:
    """
    Factory class to create instances of AgentTool subclasses.
    """
    _tools_registry = {}

    @classmethod
    def register_tool(cls, tool_name: str, tool_class: Type[AgentTool]):
        """
        Register a tool class with a unique name.
        """
        if not issubclass(tool_class, AgentTool):
            raise ValueError(f"{tool_class} is not a subclass of AgentTool")
        cls._tools_registry[tool_name] = tool_class

    @classmethod
    def create_tool(cls, tool_name: str, **kwargs) -> AgentTool:
        """
        Create an instance of the specified tool.
        """
        tool_class = cls._tools_registry.get(tool_name)
        if not tool_class:
            raise ValueError(f"Tool '{tool_name}' is not registered.")
        return tool_class(**kwargs)

    @classmethod
    def list_tools(cls) -> list:
        """
        List all registered tools.
        """
        return list(cls._tools_registry.keys())

# Register the tools
# AgentToolFactory.register_tool("python", PythonTool)
# AgentToolFactory.register_tool("bash", BashTool)
