from dotenv import load_dotenv
import os
import requests
import matplotlib.pyplot as plt
from google import genai

load_dotenv()
UP_TOKEN = os.getenv("UP_API_KEY")
GEMINI_TOKEN = os.getenv("GEMINI_API_KEY")
header = {"Authorization": f"Bearer {UP_TOKEN}"}
client = genai.Client(api_key=GEMINI_TOKEN)

# Returns all the transactions on my account
def get_all_transactions():
    all_transactions = []
    url = "https://api.up.com.au/api/v1/transactions"

    while url:
        res = requests.get(url, headers=header)
        res.raise_for_status()
        json_data = res.json()

        all_transactions.extend(json_data.get("data", []))

        url = json_data.get("links", {}).get("next")

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
        category_id = category.get("id") if category else "uncategorised"

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

# Running the logic
if __name__ == "__main__":
    # total_transactions = get_total_transactions()

    # plot(total_transactions)

    # print(get_monthly_category_totals())

    # response = client.models.generate_content(
    # model="gemini-2.5-flash",
    # contents="Explain how AI works in a few words",
    # )

    # print(response.text)

    print()