import json
import urllib.request
import sys

# Ensure UTF-8 output on Windows stdout
sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000/api/intake"

TEST_CASES = [
    {
        "customer_name": "Farah binti Abdullah",
        "customer_email": "farah.abdullah@email.com",
        "account_number": "1000998877661122",
        "nric": "950810-14-6122",
        "amount": 890.00,
        "email_subject": "Unauthorized e-wallet transfer to unrecognized account",
        "email_body": "Hello, I noticed an unauthorized e-wallet transfer of RM 890.00 from my account yesterday. I did not initiate or authorize this QR payment.",
        "attachment_name": "ewallet_statement.pdf"
    },
    {
        "customer_name": "Tan Wei Ming",
        "customer_email": "tan.weiming@email.com",
        "account_number": "8877665544332211",
        "nric": "891120-08-5433",
        "amount": 3400.00,
        "email_subject": "Mis-selling of investment-linked insurance policy",
        "email_body": "Dear Complaints Dept, I was told this policy was a guaranteed fixed deposit, but I found out it is a high-risk equity investment. I demand a full refund of RM 3,400.00.",
        "attachment_name": "policy_document.pdf"
    },
    {
        "customer_name": "Kavitha A/P Ramasamy",
        "customer_email": "kavitha.r@email.com",
        "account_number": "4455667788990011",
        "nric": "930215-05-5112",
        "amount": 150.00,
        "email_subject": "Incorrect interest calculation on housing loan",
        "email_body": "Hi, my June housing loan repayment statement charged RM 150.00 extra interest despite my early payment. Please re-calculate.",
        "attachment_name": "loan_statement.pdf"
    },
    {
        "customer_name": "Muhammad Razak bin Hashim",
        "customer_email": "razak.hashim@email.com",
        "account_number": "7766554433221100",
        "nric": "870605-10-5899",
        "amount": 6200.00,
        "email_subject": "Suspicious high-value wire transfer",
        "email_body": "Urgent: A wire transfer of RM 6,200.00 was executed from my account in Johor Bahru while I was in Kuala Lumpur. Please lock the recipient account immediately.",
        "attachment_name": "police_report_jb.pdf"
    },
    {
        "customer_name": "Chong Kah Wai",
        "customer_email": "chong.kw@email.com",
        "account_number": "3322110099887766",
        "nric": "910403-07-5231",
        "amount": 320.00,
        "email_subject": "ATM cash dispensing failure at KLCC branch",
        "email_body": "ATM #042 did not dispense RM 320.00 cash yesterday, but my account balance was debited. Please credit back.",
        "attachment_name": "atm_slip.pdf"
    }
]

def generate_cases():
    print(f"Generating {len(TEST_CASES)} test cases to backend API ({BASE_URL})...\n")
    
    for idx, case_data in enumerate(TEST_CASES, start=1):
        req = urllib.request.Request(
            BASE_URL,
            data=json.dumps(case_data).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                print(f"[{idx}/{len(TEST_CASES)}] Generated Case ID: {res_data['id']}")
                print(f"   Customer: {res_data['customer_name']} | Category: {res_data['category']}")
                print(f"   Status: {res_data['status']} | Urgency: {res_data['urgency']}")
                print(f"   SLA Due Date: {res_data['due_date']}\n")
        except Exception as e:
            print(f"Error generating test case {idx}: {e}")

if __name__ == "__main__":
    generate_cases()
