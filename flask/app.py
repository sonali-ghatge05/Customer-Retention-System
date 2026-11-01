from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_mysqldb import MySQL
import pickle
import pandas as pd
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
import io
from io import BytesIO
import os
from dotenv import load_dotenv
import tempfile
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether, HRFlowable
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.pagesizes import A3,A4, landscape
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from google import genai
import markdown


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY was not found.")

client = genai.Client(api_key=api_key)

def generate_ai_analysis(customer_data):

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

Name: {customer_data["name"]}
Age: {customer_data["age"]}
Gender: {customer_data["gender"]}
Location: {customer_data["location"]}
Customer Segment: {customer_data["segment"]}
Join Date: {customer_data["join_date"]}

Risk Level: {customer_data["risk_status"]}
Prediction Confidence: {customer_data["risk_confidence"]}

Total Transactions: {customer_data["total_transactions"]}
Average Spend: ₹{customer_data["average_spend"]:.2f}
Last Purchase: {customer_data["last_purchase"]}

Average Rating: {customer_data["average_rating"]}/5
Latest Sentiment: {customer_data["sentiment"]}

Latest Customer Feedback:
"{customer_data["latest_feedback"]}"

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

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    return response.text

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

app.config["MYSQL_HOST"] = os.getenv("MYSQL_HOST")
app.config["MYSQL_USER"] = os.getenv("MYSQL_USER")
app.config["MYSQL_PASSWORD"] = os.getenv("MYSQL_PASSWORD")
app.config["MYSQL_DB"] = os.getenv("MYSQL_DB")
app.config["MYSQL_PORT"] = int(os.getenv("MYSQL_PORT", 3306))
app.config["MYSQL_CUSTOM_OPTIONS"] = {"ssl_mode": "REQUIRED"}

mysql = MySQL(app)

with open('model.pkl', 'rb') as f:
    model = pickle.load(f)

with open ('le_gender.pkl', 'rb') as f:
    le_gender = pickle.load(f)

with open('le_location.pkl', 'rb') as f:
    le_location = pickle.load(f)

with open('le_segment.pkl', 'rb') as f:
    le_segment = pickle.load(f)

@app.route("/")
def home():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM Customers")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Customers WHERE churned = 1")
    churned = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM Customers WHERE churned = 0")
    retained = cursor.fetchone()[0]
    
    cursor.close()
    churn_rate = round((churned / total) * 100, 1) if total > 0 else 0
    return render_template("home.html", total=total, churned=churned, retained=retained, churn_rate=churn_rate)

@app.route("/customers")
def customers():
    if not session.get('logged_in'):
        flash("Please login first", "error")
        return redirect(url_for('login'))

    search = request.args.get("q", "").strip()
    cursor = mysql.connection.cursor()
    if search.isdigit():
        cursor.execute("""
            SELECT c.*, r.risk_level, r.confidence
            FROM Customers c
            LEFT JOIN (
                SELECT customer_id, risk_level, confidence
                FROM Retention_Alerts
                WHERE (customer_id, predicted_on) IN (
                    SELECT customer_id, MAX(predicted_on)
                    FROM Retention_Alerts
                    GROUP BY customer_id
                )
            ) r ON c.customer_id = r.customer_id
            WHERE c.customer_id = %s
            ORDER BY c.customer_id
        """, (int(search),))
    else:
        cursor.execute("""
            SELECT c.*, r.risk_level, r.confidence
            FROM Customers c
            LEFT JOIN (
                SELECT customer_id, risk_level, confidence
                FROM Retention_Alerts
                WHERE (customer_id, predicted_on) IN (
                    SELECT customer_id, MAX(predicted_on)
                    FROM Retention_Alerts
                    GROUP BY customer_id
                )
            ) r ON c.customer_id = r.customer_id
            WHERE
                c.name LIKE %s OR
                c.email LIKE %s OR
                c.segment LIKE %s OR
                c.gender LIKE %s OR
                c.location LIKE %s
            ORDER BY c.customer_id
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ))
    customers = cursor.fetchall()
    cursor.close()

    if search and len(customers) == 0:
        flash("No matching customer found.", "warning")

    return render_template("customers.html",customers=customers,search=search)

@app.route("/add-customers", methods = ["GET", "POST"])
def add_customers():
    if not session.get('logged_in'):
        flash("Please login first","error")
        return redirect(url_for('login'))
    
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        join_date = request.form["join_date"]
        segment = request.form["segment"]
        churned = 0
        location = request.form["location"]
        age = int(request.form["age"])
        gender = request.form["gender"]

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO Customers (name, email, join_date, segment, churned, location, age, gender) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (name, email, join_date, segment, churned, location, age, gender) )
        mysql.connection.commit()
        cursor.close()

        flash("Customers added successfully", "success")
        return redirect(url_for("customers"))
    return render_template("add_customers.html")

@app.route("/delete-customers/<int:customer_id>", methods = ["GET"])
def delete_cusromers(customer_id):
    if not session.get('logged_in'):
        flash("Please login first","error")
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM Customers WHERE customer_id = %s", (customer_id,))
    mysql.connection.commit()
    cursor.close()
    flash("Customer Deleted successfully", "success")
    return redirect(url_for("customers"))

@app.route("/update-customers/<int:customer_id>", methods = ["GET","POST"])
def update_customers(customer_id):
    if not session.get('logged_in'):
            flash("Please login first","error")
            return redirect(url_for('login'))
    
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        join_date = request.form["join_date"]
        segment = request.form["segment"]
        churned = request.form["churned"]
        location = request.form["location"]
        age = int(request.form["age"])
        gender = request.form["gender"]

        cursor = mysql.connection.cursor()
        cursor.execute("""
            UPDATE Customers
            SET name=%s, email=%s, join_date=%s, segment=%s, churned=%s, location=%s, age=%s, gender=%s
            WHERE customer_id=%s
        """, (name, email, join_date, segment, churned, location, age, gender, customer_id))
        mysql.connection.commit()
        cursor.close()
        flash("customer Updated Successfully", "success")
        return redirect(url_for("customers"))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM Customers WHERE customer_id=%s", (customer_id,))
    customer = cursor.fetchone()
    cursor.close()
    return render_template('update_customers.html', customer=customer)

@app.route("/api/customers", methods = ["GET"])
def customers_api():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM Customers")
    customer = cursor.fetchall()
    cursor.close()

    customers_list = []
    for row in customer:
        customers_list.append({
            'customer_id' : row[0],
            'name' : row[1],
            'email' : row[2],
            'join_date' : row[3],
            'segment' : row[4],
            'churned' : row[5], 
            'location' : row[6],
            'age' : row[7],
            'gender' : row[8]
        })
    return jsonify({
        'status' : 'success',
        'message' : 'all customers fetched successfully!',
        'data' : customers_list
    }), 200

@app.route("/api/customers/<int:customer_id>", methods = ["GET"])
def specified_customer(customer_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM Customers WHERE customer_id = %s", (customer_id,))
    customer = cursor.fetchone()
    cursor.close()

    if customer is None:
        return jsonify({
            'status' : 'error',
            'message' : 'customer not found'
        }), 404
    else:
        customers = {
            'customer_id' : customer[0],
            'name' : customer[1],
            'email' : customer[2],
            'join_date' : customer[3],
            'segment' : customer[4],
            'churned' : customer[5], 
            'location' : customer[6],
            'age' : customer[7],
            'gender' : customer[8]
        }
        return jsonify({
            'status' : 'success',
            'data' : customers
        }), 200

@app.route("/api/customers/churned", methods = ["GET"])
def churned_customers():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM Customers WHERE churned = 1")
    customer = cursor.fetchall()
    cursor.close()

    churned_list = []
    for row in customer:
        churned_list.append({
            'customer_id' : row[0],
            'name' : row[1],
            'email' : row[2],
            'join_date' : row[3],
            'segment' : row[4],
            'churned' : row[5], 
            'location' : row[6],
            'age' : row[7],
            'gender' : row[8]
        })
    return jsonify({
        'status' : 'success',
        'data' : churned_list
    }), 200

@app.route("/api/customers/retained", methods = ["GET"])
def retained_customers():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM Customers WHERE churned = 0")
    customer = cursor.fetchall()
    cursor.close()

    retained_list = []
    for row in customer:
        retained_list.append({
            'customer_id' : row[0],
            'name' : row[1],
            'email' : row[2],
            'join_date' : row[3],
            'segment' : row[4],
            'churned' : row[5], 
            'location' : row[6],
            'age' : row[7],
            'gender' : row[8]
        })
    return jsonify({
        'status' : 'success',
        'data' : retained_list
    }), 200

@app.route("/api/stats/customers", methods = ["GET"])
def stats_customers():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT 
            COUNT(*) AS total,
            SUM(CASE WHEN churned = 1 THEN 1 ELSE 0 END) AS churned,
            SUM(CASE WHEN churned = 0 THEN 1 ELSE 0 END) AS retained,
            ROUND(SUM(CASE WHEN churned = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS churn_rate
        FROM Customers
    """)
    data = cursor.fetchone()
    cursor.close()

    stats = {
        'total' : data[0],
        'churned' : data[1],
        'retained' : data[2],
        'churn_rate' : data[3]
    }
    return jsonify ({
        'status' : 'success',
        'data' : stats
    }), 200

@app.route('/api/predict/<int:customer_id>', methods = ['GET'])
def predict_churn(customer_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM customer_ml_view WHERE customer_id=%s", (customer_id,))
    data = cursor.fetchone()
    cursor.close()

    if data is None:
        return jsonify({
            'status' : "error",
            'message' : 'customer not found'
        }), 404
    
    customer_data = {
        'age': [data[1]],
        'gender': [data[2]],
        'location': [data[3]],
        'segment': [data[4]],
        'total_transactions': [data[6]],
        'avg_spend': [data[7]],
        'avg_rating': [data[9]],
        'sentiment_score': [data[10]]
}
    df = pd.DataFrame(customer_data)
    df = df.fillna(0)

    df['gender'] = le_gender.transform(df['gender'])
    df['location'] = le_location.transform(df['location'])
    df['segment'] = le_segment.transform(df['segment'])

    predict = model.predict(df)
    proba = model.predict_proba(df)[0][1]

    print(f"Customer : {'Churn' if predict[0]==1 else 'Stay'}, Probability: {proba*100:.1f}%")

    if proba >= 0.7:
        risk = "High Risk"
    elif proba >= 0.4:
        risk = "Medium Risk"
    else:
        risk = "Low Risk"

    avg_rating = data[9]  

    if avg_rating is not None and avg_rating <= 2.0:
        warning = "Low satisfaction detected — intervention recommended"
    else:
        warning = None


    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT alert_id FROM Retention_Alerts 
        WHERE customer_id = %s 
        AND DATE(predicted_on) = CURDATE()
    """, (customer_id,))
    existing = cursor.fetchone()

    if existing:
    # Update existing alert
        cursor.execute("""
            UPDATE Retention_Alerts 
            SET risk_level=%s, confidence=%s, action_taken=%s, predicted_on=NOW()
            WHERE alert_id=%s
        """, (risk, round(proba * 100, 2), "Pending", existing[0]))
    else:
        # Insert new alert
        cursor.execute("""
            INSERT INTO Retention_Alerts (customer_id, risk_level, action_taken, confidence)
            VALUES (%s, %s, %s, %s)
        """, (customer_id, risk, "Pending", round(proba * 100, 2)))

    mysql.connection.commit()
    cursor.close()
    
    return jsonify({
        'status': 'success',
        'customer_id': customer_id,
        'prediction': int(predict[0]),
        'churn_probability': round(proba * 100, 2),
        'sentiment_score': data[10],
        'risk_level': risk,
        'warning' : warning,
        'message': 'Will churn' if predict[0] == 1 else 'Will stay'
    }), 200
    
@app.route("/api/sentiment/<int:customer_id>", methods = ["GET"])
def sentiment_analysis(customer_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT comments, sentiment FROM Feedback WHERE customer_id = %s", (customer_id,))
    feedback = cursor.fetchall()
    cursor.close()

    if not feedback:
        return jsonify({
            'status' : 'error',
            'message' : 'Feedback not found'
        }), 404
    else:
        feedback_list = []
        for row in feedback:
            feedback_list.append({
            'comments' : row[0],
            'sentiment' : row[1]
        })
        return jsonify({
            'status': 'success',
            'customer_id': customer_id,
            'total_feedback': len(feedback_list),
            'feedback': feedback_list
        }), 200

@app.route("/api/sentiment/summery", methods = ["GET"])
def sentiment_summery():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT 
            COUNT(*) AS total,
            SUM(CASE WHEN sentiment = "Positive" THEN 1 ELSE 0 END) AS Positive,
            SUM(CASE WHEN sentiment = "Negative"  THEN 1 ELSE 0 END) AS Negative,
            SUM(CASE WHEN sentiment = "Neutral"  THEN 1 ELSE 0 END) AS Neutral
        FROM feedback
    """)    
    summery = cursor.fetchone()
    cursor.close()

    sentiment_summery = ({
        'total' : summery[0],
        'Positive' : int(summery[1]),
        "Negative" : int(summery[2]),
        "Neutral" : int(summery[3]),
        'positive_pct': round(int(summery[1]) / int(summery[0]) * 100, 1),
        'negative_pct': round(int(summery[2]) / int(summery[0]) * 100, 1),
        'neutral_pct':  round(int(summery[3]) / int(summery[0]) * 100, 1)
    })
    return jsonify({
        'status' : 'success',
        'data' : sentiment_summery, 
    }),200


@app.route("/dashboard", methods = ["GET"])
def dashboard():
    if not session.get('logged_in'):
        flash("Please login first","error")
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT 
            COUNT(*) AS total,
            SUM(CASE WHEN churned = 1 THEN 1 ELSE 0 END) AS total_churned,
            SUM(CASE WHEN churned = 0 THEN 1 ELSE 0 END) AS total_retained,
            ROUND(
                SUM(CASE WHEN churned = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 
                2
            ) AS churn_rate
        FROM Customers;
    """)
    total, churned, retained, churn_rate = cursor.fetchone()

    cursor.execute("""
        SELECT 
            SUM(CASE WHEN sentiment = 'Positive' THEN 1 ELSE 0 END),
            SUM(CASE WHEN sentiment = 'Negative' THEN 1 ELSE 0 END),
            SUM(CASE WHEN sentiment = 'Neutral' THEN 1 ELSE 0 END)
        FROM Feedback
    """)
    positive, negative, neutral = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM Retention_alerts WHERE risk_level = 'High Risk'")
    high_risk = cursor.fetchone()[0]

    cursor.execute("""
        SELECT c.name, c.segment, r.risk_level, r.confidence, r.predicted_on
        FROM Retention_Alerts r
        JOIN Customers c ON r.customer_id = c.customer_id
        WHERE r.risk_level = 'High Risk'
        ORDER BY r.confidence DESC
    """)
    high_risk_customers = cursor.fetchall()

    cursor.execute("""
        SELECT c.name, c.segment, r.risk_level, r.confidence, r.action_taken, r.predicted_on
        FROM retention_alerts r
        JOIN customers c
        ON r.customer_id = c.customer_id
        ORDER BY predicted_on DESC
        LIMIT 10
    """)
    recent_prediction = cursor.fetchall()
    cursor.close()
    return render_template("dashboard.html", total=total, churned=churned, retained=retained, churn_rate=churn_rate, positive=positive, negative=negative, neutral=neutral, high_risk=high_risk, high_risk_customers=high_risk_customers, recent_prediction=recent_prediction)

@app.route("/analyze/<int:customer_id>", methods = ["GET"])
def analyze(customer_id):
    if not session.get('logged_in'):
        flash("Please login first", "error")
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT c.customer_id, c.name, c.email, c.age, c.gender, c.segment, c.location, c.join_date, c.churned FROM customers c WHERE c.customer_id = %s", (customer_id,))
    info = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) AS total_transactions, AVG(t.amount) AS average_spend, MAX(t.date) AS last_purchase FROM transactions t WHERE customer_id = %s", (customer_id,))
    transaction_summary = cursor.fetchone()
    total_transactions, average_spend, last_purchase = transaction_summary
    last_purchase_date = last_purchase

    if average_spend is not None:
        average_spend = f"₹{average_spend:,.2f}"
    else:
        average_spend = f"₹0.00"

    if last_purchase is not None:
        last_purchase_display = last_purchase.strftime("%d %b %Y")
    else:
        last_purchase_display = "No Purchase History Yet"


    cursor.execute("""
    SELECT 
        AVG(rating) AS average_rating,
        (SELECT comments 
         FROM feedback 
         WHERE customer_id = %s 
         ORDER BY date DESC 
         LIMIT 1) AS latest_comment,
        (SELECT sentiment 
         FROM feedback 
         WHERE customer_id = %s 
         ORDER BY date DESC 
         LIMIT 1) AS latest_sentiment
        FROM feedback
        WHERE customer_id = %s
    """, (customer_id, customer_id, customer_id))

    feedback_summary = cursor.fetchone()

    if info[8] == 1:      # Customer already churned
        prediction = (
            "Churned",
            None,
            None
        )
    else:
        cursor.execute("""
            SELECT risk_level,
            confidence,
            predicted_on
        FROM retention_alerts
        WHERE customer_id=%s
        """, (customer_id,))
        prediction = cursor.fetchone()
    
        if prediction is None:
            prediction = (
                "Low Risk",
                0.00,
                None
            )

    risk_factors = []
    #low rating
    if feedback_summary[0] is not None and feedback_summary[0] < 3:
        risk_factors.append(f"Low Average Rating ({feedback_summary[0]:.1f}/5)")

    #Negative Sentiment
    if feedback_summary[2] == "Negative":
        risk_factors.append(f"💬 Latest Customer Feedback is Negative")

    #Purchse history
    if last_purchase_date is None:
        risk_factors.append(f"🛒 Customer has never made a purchase")
    else:
        today = date.today()
        difference = today - last_purchase_date

        if difference.days > 60:
            risk_factors.append(f"📅 No Purchase in Last {difference.days} Days")

    
    recommended_action =[]
    #never purchased
    if last_purchase_date is None:
        recommended_action.append("📧 Send a welcome email with a first-purchase offer.")

    #Inactive custoemrs
    difference = None
    if last_purchase_date is not None:
        today = date.today()
        difference = today-last_purchase_date
    if difference and difference.days > 60:
        recommended_action.append("🔔 Send a re-engagement email or SMS.")

    #Low rating
    if feedback_summary[0] is not None and feedback_summary[0] < 3:
        recommended_action.append("⭐ Contact the customer to understand their concerns.")

    #NEgative Feedback
    if feedback_summary[2] == "Negative":
        recommended_action.append("☎️ Assign the case to customer support for follow-up.")

    #High risk Customer
    if prediction and prediction[0] == "High Risk":
        recommended_action.append("🚨 Prioritize this customer for the retention team.")

    #if no action is required
    if not recommended_action:
        recommended_action.append("✅ No immediate action required. Customer is healthy.")
    
    cursor.close()
    print("Customer:", info[1])
    print("Churned value:", info[8])
    print("Type:", type(info[8]))
    return render_template("customer_analyzer.html", info=info, total_transactions=total_transactions, average_spend=average_spend, last_purchase=last_purchase_display, feedback_summary=feedback_summary, prediction=prediction, risk_factors=risk_factors, recommended_action=recommended_action)

@app.route("/login", methods = ["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        users = cursor.fetchone()
        cursor.close()

        if users is None:
            flash("Invalid credentials", "error")
            return redirect(url_for('login'))

        stored_hash = users[2]

        if check_password_hash(stored_hash,password):
            session["logged_in"] = True
            session["user_id"] = users[0]
            session["username"] = users[1]

            flash("Welcome back, Admin!", "success")

            return redirect(url_for("home"))

        flash("Invalid Credentials", "error")
        return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))

@app.route("/upload-csv", methods = ["GET", "POST"])
def upload_csv():
    if request.method == "POST":
        file = request.files['file']

        if not file.filename.endswith(".csv"):
            flash("Please upload a CSV file only", "Error")
            return redirect(url_for("upload_csv"))

        df = pd.read_csv(io.StringIO(file.stream.read().decode('utf-8')))

        #missing column
        required_columns = ["name", "email", "age", "gender", "location", "segment", "churned"]
        if not all(col in df.columns for col in required_columns):
            flash("CSV missing required columns", "error")
            return redirect(url_for("upload_csv"))

        #empty files
        if df.empty:
            flash("CSV file is empty", "Error")
            return redirect(url_for("upload_csv"))

        #missing values
        df = df.fillna("")

        cursor = mysql.connection.cursor()

        for index, row in df.iterrows():
            cursor.execute("""
                INSERT INTO Customers (name, email, age, gender, location, segment, churned, join_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,(row['name'], row['email'], row['age'], row['gender'],
            row['location'], row['segment'], row['churned'], row['join_date']))

        mysql.connection.commit()
        cursor.close()
        flash("Customers imported scuccesfully: ", "success")
        return redirect(url_for("customers"))

    return render_template("upload_csv.html")


@app.route("/bulk-predict", methods=["GET"])
def bulk_predict():

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT customer_id
        FROM Customers
        WHERE churned = 0
    """)

    customers = cursor.fetchall()

    # Remove previous predictions
    cursor.execute("DELETE FROM Retention_Alerts")
    mysql.connection.commit()

    high = 0
    medium = 0
    low = 0

    for customer in customers:

        customer_id = customer[0]

        # Fetch customer data
        cursor.execute(
            "SELECT * FROM customer_ml_view WHERE customer_id=%s",
            (customer_id,)
        )

        data = cursor.fetchone()

        if data is None:
            continue

        # Prepare data
        customer_data = {
            'age': [data[1]],
            'gender': [data[2]],
            'location': [data[3]],
            'segment': [data[4]],
            'total_transactions': [data[6]],
            'avg_spend': [data[7]],
            'avg_rating': [data[9]],
            'sentiment_score': [data[10]]
        }

        df = pd.DataFrame(customer_data)
        df = df.fillna(0)

        # Encode categorical values
        df['gender'] = le_gender.transform(df['gender'])
        df['location'] = le_location.transform(df['location'])
        df['segment'] = le_segment.transform(df['segment'])

        # Prediction
        prediction = model.predict(df)
        proba = model.predict_proba(df)[0][1]

        print(f"Customer {customer_id} : {'Churn' if prediction[0] == 1 else 'Stay'} | {proba*100:.2f}%")

        # Risk Level
        if proba >= 0.70:
            risk = "High Risk"
            high += 1

        elif proba >= 0.40:
            risk = "Medium Risk"
            medium += 1

        else:
            risk = "Low Risk"
            low += 1

        # Check existing alert
        cursor.execute("""
            SELECT alert_id
            FROM Retention_Alerts
            WHERE customer_id=%s
            AND DATE(predicted_on)=CURDATE()
        """, (customer_id,))

        existing = cursor.fetchone()

        if existing:

            cursor.execute("""
                UPDATE Retention_Alerts
                SET risk_level=%s,
                    confidence=%s,
                    action_taken=%s,
                    predicted_on=NOW()
                WHERE alert_id=%s
            """, (
                risk,
                round(proba * 100, 2),
                "Pending",
                existing[0]
            ))

        else:

            cursor.execute("""
                INSERT INTO Retention_Alerts
                (customer_id, risk_level, action_taken, confidence)
                VALUES (%s, %s, %s, %s)
            """, (
                customer_id,
                risk,
                "Pending",
                round(proba * 100, 2)
            ))

    mysql.connection.commit()
    cursor.close()

    return jsonify({
        "status": "success",
        "processed": len(customers),
        "high": high,
        "medium": medium,
        "low": low
    })

    return redirect(url_for("customers"))

@app.route("/report", methods=["GET"])
def reports():
    if not session.get("logged_in"):
        flash("Please login first", "error")
        return redirect(url_for("login"))

    return render_template("reports.html")

@app.route("/report/customer", methods=["GET", "POST"])
def customer_report():
    if not session.get("logged_in"):
        flash("Please login first", "error")
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT customer_id,
        name,
        email,
        join_date,
        segment,
        churned,
        location,
        age,
        gender
        FROM Customers""")
    customers = cursor.fetchall()
    cursor.close()

    total = len(customers)
    active = sum(1 for c in customers if c[5] == 0)
    churned = sum(1 for c in customers if c[5] == 1)
    premium = sum(1 for c in customers if c[4] == "Premium" )
    churn_rate = round((churned / total) * 100, 2) if total > 0 else 0

    return render_template("customer_reports.html", customers=customers, total=total, active=active, churned=churned, premium=premium, churn_rate=churn_rate)

@app.route("/report/customer/csv", methods = ["GET"])
def customer_report_csv():
    if not session.get("logged_in"):
        flash("Please login first", "error")
        return redirect(url_for("login"))
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
            SELECT customer_id,
            name,
            email,
            join_date,
            segment,
            churned,
            location,
            age,
            gender
            FROM Customers""")
    customers = cursor.fetchall()
    cursor.close()

    df = pd.DataFrame(
        customers,
        columns=[
            "Customer ID",
            "Name",
            "Email",
            "Join Date",
            "Segment",
            "Status",
            "Location",
            "Age",
            "Gender"
        ]
    )

    df["Status"] = df["Status"].map({
        0: "Active",
        1: "Churned"
    })

    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".csv"
    )

    df.to_csv(temp.name, index=False)

    return send_file(
        temp.name,
        as_attachment=True,
        download_name="customer_report.csv"
    )

@app.route("/report/customer/pdf", methods = ["GET"])
def customer_report_pdf():
    if not session.get("logged_in"):
        flash("Please login first", "error")
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
        customer_id,
        name,
        email,
        join_date,
        segment,
        churned,
        location,
        age,
        gender
        FROM Customers
    """)

    customers = cursor.fetchall()
    cursor.close()

    total = len(customers)
    active = sum(1 for c in customers if c[5] == 0)
    churned = sum(1 for c in customers if c[5] == 1)
    premium = sum(1 for c in customers if c[4] == "Premium" )
    churn_rate = round((churned / total) * 100, 2) if total > 0 else 0

    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    )

    doc = SimpleDocTemplate(temp.name, pagesize=landscape(A3))

    elements = [] 
    styles = getSampleStyleSheet()
    header = [
    [
        Paragraph(
            "<b><font size=20 color='#0b1120'>CUSTOMER RETENTION SYSTEM</font></b>",
            styles["BodyText"]
        ),
        Paragraph(
            f"<b>{date.today().strftime('%d %B %Y')}</b>",
            styles["BodyText"]
        )
    ],
    [
        Paragraph(
            "<font size=12>Customer Analytics Report</font>",
            styles["BodyText"]
        ),

        ""
    ]
]
    header_table = Table(
        header,
        colWidths=[600,100]
    )
    header_table.setStyle(
        TableStyle([
            ('BOTTOMPADDING', (0,0),(-1,-1),15),
            ('LINEBELOW', (0,1),(-1,-1),1,colors.HexColor("#0b1120"))
        ])
    )
    elements.append(header_table)
    elements.append(
        Spacer(1,20)
    )

    summery_data = [
        [
            "Customers",
            "Active",
            "Churned",
            "Churn Rate"
        ],
        [
            str(total),
            str(active),
            str(churned),
            f"{churn_rate}%"
        ]
    ]
    summery_table = Table(
        summery_data,
        colWidths=[150,150,150,150]
    )
    summery_table.setStyle(

    TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor("#0b1120")),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('BACKGROUND',(0,1),(-1,1),colors.HexColor("#F4F7F9")),
        ('GRID',(0,0),(-1,-1),1,colors.HexColor("#E5E7EB")),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTNAME',(0,1),(-1,1),'Helvetica-Bold'),
        ('FONTSIZE',(0,0),(-1,0),11),
        ('FONTSIZE',(0,1),(-1,1),16),
        ('BOTTOMPADDING',(0,0),(-1,0),10),
        ('TOPPADDING',(0,1),(-1,1),12),
        ('BOTTOMPADDING',(0,1),(-1,1),12)
    ])
)
    elements.append(summery_table)
    elements.append(Spacer(1,25))

    heading = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        alignment=TA_CENTER
    )
    elements.append(
        Paragraph("Customer Details", heading)
    )
    elements.append(Spacer(1,10))

    table_data = [
        [
            "ID",
            "Name",
            "Email",
            "Join Date",
            "Segment",
            "Status",
            "Location",
            "Age",
            "Gender"
        ]
    ]
    for customer in customers:
        status = "Active" if customer[5] == 0 else "Churned"
        table_data.append([
            customer[0],
            customer[1],
            customer[2],
            customer[3].strftime("%d-%m-%Y"),
            customer[4],
            status,
            customer[6],
            customer[7],
            customer[8]
        ])

    customer_table = Table(
        table_data,
        repeatRows=1,
        colWidths=[
            35,
            150,
            170,
            65,
            60,
            50,
            75,
            65
        ]
    )
    customer_table.setStyle(
        TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor("#0b1120")),
            ('TEXTCOLOR',(0,0),(-1,0),colors.white),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
            ('FONTSIZE',(0,0),(-1,0),10),
            ('ALIGN',(0,0),(-1,-1),'CENTER'),
            ('GRID',(0,0),(-1,-1),0.5,colors.grey),
            ('BOTTOMPADDING',(0,0),(-1,0),8),
            ('TOPPADDING',(0,1),(-1,-1),6),
            ('BOTTOMPADDING',(0,1),(-1,-1),6)
    ])
)
    for row in range(1, len(table_data)):
        if row % 2 == 0:
            customer_table.setStyle(
                TableStyle([
                    (
                        'BACKGROUND',
                        (0,row),
                        (-1,row),
                        colors.HexColor("#F8FAFC")
                    )
                ])
            )
    elements.append(customer_table)

    doc.build(elements)
    return send_file(
        temp.name,
        as_attachment=True,
        download_name="customer_report.pdf"
    )

@app.route("/report/prediction", methods = ["GET"])
def prediction_report():
    if not session.get("logged_in"):
        flash("Please login first", "error")
        return redirect(url_for("login"))
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT
            c.customer_id,
            c.name,
            c.segment,
            r.risk_level,
            r.confidence,
            r.action_taken,
            r.predicted_on

        FROM Customers c

        JOIN Retention_Alerts r
        ON c.customer_id = r.customer_id

        ORDER BY r.confidence DESC
    """ )
    prediction = cursor.fetchall()

    # Total Customers
    cursor.execute("SELECT COUNT(*) FROM Customers")
    total_customers = cursor.fetchone()[0]

    # Active Customers
    cursor.execute("""
        SELECT COUNT(*)
        FROM Customers
        WHERE churned = 0
    """)
    active_customers = cursor.fetchone()[0]

    already_churned = total_customers - active_customers

    prediction_generated = len(prediction)
    high = sum(1 for p in prediction if p[3] == "High Risk")
    medium = sum(1 for p in prediction if p[3] == "Medium Risk")
    low = sum(1 for p in prediction if p[3] == "Low Risk")
    avg_confidence = round(
        sum(p[4] for p in prediction)/prediction_generated,
        2
    ) if prediction_generated else 0

    cursor.close()

    return render_template("prediction_report.html", prediction=prediction  , prediction_generated=prediction_generated, total_customers=total_customers, active_customers=active_customers, already_churned=already_churned, high=high, low=low, medium=medium, avg_confidence=avg_confidence, current_date = date.today().strftime("%d-%m-%Y"))

@app.route("/prediction-report-csv", methods = ["GET"])
def prediction_csv():
    if not session.get("logged_in"):
        flash("Please login first", "error")
        return redirect(url_for("login"))
        
    cursor = mysql.connection.cursor()
    cursor.execute("""
         SELECT
            c.customer_id,
            c.name,
            c.segment,
            r.risk_level,
            r.confidence,
            r.action_taken,
            DATE_FORMAT(r.predicted_on, '%d-%m-%Y %H:%i')
        FROM Customers c
        JOIN Retention_Alerts r
            ON c.customer_id = r.customer_id
        ORDER BY r.confidence DESC
    """)
    predictions = cursor.fetchall()
    cursor.close()
    
    df = pd.DataFrame(
        predictions,
        columns=[
                "Customer ID",
                "Name",
                "Segment",
                "Risk Level",
                "Confidence",
                "Action Taken",
                "Predicted On"
            ]
        )
    
    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".csv"
    )
    temp.close()
    
    df.to_csv(temp.name, index=False)
    
    return send_file(
        temp.name,
        as_attachment=True,
        download_name="prediction_report.csv"
    )
    
@app.route("/prediction-report-pdf", methods = ["GET"])
def prediction_pdf():
    if not session.get("logged_in"):
        flash("Please login first", "error")
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT
            c.customer_id,
            c.name,
            c.segment,
            r.risk_level,
            r.confidence,
            r.action_taken,
            DATE_FORMAT(r.predicted_on,'%d-%m-%Y')
        FROM Customers c
        JOIN Retention_Alerts r
        ON c.customer_id=r.customer_id
        ORDER BY r.confidence DESC
        """)
    prediction = cursor.fetchall()
    total = len(prediction)

    high = sum(1 for p in prediction if p[3] == "High Risk")
    medium = sum(1 for p in prediction if p[3] == "Medium Risk")
    low = sum(1 for p in prediction if p[3] == "Low Risk")

    avg_confidence = round(
        sum(p[4] for p in prediction)/total,
        2
    ) if total else 0

    cursor.execute("SELECT COUNT(*) FROM Customers")
    total_customers = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM Customers
        WHERE churned=0
        """)

    active_customers = cursor.fetchone()[0]

    already_churned = total_customers-active_customers

    cursor.close()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize = landscape(A4),
        rightMargin = 20,
        leftMargin = 20,
        topMargin = 20,
        bottomMargin = 20
    )

    elements = []
    styles = getSampleStyleSheet()
    header = [
        [
            Paragraph(
                "<b><font size=20 color='#0b1120'>CUSTOMER RETENTION SYSTEM</font></b>",
                styles["BodyText"]
            ),
            Paragraph(
                f"<b>{date.today().strftime('%d %B %Y')}</b>",
                styles["BodyText"]
            )
        ],
        [
            Paragraph(
                "<font size=12>Prediction Report</font>",
                styles["BodyText"]
            ),
    
            ""
        ]
    ]
    header_table = Table(
        header,
        colWidths=[600,100]
    )
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ('LINEBELOW', (0,1), (-1,1), 2, colors.HexColor("#0b1120")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT')
    ]))
    elements.append(header_table)
    elements.append(
        Spacer(1,20)
    )

    summary = [
        [
            "Total\nCustomers",
            "Active\nCustomers",
            "High\nRisk",
            "Medium\nRisk"
        ],
        [
            total_customers,
            active_customers,
            high,
            medium
        ],
        [
            "Low\nRisk",
            "Avg\nConfidence",
            "Predictions",
            "Churned"
        ],
        [
            low,
            f"{avg_confidence}%",
            total,
            already_churned
        ]
]

    summary_table = Table(summary, colWidths=[170]*4)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(3,0),colors.HexColor("#0b1120")),
        ('TEXTCOLOR',(0,0),(3,0),colors.white),
        ('BACKGROUND',(0,2),(3,2),colors.HexColor("#0b1120")),
        ('TEXTCOLOR',(0,2),(3,2),colors.white),
        ('BACKGROUND',(0,1),(3,1),colors.whitesmoke),
        ('BACKGROUND',(0,3),(3,3),colors.whitesmoke),
        ('GRID',(0,0),(-1,-1),0.5,colors.grey),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('BOTTOMPADDING',(0,0),(-1,-1),10),
        ('TOPPADDING',(0,0),(-1,-1),10)
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1,20))

    table_data = [[
        "ID",
        "Name",
        "Segment",
        "Risk",
        "Confidence",
        "Action"
    ]]

    for p in prediction:
        table_data.append([
            p[0],
            p[1],
            p[2],
            p[3],
            f"{p[4]}%",
            p[5]
        ])
    prediction_table = Table(
        table_data,
        repeatRows=1,
        colWidths=[40, 140, 90, 90, 80, 100]
    )

    heading = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        alignment=TA_CENTER
    )
    elements.append(
        Paragraph("Prediction Details", heading)
    )
    elements.append(Spacer(1,10))
    elements.append(Spacer(1,10))
    elements.append(prediction_table)
    prediction_style = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0b1120")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]

    for i in range(1,len(table_data)):
        bg = colors.white
        if i%2==0:
            bg = colors.HexColor("#F4F7FC")
        prediction_style.append(
            ('BACKGROUND',(0,i),(-1,i),bg)
        )
    for row, p in enumerate(prediction, start=1):
        if p[3] == "High Risk":
            prediction_style.append(
                ('TEXTCOLOR',(3,row),(3,row),colors.red)
            )
        elif p[3] == "Medium Risk":
            prediction_style.append(
                ('TEXTCOLOR',(3,row),(3,row),colors.orange)
            )
        else:
            prediction_style.append(
                ('TEXTCOLOR',(3,row),(3,row),colors.green)
            )
    prediction_style.extend([
        ('ALIGN',(0,0),(0,-1),'CENTER'),
        ('ALIGN',(2,0),(4,-1),'CENTER'),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE')
    ])
    prediction_table.setStyle(
        TableStyle(prediction_style)
)

    doc.build(elements)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="prediction_report.pdf",
        mimetype="application/pdf"
    )

@app.route("/report/overall", methods=["GET"])
def overall_report():

    if not session.get("logged_in"):
        flash("Please login first", "error")
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    # CUSTOMER STATISTICS

    cursor.execute("SELECT COUNT(*) FROM Customers")
    total_customers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Customers WHERE churned = 0")
    active_customers = cursor.fetchone()[0]

    churned_customers = total_customers - active_customers

    retention_rate = round((active_customers / total_customers) * 100, 2) if total_customers else 0
    churn_rate = round((churned_customers / total_customers) * 100, 2) if total_customers else 0

    # PREDICTION SUMMARY
    cursor.execute("""
        SELECT
            risk_level,
            confidence
        FROM Retention_Alerts
    """)

    alerts = cursor.fetchall()

    predictions = len(alerts)

    high = sum(1 for a in alerts if a[0] == "High Risk")
    medium = sum(1 for a in alerts if a[0] == "Medium Risk")
    low = sum(1 for a in alerts if a[0] == "Low Risk")

    avg_confidence = round(
        sum(a[1] for a in alerts) / predictions,
        2
    ) if predictions else 0

    # CUSTOMER SEGMENTS
    cursor.execute("""
        SELECT segment, COUNT(*)
        FROM Customers
        GROUP BY segment
    """)

    segment_data = cursor.fetchall()

    # SENTIMENT SUMMARY
    cursor.execute("""
        SELECT sentiment, COUNT(*)
        FROM Feedback
        GROUP BY sentiment
    """)

    sentiment_data = cursor.fetchall()

    # RATING SUMMARY
    cursor.execute("""
        SELECT
            ROUND(AVG(rating),2),
            MAX(rating),
            MIN(rating)
        FROM Feedback
    """)

    rating_summary = cursor.fetchone()

    # TRANSACTION SUMMARY
    cursor.execute("""
        SELECT
            ROUND(SUM(amount),2),
            ROUND(AVG(amount),2),
            MAX(amount),
            COUNT(*)
        FROM Transactions
    """)

    transaction_summary = cursor.fetchone()

    # TOP 10 HIGH RISK
    cursor.execute("""
        SELECT
            c.customer_id,
            c.name,
            r.risk_level,
            r.confidence
        FROM Customers c
        JOIN Retention_Alerts r
            ON c.customer_id = r.customer_id
        ORDER BY r.confidence DESC
        LIMIT 10
    """)

    top_risk = cursor.fetchall()

    # TOP 10 VALUABLE CUSTOMERS
    cursor.execute("""
        SELECT
            c.customer_id,
            c.name,
            ROUND(SUM(t.amount),2) AS total_spent
        FROM Customers c
        JOIN Transactions t
            ON c.customer_id = t.customer_id
        GROUP BY c.customer_id, c.name
        ORDER BY total_spent DESC
        LIMIT 10
    """)

    top_customers = cursor.fetchall()

    cursor.close()

    return render_template(
        "overall_report.html",

        total_customers=total_customers,
        active_customers=active_customers,
        churned_customers=churned_customers,
        retention_rate=retention_rate,
        churn_rate=churn_rate,

        predictions=predictions,
        high=high,
        medium=medium,
        low=low,
        avg_confidence=avg_confidence,

        segment_data=segment_data,
        sentiment_data=sentiment_data,

        rating_summary=rating_summary,
        transaction_summary=transaction_summary,

        top_risk=top_risk,
        top_customers=top_customers,

        current_date=date.today().strftime("%d-%m-%Y")
    )

@app.route("/overall-report-csv", methods=["GET"])
def overall_csv():

    if not session.get("logged_in"):
        flash("Please login first", "error")
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            c.customer_id,
            c.name,
            c.age,
            c.gender,
            c.location,
            c.segment,
            c.churned,
            r.risk_level,
            r.confidence,
            r.action_taken,
            DATE_FORMAT(r.predicted_on,'%d-%m-%Y')
        FROM Customers c
        LEFT JOIN Retention_Alerts r
            ON c.customer_id = r.customer_id
        ORDER BY c.customer_id
    """)

    data = cursor.fetchall()
    cursor.close()

    df = pd.DataFrame(
        data,
        columns=[
            "Customer ID",
            "Name",
            "Age",
            "Gender",
            "Location",
            "Segment",
            "Churned",
            "Risk Level",
            "Confidence (%)",
            "Action Taken",
            "Prediction Date"
        ]
    )
    df["Status"] = df["Churned"].replace({
        0: "Active",
        1: "Churned"
    })

    df.drop(columns=["Churned"], inplace=True)
    
    df.fillna("-", inplace=True)

    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".csv"
    )

    df.to_csv(
        temp.name,
        index=False
    )
    return send_file(
        temp.name,
        as_attachment=True,
        download_name="overall_system_report.csv"
    )

@app.route("/overall-report-pdf", methods=["GET"])
def overall_pdf():
    
    if not session.get("logged_in"):
        flash("Please login first", "error")
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    # CUSTOMER STATISTICS

    cursor.execute("SELECT COUNT(*) FROM Customers")
    total_customers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Customers WHERE churned = 0")
    active_customers = cursor.fetchone()[0]

    churned_customers = total_customers - active_customers

    retention_rate = round((active_customers / total_customers) * 100, 2) if total_customers else 0
    churn_rate = round((churned_customers / total_customers) * 100, 2) if total_customers else 0

    # PREDICTION SUMMARY
    cursor.execute("""
        SELECT
            risk_level,
            confidence
        FROM Retention_Alerts
    """)

    alerts = cursor.fetchall()

    predictions = len(alerts)

    high = sum(1 for a in alerts if a[0] == "High Risk")
    medium = sum(1 for a in alerts if a[0] == "Medium Risk")
    low = sum(1 for a in alerts if a[0] == "Low Risk")

    avg_confidence = round(
        sum(a[1] for a in alerts) / predictions,
        2
    ) if predictions else 0

    # CUSTOMER SEGMENTS
    cursor.execute("""
        SELECT segment, COUNT(*)
        FROM Customers
        GROUP BY segment
    """)

    segment_data = cursor.fetchall()

    # SENTIMENT SUMMARY
    cursor.execute("""
        SELECT sentiment, COUNT(*)
        FROM Feedback
        GROUP BY sentiment
    """)

    sentiment_data = cursor.fetchall()

    # RATING SUMMARY
    cursor.execute("""
        SELECT
            ROUND(AVG(rating),2),
            MAX(rating),
            MIN(rating)
        FROM Feedback
    """)

    rating_summary = cursor.fetchone()

    # TRANSACTION SUMMARY
    cursor.execute("""
        SELECT
            ROUND(SUM(amount),2),
            ROUND(AVG(amount),2),
            MAX(amount),
            COUNT(*)
        FROM Transactions
    """)

    transaction_summary = cursor.fetchone()

    # TOP 10 HIGH RISK
    cursor.execute("""
        SELECT
            c.customer_id,
            c.name,
            r.risk_level,
            r.confidence
        FROM Customers c
        JOIN Retention_Alerts r
            ON c.customer_id = r.customer_id
        ORDER BY r.confidence DESC
        LIMIT 10
    """)

    top_risk = cursor.fetchall()

    # TOP 10 VALUABLE CUSTOMERS
    cursor.execute("""
        SELECT
            c.customer_id,
            c.name,
            ROUND(SUM(t.amount),2) AS total_spent
        FROM Customers c
        JOIN Transactions t
            ON c.customer_id = t.customer_id
        GROUP BY c.customer_id, c.name
        ORDER BY total_spent DESC
        LIMIT 10
    """)

    top_customers = cursor.fetchall()
    
    cursor.close()

# ========== PDF GENERATION ==========
    buffer = BytesIO()

    # Color palette
    NAVY      = colors.HexColor("#0f172a")
    SLATE     = colors.HexColor("#1e293b")
    ACCENT    = colors.HexColor("#1e40af")
    LIGHT_BG  = colors.HexColor("#f8fafc")
    ALT_ROW   = colors.HexColor("#f1f5f9")
    BORDER    = colors.HexColor("#e2e8f0")
    MUTED     = colors.HexColor("#64748b")
    WHITE     = colors.white
    RISK_RED  = colors.HexColor("#b91c1c")
    RISK_ORANGE = colors.HexColor("#c2410c")
    RISK_GREEN  = colors.HexColor("#15803d")

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=18,
        leftMargin=18,
        topMargin=18,
        bottomMargin=28
    )

    styles = getSampleStyleSheet()

    # Styles
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=WHITE,
        leading=20
    )

    section_style = ParagraphStyle(
        "SectionStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=NAVY,
        spaceBefore=2,
        spaceAfter=2
    )

    kpi_label = ParagraphStyle(
        "KPILabel",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        textColor=MUTED,
        alignment=TA_CENTER,
        leading=9
    )

    kpi_value = ParagraphStyle(
        "KPIValue",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=NAVY,
        alignment=TA_CENTER,
        leading=16
    )

    footer_style = ParagraphStyle(
        "FooterStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        textColor=MUTED,
        alignment=TA_CENTER
    )

    cell_style = ParagraphStyle(
        "CellStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=NAVY
    )

    cell_bold_white = ParagraphStyle(
        "CellBoldWhite",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=WHITE          # white text for table headers
    )

    elements = []

    # ========== HEADER ==========
    header_data = [[
        Paragraph("CUSTOMER RETENTION SYSTEM", title_style),
        Paragraph(
            f"<b>Overall System Report</b><br/>{date.today().strftime('%d %B %Y')}",
            ParagraphStyle(
                "HeaderRight",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=9,
                textColor=WHITE,
                alignment=TA_RIGHT,
                leading=12
            )
        )
    ]]

    header_table = Table(header_data, colWidths=[520, 220])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 14),
        ("RIGHTPADDING", (-1, 0), (-1, 0), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 14))

    # ========== KPI SUMMARY ==========
    def kpi_cell(label, value):
        return [
            Paragraph(label, kpi_label),
            Paragraph(str(value), kpi_value)
        ]

    kpi_row1 = [
        kpi_cell("TOTAL CUSTOMERS", total_customers),
        kpi_cell("ACTIVE CUSTOMERS", active_customers),
        kpi_cell("CHURNED CUSTOMERS", churned_customers),
        kpi_cell("RETENTION RATE", f"{retention_rate}%"),
    ]
    kpi_row2 = [
        kpi_cell("TOTAL PREDICTIONS", predictions),
        kpi_cell("HIGH RISK", high),
        kpi_cell("MEDIUM RISK", medium),
        kpi_cell("AVG CONFIDENCE", f"{avg_confidence}%"),
    ]

    kpi_data = [
        [kpi_row1[0][0], kpi_row1[1][0], kpi_row1[2][0], kpi_row1[3][0]],
        [kpi_row1[0][1], kpi_row1[1][1], kpi_row1[2][1], kpi_row1[3][1]],
        [kpi_row2[0][0], kpi_row2[1][0], kpi_row2[2][0], kpi_row2[3][0]],
        [kpi_row2[0][1], kpi_row2[1][1], kpi_row2[2][1], kpi_row2[3][1]],
    ]

    kpi_table = Table(kpi_data, colWidths=[185] * 4)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LINEABOVE", (0, 2), (-1, 2), 0.6, BORDER),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 16))

    # ========== HELPER: Section title + matching underline + table ==========
    def make_section_table(title, data, col_widths, header_bg=ACCENT):
        table_width = sum(col_widths)

        # Title + underline that exactly matches table width
        header_block = [
            [Paragraph(title, section_style)],
            [HRFlowable(
                width=table_width,
                thickness=1.5,
                color=header_bg,
                spaceBefore=1,
                spaceAfter=6
            )]
        ]
        header_table = Table(header_block, colWidths=[table_width])
        header_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(header_table)

        # Data table (left-aligned)
        t = Table(data, colWidths=col_widths, repeatRows=1)
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), header_bg),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
            ("BOX", (0, 0), (-1, -1), 0.7, SLATE),
        ]
        for i in range(1, len(data)):
            bg = WHITE if i % 2 else ALT_ROW
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))

        t.setStyle(TableStyle(style_cmds))
        elements.append(t)
        elements.append(Spacer(1, 14))

    # ========== CUSTOMER STATISTICS ==========
    cust_data = [
        [Paragraph("<b>Metric</b>", cell_bold_white), Paragraph("<b>Value</b>", cell_bold_white)],
        ["Total Customers", total_customers],
        ["Active Customers", active_customers],
        ["Churned Customers", churned_customers],
        ["Retention Rate", f"{retention_rate}%"],
        ["Churn Rate", f"{churn_rate}%"],
    ]
    make_section_table("Customer Statistics", cust_data, [280, 180], header_bg=NAVY)

    # ========== PREDICTION SUMMARY ==========
    pred_data = [
        [Paragraph("<b>Metric</b>", cell_bold_white), Paragraph("<b>Value</b>", cell_bold_white)],
        ["Total Predictions", predictions],
        ["High Risk", high],
        ["Medium Risk", medium],
        ["Low Risk", low],
        ["Average Confidence", f"{avg_confidence}%"],
    ]
    make_section_table("Prediction Summary", pred_data, [280, 180], header_bg=ACCENT)

    # ========== SEGMENT DISTRIBUTION ==========
    seg_data = [
        [Paragraph("<b>Segment</b>", cell_bold_white), Paragraph("<b>Customers</b>", cell_bold_white)]
    ]
    for s in segment_data:
        seg_data.append([s[0], s[1]])
    make_section_table("Customer Segment Distribution", seg_data, [280, 180], header_bg=SLATE)

    # ========== SENTIMENT ==========
    sent_data = [
        [Paragraph("<b>Sentiment</b>", cell_bold_white), Paragraph("<b>Count</b>", cell_bold_white)]
    ]
    for s in sentiment_data:
        sent_data.append([s[0], s[1]])
    make_section_table("Sentiment Distribution", sent_data, [280, 180], header_bg=SLATE)

    # ========== REVENUE ==========
    rev_data = [
        [Paragraph("<b>Metric</b>", cell_bold_white), Paragraph("<b>Value</b>", cell_bold_white)],
        ["Total Revenue", f"₹ {transaction_summary[0]:,.2f}" if transaction_summary[0] else "₹ 0.00"],
        ["Average Transaction", f"₹ {transaction_summary[1]:,.2f}" if transaction_summary[1] else "₹ 0.00"],
        ["Highest Transaction", f"₹ {transaction_summary[2]:,.2f}" if transaction_summary[2] else "₹ 0.00"],
        ["Total Transactions", transaction_summary[3] or 0],
    ]
    make_section_table("Revenue Summary", rev_data, [280, 200], header_bg=NAVY)

    # ========== RATING ==========
    rating_data = [
        [Paragraph("<b>Metric</b>", cell_bold_white), Paragraph("<b>Value</b>", cell_bold_white)],
        ["Average Rating", rating_summary[0] if rating_summary[0] is not None else "—"],
        ["Highest Rating", rating_summary[1] if rating_summary[1] is not None else "—"],
        ["Lowest Rating", rating_summary[2] if rating_summary[2] is not None else "—"],
    ]
    make_section_table("Customer Rating Summary", rating_data, [280, 200], header_bg=ACCENT)

    # ========== TOP 10 HIGH RISK ==========
    risk_col_widths = [90, 280, 140, 130]
    table_width = sum(risk_col_widths)

    header_block = [
        [Paragraph("Top 10 High Risk Customers", section_style)],
        [HRFlowable(width=table_width, thickness=1.5, color=RISK_RED, spaceBefore=1, spaceAfter=6)]
    ]
    header_table = Table(header_block, colWidths=[table_width])
    header_table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)

    risk_data = [[
        Paragraph("<b>Customer ID</b>", cell_bold_white),
        Paragraph("<b>Name</b>", cell_bold_white),
        Paragraph("<b>Risk Level</b>", cell_bold_white),
        Paragraph("<b>Confidence</b>", cell_bold_white),
    ]]
    for c in top_risk:
        risk_data.append([c[0], c[1], c[2], f"{c[3]}%"])

    risk_table = Table(risk_data, colWidths=risk_col_widths, repeatRows=1)
    risk_style = [
        ("BACKGROUND", (0, 0), (-1, 0), RISK_RED),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("BOX", (0, 0), (-1, -1), 0.7, SLATE),
    ]
    for i in range(1, len(risk_data)):
        bg = WHITE if i % 2 else ALT_ROW
        risk_style.append(("BACKGROUND", (0, i), (-1, i), bg))
        level = top_risk[i-1][2]
        if level == "High Risk":
            risk_style.append(("TEXTCOLOR", (2, i), (2, i), RISK_RED))
            risk_style.append(("FONTNAME", (2, i), (2, i), "Helvetica-Bold"))
        elif level == "Medium Risk":
            risk_style.append(("TEXTCOLOR", (2, i), (2, i), RISK_ORANGE))
        else:
            risk_style.append(("TEXTCOLOR", (2, i), (2, i), RISK_GREEN))

    risk_table.setStyle(TableStyle(risk_style))
    elements.append(risk_table)
    elements.append(Spacer(1, 14))

    # ========== TOP 10 VALUABLE CUSTOMERS ==========
    value_col_widths = [90, 340, 160]
    table_width = sum(value_col_widths)

    header_block = [
        [Paragraph("Top 10 Valuable Customers", section_style)],
        [HRFlowable(width=table_width, thickness=1.5, color=ACCENT, spaceBefore=1, spaceAfter=6)]
    ]
    header_table = Table(header_block, colWidths=[table_width])
    header_table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)

    value_data = [[
        Paragraph("<b>Customer ID</b>", cell_bold_white),
        Paragraph("<b>Customer Name</b>", cell_bold_white),
        Paragraph("<b>Total Spend (₹)</b>", cell_bold_white),
    ]]
    for c in top_customers:
        value_data.append([c[0], c[1], f"{c[2]:,.2f}"])

    value_table = Table(value_data, colWidths=value_col_widths, repeatRows=1)
    value_style = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("BOX", (0, 0), (-1, -1), 0.7, SLATE),
    ]
    for i in range(1, len(value_data)):
        bg = WHITE if i % 2 else ALT_ROW
        value_style.append(("BACKGROUND", (0, i), (-1, i), bg))

    value_table.setStyle(TableStyle(value_style))
    elements.append(value_table)
    elements.append(Spacer(1, 18))

    # ========== FOOTER ==========
    elements.append(HRFlowable(width="100%", thickness=0.6, color=BORDER, spaceBefore=4, spaceAfter=6))
    elements.append(Paragraph(
        "<b>Generated by Customer Retention System</b>  •  This report is confidential and intended for internal management use only.",
        footer_style
    ))

    def add_page_number(canvas, doc):
        canvas.saveState()
        page_num = canvas.getPageNumber()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawCentredString(landscape(A4)[0] / 2, 12, f"Page {page_num}")
        canvas.restoreState()

    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="overall_system_report.pdf",
        mimetype="application/pdf"
    )

@app.context_processor
def notification_data():

    if not session.get("logged_in"):
        return {}

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM Retention_Alerts
        WHERE risk_level='High Risk'
    """)
    high = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM Retention_Alerts
        WHERE risk_level='Medium Risk'
    """)
    medium = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM Retention_Alerts
    """)
    predictions = cursor.fetchone()[0]

    cursor.close()
    notification_count = 0

    if high > 0:
        notification_count += 1

    if medium > 0:
        notification_count += 1

    if predictions > 0:
        notification_count += 1

    return dict(
        high_notification=high,
        medium_notification=medium,
        prediction_notification=predictions,
        notification_count=notification_count
    )

@app.route("/profile", methods = ["GET"])
def profile():
    if not session.get("logged_in"):
        flash("Please login first", "error")
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, username FROM users WHERE username=%s",(session["username"],))
    admin = cursor.fetchone()
    cursor.close()
    return render_template("profile.html", admin=admin)

@app.route("/change-password", methods=["GET", "POST"])
def change_password():

    if not session.get("logged_in"):
        flash("Please login first", "error")
        return redirect(url_for("login"))

    if request.method == "POST":

        current_password = request.form["current_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        # Basic validations
        if new_password != confirm_password:
            flash("New password and confirm password do not match.", "danger")
            return redirect(url_for("change_password"))

        if len(new_password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return redirect(url_for("change_password"))

        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT id, password_hash
            FROM users
            WHERE username=%s
        """, (session["username"],))

        user = cursor.fetchone()

        if not user:
            cursor.close()
            flash("User not found.", "danger")
            return redirect(url_for("change_password"))

        user_id = user[0]
        stored_hash = user[1]

        if not check_password_hash(stored_hash, current_password):
            cursor.close()
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("change_password"))

        if check_password_hash(stored_hash, new_password):
            cursor.close()
            flash("New password cannot be the same as the current password.", "warning")
            return redirect(url_for("change_password"))

        new_hash = generate_password_hash(new_password)

        cursor.execute("""
            UPDATE users
            SET password_hash=%s
            WHERE id=%s
        """, (new_hash, user_id))

        mysql.connection.commit()
        cursor.close()

        flash("Password updated successfully.", "success")
        return redirect(url_for("profile"))

    return render_template("change_password.html")

@app.route("/sidebar", methods = ["GET"])
def about():
    if not session.get("logged_in"):
        flash("Please login first", "error")
        return redirect(url_for("login"))

    return render_template("about.html")

@app.route("/ai-analyst", methods=["GET"])
def ai_analyst():
    if not session.get("logged_in"):
        flash("Please login first", "error")
        return redirect(url_for("login"))

    customer_id = request.args.get("customer_id")
    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            customer_id,
            name,
            email,
            age,
            gender,
            segment,
            location,
            join_date,
            churned
        FROM customers
        ORDER BY name ASC
    """)

    customers = cursor.fetchall()

    selected_customer = None
    transaction_summary = None
    feedback_summary = None
    prediction = None
    customer_data = None
    ai_analysis = None
    ai_analysis_html = None

    if customer_id:

        cursor.execute("""
            SELECT
                customer_id,
                name,
                email,
                age,
                gender,
                segment,
                location,
                join_date,
                churned
            FROM customers
            WHERE customer_id = %s
        """, (customer_id,))

        selected_customer = cursor.fetchone()

        cursor.execute("""
            SELECT
                COUNT(*) AS total_transactions,
                AVG(amount) AS average_spend,
                MAX(date) AS last_purchase
            FROM transactions
            WHERE customer_id = %s
        """, (customer_id,))

        transaction_summary = cursor.fetchone()

        cursor.execute("""
            SELECT
                AVG(rating) AS average_rating,
                (
                    SELECT comments
                    FROM feedback
                    WHERE customer_id = %s
                    ORDER BY date DESC
                    LIMIT 1
                ) AS latest_comment,
                (
                    SELECT sentiment
                    FROM feedback
                    WHERE customer_id = %s
                    ORDER BY date DESC
                    LIMIT 1
                ) AS latest_sentiment
            FROM feedback
            WHERE customer_id = %s
        """, (
            customer_id,
            customer_id,
            customer_id
        ))

        feedback_summary = cursor.fetchone()

        if selected_customer[8] == 1:

            prediction = (
                "Churned",
                None,
                None
            )

        else:

            cursor.execute("""
                SELECT
                    risk_level,
                    confidence,
                    predicted_on
                FROM retention_alerts
                WHERE customer_id = %s
                ORDER BY predicted_on DESC
                LIMIT 1
            """, (customer_id,))

            prediction = cursor.fetchone()

            if prediction is None:
                prediction = (
                    "Low Risk",
                    0.00,
                    None
                )

    # ==========================================
    # CREATE AI CUSTOMER DATA
    # ==========================================

        customer_data = {
            "name": selected_customer[1],
            "age": selected_customer[3],
            "gender": selected_customer[4],
            "segment": selected_customer[5],
            "location": selected_customer[6],
            "join_date": str(selected_customer[7]),
            "churned": selected_customer[8],

            "risk_status": prediction[0] if prediction else "Unknown",
            "risk_confidence": prediction[1] if prediction else None,

            "total_transactions": (
                transaction_summary[0]
                if transaction_summary else 0
            ),

            "average_spend": (
                float(transaction_summary[1])
                if transaction_summary
                and transaction_summary[1] is not None
                else 0
            ),

            "last_purchase": (
                str(transaction_summary[2])
                if transaction_summary
                and transaction_summary[2] is not None
                else None
            ),

            "average_rating": (
                float(feedback_summary[0])
                if feedback_summary
                and feedback_summary[0] is not None
                else 0
            ),

            "latest_feedback": (
                feedback_summary[1]
                if feedback_summary
                else None
            ),

            "sentiment": (
                feedback_summary[2]
                if feedback_summary
                else None
            )
        }

    # ==========================================
    # GENERATE AI ANALYSIS
    # ==========================================

        ai_analysis = generate_ai_analysis(customer_data)
        if ai_analysis:
            ai_analysis_html = markdown.markdown(
                ai_analysis,
                extensions=['extra', 'nl2br', 'sane_lists']
            )
        else:
            ai_analysis_html = None

        cursor.close()

    return render_template(
        "ai_analyst.html",
        customers=customers,
        selected_customer=selected_customer,
        transaction_summary=transaction_summary,
        feedback_summary=feedback_summary,
        prediction=prediction,
        customer_data=customer_data,
        ai_analysis=ai_analysis,
        ai_analysis_html=ai_analysis_html
    )

if __name__ == "__main__":
    app.run(debug=True, use_reloader = True)