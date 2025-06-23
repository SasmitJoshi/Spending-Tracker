from dotenv import load_dotenv
import os
import requests


load_dotenv()
UP_TOKEN = os.getenv("UP_API_KEY")
header = {"Authorization": f"Bearer {UP_TOKEN}"}

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




# Running the logic
if __name__ == "__main__":
    print(get_total_transactions())