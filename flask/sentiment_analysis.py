import pymysql
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv
import os

load_dotenv()

connection = pymysql.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DB")
)

cursor = connection.cursor()

analyzer = SentimentIntensityAnalyzer()

cursor.execute("SELECT feedback_id, comments FROM Feedback")
feedback = cursor.fetchall()

positive = 0
negative = 0
neutral = 0

for row in feedback:
    feedback_id = row[0]
    comment = row[1]

    if comment is None:
        sentiment = "Neutral"
    else: 
        score = analyzer.polarity_scores(comment)
        compound = score['compound']

        if compound >= 0.05:
            sentiment = "Positive"
            positive += 1
        elif compound <= -0.05:
            sentiment = "Negative"
            negative += 1
        else:
            sentiment = "Neutral"
            neutral += 1

        cursor.execute("""
            UPDATE Feedback 
            SET sentiment = %s 
            WHERE feedback_id = %s
        """, (sentiment, feedback_id))
        print(f"Feedback {feedback_id}: '{comment}' → {sentiment}")

connection.commit()
cursor.close()
connection.close()

total = positive + negative + neutral

print(f"\nTotal feedback analyzed: {total}")

if total > 0:
    print(f"Positive: {positive} ({positive/total*100:.1f}%)")
    print(f"Negative: {negative} ({negative/total*100:.1f}%)")
    print(f"Neutral:  {neutral} ({neutral/total*100:.1f}%)")
else:
    print("No feedback comments found to analyze.")