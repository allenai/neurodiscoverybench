# 🧬 NeuroDiscoveryBench Benchmark Datasets

## 🗂️ Structure

Each folder in `neurodiscoverybench/` represents a subset of benchmark tasks built from a specific **Allen Institute** publication.

| Folder                      | Description                                                                                                                                                       |
| :-------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`WMB-raw-text`**          | Text-based tasks from the *Whole Mouse Brain Atlas*, using raw data that requires substantial data wrangling and filtering by the agent.                |
| **`WMB-raw-fig`**           | Visualization tasks from raw WMB data, requiring code-to-figure generation based on unprocessed datasets.                                                         |
| **`WMB-raw-no-traces`**     | Harder WMB subset without ececution traces, extracted directly from the paper for testing benchmark robustness.                                                   |
| **`WMB-processed-text`**    | Text based tasks on preprocessed WMB data, where intermediate cleaning and aggregation steps are already applied.                                             |
| **`WMB-processed-fig`**     | Visualization tasks from preprocessed WMB data, allowing agents to focus on analysis and figure accuracy rather than preprocessing.                               |
| **`SEA-AD-text`**           | Text-based tasks from the *Seattle Alzheimer’s Disease (SEA-AD)* atlas, focusing on TBA (multimodal relationships across pathology, gene expression, and cell classes.) |
| **`SEA-AD-fig`**            | Visualization tasks from SEA-AD exploring Braak/Thal staging and cell-class distributions across disease progression.                                             |
| **`BlackDeath-Immune-fig`** | Figure-generation tasks from *Evolution of Immune Genes and the Black Death*, analyzing evolutionary signals in immune gene variants.                             |


  TODO: Add numbers to the table 
---

## 🧩 Naming Conventions

Datasets are organized along three key axes:

* **Source paper:**

  * **WMB** → *Whole Mouse Brain Atlas* (Yao et al., 2023)
  * **SEA-AD** → *Seattle Alzheimer’s Disease Atlas* (Gabitto et al., 2024)
  * **BlackDeath-Immune** → *Evolution of Immune Genes and the Black Death* (Klunk et al., 2022)
* **Task type:**

  * **text** → hypothesis or textual reasoning tasks
  * **fig** → visualization or figure-generation tasks
* **Data processing level (for WMB):**

  * **raw** → agents must perform heavy data manipulation directly on the raw dataset
  * **processed** → intermediate preprocessing performed, simplifying analysis
  * **no-traces** → harder questions without execution traces (extracted directly from the paper)
