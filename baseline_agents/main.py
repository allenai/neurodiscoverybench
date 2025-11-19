import asyncio
import json
import re
import pandas as pd
import glob
from pathlib import Path
from datetime import datetime
import click


from utils.parse_logs import parse_log
from no_data_agent.run_agent import run_agent as run_no_data_agent
from no_data_and_search_agent.run_agent import run_agent as run_no_data_and_search_agent
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
    dataset_path: str,
    sample: int = 1,
) -> pd.DataFrame:
    """
    Given a NeuroDiscoveryBench dataset directory, it traverses all the
    dataset json files and compiles a dataframe.

    Parameters
    ----------
    dataset_path : str
        Location of the NeuroDiscoveryBench dataset directory.
    sample : int
        Number of samples per dataset to include in the returned DataFrame
        from each dataset. If `sample` is None or <= 0, all samples are included.

    Returns
    -------
    pd.DataFrame
        Compiled DataFrame containing unique id, query, gold hypo & image,
        metadata and path to sample dataset directory
    """

    dataframe_columns = [
        "unique_id",
        "dataset",
        "query",
        "metadata",
        "gold_image",
        "gen_image",
        "gold_hypo",
        "gen_hypo",
        "hms_score",
        "eval_result",
    ]

    dataset_path = Path(dataset_path)

    # Support either a directory containing many metadata JSON files, or a
    # single metadata JSON file. If a single file is provided, only questions
    # from that file will be used.
    project_root = Path(__file__).resolve().parents[1]
    eval_root = project_root / "eval"
    eval_directory = eval_root if eval_root.is_dir() else None

    if dataset_path.is_file():
        metadata_files = [str(dataset_path)]
    elif dataset_path.is_dir():
        pattern = str(dataset_path / "**/*.json")
        metadata_files = glob.glob(pattern, recursive=True)
    else:
        raise ValueError(
            "`dataset_directory` must be a directory or a json file path"
        )

    answer_key_df = pd.DataFrame()
    if eval_directory is not None:
        answer_key_path = eval_directory / "answer_key.csv"
        if answer_key_path.exists():
            answer_key_df = pd.read_csv(answer_key_path)

            def _make_unique_id(row):
                return (
                    f"{row['dataset']}||{row['metadataid']}||"
                    f"{row['query_id']}"
                )

            answer_key_df["unique_id"] = answer_key_df.apply(
                _make_unique_id, axis=1
            )

    data = pd.DataFrame(columns=dataframe_columns)

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
                    # Only set `gold_image` if we located an `eval/` dir and
                    # a matching image exists.
                    if eval_directory is not None and png_files:
                        dataset_name_prefix = dataset_name.split("-")[0]
                        gold_image_dir = _IMAGE_ANSWER_KEY_MAP.get(
                            dataset_name_prefix
                        )
                        if gold_image_dir is not None:
                            gold_image = (
                                eval_directory / gold_image_dir / png_files[0]
                            )
                else:
                    # For non-figure datasets, try to look up the gold
                    # hypothesis in the answer key if available.
                    if not answer_key_df.empty:
                        try:
                            gold_hypo = answer_key_df.loc[
                                answer_key_df["unique_id"] == unique_id
                            ]["gold_hypo"].values[0]
                        except Exception:
                            gold_hypo = None

                instance = {
                    "unique_id": unique_id,
                    "dataset": dataset_name,
                    "query": q["question"],
                    "metadata": dataset_metadata,
                    "dataset_directory": str(file.parent),
                    "gold_image": gold_image,
                    "gen_image": gen_image,
                    "gold_hypo": gold_hypo,
                    "gen_hypo": gen_hypo,
                    "hms_score": hms_score,
                    "eval_result": eval_result,
                }
                data = pd.concat([data, pd.DataFrame([instance])])

    data = data.sort_values(by="unique_id").reset_index(drop=True)

    # If the user provided a single metadata JSON file, ignore `sample`
    # and return all samples in that file. Otherwise, limit to the first
    # `sample` items per dataset (if sample > 0).
    if not dataset_path.is_file() and sample is not None and sample > 0:
        limited = (
            data.groupby("dataset", sort=False)
            .head(sample)
            .reset_index(drop=True)
        )
        return limited

    return data


async def run_agent_async(
    agent_name: str,
    config_file: str,
    metadata_path: str = "neurodiscoverybench",
    provide_domain_knowledge: bool = False,
    provide_workflow_tags: bool = False,
    experiment_name: str = DEFAULT_EXP_NAME,
    sample: int = 1,
):
    # Prepare logging directory
    log_dir = Path(LOG_DIR)
    cur_dir = Path(log_dir / experiment_name)
    cur_dir.mkdir(parents=True, exist_ok=True)

    def _export_results():
        csv_path = (cur_dir / "results").with_suffix(".csv")
        dataset_df.to_csv(csv_path, index=False)

    # Downlaod and setup bio datasets
    setup_datasets(dataset_config="utils/bio_datasets_config.yaml")

    # Create dataset df
    dataset_df = get_dataset_df(
        dataset_path=metadata_path,
        sample=sample,
    )

    _export_results()

    # Loop through each sample in the dataset
    for idx, row in dataset_df.iterrows():
        row = row.to_dict()

        dataset_name = row["unique_id"].split("||")[0]
        log_filename = row["unique_id"].replace("||", "_")

        sample_dir = cur_dir / dataset_name
        sample_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = (sample_dir / log_filename).with_suffix(".jsonl")

        run_agent_method = _AGENTS.get(agent_name, None)

        if not run_agent_method:
            raise ValueError(f"{agent_name} is not a valid agent.")

        # Run the agent
        await run_agent_method(
            data_row=row,
            config_file=config_file,
            log_file_path=str(log_file_path),
            domain_knowledge=provide_domain_knowledge,
            workflow_tags=provide_workflow_tags,
        )

        # Read the log file and parse the log
        result, status = parse_log(str(log_file_path))
        if status:
            hypothesis = result.hypothesis if result else ""
            dataset_df.at[idx, "gen_hypo"] = hypothesis
        else:
            print("Unable to parse log:", log_file_path)
            dataset_df.at[idx, "gen_hypo"] = None

        _export_results()


def run_agent(
    agent_name: str,
    config_file: str,
    metadata_path: str = "neurodiscoverybench",
    provide_domain_knowledge: bool = False,
    provide_workflow_tags: bool = False,
    experiment_name: str = DEFAULT_EXP_NAME,
    sample: int = 1,
):
    asyncio.run(
        run_agent_async(
            agent_name=agent_name,
            config_file=config_file,
            metadata_path=metadata_path,
            provide_domain_knowledge=provide_domain_knowledge,
            provide_workflow_tags=provide_workflow_tags,
            experiment_name=experiment_name,
            sample=sample,
        )
    )


@click.command(name="run-agent")
@click.option(
    "--agent-name",
    "agent_name",
    "-a",
    type=click.Choice(list(_AGENTS.keys())),
    required=True,
    help="Agent to run. Choices: no_data_agent, no_data_and_search_agent",
)
@click.option(
    "--config-file",
    "-c",
    default=None,
    help="Path to agent config file. If omitted, use the agent default.",
)
@click.option(
    "--metadata-path",
    "-d",
    default="neurodiscoverybench",
    show_default=True,
    help=(
        "Path to the dataset directory or a single metadata json file. "
        "If a file is provided, only questions from that file are used."
    ),
)
@click.option(
    "--provide-domain-knowledge/--no-domain-knowledge",
    default=False,
    show_default=True,
    help="Whether to provide domain knowledge to the agent.",
)
@click.option(
    "--provide-workflow-tags/--no-workflow-tags",
    default=False,
    show_default=True,
    help="Whether to provide workflow tags to the agent.",
)
@click.option(
    "--experiment-name",
    "-e",
    default=None,
    help="Experiment name (directory under logs). Defaults to timestamp.",
)
@click.option(
    "--sample",
    "-s",
    default=1,
    type=int,
    show_default=True,
    help="Number of samples per dataset to run (1 = first sample).",
)
def cli(
    agent_name: str,
    config_file: str,
    metadata_path: str,
    provide_domain_knowledge: bool,
    provide_workflow_tags: bool,
    experiment_name: str,
    sample: int,
):
    """CLI wrapper for `run_agent`.

    Example:
        python3 baseline_agents/main.py \b
            --agent-name no_data_agent \b
            --config-file utils/bio_datasets_config.yaml
    """
    if experiment_name is None:
        experiment_name = DEFAULT_EXP_NAME

    # If no config provided, pick the agent-specific default in the agent
    # `config/` directory.
    if config_file is None:
        agent_config_name = f"{agent_name}_gpt4o_config.yaml"
        agent_dir = Path(__file__).resolve().parent / agent_name
        config_path = agent_dir / "config" / agent_config_name
        config_file = str(config_path)

    run_agent(
        agent_name=agent_name,
        config_file=config_file,
        metadata_path=metadata_path,
        provide_domain_knowledge=provide_domain_knowledge,
        provide_workflow_tags=provide_workflow_tags,
        experiment_name=experiment_name,
        sample=sample,
    )


if __name__ == "__main__":
    # Run via CLI
    cli()
