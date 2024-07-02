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


def remove_stop_words(words: list[str]):
    """
    Remove stop words from a list of words, including a custom list of excluded words.
    """
    CUSTOM_EXCLUDED_WORDS = [
        "x", "com", "twitter", "like", "new", "one", "crypto", "utc", "go", "get",
        "also", "make", "see", "yes", "no", "good", "time", "day", "know", "people",
        "gm", "wagmi", "remilio", "token", "trading", "hours", "time", "rt", "first",
        "soon", "every", "still", "next", "follow", "higher", "team", "param", "launch",
        "price", "ever", "join", "money", "app", "buy", "week", "send", "comment", "https",
        "discord", "chart", "bag", "best", "update", "market", "back", "today", "news",
        "last", "really", "much", "right", "dont", "pump", "back", "today", "high",
        "year", "early", "big", "low", "long", "well", "look", "take", "need", "let",
        "en", "tp", "list", "keep", "billion", "tweet", "link", "share", "video", "going",
        "use", "hit", "account", "followers", "telegram", "website", "contract", "address",
        "mcap", "low", "big", "enjoy", "ready", "amp", "usd", "eth", "btc", "moon",
        "want", "terms", "conditions", "privacy", "policy", "contact", "support", "help",
        "mc", "think", "give", "away", "giveaway", "win", "winning", "winners", "winner",
        "days", "since", "many", "rewards", "thanks", "daily", "weekly", "monthly", "yearly",
        "biggest", "projects", "many", "much", "huge", "end", "us", "project", "interesting",
        "important", "show", "pre", "always", "everyone", "earn", "co", "live", "got", "bro",
        "free", "start", "trade", "making", "available", "wallets", "multiple", "exchange", "futures",
        "looking", "great", "case", "around", "users", "community", "members", "brother", "range",
        "morning", "even", "imagine", "thank", "thanks", "night", "world", "tax", "listing", "lost",
        "getting", "officially", "already", "chance", "submit", "printed", "hour", "seems", "hours",
        "study", "kind", "love", "doubt", "weeks", "running", "gets", "remember", "target", "sold", "asses",
        "holding", "never", "supply", "total", "similar", "man", "happy", "call", "premium", "post", "enough",
        "mate", "called", "currently", "future", "massive", "theres", "campaign", "task", "tasks", "bros", "things",
        "alert", "gemscore", "friend", "friends", "brothers", "sister", "sisters", "brother", "details", "could",
        "listed", "listings", "list", "lists", "tokens", "token", "volume", "another", "easter", "bought", "made",
        "gemscorealpha", "content", "looks", "looked", "growing", "etc", "solid", "sunday", "system", "partnership",
        "rich", "spot", "trending", "add", "place", "secure", "security", "via", "metrics", "yeah", "tell", "recent",
        "least", "second", "highest", "forget", "launches", "development", "investment", "doesnt", "luck", "funds",
        "backed", "ones", " user", "waiting", "due", "went", "mean", "favorite", "trying", "create", "nfa", "cool",
        "point", "probably", "dollar", "transactions", "conviction", "comes", "hodl", "hodling", "hodlers", "official",
        "burn", "strategy", "vote", "maybe", "success", "reply", "goes", "simple", "research", "millions", "plays",
        "access", "ticker", "billions", "happens", "non", "grow", "step", "yesterday", "sitting", "read", "set",
        "zone", "means", "thats", "means", "quick", "break", "taking", "offers", "single", "wrong", "feel", "rent",
        "seen", "others", "try", "together", "times", "part", "unique", "gave", "giving", "gives", "gave", "talking",
        "code", "cant", "build", "watch", "weekend", "powered", "gains", "lose", "true", "portfolio", "guy", "guys",
        "found", "almost", "fun", "missed", "makes", "native", "gems", "leg", "seeing", "safe", "safu", "mil", "boost",
        "active", "hot", "opportunities", "expect", "technology", "king", "investors", "action", "position", "scam",
        "different", "hype", "hyped", "hypes", "coming", "airdrop", "would", "run", "entry", "announce", "thread",
        "lower", "strong", "without", "points", "thrilled", "might", "hard", "concluded", "opened", "pair", "pairs",
        "told", "anything", "level", "become", "innovation", "lfg", "please", "thing", "circle", "wait", "come",
        "find", "found", "yet", "term", "event", "profit", "building", "easy", "started", "season", "previous", "gem",
        "recently", "product", "usdt", "bitcoin", "chain", "ecosystem", "coin", "coins", "months", "everything",
        "beyond", "buying", "block", "chain", "protocol", "wallet", "wallets", "exchange", "exchanges", "platform",
        "mexc", "everything", "narrative", "million", "launched", "presale", "cycle", "lets", "gonna", "airdrops",
        "network", "miss", "drop", "worth", "hold", "open", "something", "everything", "maestro", "mexc", "platforms",
        "nice", "ecosystems", "lets", "sell", "short", "current", "believe", "check", "sell", "buy", "sells", "buys",
        "close", "space", "gonna", "presale", "airdrops", "web", "risk", "labs", "staking", "cookie", "say",
        "lot", "opportunity", "sure", "work", "dyor", "nfa", "assets", "fade", "ngmi", "wagmi", "check", "data",
        "blockchain", "stone", "defi", "worth", "drop", "dump", "pump", "dexscreener", "defillama", "dune",
        "ath", "atl", "nice", "ecosystem", "open", "trip", "potential", "cap", "deposit", "claim", "life",
        "lol", "using", "spaces", "growth", "holders", "decentralized", "utility", "dextools", "life", "name",
        "profits", "years", "latest"
    ]

    # Combine NLTK English stopwords with the custom excluded words
    stops = set(stopwords.words("english")).union(set(CUSTOM_EXCLUDED_WORDS))

    # Filter out stopwords and words with less than 2 characters
    meaningful_words = [w for w in words if w not in stops and len(w) > 2 and not profanity.contains_profanity(w)]

    return meaningful_words


def frequency_analysis(posts: list, limit: int):
    """
    Perform a frequency analysis on a list of posts, excluding English stop words.

    Parameters:
    - posts: a list of strings, where each string is a post.

    Returns:
    - A Counter object mapping words to their frequencies.
    """
    all_words = []

    for post in posts:
        # Clean and tokenize each post
        words = clean_text(post)
        # Remove stop words
        meaningful_words = remove_stop_words(words)
        # Accumulate words
        all_words.extend(meaningful_words)

    # Count word frequencies
    word_counts = Counter(all_words)

    # Filter words that appear more than 3 times
    filtered_counts = {word: count for word, count in word_counts.items() if count > 3}

    # Sort and apply limit
    # To maintain the 'most_common' behavior, we sort the filtered dictionary by count, descending
    sorted_filtered_counts = dict(sorted(filtered_counts.items(), key=lambda item: item[1], reverse=True)[:limit])

    return sorted_filtered_counts


def extract_categories_from_json(json_data):
    """
    Recursively search for and extract values associated with the key 'category' in nested JSON data.

    :param json_data: A JSON object (can be a dict or a list) from which to extract 'category' values.
    :return: A list of values associated with the key 'category'.
    """
    if not json_data:
        return []

    categories = []

    if isinstance(json_data, dict):
        # If json_data is a dictionary
        for key, value in json_data.items():
            if key == 'category' or key == "categories":
                categories.append(value)
            else:
                # If the value is a dict or list, search recursively
                categories.extend(extract_categories_from_json(value))
    elif isinstance(json_data, list):
        # If json_data is a list
        for item in json_data:
            categories.extend(extract_categories_from_json(item))

    return categories


def flatten_mixed_list(mixed_list):
    flat_list = []
    for item in mixed_list:
        if isinstance(item, list):  # If the item is a list, extend flat_list with its contents
            flat_list.extend(item)
        else:  # Otherwise, simply append the item to flat_list
            flat_list.append(item)
    return flat_list
