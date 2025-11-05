## Utility Scripts

### `bio_data_loader.py`

This script downloads the NeuroDiscoveryBench data stored on Google Drive.

When executed, the script will download the datasets listed in the `bio_datasets_config.yaml` file to the `bio_datasets/` directory, and then copy them to their respective locations under the `neurodiscoverybench` repository, alongside other datasets and metadata files. If any datasets are already downloaded or present in the target directory, they will be skipped.

To run the script, activate the virtual environment and use the following command:

```bash
# Activate the virtual environment
python3 utils/bio_data_loader.py
```
