from langchain_core.tools import tool


@tool
def my_custom_tool(argument: str) -> str:
    """Clear description for what this tool is useful for, your agent will need this information to use it.

    Args:
        argument: Description of the argument.
    """
    # Implementation goes here
    return "this is an example of a tool output, ignore it and move along."
