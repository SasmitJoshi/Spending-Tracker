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
def split_transactions():
    transactions = get_all_transactions()
    transactions = clean_transactions(transactions)
    # need to split transactions into monthly ones
    monthly_transactions = {
        "inflow": {},
        "outflow": {}
    }

    for transaction in transactions:
        transaction = transaction["attributes"]
        amount = float(transaction["amount"]["value"])
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


# Running the logic
if __name__ == "__main__":
    # transactions = get_all_transactions()
    # print(f"Fetched {len(transactions)} transactions")
    # cleaned_transactions = clean_transactions(transactions)
    # for transaction in cleaned_transactions:
    #     transaction = transaction["attributes"]
    #     desc = transaction["description"]
    #     amt = transaction["amount"]["value"]
    #     date = transaction["createdAt"]
    #     print(f"{date} | {desc} | {amt}")
    print(split_transactions())