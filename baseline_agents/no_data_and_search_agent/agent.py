import asyncio

import yaml
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

from utils.logger import (
    AgentLogger,
    log_to_console,
    log_to_json_file,
    log_to_markdown_file,
)
from utils.tools import DataVoyagerShell, exec_python as python_tool

from openai import OpenAI

# Initialize client
client = OpenAI()
MAX_TOOL_CALLS = 3
current_tool_calls = 0


def exec_python(code: str):
    """
    Execute python code and return the output or error message.

    Parameters
    ----------
    code (str): Python code to execute.

    Returns
    -------
    str: Output or error message.
    """
    global current_tool_calls

    if current_tool_calls > MAX_TOOL_CALLS:
        return "You have exhausted maximum number of allowed tool calls."

    current_tool_calls += 1
    return python_tool(code)


def web_search(query: str) -> dict:
    """
    Executes a web search using the OpenAI Responses API to retrieve and summarize relevant information from online sources.

    Args:
        query (str): The search query

    Returns:
        Search Result: Generated text with citations
        Citations:     Extracted citations with url and title
        Raw:           Raw response for debugging

    Note:
    Ensure the search query is specific and well-formed to retrieve accurate and relevant results. Retry with a revised query if the initial search does not yield satisfactory content.
    """
    global current_tool_calls

    if current_tool_calls > MAX_TOOL_CALLS:
        return "You have exhausted maximum number of allowed tool calls."

    current_tool_calls += 1

    response = client.responses.create(
        model="gpt-4o",
        input=query,
        tools=[{"type": "web_search_preview"}],
        tool_choice={"type": "web_search_preview"},  # force the tool to be used
    )

    text_output = ""
    citations = []

    for item in response.output:
        # Check if web search was actually triggered
        if item.type == "web_search_call":
            # Could log item.action, domains, etc. if needed
            pass

        # Extract the assistant's message text and annotations
        if item.type == "message":
            for content in item.content:
                if content.type == "output_text":
                    text_output += content.text + "\n"
                    if "annotations" in content:
                        for ann in content.annotations:
                            if ann["type"] == "url_citation":
                                citations.append(
                                    {
                                        "url": ann["url"],
                                        "title": ann.get("title"),
                                        "start_index": ann.get("start_index"),
                                        "end_index": ann.get("end_index"),
                                    }
                                )

    result = {
        "text": text_output.strip(),
        "citations": citations,
        "raw": response.model_dump(),  # keep raw for inspection/debugging
    }

    output_text = ""
    output_text += f"# Search Result:\n{result['text']}\n\n\n"
    output_text += "# Citations:\n"
    for i, c in enumerate(result["citations"]):
        output_text += f"{i + 1}. {c['title']}: {c['url']}\n"
    return output_text


class NoDataAgentWithSearchTool:
    def __init__(
        self,
        config_file: str,
        log_file: str,
    ):
        global current_tool_calls
        current_tool_calls = 0
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        config["model_client"] = OpenAIChatCompletionClient(**config["model_client"])
        config["log_file"] = log_file

        self.name = config["name"]
        self.model_client = config["model_client"]
        self.system_message = config["system_message"]
        self.log_file = config["log_file"]
        self.max_iterations = config["max_iterations"]
        self.max_tool_iterations = config["max_tool_iterations"]
        self.termination_keyword = config["termination_keyword"]

        self.dv_shell = DataVoyagerShell()

        self.agent = AssistantAgent(
            name=self.name,
            model_client=self.model_client,
            system_message=self.system_message,
            tools=[exec_python, web_search],
        )
        self.termination_condition = MaxMessageTermination(
            self.max_iterations
        ) | TextMentionTermination(self.termination_keyword)
        self.orchestrator = RoundRobinGroupChat(
            participants=[self.agent], termination_condition=self.termination_condition
        )

        self.md_logger = AgentLogger(
            logger_name=f"dv_{log_file}_md",
            log_filename=log_file.rsplit(".", 1)[0] + ".md",
            use_json_formatter=False,
        )
        self.console_logger = AgentLogger(
            logger_name=f"dv_{log_file}_console",
            log_filename=None,
            use_json_formatter=False,
        )
        self.json_logger = AgentLogger(
            logger_name=f"dv_{log_file}_json", log_filename=log_file
        )

    async def run(self, task: str):
        stream = self.orchestrator.run_stream(task=task)
        async for message in stream:
            try:
                log_to_markdown_file(self.md_logger, message)
                log_to_console(self.console_logger, message)
                log_to_json_file(self.json_logger, message)
            except Exception as e:
                print(f"Error while logging the groupchat message: {e}")


if __name__ == "__main__":
    config_file = "agents/no_data_and_search_agent/config/no_data_and_search_agent_gpt4o_config.yaml"
    log_file = "tmp.jsonl"
    no_code_agent = NoDataAgentWithSearchTool(config_file, log_file)
    asyncio.run(
        no_code_agent.run(
            "can you please load titanic dataset and perform correlation analysis"
        )
    )
