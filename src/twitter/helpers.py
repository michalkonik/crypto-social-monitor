import json
import logging
from datetime import datetime
import pytz
import re

from collections import Counter
from nltk.corpus import stopwords
import nltk

from better_profanity import profanity

# Ensure NLTK resources are downloaded (do this once)
nltk.download('punkt')
nltk.download('stopwords')

from src.constants import (
    TIME_UNITS
)


def extract_account_info(profile_data: dict) -> dict:
    account_info = {
        "screen_name": profile_data["screen_name"],
        "profile_id": profile_data["id_str"],
        "account_info": profile_data,
    }
    return account_info


def get_current_time():
    return datetime.now(pytz.timezone('US/Eastern'))


def parse_timeframe_to_hours(timeframe_str):
    """Convert a timeframe string to hours."""
    return int(timeframe_str[:-1]) * TIME_UNITS[timeframe_str[-1]]


def calculate_smart_followers_score(
        smart_followers_for_timeframe: int,
        total_smart_followers: int,
        total_smart_followers_monitored: int
) -> float:
    """
    Calculate a score from 1 to 10 based on:
    1. The ratio of smart_followers_for_timeframe to total_smart_followers,
    2. The ratio of total_smart_followers to total_smart_followers_monitored.

    Parameters:
    - smart_followers_for_timeframe: The count of smart followers for the specified timeframe.
    - total_smart_followers: The current total count of smart followers.
    - total_smart_followers_monitored: All possible smart followers ever monitored.

    Returns:
    - A score between 1 and 10.
    """
    if total_smart_followers > 0 and smart_followers_for_timeframe > 0 and total_smart_followers_monitored > 0:
        # Ratio of smart followers for timeframe to total smart followers
        timeframe_to_total_ratio = (smart_followers_for_timeframe / total_smart_followers) * 100

        # Ratio of total smart followers to total smart followers monitored
        total_to_monitored_ratio = (total_smart_followers / total_smart_followers_monitored) * 100

        # Calculate the weighted score, considering both ratios
        # Adjust weights if necessary to prioritize one ratio over the other
        percentage_score = (timeframe_to_total_ratio * 0.5) + (total_to_monitored_ratio * 0.5)

        score = round(percentage_score / 10, 2)  # Scale to 1-10 and round to 2 decimal places
        return min(score, 10)  # Ensure score does not exceed 10
    else:
        return 0


def match_category_with_score(categories_with_keywords, description):
    """
    Matches a category to a given description by scoring each category based on keyword relevance,
    looking for exact or close matches using word boundaries to avoid partial word matches.

    Parameters:
    - categories_with_keywords: A dictionary where each key is a category and its value is a list of keywords.
    - description: A string representing the description to match against.

    Returns:
    - The category with the highest relevance score to the description, or "Other" if no match is found.
    """
    description_lower = description.lower()
    scores = {}

    if not description_lower:
        return "Other"

    # Compile a regex pattern for word boundary matching for each keyword
    # This helps in matching ' AI ' but not 'said' if AI is a keyword
    keywords_pattern = {category: [re.compile(r'\b' + re.escape(keyword.lower()) + r'\b') for keyword in keywords]
                        for category, keywords in categories_with_keywords.items()}

    # Iterate through each category and its compiled regex patterns for keywords
    for category, patterns in keywords_pattern.items():
        scores[category] = 0
        category_lower = category.lower()

        # Check for the presence of the category name itself as a whole word in the description
        if re.search(r'\b' + re.escape(category_lower) + r'\b', description_lower):
            scores[category] += description_lower.count(category_lower) * 5  # Weight category name matches higher

        # Check for the presence of associated keywords as whole words in the description
        for pattern in patterns:
            match_count = len(pattern.findall(description_lower))
            if match_count > 0:
                # Increase score by the count of occurrences
                scores[category] += match_count

    # Find the category with the highest score
    best_category = max(scores, key=scores.get) if scores else "Other"

    # Return the best category if its score is greater than 0, otherwise return "Other"
    return best_category if scores[best_category] > 0 else "Other"


def clean_text(text: str):
    """Clean and tokenize text."""
    # Remove non-letters and lowercase
    letters_only = re.sub("[^a-zA-Z]", " ", text)
    words = letters_only.lower().split()
    return words


