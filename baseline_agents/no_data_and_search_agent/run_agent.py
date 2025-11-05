import asyncio
import glob
import json
import os
import shutil
from datetime import datetime

import pandas as pd
import matplotlib

from agent import NoDataAgentWithSearchTool
from bio_data_loader import BioDatasetDownloader

matplotlib.use("Agg")


DEFAULT_EXP_NAME = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


def setup_datasets(dataset_config: str = "bio_datasets_config.yaml"):
    dataset_loader = BioDatasetDownloader(config_path=dataset_config)
    dataset_loader.download_all_datasets()
    dataset_loader.copy_files_to_locations(
        locations=[
            "neurodiscoverybench/WMB-raw-fig/",
            "neurodiscoverybench/WMB-raw-no-traces/",
            "neurodiscoverybench/WMB-raw-text",
        ],
        exclude_files=["cell_subsampled.csv"],
    )
    dataset_loader.copy_files_to_locations(
        locations=[
            "neurodiscoverybench/WMB-processed-fig/",
            "neurodiscoverybench/WMB-processed-text/",
        ],
        exclude_files=[
            "cell_metadata.csv",
            "color.csv",
            "pivot.csv",
            "result.csv",
            "term_set.csv",
            "cluster_to_cluster_annotation_membership_pivoted.csv",
        ],
    )


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


def get_metadata(
    data_loc: str,
) -> pd.DataFrame:
    data = pd.DataFrame(columns=["unique_id", "query", "metadata"])
    metadata_files = []
    if os.path.isdir(data_loc):
        metadata_files = glob.glob(os.path.join(data_loc, "**/*.json"), recursive=True)
    else:
        metadata_files = [data_loc]

    for file in metadata_files:
        with open(file) as f:
            dataset_metadata = json.load(f)
            for q in dataset_metadata["queries"][0]:
                path_splits = file.split("/")
                dataset_name = path_splits[-2]
                metadata_name = path_splits[-1].split(".")[0].split("_")[-1]
                query_id = q["qid"]
                uniq_id = f"{dataset_name}||{metadata_name}||{query_id}"
                instance = {
                    "unique_id": uniq_id,
                    "query": q["question"],
                    "metadata": dataset_metadata,
                    "data_dir": os.path.dirname(file),
                }
                data = pd.concat([data, pd.DataFrame([instance])])

    data = data.sort_values(by="unique_id").reset_index(drop=True)
    return data


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


async def main(
    data_loc: str,
    config_file: str,
    domain_knowledge: bool = True,
    workflow_tags: bool = True,
    experiment_name: str = DEFAULT_EXP_NAME,
):
    metadata = get_metadata(data_loc=data_loc)
    metadata.to_csv("neurodiscoverybench_data.csv")

    for idx, row in metadata.iterrows():
        row = row.to_dict()
        query = row["query"]
        data = row["metadata"]
        data_dir = row["data_dir"]
        logfilename = row["unique_id"].replace("||", "_")

        dataset_name = row["unique_id"].split("||")[0]
        cur_dir = os.path.join(LOG_DIR, experiment_name, dataset_name)
        os.makedirs(cur_dir, exist_ok=True)
        log_file_path = os.path.join(cur_dir, logfilename + ".jsonl")

        no_data_search_agent = NoDataAgentWithSearchTool(
            config_file=config_file,
            log_file=log_file_path,
        )

        data_input = {"metadata": data, "data_folder": data_dir, "query": query}

        query = format_query(
            input=data_input,
            provide_domain_knowledge=domain_knowledge,
            provide_workflow_tags=workflow_tags,
        )

        await no_data_search_agent.run(task=query)
        copy_png_files(source_dir=".", destination_dir=cur_dir)


if __name__ == "__main__":
    data_loc = "neurodiscoverybench"
    config_file = (
        "agents/no_data_and_search_agent/config/no_data_and_search_gpt4o_config.yaml"
    )
    setup_datasets(
        dataset_config="agents/no_data_and_search_agent/bio_datasets_config.yaml"
    )
    asyncio.run(
        main(
            data_loc=data_loc,
            config_file=config_file,
            domain_knowledge=False,
            workflow_tags=True,
        )
    )
