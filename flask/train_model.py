import pandas as pd
import pymysql
from sklearn.preprocessing import LabelEncoder 
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import pickle
import os
from dotenv import load_dotenv

load_dotenv()

conn = pymysql.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DB")
)

df = pd.read_sql("SELECT * FROM customer_ml_view", conn)
conn.close()

print(df.head())

df = df.fillna(0)

df = df.drop(['customer_id','last_purchase'], axis=1)

print(df.head())

le_gender = LabelEncoder()
df['gender'] = le_gender.fit_transform(df["gender"])

le_location = LabelEncoder()
df['location'] = le_location.fit_transform(df["location"])

le_segment = LabelEncoder()
df['segment'] = le_segment.fit_transform(df["segment"])

print("After encoding: \n", df.head())

x = df.drop('churned', axis=1)
y = df['churned']

print("\nFeatures")
print(x.head())

print("\nLabels")
print(y.head())

x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42, stratify=y)

print("training sixe: ", len(x_train))
print("testing sixe: ", len(x_test))

model = RandomForestClassifier(n_estimators=300, max_depth=10, min_samples_split=5, min_samples_leaf=2, random_state=42)
model.fit(x_train, y_train)

predictions = model.predict(x_test)
print("Predictions: ", predictions)
print("Actual: ", y_test.values)

accuracy = accuracy_score(y_test, predictions)
print(f"Accuracy: {accuracy:.2%}")
cm = confusion_matrix(y_test,predictions)
print("Confusion matrics:", cm)

print("classification report: ", classification_report(y_test,predictions))

importance = pd.DataFrame({
    "Feature": x.columns,
    "Importance": model.feature_importances_
})

print("\n========== FEATURE IMPORTANCE ==========")
print(importance.sort_values(by="Importance", ascending=False))


with open('model.pkl', 'wb') as f:
    pickle.dump(model, f)

with open('le_gender.pkl', 'wb') as f:
    pickle.dump(le_gender, f)

with open('le_location.pkl', 'wb') as f:
    pickle.dump(le_location, f)

with open('le_segment.pkl', 'wb') as f:
    pickle.dump(le_segment, f)

with open ('model.pkl', 'rb') as f:
    loaded_model = pickle.load(f)

with open('le_gender.pkl', 'rb') as f:
    loaded_le_gender = pickle.load(f)

with open('le_location.pkl', 'rb') as f:
    loaded_le_location = pickle.load(f)

with open('le_segment.pkl', 'rb') as f:
    loaded_le_segment = pickle.load(f)  

new_predictions = loaded_model.predict(x_test)
print("Predictions from loaded model:", new_predictions)

print("\n========== CHURN DISTRIBUTION ==========")
print(df["churned"].value_counts())
