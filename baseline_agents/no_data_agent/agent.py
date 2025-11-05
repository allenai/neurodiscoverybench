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
from utils.tools import DataVoyagerShell, exec_python


class NoDataAgent:
    def __init__(
        self,
        config_file: str,
        log_file: str,
    ):
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        config["model_client"] = OpenAIChatCompletionClient(**config["model_client"])
        config["log_file"] = log_file

        self.name = config["name"]
        self.model_client = config["model_client"]
        self.system_message = config["system_message"]
        self.log_file = config["log_file"]
        self.max_iterations = config["max_iterations"]
        self.termination_keyword = config["termination_keyword"]

        self.dv_shell = DataVoyagerShell()

        self.agent = AssistantAgent(
            name=self.name,
            model_client=self.model_client,
            system_message=self.system_message,
            tools=[exec_python],
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
    config_file = "agents/no_data_agent/config/no_data_agent_gpt4o_config.yaml"
    log_file = "tmp.jsonl"
    no_code_agent = NoDataAgent(config_file, log_file)
    asyncio.run(
        no_code_agent.run(
            "can you please load titanic dataset and perform correlation analysis"
        )
    )
