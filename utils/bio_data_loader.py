import os
import shutil

import gdown
import yaml


class BioDatasetDownloader:
    def __init__(
        self,
        config_path: str = "bio_datasets_config.yaml",
        output_dir: str = "bio_datasets",
    ):
        self.dataset_config = self.load_config(config_path=config_path)
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def load_config(self, config_path):
        """
        Load the bio dataset config file
        """
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f.read())
        except Exception as e:
            print(f"Error loading bio datasets config: {e}")

    def get_available_datasets(self):
        """
        Returns list of available datasets
        """
        try:
            return list(self.dataset_config["datasets"].keys())
        except Exception as e:
            print(f"Error reading available datasets: {e}")

    def download_file(
        self, file_id: str, filename: str = None, output_path: str = None
    ):
        """
        Downloads a single file from Google Drive using a sharable link.
        """
        try:
            output_path = output_path or os.path.join(
                self.output_dir, filename or f"{file_id}.file"
            )
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            if os.path.exists(output_path):
                print(
                    f"Skipping downloading dataset at {output_path} because the file already exists."
                )
                return output_path

            gdown.download(id=file_id, output=output_path, quiet=False)
            return output_path
        except Exception as e:
            print(f"Error download file '{filename}': {e}")

    def download_dataset(self, dataset_name: str, output_path: str = None):
        """
        Downloads a single dataset with the given dataset_name
        """
        try:
            dataset = self.dataset_config["datasets"].get(dataset_name)
            file_id = dataset["file_id"]
            filename = dataset["filename"]
            return self.download_file(
                file_id=file_id, filename=filename, output_path=output_path
            )
        except Exception as e:
            print(f"Error downloading dataset '{dataset_name}': {e}")

    def download_all_datasets(self):
        """
        Download all datasets specified in the config
        """
        downloaded_dataset_output_paths = []
        for dataset_name in self.dataset_config["datasets"]:
            try:
                output_path = self.download_dataset(dataset_name=dataset_name)
                downloaded_dataset_output_paths.append(output_path)
            except Exception as e:
                print(f"Error downloading dataset '{dataset_name}': {e}")
        return downloaded_dataset_output_paths

    def copy_files_to_locations(
        self, locations: list[str], exclude_files: list[str] = None
    ):
        """
        Copy all the files present in `output_dir` to each of the given locations,
        excluding any files listed in `exclude_files`.
        """
        if not os.path.isdir(self.output_dir):
            raise FileNotFoundError(
                f"Output directory '{self.output_dir}' does not exist."
            )

        exclude_set = set(exclude_files or [])

        def ignore_function(directory, files):
            return {f for f in files if f in exclude_set}

        for loc in locations:
            try:
                if os.path.exists(loc):
                    src_files = set(os.listdir(self.output_dir)) - exclude_set
                    dest_files = set(os.listdir(loc))
                    if src_files <= dest_files:
                        print(
                            f"Skipping copying to '{loc}' because all files already exist."
                        )
                        continue
                shutil.copytree(
                    self.output_dir, loc, dirs_exist_ok=True, ignore=ignore_function
                )
            except Exception as e:
                print(
                    f"Error copying dataset files from '{self.output_dir}' to '{loc}': {e}"
                )


if __name__ == "__main__":
    dataset_loader = BioDatasetDownloader(config_path="utils/bio_datasets_config.yaml")
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
