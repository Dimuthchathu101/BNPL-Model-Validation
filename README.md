# BNPL-Model-Validation

A comprehensive Buy Now, Pay Later (BNPL) model validation suite, including a Flask web app, advanced risk model validation scripts, Playwright end-to-end tests, and automated edge case simulation.

## Features
- **Flask Web App** for user registration, purchases, repayments, income verification, and dashboards.
- **Advanced Risk Model Validation** with customizable checks and detailed reporting.
- **Playwright UI/API Tests** for both standard and edge-case user flows.
- **Automated Edge Case Data Generation** for robust risk model testing.

---

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd BNPL-Model-Validation
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   ```

3. **Install dependencies:**
   ```bash
   pip install flask pytest pytest-playwright
   python -m playwright install
   ```

---

## Running the Flask Web App

```bash
python app.py
```
Visit [http://localhost:5000](http://localhost:5000) in your browser.

---

## Playwright Testing

- **Run all Playwright tests:**
  ```bash
  pytest tests/ --browser chromium
  ```
- **Edge case tests:**
  ```bash
  pytest tests/test_edge_cases_playwright.py --browser chromium
  ```

---

## Risk Model Validation Scripts

- **Run advanced validation:**
  ```bash
  python validation/validate_risk_models.py
  ```
- **Custom checks, output, or user:**
  ```bash
  python validation/validate_risk_models.py --checks utilization,velocity --output my_report.csv --summary-only
  ```
- **See detailed report:**
  - Console output
  - `validation/risk_validation_report.json` (or `.csv`)

### What is validated?
- Utilization, default status, risk scores, compliance, repayments, velocity, duplicate/future/negative transactions, underage users, and more.
- See comments in `validation/validate_risk_models.py` for all checks.

---

## Edge Case Data Simulation

- **Insert edge cases:**
  ```bash
  python validation/insert_edge_cases.py
  ```
- This will add users and transactions for scenarios like:
  - High utilization
  - Over-repayment
  - Repayment before purchase
  - Duplicate/future/negative transactions
  - Underage users
  - Large purchases without verification
  - High velocity, zero credit limit, and more

---

## Project Structure

- `app.py` — Flask web app and API
- `data/` — JSON data files (users, transactions, repayments, etc.)
- `templates/` — HTML templates for the web app
- `tests/` — Playwright and API tests
- `validation/validate_risk_models.py` — Advanced risk model validation script
- `validation/insert_edge_cases.py` — Edge case data generator

---

## Risk Model Logic
- **Champion/Challenger scores**: Penalize high utilization, overdue status, lack of income verification, and high velocity.
- **Compliance**: Checks for underage users, large purchases without verification, and more.
- **See code comments for detailed logic.**

---

## Contributing
Pull requests and suggestions are welcome!

---

## License
MIT