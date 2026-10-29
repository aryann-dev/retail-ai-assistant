from flask import Flask, request, jsonify, render_template
from groq import Groq
from dotenv import load_dotenv
import os
from business import get_ai_reply, get_dashboard_data, get_sales_analytics

load_dotenv()

app = Flask(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    reply = get_ai_reply(user_message)
    return jsonify({"reply": reply})

@app.route("/sales-data")
def sales_data():
    data = get_sales_analytics()
    return jsonify(data)

@app.route("/dashboard-data")
def dashboard_data():
    data = get_dashboard_data()
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)
