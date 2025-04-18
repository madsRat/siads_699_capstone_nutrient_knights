import os
import re
import json

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain import hub
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser

# from code_profiler import timeit

def get_json_plaintext(plaintxt):

    """
    :param plaintxt: 24-hour diet recall
    :return: structured json file in results directory
    """

    system_prompt = """Create a JSON for the information available in the below text. Include all information in the JSON.\n\n
    Adhere to the following JSON structure:
{
  "patient": {
    "name": "May Day",
    "date": "9/3/2024",
    "telephone": "204.900.6666",
    "physician": {
      "name": "John Doe",
      "phone": "555.666.7777"
    },
    "height": "150 inches",
    "weight": "142 lbs",
    "dob": "09/06/1979",
    "age": "46 years",
    "sex": "Female",
    "activity level": "Active"
  },
  "diet_recall": [
    {
      "time": "6 am",
      "place": "Kitchen",
      "items": [
        {
          "amount": "¾ cup",
          "food_description": "Raisin Bran",
          "notes": ""
        },
        {
          "amount": "½ cup",
          "food_description": "Mango juice",
          "notes": ""
        },
        {
          "amount": "1 medium",
          "food_description": "Fresh apple",
          "notes": ""
        }
      ]
    },
    {
      "time": "12 pm",
      "place": "Dining table",
      "items": [
        {
          "amount": "½ cup",
          "food_description": "Ground pork",
          "notes": ""
        },
        {
          "amount": "1 cup",
          "food_description": "Cauliflower stew",
          "notes": ""
        },
        {
          "amount": "½ cup",
          "food_description": "Rice",
          "notes": ""
        },
        {
          "amount": "¼ cup",
          "food_description": "Green beans",
          "notes": ""
        },
        {
          "amount": "8 oz",
          "food_description": "Water",
          "notes": ""
        }
      ]
    },
    {
      "time": "4 pm",
      "place": "Kitchen",
      "items": [
        {
          "amount": "½ cup",
          "food_description": "Pretzels",
          "notes": ""
        },
        {
          "amount": "1 oz",
          "food_description": "Chocolate",
          "notes": ""
        }
      ]
    },
    {
      "time": "7 pm",
      "place": "Dining table",
      "items": [
        {
          "amount": "1 cup",
          "food_description": "Spaghetti",
          "notes": ""
        },
        {
          "amount": "½ cup",
          "food_description": "Ground beef",
          "notes": ""
        },
        {
          "amount": "8 oz",
          "food_description": "Water",
          "notes": ""
        }
      ]
    }
  ]
}
    """

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.environ.get("OPENAI_API_KEY"))
    prompt = system_prompt + plaintxt
    result = llm.invoke(prompt).content

    json_txt = extract_json(result) # content_string

    python_dict = json.loads(json_txt)

    if python_dict['patient']['name'] == "May Day":
        print('Not a valid diet recall. Please try again.')
    else:
        with open('results/llm_output_data.json', 'w') as outfile:
            json.dump(python_dict, outfile, indent=4)
            print('JSON FILE EXPORTED')
    return None

def get_json(pdf_file_path):

    """
    :param pdf: 24-hour diet recall
    :return: structured json file in results directory
    """

    json = ''
    system_prompt = """Create a JSON for the information available in the document. Include all information in the JSON.
     Adhere to the following JSON structure:
{
  "patient": {
    "name": "May Day",
    "date": "9/3/2024",
    "telephone": "204.900.6666",
    "physician": {
      "name": "John Doe",
      "phone": "555.666.7777"
    },
    "height": "150 inches",
    "weight": "142 lbs",
    "dob": "09/06/1979",
    "age": "46 years"
    "sex": "Female"
    "activity level": "Active"
  },
  "diet_recall": [
    {
      "time": "6 am",
      "place": "Kitchen",
      "items": [
        {
          "amount": "¾ cup",
          "food_description": "Raisin Bran",
          "notes": ""
        },
        {
          "amount": "½ cup",
          "food_description": "Mango juice",
          "notes": ""
        },
        {
          "amount": "1 medium",
          "food_description": "Fresh apple",
          "notes": ""
        }
      ]
    },
    {
      "time": "12 pm",
      "place": "Dining table",
      "items": [
        {
          "amount": "½ cup",
          "food_description": "Ground pork",
          "notes": ""
        },
        {
          "amount": "1 cup",
          "food_description": "Cauliflower stew",
          "notes": ""
        },
        {
          "amount": "½ cup",
          "food_description": "Rice",
          "notes": ""
        },
        {
          "amount": "¼ cup",
          "food_description": "Green beans",
          "notes": ""
        },
        {
          "amount": "8 oz",
          "food_description": "Water",
          "notes": ""
        }
      ]
    },
    {
      "time": "4 pm",
      "place": "Kitchen",
      "items": [
        {
          "amount": "½ cup",
          "food_description": "Pretzels",
          "notes": ""
        },
        {
          "amount": "1 oz",
          "food_description": "Chocolate",
          "notes": ""
        }
      ]
    },
    {
      "time": "7 pm",
      "place": "Dining table",
      "items": [
        {
          "amount": "1 cup",
          "food_description": "Spaghetti",
          "notes": ""
        },
        {
          "amount": "½ cup",
          "food_description": "Ground beef",
          "notes": ""
        },
        {
          "amount": "8 oz",
          "food_description": "Water",
          "notes": ""
        }
      ]
    }
  ]
}
    """
    model="gpt-4o-mini"
    result = get_llm_response(pdf_file_path, model, system_prompt).content
    json_txt = extract_json(result) # content_string

    python_dict = json.loads(json_txt)

    if python_dict['patient']['name'] == "May Day":
        print('Not a valid diet recall. Please try again.')
    else:
        with open('results/llm_output_data.json', 'w') as outfile:
            json.dump(python_dict, outfile, indent=4)
            print('JSON FILE EXPORTED')
    return None

def get_food_json(pdf_file_path):

    """
    :param pdf: gets food description and amounts
    :return: structured json file in results directory
    """

    json_1 = ''
    system_prompt = """Create a JSON for the food description and amount. Do not include other information in the JSON."""
    model="gpt-4o-mini"
    result = get_llm_response(pdf_file_path, model, system_prompt)
    content = str(result)
    content_string = content.replace("\\n", "\n").replace("\\'", "'").replace("\\\"", "\"")
    json_1 = extract_json(content_string)

    return json_1

def get_llm_response(pdf_file_path, model, system_prompt):

    """
    :param pdf_file_path:
    :param model: OpenAI model
    :param system_prompt:
    :return: llm prompt
    """
    
    loader = PyPDFLoader(pdf_file_path)
    docs = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,  
        chunk_overlap=20,  
        add_start_index=True,  
    )
    all_splits = text_splitter.split_documents(docs)

    # ingestion
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=os.environ.get("OPENAI_API_KEY"))
    vector_store = InMemoryVectorStore(embeddings)
    vector_store.add_documents(documents=all_splits)
    
    prompt = hub.pull("rlm/rag-prompt", api_key=os.environ.get("OPENAI_API_KEY"))
    parser = JsonOutputParser()
    system_prompt = system_prompt
    retrieved_docs = vector_store.similarity_search(system_prompt)
    docs_content = "\n\n".join(doc.page_content for doc in retrieved_docs)
    prompt = prompt.invoke({"context": docs_content, "question": system_prompt, "format_instructions": parser.get_format_instructions()})

    # initialize the llm
    llm = ChatOpenAI(model=model, temperature=0)

    return llm.invoke(prompt)

def extract_json(text):

    """
    :param text:
    :return: json
    """

    match = re.search(r'```json\n({.*?})\n```', text, re.DOTALL)
    if match:
        return match.group(1)
    return None
