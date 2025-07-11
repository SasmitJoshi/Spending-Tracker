from flask import Flask, render_template, request, redirect, url_for
from tracker import clean_transactions, get_all_transactions, get_daily_category_totals, get_weekly_category_totals, get_yearly_category_totals, summarise_outflow_transactions, get_monthly_category_totals
import markdown

app = Flask(__name__)

ai_output_store = {}

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        user_input = request.form.get('user_input')
        raw_output = summarise_outflow_transactions(user_input)
        output_id = "current"
        ai_output_store[output_id] = markdown.markdown(raw_output)
        return redirect(url_for('home'))

    ai_output = ai_output_store.pop("current", "")
    return render_template('index.html', ai_output=ai_output)

@app.route('/dashboard')
def dashboard():
    monthly = get_monthly_category_totals()
    daily = get_daily_category_totals()
    weekly = get_weekly_category_totals()
    yearly = get_yearly_category_totals()
    return render_template(
        "dashboard.html",
        monthly=monthly,
        daily=daily,
        yearly=yearly,
        weekly=weekly
    )

@app.route('/transactions')
def transactions():
    transactions = clean_transactions(get_all_transactions())
    return render_template('transactions.html', transactions=transactions)

if __name__ == '__main__':
    app.run(debug=True)
