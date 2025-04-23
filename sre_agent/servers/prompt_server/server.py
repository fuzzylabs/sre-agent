"""A server containing a prompt to trigger the agent."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("sre-agent-prompt")
mcp.settings.port = 3001


@mcp.prompt()
def diagnose(service: str, channel_id: str) -> str:
    """Prompt the agent to perform a task."""
    return f"""I have an error with my application, can you check the logs for the
    {service} service, I only want you to check the pods logs, look up only the 1000
    most recent logs. Feel free to scroll up until you find relevant errors that
    contain reference to a file, once you have these errors and the file name, get the
    file contents of the path src for the repository microservices-demo in the
    organisation fuzzylabs. Keep listing the directories until you find the file name
    and then get the contents of the file. Once you have diagnosed the error please
    report this to the following slack channel: {channel_id}."""


if __name__ == "__main__":
    mcp.run()
