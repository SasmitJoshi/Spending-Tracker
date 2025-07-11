# 💸 Spending-Tracker

Recently, I noticed I’ve been spending a bit too much money. While the UP Bank app already breaks down my spending, I wanted to see if I could build something **even better myself** and learn more about data processing, visualisation, and AI along the way.

So I created this **personal spending tracker** that:

- Fetches transactions from the UP Bank API
- Cleans and categorises them (using Gemini AI for uncategorised merchants)
- Tracks inflows vs outflows over time
- Breaks down spending by category and by month
- Visualises cash flow trends
- Summarises spending habits using an AI assistant

It’s a fun way to keep myself accountable, and a pretty cool personal project to showcase Python + API integration + AI all in one.

---

## ⚙️ Features

✅ Fetches all transactions from the UP Bank API (with local caching)  
✅ Removes internal transfers so it only tracks real spending  
✅ Automatically categorises transactions — including unknown merchants via Gemini AI  
✅ Stores transaction & category data locally to avoid repeated API calls  
✅ Groups spending by day or month, and by category  
✅ Generates AI-based summaries of how to optimise spending

---

## 🚀 Tech Stack

- **Python** — core language
- **UP Bank API** — to fetch real transaction data
- **Gemini AI (Google Generative AI)** — for merchant categorisation & spending insights
- **JSON** — local caching of transactions and category mappings

---

## 📝 Why I built this

- To better understand where my money is going each month.
- To practice working with APIs, data cleaning, and time series analysis.

---
