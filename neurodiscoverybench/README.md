# 🧬 NeuroDiscoveryBench Benchmark Datasets

## 🗂️ Structure

Each folder in `neurodiscoverybench` represents a subset of benchmark tasks - each of which include metadata, dataset files and benchmark questions. **NOTE** for the WMB* directories, the dataset files are not present in this repository (as they are large) and need to be downloaded using utils/bio_data_loader.py, see the top-level README.md for instructions. 

| **Benchmark Folder**        | **Question Count** | **Subset Description**                                                                                                                                                                            |
| :-------------------------- | :-------: | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`SEA-AD-text`**           |     7     | Tasks from the *Seattle Alzheimer’s Disease (SEA-AD)* atlas. All the hypotheses in this folder are text based.                    |
| **`SEA-AD-fig`**            |     3     | Figure output based tasks from SEA-AD exploring Braak/Thal staging etc. across disease progression.                                                                      |
| **`BlackDeath-Immune-fig`** |     5     | Figure-generation tasks from *Evolution of Immune Genes and the Black Death*, analyzing evolutionary signals in immune gene variants.                                                      |
| **`WMB-raw-text`**          |     4     | Tasks from the *Whole Mouse Brain Atlas*, using raw data that requires substantial data wrangling and filtering by the agent. All the hypotheses in this folder are text based. |
| **`WMB-raw-fig`**           |     18    | Visualization tasks from raw WMB data, requiring figure generation based on unprocessed datasets.                                                                                  |
| **`WMB-raw-no-traces`**     |     10    | Harder WMB subset without gold execution traces, extracted directly from the paper for validating benchmark robustness.                                                                            |
| **`WMB-processed-text`**    |     4     | Text-based tasks on preprocessed WMB data, where intermediate cleaning and aggregation steps are already applied for easier further analysis.                                                                          |
| **`WMB-processed-fig`**     |     18    | Figure output based tasks from preprocessed WMB data, allowing agents to focus on basic analysis and visualization.                                     |



## 🧩 Naming Conventions

Datasets are organized along three key axes (paper, task-type, data-level):

* **Source paper:**

  * **WMB** → *Whole Mouse Brain Atlas* (Yao et al., 2023)
  * **SEA-AD** → *Seattle Alzheimer’s Disease Atlas* (Gabitto et al., 2024)
  * **BlackDeath-Immune** → *Evolution of Immune Genes and the Black Death* (Klunk et al., 2022)
* **Task type:**

  * **text** → text based output
  * **fig** → figure based output 
* **Data processing level (not applicable for all):**

  * **raw** → agents must perform heavy data manipulation directly on the raw dataset
  * **processed** → intermediate preprocessing performed, simplifying analysis
  * **no-traces** → generally harder questions without gold execution traces extracted from the paper
