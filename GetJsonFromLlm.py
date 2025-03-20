
def get_json_plaintext(plaintxt):
    import os
    from langchain import hub
    from langchain_openai import ChatOpenAI
    
    json = ''
    system_prompt = """Create a JSON for the information available in the below text. Include all information in the JSON.\n\n"""
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.environ.get("OPENAI_API_KEY"))
    prompt = system_prompt + plaintxt
    result = llm.invoke(prompt).content
    content = str(result)
    content_string = content.replace("\\n", "\n").replace("\\'", "'").replace("\\\"", "\"")

    json = extract_json(content_string)
    return json

def get_json(pdf_file_path):
    json = ''
    system_prompt = """Create a JSON for the information available in the document. Include all information in the JSON."""
    model="gpt-4o-mini"
    result = get_llm_response(pdf_file_path, model, system_prompt)
    content = str(result)
    content_string = content.replace("\\n", "\n").replace("\\'", "'").replace("\\\"", "\"")

    json = extract_json(content_string)
    return json

def get_food_json(pdf_file_path):
    json = ''
    system_prompt = """Create a JSON for the food description and amount. Do not include other information in the JSON."""
    model="gpt-4o-mini"
    result = get_llm_response(pdf_file_path, model, system_prompt)
    content = str(result)
    content_string = content.replace("\\n", "\n").replace("\\'", "'").replace("\\\"", "\"")

    json = extract_json(content_string)
    return json

def get_llm_response(pdf_file_path, model, system_prompt):
    import os
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings
    from langchain_core.vectorstores import InMemoryVectorStore
    from langchain import hub
    from langchain_openai import ChatOpenAI
    
    loader = PyPDFLoader(pdf_file_path)
    docs = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,  
        chunk_overlap=20,  
        add_start_index=True,  
    )
    all_splits = text_splitter.split_documents(docs)

    #ingestion
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=os.environ.get("OPENAI_API_KEY"))
    vector_store = InMemoryVectorStore(embeddings)
    vector_store.add_documents(documents=all_splits)
    
    prompt = hub.pull("rlm/rag-prompt", api_key=os.environ.get("OPENAI_API_KEY"))
    system_prompt = system_prompt
    retrieved_docs = vector_store.similarity_search(system_prompt)
    docs_content = "\n\n".join(doc.page_content for doc in retrieved_docs)
    prompt = prompt.invoke({"context": docs_content, "question": system_prompt})

    # initialize the llm
    llm = ChatOpenAI(model=model)

    return llm.invoke(prompt)

def extract_json(text):
    import re
    
    match = re.search(r'```json\n({.*?})\n```', text, re.DOTALL)
    if match:
        return match.group(1)
    return None

# To test PDF
# pdf_file_path = "./Food and Beverage Diary Cover Sheet.pdf"
# print(get_json(pdf_file_path))
# print(get_food_json(pdf_file_path))

# To test plaintext
# plaintext = '''Name: Jane Doe Date: 3/9/2025
# Telephone: 214.920.9999
# Physician: Sarah Connor
# Physician phone: 888.777.6666
# Height: 180 inches
# Weight: 172 lbs
# DOB: 09/09/1979
# Age: 46 years
# 24-hr Diet Recall
# Time	Place	Amount	Food Description	Notes
# 8 am	Kitchen	¾ cup	Raisin Bran	
# 		½ cup	Apple juice	
# 		1 medium	Fresh peach	
# 12 pm	Dining table	½ cup	Ground beef	
# 		1 cup	Mushroom stew	
# 		½ cup	Rice	
# 		¼ cup	Green beans	
# 		8 oz	Water	
# 4 pm	Kitchen	½ cup	Pretzels	
# 		1 oz	Chocolate	
# 7 pm	Dining table	1 cup	Spaghetti	
# 		½ cup	Ground beef	
# 		8 oz	Water	
				
# '''
# print(get_json_plaintext(plaintext))