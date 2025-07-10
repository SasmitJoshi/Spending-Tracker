from dotenv import load_dotenv
import os
import requests
import matplotlib.pyplot as plt
from google import genai
import time
import json

load_dotenv()
UP_TOKEN = os.getenv("UP_API_KEY")
GEMINI_TOKEN = os.getenv("GEMINI_API_KEY")
header = {"Authorization": f"Bearer {UP_TOKEN}"}
client = genai.Client(api_key=GEMINI_TOKEN)

categories = f"""
games-and-software
booze
events-and-gigs
hobbies
holidays-and-travel
lottery-and-gambling
pubs-and-bars
restaurants-and-cafes
takeaway
tobacco-and-vaping
tv-and-music

friends
children-and-family
clothing-and-accessories
education-and-student-loans
fitness-and-wellbeing
gifts-and-charity
hair-and-beauty
health-and-medical
investments
life-admin
mobile-phone
news-magazines-and-books
technology

groceries
homeware-and-appliances
internet
maintenance-and-improvements
pets
rates-and-insurance
rent-and-mortgage
utilities

rego-and-maintenance
cycling
fuel
parking
public-transport
repayments
taxis-and-share-cars
tolls
"""

TRANSACTIONS_FILE = "transactions_cache.json"
CATEGORY_FILE = "category_cache.json"

def load_json_file(filename, default):
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {filename} is corrupted or empty.")
    return default

def save_json_file(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

category_cache = load_json_file(CATEGORY_FILE, {})
transactions_cache = load_json_file(TRANSACTIONS_FILE, [])

def save_transactions_cache(transactions):
    save_json_file(TRANSACTIONS_FILE, transactions)

def save_category_cache():
    save_json_file(CATEGORY_FILE, category_cache)

# Retrieves all the transactions that have occured with this UP
# account
def get_all_transactions(force_refresh=False):
    global transactions_cache
    if not force_refresh and transactions_cache:
        return transactions_cache

    print("Fetching transactions from UP API...")
    all_transactions = []
    url = "https://api.up.com.au/api/v1/transactions"

    while url:
        res = requests.get(url, headers=header)
        res.raise_for_status()
        json_data = res.json()
        all_transactions.extend(json_data.get("data", []))
        url = json_data.get("links", {}).get("next")

    transactions_cache = all_transactions
    save_transactions_cache(all_transactions)
    return all_transactions

# Cleans the transactions, removing any transactions that are transfers to and from
# accounts
def clean_transactions(transactions):
    cleaned_transactions = []
    for transaction in transactions:
        transfer_account = transaction["relationships"].get("transferAccount", {}).get("data")
        if not transfer_account:
            cleaned_transactions.append(transaction)

    return cleaned_transactions

# Splits transactions into months of the year as well as inflows and outflows
# Good for tracking individual expenses.
def split_transactions():
    transactions = get_all_transactions()
    transactions = clean_transactions(transactions)

    monthly_transactions = {
        "inflow": {},
        "outflow": {}
    }

    for transaction in transactions:
        transaction = transaction["attributes"]
        amount = round(float(transaction["amount"]["value"]), 2)
        date = transaction["createdAt"]

        year = date.split("-")[0]
        month = date.split("-")[1]

        key = month + "-" + year

        if amount < 0:
            if key not in monthly_transactions["outflow"]:
                monthly_transactions["outflow"][key] = [amount]
            else:
                monthly_transactions["outflow"][key].append(amount)
        else:
            if key not in monthly_transactions["inflow"]:
                monthly_transactions["inflow"][key] = [amount]
            else:
                monthly_transactions["inflow"][key].append(amount)

    return monthly_transactions

# Calculate total inflows and outflows for each month
# Good for tracking overall view
def get_total_transactions():
    transactions = split_transactions()
    total_transactions = {}

    for month in transactions.get("inflow", {}):
        total = round(sum(transactions["inflow"][month]), 2)
        if month not in total_transactions:
            total_transactions[month] = {}
        total_transactions[month]["inflows"] = total

    for month in transactions.get("outflow", {}):
        total = round(sum(transactions["outflow"][month]), 2)
        if month not in total_transactions:
            total_transactions[month] = {}
        total_transactions[month]["outflows"] = total

    return total_transactions


# Determine the category of a transaction given the merchant name for uncategorised transactions
def determine_category(merchant_name):
    prompt = f"""
    Given this list of categories:
    {categories}

    Which category does {merchant_name} fall under?
    Just give the one word response for the category in lowercase and do not shorten any
    of the categories.

    If you're given a string that sounds like a person's name or does not fall under any category
    just put it under the 'friends' category (except for 'Sasmit Joshi Stake' it should be 'investments').
    """
    response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt
    )

    return response.text

# Calculate the daily outflows by category
def get_daily_category_totals():
    transactions = get_all_transactions()
    transactions = clean_transactions(transactions)

    daily_category_totals = {}

    for transaction in transactions:
        attributes = transaction["attributes"]
        amount = round(float(attributes["amount"]["value"]), 2)

        if amount >= 0:
            continue

        date = attributes["createdAt"]
        date = date.split("T")[0]
        category = transaction.get("relationships", {}).get("category", {}).get("data")
        merchant_name = transaction.get("attributes", {}).get("description")

        if category:
            category_id = category.get("id")
        else:
            if merchant_name in category_cache:
                category_id = category_cache[merchant_name]
            else:
                category_id = determine_category(merchant_name)
                print(f"{merchant_name} has category: {category_id}")

                category_cache[merchant_name] = category_id
                save_category_cache()

                # Sleep 3 or 4 seconds to avoid the going out request count limit (15 per min)
                time.sleep(3)

        if date not in daily_category_totals:
            daily_category_totals[date] = {}

        if category_id not in daily_category_totals[date]:
            daily_category_totals[date][category_id] = amount
        else:
            daily_category_totals[date][category_id] += amount

        daily_category_totals[date][category_id] = round(daily_category_totals[date][category_id], 2)

    return daily_category_totals

# Calculate the outflows by category for each month
def get_monthly_category_totals():
    transactions = get_all_transactions()
    transactions = clean_transactions(transactions)

    monthly_category_totals = {}

    for transaction in transactions:
        attributes = transaction["attributes"]
        amount = round(float(attributes["amount"]["value"]), 2)

        if amount >= 0:
            continue

        date = attributes["createdAt"]
        year = date.split("-")[0]
        month = date.split("-")[1]
        key = month + "-" + year

        category = transaction.get("relationships", {}).get("category", {}).get("data")
        merchant_name = transaction.get("attributes", {}).get("description")

        if category:
            category_id = category.get("id")
        else:
            if merchant_name in category_cache:
                category_id = category_cache[merchant_name]
            else:
                category_id = determine_category(merchant_name)
                print(f"{merchant_name} has category: {category_id}")

                category_cache[merchant_name] = category_id
                save_category_cache()

                # Sleep 3 or 4 seconds to avoid the going out request count limit (15 per min)
                time.sleep(3)

        if key not in monthly_category_totals:
            monthly_category_totals[key] = {}

        if category_id not in monthly_category_totals[key]:
            monthly_category_totals[key][category_id] = amount
        else:
            monthly_category_totals[key][category_id] += amount

        monthly_category_totals[key][category_id] = round(monthly_category_totals[key][category_id], 2)


    return monthly_category_totals

# Plot the monthly inflows and outflows and net spending
def plot(total_transactions):
    months = sorted(total_transactions.keys(), key=lambda m: (int(m.split("-")[1]), int(m.split("-")[0])))

    inflows = [total_transactions[m].get("inflows", 0) for m in months]
    outflows = [abs(total_transactions[m].get("outflows", 0)) for m in months]
    net_savings = [i - o for i, o in zip(inflows, outflows)]

    plt.figure(figsize=(12, 6))
    plt.plot(months, inflows, marker='o', label="Inflows")
    plt.plot(months, outflows, marker='o', label="Outflows")
    plt.plot(months, net_savings, marker='o', linestyle='--', label="Net Savings")

    plt.title("Monthly Cash Flow Overview")
    plt.xlabel("Month")
    plt.ylabel("Amount ($AUD)")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

# Summarise the outflow transactions given the monthly data using Gemini
def summarise_outflow_transactions(monthly_data, question):
    summary_text = "Here is my monthly spending breakdown:\n"
    for month, categories in monthly_data.items():
        summary_text += f"{month}:\n"
        for category, amount in categories.items():
            summary_text += f"  - {category}: ${abs(amount):.2f}\n"

    prompt = f"""
    You are a smart financial assistant. Based on the transaction data below, answer this question:
    {question}
    Here is the transaction data:
    {summary_text}
    """

    response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt
    )

    return response.text

# Running the logic
if __name__ == "__main__":
    print()