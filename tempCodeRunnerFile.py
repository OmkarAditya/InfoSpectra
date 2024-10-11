while True:
    question = input("Enter your question (or 'exit' to quit): ")
    if question.lower() == "exit":
        break
    
    # Query the QA system with the user's question
    result = qa_chain.invoke({"query": question})

    print(result)