
import pandas as pd
import pickle
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier

# Load everything from saved pickle files
with open('model.pkl', 'rb') as f:
    model = pickle.load(f)

with open('le_gender.pkl', 'rb') as f:
    le_gender = pickle.load(f)

with open('le_location.pkl', 'rb') as f:
    le_location = pickle.load(f)\
    
with open('le_segment.pkl', 'rb') as f:
    le_segment = pickle.load(f) 

customer1 = {
    'age': [30],
    'gender': ['Male'],
    'location': ['Mumbai'],
    'segment': ['Premium'],
    'total_transactions': [10],
    'avg_spend': [1500.0],
    'avg_rating': [5.0]
}
df1 = pd.DataFrame(customer1)
df1['gender'] = le_gender.transform(df1["gender"])
df1['location'] = le_location.transform(df1["location"])
df1['segment'] = le_segment.transform(df1["segment"])
pred1 = model.predict(df1)
prob1 = model.predict_proba(df1)[0][1]
print(f"Customer 1: {'Churn' if pred1[0]==1 else 'Stay'}, Probability: {prob1*100:.1f}%")
if prob1 >= 0.7:
    risk = "High Risk"
elif prob1 >= 0.4:
    risk = "Medium Risk"
else:
    risk = "Low Risk"

customer2 = {
    'age': [45],
    'gender': ['Female'],
    'location': ['Delhi'],
    'segment': ['Regular'],
    'total_transactions': [1],
    'avg_spend': [150.0],
    'avg_rating': [1.0]
}
df2 = pd.DataFrame(customer2)
df2['gender'] = le_gender.transform(df2["gender"])
df2['location'] = le_location.transform(df2["location"])
df2['segment'] = le_segment.transform(df2["segment"])
pred2 = model.predict(df2)
prob2 = model.predict_proba(df2)[0][1]
print(f"Customer 2: {'Churn' if pred2[0]==1 else 'Stay'}, Probability: {prob2*100:.1f}%")
if prob2 >= 0.7:
    risk = "High Risk"
elif prob2 >= 0.4:
    risk = "Medium Risk"
else:
    risk = "Low Risk"

customer3 = {
    'age': [35],
    'gender': ['Male'],
    'location': ['Pune'],
    'segment': ['Regular'],
    'total_transactions': [3],
    'avg_spend': [600.0],
    'avg_rating': [3.0]
}
df3 = pd.DataFrame(customer3)
df3['gender'] = le_gender.transform(df3["gender"])
df3['location'] = le_location.transform(df3["location"])
df3['segment'] = le_segment.transform(df3["segment"])
pred3 = model.predict(df3)
prob3 = model.predict_proba(df3)[0][1]
print(f"Customer 3: {'Churn' if pred3[0]==1 else 'Stay'}, Probability: {prob3*100:.1f}%")
if prob3 >= 0.7:
    risk = "High Risk"
elif prob3 >= 0.4:
    risk = "Medium Risk"
else:
    risk = "Low Risk"