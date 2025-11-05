# Baseline Agents

We run NeuroDiscoveryBench on a set of **baseline agents** as well as on **DataVoyager** [(link)]() to evaluate how well large language models (LLMs) can generate scientific hypotheses under different information constraints.
Baseline agents include:

## No Data Agent

The **No Data Agent** tests how much the model can reason based solely on its **pretrained knowledge** of the domain.  
This agent **does not have access to any datasets** when generating hypotheses.  
It serves as a control to measure the model’s intrinsic scientific understanding of neuroscience, without any additional context.

## No Data + Search Agent

The **No Data + Search Agent** also operates **without direct dataset access**, but it is equipped with a [**web search tool**](https://platform.openai.com/docs/guides/tools-web-search?api-mode=responses).  
This allows the agent to **gather relevant information and citations** from the web to inform its hypotheses.  
It helps assess how access to external information sources influences the agent's reasoning and the correctness of its hypotheses.

