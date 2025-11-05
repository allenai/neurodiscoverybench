import os
from pathlib import Path
import shutil
from datetime import datetime

import matplotlib

from no_data_and_search_agent.agent import NoDataAgentWithSearchTool

matplotlib.use("Agg")


DEFAULT_EXP_NAME = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


def format_query(
    input: dict,
    provide_domain_knowledge: bool = False,
    provide_workflow_tags: bool = False,
):
    """
    This function constructs a full query with metadata details.
    Args:
        input (dict): The task input containing query, question_type, data_folder, and metadata.
        provide_domain_knowledge (bool): Whether to provide domain knowledge.
        provide_workflow_tags (bool): Whether to provide workflow tags.
    Returns:
        formatted_query (str): The query to be sent to the solver.
    """
    dataset_meta = ""
    for dataset_metadata in input["metadata"]["datasets"]:
        # dataset_meta += (
        #     "Dataset path: "
        #     + os.path.join(input["data_folder"], dataset_metadata["name"])
        #     + "\n"
        # )
        dataset_meta += "Dataset description: " + dataset_metadata["description"] + "\n"
        dataset_meta += "\nBrief description of columns: " + "\n"
        for col in dataset_metadata["columns"]["raw"]:
            dataset_meta += col["name"] + ": " + col["description"] + ", " + "\n"

    formatted_query = dataset_meta

    formatted_query += f"\nQuery: {input['query']}"

    formatted_query += "\n\nUsing your knowledge of neuroscience, relevant web information, and the dataset schema, analyze the query and generate a scientific hypothesis in response. Start by using the web search tool to verify or supplement key facts - especially for unfamiliar terms or recent findings. Use the Python tool as needed for calculations or visualizations."

    if provide_domain_knowledge:
        formatted_query += (
            "\nAdditionally, we provide some hints that might be useful to solve the task. Domain Knowledge: \n"
            + input["metadata"]["domain_knowledge"]
            + ".\n"
        )

    if provide_workflow_tags:
        formatted_query += (
            "\n\nThe meta tags are: " + input["metadata"]["workflow_tags"] + ".\n"
        )

    formatted_query += """
In the final answer, please output a JSON containing one key:

{
    "hypothesis": SCIENTIFIC HYPOTHESIS,
}

where
the SCIENTIFIC HYPOTHESIS is a natural language hypothesis, clearly stating the context of hypothesis (if any), variables chosen (if any) and relationship between those variables (if any) including any statistical significance. Please include all numeric information as necessary to support the hypothesis.
"""

    return formatted_query


def copy_png_files(source_dir, destination_dir):
    """
    Copies all .png files from source_dir to destination_dir.

    Args:
        source_dir (str): Path to the source directory.
        destination_dir (str): Path to the destination directory.
    """
    if not os.path.isdir(source_dir):
        raise ValueError(f"Source directory does not exist: {source_dir}")

    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir, exist_ok=True)

    for filename in os.listdir(source_dir):
        if filename.lower().endswith(".png"):
            full_source_path = os.path.join(source_dir, filename)
            full_destination_path = os.path.join(destination_dir, filename)
            shutil.move(full_source_path, full_destination_path)
            print(f"Moved: {filename}")


async def run_agent(
    data_row: dict,
    config_file: str,
    log_file_path: str,
    domain_knowledge: bool = False,
    workflow_tags: bool = False,
):
    cur_dir = Path(log_file_path).parent

    query = data_row["query"]
    data = data_row["metadata"]
    data_dir = data_row["data_dir"]

    no_data_agent = NoDataAgentWithSearchTool(
        config_file=config_file,
        log_file=log_file_path,
    )

    data_input = {"metadata": data, "data_folder": data_dir, "query": query}

    query = format_query(
        input=data_input,
        provide_domain_knowledge=domain_knowledge,
        provide_workflow_tags=workflow_tags,
    )

    await no_data_agent.run(task=query)
    copy_png_files(source_dir=".", destination_dir=cur_dir)
