import asyncio
import json
import re
import pandas as pd
import glob
from pathlib import Path
from datetime import datetime


from no_data_agent.run_agent import run_agent as run_no_data_agent
from no_data_and_search_agent.agent import run_agent as run_no_data_and_search_agent
from utils.bio_data_loader import BioDatasetDownloader

# A mapping from dataset prefix (split by "-") to appropriate image answer key directory
_IMAGE_ANSWER_KEY_MAP = {
    "WMB": "WMB-fig",
    "SEA": "SEA-AD-fig",
    "BlackDeath": "BlackDeath-Immune-fig",
}
_AGENTS = {
    "no_data_agent": run_no_data_agent,
    "no_data_and_search_agent": run_no_data_and_search_agent,
}
LOG_DIR = "logs"
DEFAULT_EXP_NAME = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")


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
            "pivot.csv",
            "result.csv",
            "cluster_to_cluster_annotation_membership_pivoted.csv",
        ],
    )


def extract_png_names_from_text(metadata: dict) -> list[str]:
    """
    Recursively search through JSON data to find PNG file names embedded in natural language strings.

    Parameters
    ----------
    metadata : dict
        Metadata dictionary.

    Returns
    -------
    list[str]
        Returns a list of all matching PNG file names.
    """

    png_files = []

    # matches image.png, path/image-name.png, etc.
    pattern = r"\b[\w\-\/\.]*?\.png\b"

    if isinstance(metadata, dict):
        for value in metadata.values():
            png_files.extend(extract_png_names_from_text(value))
    elif isinstance(metadata, list):
        for item in metadata:
            png_files.extend(extract_png_names_from_text(item))
    elif isinstance(metadata, str):
        matches = re.findall(pattern, metadata, flags=re.IGNORECASE)
        png_files.extend(matches)

    return png_files


def get_dataset_df(
    dataset_directory: str,
) -> pd.DataFrame:
    """
    Given a NeuroDiscoveryBench dataset directory, it traverses all the
    dataset json files and compiles a dataframe.

    Parameters
    ----------
    dataset_directory : str
        Location of the NeuroDiscoveryBench dataset directory.

    Returns
    -------
    pd.DataFrame
        Compiled DataFrame containing unique id, query, gold hypo & image,
        metadata and path to sample dataset directory
    """

    dataframe_columns = [
        "unique_id",
        "query",
        "metadata",
        "dataset_directories",
        "gold_image",
        "gen_image",
        "gold_hypo",
        "gen_hypo",
        "hms_score",
        "eval_result",
    ]

    dataset_directory = Path(dataset_directory)
    if not dataset_directory.is_dir():
        raise ValueError(
            "Parameter `dataset_directory` should be a string to a valid directory"
        )

    eval_directory = dataset_directory / "eval"
    if not eval_directory.is_dir():
        raise ValueError(
            "`dataset_directory` doesn't have a valid `eval/` subdirectory."
        )

    answer_key_df = pd.read_csv(eval_directory / "answer_key.csv")
    answer_key_df["unique_id"] = answer_key_df.apply(
        lambda row: f"{row['dataset']}||{row['metadataid']}||{row['query_id']}", axis=1
    )

    data = pd.DataFrame(columns=dataframe_columns)

    metadata_files = []
    metadata_files = glob.glob(str(dataset_directory / "**/*.json"), recursive=True)

    for file in metadata_files:
        file = Path(file)
        with open(file) as f:
            dataset_metadata = json.load(f)
            for q in dataset_metadata["queries"][0]:
                path_splits = file.parts

                dataset_name = path_splits[-2]
                metadata_name = path_splits[-1].split(".")[0].split("_")[-1]
                query_id = q["qid"]
                unique_id = f"{dataset_name}||{metadata_name}||{query_id}"
                png_files = extract_png_names_from_text(dataset_metadata)
                gold_hypo = None
                gen_hypo = None
                gold_image = None
                gen_image = None
                hms_score = None
                eval_result = None

                if "fig" in dataset_name:
                    # NOTE: assuming each sample generates only one png
                    dataset_name_prefix = dataset_name.split("-")[0]
                    gold_image_dir = _IMAGE_ANSWER_KEY_MAP.get(dataset_name_prefix)
                    gold_image = eval_directory / gold_image_dir / png_files[0]
                else:
                    gold_hypo = answer_key_df.loc[
                        answer_key_df["unique_id"] == unique_id
                    ]["gold_hypo"].values[0]

                instance = {
                    "unique_id": unique_id,
                    "query": q["question"],
                    "metadata": dataset_metadata,
                    "dataset_directories": file.parent,
                    "gold_image": gold_image,
                    "gen_image": gen_image,
                    "gold_hypo": gold_hypo,
                    "gen_hypo": gen_hypo,
                    "hms_score": hms_score,
                    "eval_result": eval_result,
                }
                data = pd.concat([data, pd.DataFrame([instance])])

    data = data.sort_values(by="unique_id").reset_index(drop=True)
    return data


async def run_agent_async(
    agent_name: str,
    config_file: str,
    data_dir: str = "neurodiscoverybench",
    provide_domain_knowledge: bool = False,
    provide_workflow_tags: bool = False,
    experiment_name: str = DEFAULT_EXP_NAME,
):
    # Downlaod and setup bio datasets
    setup_datasets(dataset_config="utils/bio_datasets_config.yaml")

    # Create dataset df
    dataset_df = get_dataset_df(
        dataset_directory=data_dir,
    )

    # Loop through each sample in the dataset
    for idx, row in dataset_df.iterrows():
        row = row.to_dict()

        dataset_name = row["unique_id"].split("||")[0]
        log_filename = row["unique_id"].replace("||", "_")

        log_dir = Path(LOG_DIR)
        cur_dir = Path(log_dir / experiment_name, dataset_name).mkdir(
            parents=True, exist_ok=True
        )
        log_file_path = cur_dir / log_filename + ".jsonl"

        run_agent_method = _AGENTS.get(agent_name, None)

        if not run_agent_method:
            raise ValueError(f"{agent_name} is not a valid agent.")

        # Run the agent
        await run_agent_method(
            data_row=row,
            config_file=config_file,
            log_file_path=log_file_path,
            domain_knowledge=provide_domain_knowledge,
            workflow_tags=provide_workflow_tags,
        )


def run_agent(
    agent_name: str,
    config_file: str,
    data_dir: str = "neurodiscoverybench",
    provide_domain_knowledge: bool = False,
    provide_workflow_tags: bool = False,
    experiment_name: str = DEFAULT_EXP_NAME,
):
    asyncio.run(
        run_agent_async(
            agent_name=agent_name,
            config_file=config_file,
            data_dir=data_dir,
            provide_domain_knowledge=provide_domain_knowledge,
            provide_workflow_tags=provide_workflow_tags,
            experiment_name=experiment_name,
        )
    )


if __name__ == "__main__":
    run_agent()
