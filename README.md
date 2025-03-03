Example code to get us started with RAG LLM for our Capstone Project.

You will need to setup a Microsoft Azure account and create LLM instance in Azure AI Foundry. This will get you your LLM endponts and word vector embedding models. 

https://azure.microsoft.com/en-us/pricing/purchase-options/azure-account?icid=ai-foundry

1. In terminal, type: pip install -r requirements.txt
2. In python code, replace Microsoft Azure Endpoint with your credentials. For example, change the following in the python code.

(Lines 27 - 30)
- os.environ["AZURE_OPENAI_ENDPOINT"] = "https://ai-dltorrecampo3215ai914253886295.openai.azure.com/openai/deployments/gpt-4o-mini-2/chat/completions?api-version=2024-08-01-preview"
- os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "gpt-4o-mini"
- os.environ["AZURE_OPENAI_API_VERSION"] = "2024-08-01-preview"

(Lines 49 - 53)
- os.environ["AZURE_OPENAI_ENDPOINT"] = "https://ai-dltorrecampo3215ai914253886295.openai.azure.com/openai/deployments/text-embedding-3-large-2/embeddings?api-version=2023-05-15"
- os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "text-embedding-3-large"
- os.environ["AZURE_OPENAI_API_VERSION"] = "2023-05-15"

3. Run python code. Python code will ask for your API Key in terminal. Enter your API Key.
