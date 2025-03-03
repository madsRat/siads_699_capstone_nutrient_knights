"""
Example RAG LLM from Lang Chain using MS Azure OpenAI
Source: https://python.langchain.com/docs/tutorials/rag/
Date Created: 2/11/2025
Last Modified: 3/2/2025
"""

# temporary solution to address 'RateLimit Error'
from langchain_core.rate_limiters import InMemoryRateLimiter
rate_limiter = InMemoryRateLimiter(
    requests_per_second=0.05,  # <-- Super slow! We can only make a request once every 10 seconds!! 0.1
    check_every_n_seconds=0.05,  # Wake up every 100 ms to check whether allowed to make a request, 0.1
    max_bucket_size=10,  # Controls the maximum burst size.
)





import getpass
import os

if not os.environ.get("AZURE_OPENAI_API_KEY"):
  os.environ["AZURE_OPENAI_API_KEY"] = getpass.getpass("Enter API key for Azure: ")

from langchain_openai import AzureChatOpenAI
os.environ[
    "AZURE_OPENAI_ENDPOINT"] = "https://ai-dltorrecampo3215ai914253886295.openai.azure.com/openai/deployments/gpt-4o-mini-2/chat/completions?api-version=2024-08-01-preview"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "gpt-4o-mini"
os.environ["AZURE_OPENAI_API_VERSION"] = "2024-08-01-preview"

llm = AzureChatOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    rate_limiter=rate_limiter,
    max_tokens=300
)





from langchain_openai import AzureOpenAIEmbeddings
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://ai-dltorrecampo3215ai914253886295.openai.azure.com/openai/deployments/text-embedding-3-large-2/embeddings?api-version=2023-05-15"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "text-embedding-3-large"
os.environ["AZURE_OPENAI_API_VERSION"] = "2023-05-15"

embeddings = AzureOpenAIEmbeddings(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"]
)




from langchain_core.vectorstores import InMemoryVectorStore
vector_store = InMemoryVectorStore(embeddings)





import bs4
from langchain import hub
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import START, StateGraph
from typing_extensions import List, TypedDict

# Load and chunk contents of the blog
loader = WebBaseLoader(
    web_paths=("https://lilianweng.github.io/posts/2023-06-23-agent/",),
    bs_kwargs=dict(
        parse_only=bs4.SoupStrainer(
            class_=("post-content", "post-title", "post-header")
        )
    ),
)
docs = loader.load()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
all_splits = text_splitter.split_documents(docs)

# Index chunks
_ = vector_store.add_documents(documents=all_splits)

# Define prompt for question-answering
prompt = hub.pull("rlm/rag-prompt")

# Define state for application
class State(TypedDict):
    question: str
    context: List[Document]
    answer: str

# Define application steps
def retrieve(state: State):
    retrieved_docs = vector_store.similarity_search(state["question"])
    return {"context": retrieved_docs}

def generate(state: State):
    docs_content = "\n\n".join(doc.page_content for doc in state["context"])
    messages = prompt.invoke({"question": state["question"], "context": docs_content})
    response = llm.invoke(messages)
    return {"answer": response.content}

# Compile application and test
graph_builder = StateGraph(State).add_sequence([retrieve, generate])
graph_builder.add_edge(START, "retrieve")
graph = graph_builder.compile()




response = graph.invoke({"question": "What is Task Decomposition?"})
print(response["answer"])




response = graph.invoke({"question": "Whats the difference between retrieval and reflection in generative agents simulation?"})
print(response["answer"])

