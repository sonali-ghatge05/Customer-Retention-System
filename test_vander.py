from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

comments = [
    "Great service and fast delivery!",
    "Product quality was poor.",
    "Average experience",
    "Worst experience ever",
    "Loved the product",
    "Okay",
    "Waste of money",
    "Perfect purchase"
]

for comment in comments:
    scores = analyzer.polarity_scores(comment)
    compound = scores['compound']
    
    if compound >= 0.05:
        sentiment = "Positive"
    elif compound <= -0.05:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"
    
    print(f"{comment:<40} → {sentiment} ({compound})")