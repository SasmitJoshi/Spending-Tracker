from flask import Flask, render_template, request
from tracker import get_daily_category_totals, get_yearly_category_totals, summarise_outflow_transactions, get_monthly_category_totals, get_total_transactions, plot
import markdown

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    ai_output = ''

    if request.method == 'POST':
        user_input = request.form.get('user_input')
        raw_output = summarise_outflow_transactions(get_monthly_category_totals(), user_input)
        ai_output = markdown.markdown(raw_output)

    return render_template('index.html', ai_output=ai_output)

@app.route('/dashboard')
def dashboard():
    monthly = get_monthly_category_totals()
    daily = get_daily_category_totals()
    yearly = get_yearly_category_totals()
    return render_template(
        "dashboard.html",
        monthly=monthly,
        daily=daily,
        yearly=yearly
    )


if __name__ == '__main__':
    app.run(debug=True)