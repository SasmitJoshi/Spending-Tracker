from dotenv import load_dotenv
import os
import requests
import matplotlib.pyplot as plt
from google import genai
import time
import json
from datetime import datetime

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

# Retrieves all the transactions that have occured with this UP
# account
def get_all_transactions():
    global transactions_cache
    if transactions_cache:
        return transactions_cache

    print("Fetching transactions from UP API...")
    all_transactions = []
    url = "https://api.up.com.au/api/v1/transactions"

    while url:
        res = requests.get(url, headers=header)
        res.raise_for_status()
        json_data = res.json()
        for t in json_data.get("data", []):
            attributes = t.get("attributes", {})
            merchant_name = attributes.get("description")
            amount = round(float(attributes.get("amount", {}).get("value", 0)), 2)
            date = attributes.get("createdAt")

            category_data = t.get("relationships", {}).get("category", {}).get("data")
            category = category_data.get("id") if category_data else None

            if not category:
                if merchant_name in category_cache:
                    category = category_cache[merchant_name]
                else:
                    category = determine_category(merchant_name)
                    print(f"{merchant_name} has category: {category}")

                    category_cache[merchant_name] = category
                    save_category_cache()

                    # Sleep 3 or 4 seconds to avoid the going out request count limit (15 per min)
                    time.sleep(3)

            all_transactions.append({
                "merchant_name": merchant_name,
                "category": category,
                "amount": amount,
                "date": date
            })

        url = json_data.get("links", {}).get("next")

    transactions_cache = all_transactions
    save_transactions_cache(all_transactions)
    return all_transactions

# Cleans the transactions, removing any transactions that are transfers to and from
# accounts
def clean_transactions(transactions):
    cleaned_transactions = []
    for transaction in transactions:
        merchant_name = transaction["merchant_name"]
        if not (merchant_name.startswith("Transfer to") or merchant_name.startswith("Transfer from")):
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
        amount = round(float(transaction["amount"]), 2)
        date = transaction["date"]

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

# Calculate the daily outflows by category
def get_daily_category_totals():
    transactions = get_all_transactions()
    transactions = clean_transactions(transactions)

    daily_category_totals = {}

    for transaction in transactions:
        amount = round(float(transaction["amount"]), 2)

        if amount >= 0:
            continue

        date = transaction["date"]
        date = date.split("T")[0]
        category = transaction["category"]

        if date not in daily_category_totals:
            daily_category_totals[date] = {}

        if category not in daily_category_totals[date]:
            daily_category_totals[date][category] = amount
        else:
            daily_category_totals[date][category] += amount

        daily_category_totals[date][category] = round(daily_category_totals[date][category], 2)

    return daily_category_totals

def get_weekly_category_totals():
    transactions = get_all_transactions()
    transactions = clean_transactions(transactions)

    weekly_category_totals = {}

    for transaction in transactions:
        amount = round(float(transaction["amount"]), 2)

        if amount >= 0:
            continue

        date = transaction["date"]
        date = datetime.fromisoformat(date)

        iso_year, iso_week, _ = date.isocalendar()
        week_key = f"{iso_year}-W{iso_week:02}"

        category = transaction["category"]

        if week_key not in weekly_category_totals:
            weekly_category_totals[week_key] = {}

        if category not in weekly_category_totals[week_key]:
            weekly_category_totals[week_key][category] = amount
        else:
            weekly_category_totals[week_key][category] += amount

        weekly_category_totals[week_key][category] = round(weekly_category_totals[week_key][category], 2)

    return weekly_category_totals

# Calculate the outflows by category for each month
def get_monthly_category_totals():
    transactions = get_all_transactions()
    transactions = clean_transactions(transactions)

    monthly_category_totals = {}

    for transaction in transactions:
        amount = round(float(transaction["amount"]), 2)

        if amount >= 0:
            continue

        date = transaction["date"]
        year = date.split("-")[0]
        month = date.split("-")[1]
        key = month + "-" + year

        category = transaction["category"]

        if key not in monthly_category_totals:
            monthly_category_totals[key] = {}

        if category not in monthly_category_totals[key]:
            monthly_category_totals[key][category] = amount
        else:
            monthly_category_totals[key][category] += amount

        monthly_category_totals[key][category] = round(monthly_category_totals[key][category], 2)

    return monthly_category_totals

def get_yearly_category_totals():
    transactions = get_all_transactions()
    transactions = clean_transactions(transactions)

    yearly_category_totals = {}
    for transaction in transactions:
        amount = round(float(transaction["amount"]), 2)

        if amount >= 0:
            continue

        year = transaction["date"].split("-")[0]
        category = transaction["category"]

        if year not in yearly_category_totals:
            yearly_category_totals[year] = {}

        yearly_category_totals[year][category] = yearly_category_totals[year].get(category, 0) + amount
        yearly_category_totals[year][category] = round(yearly_category_totals[year][category], 2)

    return yearly_category_totals

# FIXME: Need to fix the data so that it can return a wider range of responses (currently limited to monthly)
# Summarise the outflow transactions given the monthly data using Gemini
def summarise_outflow_transactions(question):
    data = get_all_transactions()
    summary_text = ""
    for transaction in data:
        summary_text += f"- {transaction['date'][:10]} | {transaction['merchant_name']} | {transaction['category']} | ${transaction['amount']:.2f}\n"

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
    # print(get_all_transactions())
    # print(clean_transactions(get_all_transactions()))
    # print(split_transactions())
    print(summarise_outflow_transactions("how much did i spend in march 2025?"))