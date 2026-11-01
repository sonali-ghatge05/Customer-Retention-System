from google import genai
from dotenv import load_dotenv
import os

# ---------------------------------------
# Load .env
# ---------------------------------------

load_dotenv()

# Get API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: GEMINI_API_KEY was not found.")
    exit()

print("API key loaded successfully.")

# ---------------------------------------
# Create Gemini client
# ---------------------------------------

client = genai.Client(api_key=api_key)


# ---------------------------------------
# Test Customers
# ---------------------------------------

customers = [

    # =====================================
    # CUSTOMER 1 - HIGH RISK
    # =====================================

    {
        "name": "Balendra Pingle",
        "age": 50,
        "location": "Delhi",
        "segment": "Premium",
        "risk_level": "High Risk",
        "confidence": 0.87,
        "total_transactions": 3,
        "average_spend": 1034.97,
        "last_purchase": "24 Jul 2026",
        "average_rating": 2.3,
        "sentiment": "Negative",
        "latest_feedback": (
            "The T-Shirt has defects. Delivery was delayed. "
            "Customer support was unhelpful. Won't buy again."
        )
    },

    # =====================================
    # CUSTOMER 2 - LOW RISK
    # =====================================

    {
        "name": "Rahul Sharma",
        "age": 32,
        "location": "Mumbai",
        "segment": "Regular",
        "risk_level": "Low Risk",
        "confidence": 0.91,
        "total_transactions": 12,
        "average_spend": 1850.50,
        "last_purchase": "05 Aug 2026",
        "average_rating": 4.6,
        "sentiment": "Positive",
        "latest_feedback": (
            "Great product quality and very fast delivery. "
            "Very satisfied."
        )
    },

    # =====================================
    # CUSTOMER 3 - CHURNED
    # =====================================

    {
        "name": "Aryan Maharaj",
        "age": 58,
        "location": "Delhi",
        "segment": "Premium",
        "risk_level": "Churned",
        "confidence": None,
        "total_transactions": 7,
        "average_spend": 2100.75,
        "last_purchase": "15 May 2026",
        "average_rating": 3.1,
        "sentiment": "Negative",
        "latest_feedback": (
            "I was unhappy with my recent experience and "
            "don't plan to purchase again."
        )
    }
]


# ---------------------------------------
# Analyze each customer
# ---------------------------------------

for customer in customers:

    print("\n")
    print("=" * 60)
    print("ANALYZING:", customer["name"])
    print("RISK:", customer["risk_level"])
    print("=" * 60)

    # -----------------------------------
    # Build prompt
    # -----------------------------------

    prompt = f"""
You are a Business Analyst for a Customer Retention System.

Your job is to analyze customer data and provide practical business
strategies that can help improve customer retention, satisfaction,
and potential business value.

IMPORTANT RULES:

1. Do NOT calculate, modify, or contradict the customer's risk level.

2. The risk level and confidence come from our own prediction system.

3. Do NOT invent customer information, transactions, revenue,
   complaints, policies, or financial values.

4. Clearly distinguish between facts provided in the customer data
   and your business recommendations.

5. Base your analysis primarily on the provided customer data.

6. You may make reasonable business interpretations from the data,
   but do not present assumptions as facts.

7. Recommendations must be practical and realistic.

8. Do not assume that a refund, discount, replacement, or compensation
   is automatically allowed. Present such actions as options subject
   to company policy.

9. Do not calculate potential future revenue unless the necessary
   financial data is explicitly provided.

10. Do not use technical machine-learning terminology.

11. If the customer is already Churned, do not recommend normal
    retention actions. Focus specifically on WIN-BACK, reactivation,
    and understanding the reason for churn.

12. If the customer is High Risk, focus on immediate retention actions.

13. If the customer is Medium Risk, focus on preventive retention.

14. If the customer is Low Risk, do not recommend unnecessary urgent
    intervention. Focus on relationship strengthening and loyalty.

15. Keep recommendations specific to the customer's situation.

16. Do not assume that a churned customer has moved to a competitor or intends
    to do so unless the customer data explicitly states this.

CUSTOMER DATA:

Name: {customer["name"]}
Age: {customer["age"]}
Location: {customer["location"]}
Customer Segment: {customer["segment"]}

Risk Level: {customer["risk_level"]}
Prediction Confidence: {customer["confidence"]}

Total Transactions: {customer["total_transactions"]}
Average Spend: ₹{customer["average_spend"]:.2f}
Last Purchase: {customer["last_purchase"]}

Average Rating: {customer["average_rating"]}/5
Latest Sentiment: {customer["sentiment"]}

Latest Customer Feedback:
"{customer["latest_feedback"]}"

Provide the analysis using exactly these sections:

1. BUSINESS SUMMARY
Briefly explain the customer's current situation.

2. KEY PROBLEMS
Identify the main business problems visible in the data.

3. RECOMMENDED ACTIONS
Give 3 practical actions the business should take.

4. RETENTION STRATEGY
Explain the appropriate strategy for this customer.
For a churned customer, provide a WIN-BACK strategy instead.

5. BUSINESS OPPORTUNITY
Explain the potential business value of the recommended strategy.
Do not invent a specific revenue amount.

6. PRIORITY
Give a priority level of Low, Medium, or High and briefly explain why.
"""

    # -----------------------------------
    # Send request to Gemini
    # -----------------------------------

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    # -----------------------------------
    # Display response
    # -----------------------------------

    print("\n========== AI BUSINESS ANALYST ==========\n")

    print(response.text)

    print("\n")
    print("=" * 60)