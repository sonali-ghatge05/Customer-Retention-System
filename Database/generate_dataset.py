import pandas as pd
import random
from faker import Faker
from datetime import datetime, timedelta

# -----------------------------
# Configuration
# -----------------------------
fake = Faker("en_IN")

random.seed(42)
Faker.seed(42)

NUM_CUSTOMERS = 250

cities = [
    "Mumbai",
    "Delhi",
    "Bangalore",
    "Hyderabad",
    "Pune",
    "Chennai",
    "Ahmedabad",
    "Kolkata"
]

electronics = [
    "Smartphone",
    "Laptop",
    "Tablet",
    "Camera",
    "Headphones",
    "Bluetooth Speaker",
    "Power Bank",
    "Smart Watch"
]

fashion = [
    "T-Shirt",
    "Shoes",
    "Jeans",
    "Backpack",
    "Perfume"
]

home = [
    "Mixer Grinder",
    "Water Bottle"
]

products = electronics + fashion + home

positive_quality = [
    "quality is excellent",
    "works perfectly",
    "exceeded my expectations",
    "is worth every rupee",
    "is amazing",
    "looks premium",
    "is exactly as described",
    "is fantastic"
]

neutral_quality = [
    "quality is average",
    "is decent",
    "works fine",
    "meets expectations",
    "is acceptable",
    "is okay"
]

negative_quality = [
    "quality is poor",
    "stopped working quickly",
    "is disappointing",
    "is below expectations",
    "has defects",
    "is not worth the price"
]

delivery_positive = [
    "Delivery was very fast.",
    "Package arrived on time.",
    "Packaging was excellent.",
    "Delivery exceeded expectations."
]

delivery_neutral = [
    "Delivery was okay.",
    "Packaging was acceptable.",
    "Delivery was average."
]

delivery_negative = [
    "Delivery was delayed.",
    "Package arrived damaged.",
    "Packaging was poor.",
    "Delivery took too long."
]

support_positive = [
    "Customer support was helpful.",
    "Support team resolved my issue quickly.",
    "Excellent customer service."
]

support_neutral = [
    "Didn't need customer support.",
    "No issues with support."
]

support_negative = [
    "Customer support was unhelpful.",
    "Support never responded.",
    "Very poor customer service."
]

ending_positive = [
    "Highly recommended.",
    "Very satisfied.",
    "Will definitely buy again.",
    "Loved the experience."
]

ending_neutral = [
    "Overall an average experience.",
    "Nothing special.",
    "It was okay."
]

ending_negative = [
    "Would not recommend.",
    "Very disappointed.",
    "Won't buy again."
]

def generate_comment(product, rating):

    if rating >= 4:

        comment = (
            f"The {product} "
            + random.choice(positive_quality)
            + ". "
            + random.choice(delivery_positive)
            + " "
            + random.choice(support_positive)
            + " "
            + random.choice(ending_positive)
        )

        sentiment = "Positive"

    elif rating == 3:

        comment = (
            f"The {product} "
            + random.choice(neutral_quality)
            + ". "
            + random.choice(delivery_neutral)
            + " "
            + random.choice(support_neutral)
            + " "
            + random.choice(ending_neutral)
        )

        sentiment = "Neutral"

    else:

        comment = (
            f"The {product} "
            + random.choice(negative_quality)
            + ". "
            + random.choice(delivery_negative)
            + " "
            + random.choice(support_negative)
            + " "
            + random.choice(ending_negative)
        )

        sentiment = "Negative"

    return comment

# ==========================================================
# CUSTOMER GENERATION
# ==========================================================

customers = []

for customer_id in range(1, NUM_CUSTOMERS + 1):

    name = fake.name()

    email = (
        name.lower()
        .replace(" ", ".")
        .replace("'", "")
        + str(customer_id)
        + "@gmail.com"
    )

    age = random.randint(18, 60)

    gender = random.choice(["Male", "Female"])

    location = random.choice(cities)

    join_date = fake.date_between(
        start_date="-3y",
        end_date="-30d"
    )

    # -----------------------------------
    # Persona
    # -----------------------------------

    if age <= 25:

        persona = random.choices(
            ["New Customer", "Bargain Hunter", "Happy Regular"],
            weights=[35, 40, 25],
            k=1
        )[0]

    elif age <= 35:

        persona = random.choices(
            ["Happy Regular", "Bargain Hunter", "Loyal Premium"],
            weights=[45, 30, 25],
            k=1
        )[0]

    elif age <= 50:

        persona = random.choices(
            ["Loyal Premium", "Happy Regular", "Inactive"],
            weights=[50, 30, 20],
            k=1
        )[0]

    else:

        persona = random.choices(
            ["Inactive", "Loyal Premium", "Dissatisfied"],
            weights=[50, 20, 30],
            k=1
        )[0]

    # -----------------------------------
    # Segment
    # -----------------------------------

    if persona == "Loyal Premium":

        segment = "Premium"

    elif persona == "Happy Regular":

        segment = "Regular"

    else:

        segment = random.choices(
            ["Premium", "Regular"],
            weights=[40, 60],
            k=1
        )[0]

    # -----------------------------------
    # Churn
    # -----------------------------------

    if persona == "Loyal Premium":

        churned = random.choices(
            [0, 1],
            weights=[98, 2],
            k=1
        )[0]

    elif persona == "Happy Regular":

        churned = random.choices(
            [0, 1],
            weights=[92, 8],
            k=1
        )[0]

    elif persona == "Bargain Hunter":

        churned = random.choices(
            [0, 1],
            weights=[70, 30],
            k=1
        )[0]

    elif persona == "Inactive":

        churned = random.choices(
            [0, 1],
            weights=[30, 70],
            k=1
        )[0]

    elif persona == "Dissatisfied":

        churned = random.choices(
            [0, 1],
            weights=[10, 90],
            k=1
        )[0]

    else:

        churned = random.choices(
            [0, 1],
            weights=[95, 5],
            k=1
        )[0]

    customers.append({

        "customer_id": customer_id,
        "name": name,
        "email": email,
        "join_date": join_date,
        "segment": segment,
        "churned": churned,
        "age": age,
        "gender": gender,
        "location": location,
        "persona": persona

    })

customers_df = pd.DataFrame(customers)

print(customers_df.head())

print("\nCustomers :", len(customers_df))
print(customers_df["persona"].value_counts())
print(customers_df["churned"].value_counts())

# ==========================================================
# TRANSACTION GENERATION
# ==========================================================

transactions = []

transaction_id = 1

for customer in customers:

    customer_id = customer["customer_id"]
    persona = customer["persona"]
    join_date = customer["join_date"]

    # -----------------------------
    # Buying Behaviour
    # -----------------------------

    if persona == "Loyal Premium":

        transaction_count = random.randint(18, 30)
        min_amount = 2500
        max_amount = 7000

        product_pool = (
            electronics * 6 +
            fashion * 2 +
            home
        )

    elif persona == "Happy Regular":

        transaction_count = random.randint(10, 18)
        min_amount = 1000
        max_amount = 3500

        product_pool = (
            electronics * 3 +
            fashion * 4 +
            home * 2
        )

    elif persona == "Bargain Hunter":

        transaction_count = random.randint(12, 22)
        min_amount = 250
        max_amount = 1500

        product_pool = (
            fashion * 5 +
            home * 4 +
            electronics
        )

    elif persona == "Inactive":

        transaction_count = random.randint(1, 4)
        min_amount = 500
        max_amount = 2500

        product_pool = products

    elif persona == "Dissatisfied":

        transaction_count = random.randint(2, 6)
        min_amount = 400
        max_amount = 3000

        product_pool = electronics * 5 + fashion

    else:

        transaction_count = random.randint(1, 5)
        min_amount = 300
        max_amount = 1800

        product_pool = products

    # -----------------------------
    # Create Transactions
    # -----------------------------

    for i in range(transaction_count):

        total_days = max(
            1,
            (datetime.today().date() - join_date).days
        )

        purchase_date = join_date + timedelta(
            days=random.randint(1, total_days)
        )

        amount = round(
            random.uniform(min_amount, max_amount),
            2
        )

        product = random.choice(product_pool)

        transactions.append({

            "transaction_id": transaction_id,

            "customer_id": customer_id,

            "date": purchase_date,

            "amount": amount,

            "product": product

        })

        transaction_id += 1

transactions_df = pd.DataFrame(transactions)

transactions_df = transactions_df.sort_values(
    ["customer_id", "date"]
)

print(transactions_df.head())

print("\nTotal Transactions :", len(transactions_df))

# ==========================================================
# FEEDBACK GENERATION (WITHOUT SENTIMENT)
# ==========================================================

feedback = []

feedback_id = 1

for _, transaction in transactions_df.iterrows():

    customer_id = transaction["customer_id"]
    purchase_date = transaction["date"]
    product = transaction["product"]

    persona = customers_df.loc[
        customers_df["customer_id"] == customer_id,
        "persona"
    ].values[0]

    # -----------------------------
    # Rating based on persona
    # -----------------------------

    if persona == "Loyal Premium":

        rating = random.choices(
            [5, 4, 3],
            weights=[60, 35, 5],
            k=1
        )[0]

    elif persona == "Happy Regular":

        rating = random.choices(
            [5, 4, 3, 2],
            weights=[35, 40, 20, 5],
            k=1
        )[0]

    elif persona == "Bargain Hunter":

        rating = random.choices(
            [5, 4, 3, 2, 1],
            weights=[20, 30, 30, 15, 5],
            k=1
        )[0]

    elif persona == "Inactive":

        rating = random.choices(
            [5, 4, 3, 2, 1],
            weights=[10, 20, 35, 20, 15],
            k=1
        )[0]

    elif persona == "Dissatisfied":

        rating = random.choices(
            [3, 2, 1],
            weights=[20, 40, 40],
            k=1
        )[0]

    else:

        rating = random.randint(3, 5)

    # -----------------------------
    # Generate Comment Only
    # -----------------------------

    comment = generate_comment(product, rating)

    feedback_date = purchase_date + timedelta(
        days=random.randint(1, 10)
    )

    feedback.append({

        "feedback_id": feedback_id,
        "customer_id": customer_id,
        "date": feedback_date,
        "rating": rating,
        "comments": comment

    })

    feedback_id += 1

feedback_df = pd.DataFrame(feedback)

feedback_df = feedback_df.sort_values(
    ["customer_id", "date"]
)

print(feedback_df.head())
print()

print("Total Feedback :", len(feedback_df))

customers_df.drop(columns=["persona"]).to_csv(
    "customers.csv",
    index=False
)

transactions_df.to_csv(
    "transactions.csv",
    index=False
)

feedback_df.to_csv(
    "feedback.csv",
    index=False
)

print("\nCSV files generated successfully.")