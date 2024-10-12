# while True:
#     question = input("Enter your question (or 'exit' to quit): ")
#     if question.lower() == "exit":
#         break
    
#     # Query the QA system with the user's question
#     result = qa_chain.invoke({"query": question})
#     # Extract the 'result' field, which contains the answers and similarity scores
#     answers = result.get('result', 'No answers found.')
#     # Print the answers only, excluding source documents
#     print(answers)



# from flask import Flask, request, jsonify, render_template
# from dotenv import load_dotenv
# from pymongo import MongoClient
# from datetime import datetime
# import warnings
# import os

# # Import the function from query.py
# from query import initialize_qa_chain

# warnings.filterwarnings("ignore")

# # Load environment variables
# load_dotenv()

# # MongoDB setup
# MONGO_URI = os.getenv("MONGO_URI")
# client = MongoClient(MONGO_URI)
# db = client.get_database()
# user_collection = db.users
# query_collection = db.queries

# app = Flask(__name__)

# # Initialize QA chain
# qa_chain = initialize_qa_chain()

# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/user', methods=['POST'])
# def handle_user():
#     data = request.get_json()
#     user_type = data.get('user_type')
#     user_name = data.get('user_name', '')

#     if user_type == 'new':
#         user_id = f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}"
#         user_collection.insert_one({"user_id": user_id, "frequency": 1, "user_name": user_name})
#         return jsonify({"status": "new", "user_id": user_id})
#     elif user_type == 'old':
#         user_id = data.get('user_id', '')
#         user = user_collection.find_one({"user_id": user_id})
#         if user:
#             if user['frequency'] >= 5:
#                 return jsonify({"error": "User limit exceeded"}), 403
#             user_collection.update_one({"user_id": user_id}, {"$inc": {"frequency": 1}})
#             return jsonify({"status": "existing", "user_id": user_id})
#         else:
#             return jsonify({"error": "User not found"}), 404
#     else:
#         return jsonify({"error": "Invalid user type"}), 400

# @app.route('/ask', methods=['POST'])
# def ask_question():
#     try:
#         data = request.get_json()
#         user_id = data.get('user_id', '')
#         question = data.get('question', '')

#         if not user_id:
#             return jsonify({"error": "User ID is required"}), 400

#         user = user_collection.find_one({"user_id": user_id})
#         if user:
#             if user['frequency'] >= 5:
#                 return jsonify({"error": "User limit exceeded"}), 403
#             user_collection.update_one({"user_id": user_id}, {"$inc": {"frequency": 1}})
#         else:
#             return jsonify({"error": "User not found"}), 404

#         # Use the qa_chain object initialized from query.py
#         result = qa_chain({"query": question})

#         query_collection.insert_one({
#             "user_id": user_id,
#             "question": question,
#             "answer": result["result"],
#             "timestamp": datetime.utcnow()
#         })

#         return jsonify({
#             'answer': result["result"],
#             'sources': [doc.page_content for doc in result["source_documents"]]
#         })

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# @app.route('/search')
# def queries():
#     return render_template('queries.html')

# @app.route('/user/queries', methods=['POST'])
# def get_user_queries():
#     data = request.get_json()
#     user_id = data.get('user_id', '')

#     if not user_id:
#         return jsonify({"error": "User ID is required"}), 400

#     queries = list(query_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(5))
#     return jsonify({
#         'queries': [{"question": q["question"], "answer": q["answer"], "timestamp": q["timestamp"].strftime('%Y-%m-%d %H:%M:%S')} for q in queries]
#     })

# if __name__ == "__main__":
#     app.run(debug=True)
