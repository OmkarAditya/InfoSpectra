from langchain import PromptTemplate
from langchain.chains import RetrievalQA
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS  
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

import os
import tempfile
from dotenv import load_dotenv
from firebase_admin import storage

# Cache to store answers based on file name and query
cache = {}

def get_cached_answer(file_name, query):
    # Check if a cached answer exists for the given file name and query
    cache_key = f"{file_name}:{query}"
    return cache.get(cache_key)

def set_cached_answer(file_name, query, answer):
    # Cache the answer using file name and query as the key
    cache_key = f"{file_name}:{query}"
    cache[cache_key] = answer

def initialize_qa_chain(user_query):
    load_dotenv()
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    llm = ChatGoogleGenerativeAI(
        model="gemini-pro",
        google_api_key=GOOGLE_API_KEY,
        temperature=0.2,
        convert_system_message_to_human=True
    )

    bucket = storage.bucket()
    blobs = bucket.list_blobs(prefix='pdfs/')
    pdf_files = [blob for blob in blobs if blob.name.endswith('.pdf')]
    latest_pdf_blob = max(pdf_files, key=lambda b: b.updated, default=None)

    if latest_pdf_blob is None:
        raise Exception("No PDF files found in Firebase Storage.")

    file_name = latest_pdf_blob.name

    # Check for cached answer before processing
    cached_answer = get_cached_answer(file_name, user_query)
    if cached_answer:
        return cached_answer  # Return cached answer if it exists

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        latest_pdf_blob.download_to_file(temp_file)
        temp_file_path = temp_file.name

    pdf_loader = PyPDFLoader(temp_file_path)
    pages = pdf_loader.load_and_split()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    context = "\n\n".join(str(p.page_content) for p in pages)
    texts = text_splitter.split_text(context)

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=GOOGLE_API_KEY
    )
    vector_index = FAISS.from_texts(texts, embeddings).as_retriever(search_kwargs={"k": 5})

    template = """Use the following pieces of context to answer the question at the end. 
    If you don't know the answer, just say that you don't know, don't try to make up an answer. 
    Keep the answer as concise as possible. Always say "thanks for asking!" at the end of the answer.

    Context:
    {context}

    Question: {question}
    Top K Results: 5
    Threshold: 0.2

    Provide the top 5 answers based on the context, where each answer should include:
    1. The answer text.
    2. The similarity score of the answer.

    Only include results where the similarity score is greater than or equal to the threshold, also give each answer in new line. 

    Format your response as a list of answers with their similarity scores:
    1. Answer 1: [Answer Text] (Score: [Similarity Score])
    2. Answer 2: [Answer Text] (Score: [Similarity Score])
    ...
    5. Answer 5: [Answer Text] (Score: [Similarity Score])

    If no results meet the threshold, say "No relevant answers found." 
    Thanks for asking!"""

    QA_CHAIN_PROMPT = PromptTemplate.from_template(template)

    qa_chain = RetrievalQA.from_chain_type(
        llm,
        retriever=vector_index,
        return_source_documents=True,
        chain_type_kwargs={"prompt": QA_CHAIN_PROMPT}
    )

    # Retrieve answer from the QA chain
    result = qa_chain({"query": user_query})["result"]

    # Cache the result with file name and query
    set_cached_answer(file_name, user_query, result)

    return result
