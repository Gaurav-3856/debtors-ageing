import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="Debtors Ageing Report", layout="centered")
st.title("📊 Debtors Ageing Report (FIFO Based)")

uploaded_file = st.file_uploader("Upload Debtors Ledger Excel File", type=["xlsx"])

def generate_ageing(df):
    df = df[df['Account Name'].notna()]
    df = df[~df['Account Name'].astype(str).str.contains("ACCOUNT Wise Totals", na=False)]

    df['Doc Date'] = pd.to_datetime(df['Doc Date'], errors='coerce')
    df['Debit'] = pd.to_numeric(df['Debit'], errors='coerce')
    df['Credit'] = pd.to_numeric(df['Credit'], errors='coerce')
    reference_date = pd.Timestamp.today()

    unsettled_items = []
    df_sorted = df.sort_values(['Account Name', 'Doc Date'])

    for party, group in df_sorted.groupby('Account Name'):
        bills = group[group['Credit'].notnull()][['Doc Date', 'Credit']].copy()
        payments = group[group['Debit'].notnull()][['Doc Date', 'Debit']].copy()
        bill_queue = [{'date': row['Doc Date'], 'remaining': row['Credit']} for _, row in bills.iterrows()]

        for _, row in payments.iterrows():
            payment = row['Debit']
            while payment > 0 and bill_queue:
                bill = bill_queue[0]
                if payment >= bill['remaining']:
                    payment -= bill['remaining']
                    bill_queue.pop(0)
                else:
                    bill['remaining'] -= payment
                    payment = 0

        for bill in bill_queue:
            unsettled_items.append({
                'Account Name': party,
                'Doc Date': bill['date'],
                'Unpaid Amount': bill['remaining'],
                'Age (Days)': (reference_date - bill['date']).days
            })

    def bucket(days):
        if days <= 30: return '1 Month'
        elif days <= 60: return '2 Months'
        elif days <= 90: return '3 Months'
        elif days <= 120: return '4 Months'
        elif days <= 150: return '5 Months'
        elif days <= 180: return '6 Months'
        elif days <= 210: return '7 Months'
        elif days <= 240: return '8 Months'
        else: return '9+ Months'

    df_unpaid = pd.DataFrame(unsettled_items)
    df_unpaid['Bucket'] = df_unpaid['Age (Days)'].apply(bucket)

    final = df_unpaid.groupby(['Account Name', 'Bucket'])['Unpaid Amount'].sum().unstack(fill_value=0).reset_index()
    final['Total Outstanding'] = final.drop(columns='Account Name').sum(axis=1)
    return final

if uploaded_file:
    try:
        df_raw = pd.read_excel(uploaded_file, skiprows=2, header=None)
        df_raw.columns = ['SNO', 'Account Name', 'Doc No', 'Doc Date', 'Narration', 'Debit', 'Credit', 'Running Balance']
        result = generate_ageing(df_raw)

        st.success("Report Generated Successfully ✅")
        st.dataframe(result)

        buffer = BytesIO()
        result.to_excel(buffer, index=False)
        buffer.seek(0)
        st.download_button("📥 Download Excel Report", buffer, file_name="Debtors_Ageing_FIFO.xlsx")

    except Exception as e:
        st.error(f"Error processing file: {e}")