from langchain import PromptTemplate
from langchain.chains import RetrievalQA
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

import os
from dotenv import load_dotenv

def initialize_qa_chain():
    # Load environment variables from .env file
    load_dotenv()

    # Extract the GOOGLE_GEMINI_KEY from .env file
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    # Initialize the LLM (Google Gemini Pro) with API key
    llm = ChatGoogleGenerativeAI(
        model="gemini-pro",
        google_api_key=GOOGLE_API_KEY,
        temperature=0.2,
        convert_system_message_to_human=True
    )

    # Load the PDF document and split it into pages
    pdf_loader = PyPDFLoader("./data/doc.pdf")
    pages = pdf_loader.load_and_split()

    # Split text into chunks with overlap for better retrieval context
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    context = "\n\n".join(str(p.page_content) for p in pages)
    texts = text_splitter.split_text(context)

    # Create embeddings for text chunks using Google Generative AI Embeddings
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=GOOGLE_API_KEY
    )
    vector_index = Chroma.from_texts(texts, embeddings).as_retriever(search_kwargs={"k": 5})

    # Define the prompt template for answering questions based on retrieved documents
    template = """Use the following pieces of context to answer the question at the end. 
    If you don't know the answer, just say that you don't know, don't try to make up an answer. 
    Keep the answer as concise as possible. Always say "thanks for asking!" at the end of the answer.

    Context:
    {context}

    Question: {question}
    Top K Results: 5
    Threshold: 0.5

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

    # Create a QA chain combining the LLM and retriever for context-based question answering
    qa_chain = RetrievalQA.from_chain_type(
        llm,
        retriever=vector_index,
        return_source_documents=True,
        chain_type_kwargs={"prompt": QA_CHAIN_PROMPT}
    )

    return qa_chain
