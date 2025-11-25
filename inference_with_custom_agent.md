# ⭐️ Running a Custom Agent on NeuroDiscoveryBench

This guide provides step-by-step instructions for integrating your **custom agent** into the NeuroDiscoveryBench pipeline, performing inference on benchmark tasks, and evaluating your agent's performance using our provided metrics.

## 1. Prerequisites

Before you begin, please ensure that you have:
- Installed all required Python dependencies (see `README.md` for instructions).
- Downloaded and set up the NeuroDiscoveryBench datasets by running:
    ```bash
    python3 utils/bio_data_loader.py
    ```
  This command will place all necessary datasets in the appropriate directories under `neurodiscoverybench/`.

## 2. Understanding Dataset Structure and Inputs

Each task is represented by a `metadata.json` file located within its respective subdirectory under `neurodiscoverybench/`. There are 69 metadata files in total, each corresponding to a unique inference sample.

Each `metadata.json` file contains the following fields:
- `domain`: The scientific domain (e.g., genomics, biology)
- `workflow tags`: Tags describing workflow steps for the task
- `datasets`: A list, each entry including:
    - `name`: Name of the dataset file
    - `description`: Brief summary of the dataset
    - `columns`: List of dataset columns, each with a name and description
- `queries`: A list, each entry including:
    - `question_type`: Type of scientific question (e.g., relationship)
    - `question`: The question string for the agent to answer

We use the [`format_query`](https://github.com/allenai/neurodiscoverybench/blob/429dd41c0b063db8f440a522d4461fa0fafe0555/baseline_agents/no_data_agent/run_agent.py#L18) function, which takes this metadata JSON dictionary as input and produces a query prompt as output.

## 3. Integrating Your Custom Agent and Performing Inference

### Overview

The standard workflow in NeuroDiscoveryBench consists of two main phases:

**A. Inference**
- Aggregate all metadata files into a unified DataFrame.
- For each row (task) in the DataFrame:
    - Generate a prompt using the metadata and the `format_query` function.
    - Run your agent on the generated prompt.
    - Parse your agent's output (hypothesis and/or image path).
    - Collect results and save them to a CSV file.

**B. Evaluation**
- Evaluate the inference results using our NeuroDiscoveryBench evaluation function.
- Save the evaluated results to a new CSV file.

### You can evaluate your custom agent on NeuroDiscoveryBench in two ways:

#### 1. Wrap your agent as a function and add it to our set of agents
- Wrap your agent in an asynchronous [`run_agent`](https://github.com/allenai/neurodiscoverybench/blob/429dd41c0b063db8f440a522d4461fa0fafe0555/baseline_agents/no_data_agent/run_agent.py#L98) function that takes the appropriate parameters and add it to the [`_AGENTS`](https://github.com/allenai/neurodiscoverybench/blob/429dd41c0b063db8f440a522d4461fa0fafe0555/baseline_agents/main.py#L23) dictionary like this:
    ```python
    _AGENTS = {
        "your_agent": your_agent_wrapper_function,
        ...
    }
    ```
- You do not need to handle inputs and outputs directly; our script will manage this as long as your function accepts the appropriate parameters and returns the expected output.
- Ideally, the function should take the following parameters as input:
    - `data_row`: dictionary containing all the required fields
    - `config_file`: string path to the config file; if your agent has hard-coded configuration and does not require one, you may ignore this
    - `log_file_path`: your agent should log messages to this file, preferably in JSON format
    - `domain_knowledge`: include if your agent needs domain knowledge
    - `workflow_tags`: include if your agent needs workflow tags
- You can copy the sample function and replace `no_data_agent.run()` with your agent's inference method.

#### 2. Use the details of our inference script to write your own integration

1. **Aggregate Metadata**  
   Use the `get_dataset_df` function in [`main.py`](link_to_main.py) to:
    - Traverse all `metadata.json` files.
    - Create a DataFrame where each row corresponds to one query.
    - Add helper columns such as `gold_hypo` (the gold-standard hypothesis) and `gold_image` (reference image, if applicable).

2. **Agent Integration**  
    - For each row, use `format_query` to transform the metadata into an input string for your agent.
    - Call your agent with this input. Your agent should generate a JSON output in the format:
      ```json
      {"hypothesis": "Protein X plays a role in ..."}
      ```
      If your agent also generates an image, save its absolute path for later reference.
    - Parse the agent's output using the [`parse_log`](https://github.com/allenai/neurodiscoverybench/blob/429dd41c0b063db8f440a522d4461fa0fafe0555/baseline_agents/utils/parse_logs.py#L103) function in `parse_logs.py`.
    - Add the generated hypothesis string (`gen_hypo`) and the generated image path (`gen_image`, if applicable) to the DataFrame.

3. **Save Inference Results**  
    - Save the DataFrame as `results.csv` in the directory `logs/EXPERIMENT_NAME/`.

## 4. Required Output Schema (`results.csv`)

Once your agent is integrated and inference is performed, it should create a CSV file with the following schema and save the results as `results.csv` in `logs/EXPERIMENT_NAME/`.

Each row in your `results.csv` file must include the following columns:

- `unique_id`: Concatenated string formed as `<dataset_name>||<metadata_id>||<query_id>`, e.g., `BlackDeath-Immune-fig||2||0`, where:
    - `<dataset_name>`: The dataset's name
    - `<metadata_id>`: The numeric part of the metadata filename, e.g., `metadata_5.json` → `5`
    - `<query_id>`: The index of the question in the queries list
- `dataset`: Dataset file name
- `query`: The query string
- `metadata`: The full metadata dictionary as a JSON string
- `dataset_directory`: List of absolute paths to all datasets required for the task
- `gold_image`: Absolute path to gold/reference image (leave empty if not applicable)
- `gen_image`: Absolute path to generated image (leave empty if not applicable)
- `gold_hypo`: Gold standard hypothesis string
- `gen_hypo`: Your agent's generated hypothesis string
- `hms_score`: Leave empty (to be filled by the evaluation script)
- `eval_result`: Leave empty (to be filled by the evaluation script)

> Note: For tasks that do not use images, leave `gold_image` and `gen_image` blank.

## 5. Running Evaluation

To evaluate the results, use the provided evaluation script:

```bash
python3 eval/eval.py logs/EXPERIMENT_NAME/results.csv
```

Optionally, specify a custom output file and/or evaluation model:
```bash
python3 eval/eval.py logs/EXPERIMENT_NAME/results.csv --output-csv /path/to/evaluated.csv --eval-model gpt-4o
```
The evaluation script will process each row of your `results.csv` and populate the `hms_score` and `eval_result` columns.

The evaluated output will be saved as `/path/to/evaluated.csv` or with a default suffix `_evaluated.csv` in the same directory if not specified.

## 6. Analyzing Results

You can use our analysis script to aggregate scores by dataset or task type:

```bash
python3 baseline_agents/utils/analyse_score.py --input path/to/evaluated.csv
```
This will summarize your agent's performance and can help identify strengths and weaknesses across different tasks.
