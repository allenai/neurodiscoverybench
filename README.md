# 🧬 NeuroDiscoveryBench

NeuroDiscoveryBench is an open benchmark designed to evaluate how well AI systems can analyze real world neuroscience, genetics, and immunology datasets to generate scientific insights. The benchmark includes both text- and figure-based tasks, modeled after real world workflows that involve data manipulation, data analysis, and visualization. 

It builds on landmark open datasets by the Allen Institute and includes workflows derived from following papers:

- Yao, Z., van Velthoven, C.T.J., Kunst, M. et al. A high-resolution transcriptomic and spatial atlas of cell types in the whole mouse brain. Nature 624, 317–332 (2023). https://doi.org/10.1038/s41586-023-06812-z

- Klunk, J., Vilgalys, T.P., Demeure, C.E. et al. Evolution of immune genes is associated with the Black Death. Nature 611, 312–319 (2022). https://doi.org/10.1038/s41586-022-05349-x

- Gabitto, M.I., Travaglini, K.J., Rachleff, V.M. et al. Integrated multimodal cell atlas of Alzheimer’s disease. Nat Neurosci 27, 2366–2383 (2024). https://doi.org/10.1038/s41593-024-01774-5

<img width="746" alt="image" src="https://github.com/user-attachments/assets/df85845d-cb1d-4cc1-8ff4-f675d0b52fed" />

### 🗂️ Repository Structure
This repository is organized into four main components:
* **`neurodiscoverybench/`** – Core benchmark data & metadata.
* **`baseline_agents/`** – Baseline agents and orchestration code for running inference.
* **`eval/`** – Evaluation scripts and gold-standard answers.
* **`utils/`** – Supporting utilities, including dataset downloaders and helper analysis functions.


<!-- <img width="792" height="703" alt="image" src="https://github.com/user-attachments/assets/df85845d-cb1d-4cc1-8ff4-f675d0b52fed" /> -->

## 🚀 Getting Started

These installation instructions have been tested on Linux/macOS/Ubuntu.

### 1. Setup `OPENAI_API_KEY` in your execution environment

The following command will set the temporary variables in your environment.
```bash
export OPENAI_API_KEY="sk-xxx"
```

### 2. Setup python virtual environment

Create a Python virtual environment to isolate your work with NeuroDiscoveryBench and avoid dependency conflicts with your global Python environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```
If you use `uv` package manager, use these following commands to set up the virtual environment:

```bash
uv venv
source .venv/bin/activate
uv pip3 install -r requirements.txt
```
Note that the install can take several minutes.

### 3. Download the dataset files

Some large data files are hosted on Google Drive. To download and set them up, run the following script:

```bash
python3 utils/bio_data_loader.py
```

### 4. Running Baseline Agents

To run the baseline agents, use the `baseline_agents/main.py` script with the following configurations:

``` bash
python3 main.py --help
```
The output will show the following options:
```bash
Usage: main.py [OPTIONS]

  Run a neurodiscovery benchmarking agent.

  Example:

      python3 baseline_agents/main.py --agent-name no_data_agent --metadata-
      path neurodiscoverybench

Options:
  -a, --agent-name                [no_data_agent|no_data_and_search_agent]
                                  Agent to run. Choices: no_data_agent,
                                  no_data_and_search_agent  [required]
  -c, --config-file TEXT          Path to agent config file. If omitted, use
                                  the agent default.
  -d, --metadata-path TEXT        Path to the dataset directory or a single
                                  metadata json file. If a file is provided,
                                  only questions from that file are used.
                                  [default: neurodiscoverybench]
  -dk, --provide-domain-knowledge
                                  Provide domain knowledge to the agent.
  -wt, --provide-workflow-tags    Whether to provide workflow tags to the
                                  agent.
  -e, --experiment-name TEXT      Experiment name (directory under logs).
                                  Defaults to timestamp.
  -s, --sample INTEGER            Number of samples per dataset to run (None =
                                  all samples, 1 = first sample).
  --help                          Show this message and exit.
```
> [!NOTE]
> Please note that if requisite data files are not downloaded, the agents will automatically download and set them up. 

<details>

**<summary>:wrench: Usage Examples</summary>**
1. Run the agent on all the samples on all the datasets, specifying the agent name.
``` bash
python3 baseline_agents/main.py --agent-name no_data_agent
```

2. Run the agent on just the first sample of each dataset, specify the number of samples using `--sample` flag.
``` bash
python3 baseline_agents/main.py --agent-name no_data_agent --sample 1
```

3. Run the agent on just one dataset, set `--metadata-path` to a specific dataset directory.
``` bash
python3 baseline_agents/main.py --agent-name no_data_agent --metadata-path neurodiscoverybench/WMB-processed-text
```

4. Run the agent on just one metadata file, set `--metadata-path` to a specific metadata JSON file.
``` bash
python3 baseline_agents/main.py --agent-name no_data_agent --metadata-path neurodiscoverybench/WMB-processed-text/metadata_0.json
```
</details>

> [!NOTE]
> This script will create a new directory called `logs`. Inside this directory, you will find:
>
> - The **agent-generated logs** for the experiment.
> - A **`results.csv`** file containing the instances on which the agent ran.
>
> The `results.csv` file is essential, as it serves as the input required to evaluate the agent’s performance.


### 5. Evaluating Agent-Generated Results

To evaluate the results generated by the agent, use the following command:

```bash
python3 eval/eval.py --help
```
The output will show:
```bash
Usage: eval.py [OPTIONS] AGENT_RESULTS_CSV

  Evaluate agent-generated hypotheses and compute scores for each task.

Options:
  -o, --output-csv PATH  Path to save evaluated CSV file. If not provided, a
                         file with '_evaluated' suffix will be created.

  -m, --eval-model TEXT  Model to use for evaluating the samples.  [default:
                         gpt-4o]

  --help                 Show this message and exit.
```

> [!NOTE]
> The evaluation script will create a new CSV file with `_evaluated` suffix unless a file is explicitly specified using `--output-csv` flag.
> To analyse the scores you need to pass this evaluated CSV to `analyse_scores.py`.

### 6. Analyse the Evaluation Scores

To analyse the evaluation scores, use the following script:

```bash
python3 baseline_agents/utils/analyse_scores.py --help
```

The output will show:

```bash
usage: analyse_scores.py [-h] --input INPUT [--score-col SCORE_COL] [--output-csv OUTPUT_CSV]

options:
  -h, --help            show this help message and exit
  --input, -i INPUT     Path to evaluated CSV
  --score-col SCORE_COL
                        Score column name (default: hms_score)
  --output-csv OUTPUT_CSV
                        Optional: write dataset-level aggregates to CSV
```

## 🧩 Custom Agent Integration

To add your own agent to NeuroDiscoveryBench, follow the setup-by-step guide [here](inference_with_custom_agent.md). It covers plugging in your agent, running inference, and evaluating on all datasets.

## 🤗 Huggingface
Explore BioDiscoveryBench at Huggingface's data viewer TBA

## 📄 License 
The code is licensed under Apache 2.0. The datasets are licensed under [ODC-BY](https://opendatacommons.org/licenses/by/1-0/), and are intended for research and educational use in accordance with Ai2's [Responsible Use Guidelines](https://allenai.org/responsible-use). 

### Source attributions
The datasets are derived from the following datasets originally published and made available by the Allen Institute:
- Allen Brain Cell Atlas (ABC Atlas) Mouse Whole Brain dataset at https://alleninstitute.github.io/abc_atlas_access/intro.html 
- Seattle Alzheimer's Disease Brain Cell Atlas (SEA-AD) at https://brain-map.org/consortia/sea-ad/our-data

It also contains a small subset of the GSE1914118 dataset made available at the NCBI Gene Expression Omnibus (GEO) at https://www.ncbi.nlm.nih.gov/geo/download/?acc=GSE194118 by the authors of the following paper, as part of their supporting data: Evolution of immune genes is associated with the Black Death. Klunk, J., Vilgalys, T.P., Demeure, C.E. et al. Nature 611, 312–319 (2022).  https://doi.org/10.1038/s41586-022-05349-x 


## ✍️ Citation

If you find our work helpful, please use the following citations.
```
@misc{surana2025neurodiscoverybench,
  author    = "Harshit Surana, Bodhisattwa Prasad Majumder, Abhijeetsingh Meena, Nabid Akhtar, Bhavana Dalvi Mishra, Kris Ganjam, Peter Clark",
  title     = "NeuroDiscoveryBench: Benchmarking AI for Neuroscience Data Analysis",
  journal   = "Github",
  howpublished = {\url{https://github.com/allenai/neurodiscoverybench}}
  year      = "2025"
}

```
