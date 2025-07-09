import streamlit as st
from tracker import summarise_outflow_transactions, get_monthly_category_totals

st.title("AI Personal Finance Advisor")
user_input = st.text_input("How can I help you with your personal finance journey today?")

# ai_output = summarise_outflow_transactions(get_monthly_category_totals(), user_input)
st.write(f"{user_input}")