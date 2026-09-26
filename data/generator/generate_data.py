"""
Northbridge Software Ltd - synthetic data room generator
=========================================================
Buy-side due diligence simulation (Transaction Analytics).

Generates six CSVs modelling a ~£40m/year UK B2B SaaS business over
Jan 2022 - Dec 2025, with realistic commercial behaviour and a set of
deliberately planted issues for the analyst to find.

Run from the repo root:
    pip install -r requirements.txt
    python data/generator/generate_data.py
Outputs are written to data/raw/*.csv. Fixed seed => reproducible.
"""

import numpy as np
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
import os

SEED = 20260926
rng = np.random.default_rng(SEED)

# Write to <repo>/data/raw regardless of the working directory the script is
# launched from. This file lives at data/generator/, so ../raw is data/raw.
OUTDIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "raw"))
os.makedirs(OUTDIR, exist_ok=True)

# ----------------------------------------------------------------------
# Reference dimensions
# ----------------------------------------------------------------------
WINDOW_START = date(2022, 1, 1)   # first reported month
WINDOW_END   = date(2025, 12, 1)  # last reported month (month starts)

def month_range(start, end):
    months, d = [], date(start.year, start.month, 1)
    while d <= end:
        months.append(d)
        d += relativedelta(months=1)
    return months

REPORTED_MONTHS = month_range(WINDOW_START, WINDOW_END)

INDUSTRIES = ["Retail", "Professional Services", "Manufacturing", "Healthcare",
              "Financial Services", "Hospitality", "Construction", "Technology",
              "Education", "Logistics"]

REGIONS = ["London", "South East", "South West", "Midlands", "North West",
           "North East", "Yorkshire", "Scotland", "Wales", "Northern Ireland",
           "Ireland (EU)", "Netherlands (EU)", "Germany (EU)"]
REGION_WEIGHTS = np.array([0.22, 0.15, 0.08, 0.12, 0.10, 0.05, 0.06, 0.07,
                           0.04, 0.03, 0.03, 0.03, 0.02])
REGION_WEIGHTS = REGION_WEIGHTS / REGION_WEIGHTS.sum()

SIZE_BANDS = ["Micro (1-9)", "Small (10-49)", "Medium (50-249)", "Large (250+)"]
SIZE_WEIGHTS = np.array([0.30, 0.40, 0.22, 0.08])

CHANNELS = ["Direct Sales", "Inbound/Website", "Partner/Reseller",
            "Paid Search", "Referral"]
CHANNEL_WEIGHTS = np.array([0.25, 0.28, 0.17, 0.18, 0.12])

ACCOUNT_MANAGERS = ["A. Okafor", "B. Novak", "C. Ferreira", "D. Ahmed",
                    "E. Lindqvist", "F. Marsh", "G. Patel", "H. Romano"]

# Products: product_line, revenue_type, monthly list price (recurring) or
# fee basis (one-off implementation priced as a multiple of platform MRR)
PRODUCTS = [
    # product_id, product_name,            product_line,            revenue_type, list_price
    (1, "Core Platform - Starter",  "Core Platform",          "recurring", 480),
    (2, "Core Platform - Growth",   "Core Platform",          "recurring", 1150),
    (3, "Core Platform - Scale",    "Core Platform",          "recurring", 2900),
    (4, "Analytics Add-on",         "Analytics Add-on",       "recurring", 550),
    (5, "Payments Module",          "Payments Module",        "recurring", 720),
    (6, "Implementation Services",  "Implementation Services","one-off",   0),
]
products_df = pd.DataFrame(PRODUCTS,
    columns=["product_id", "product_name", "product_line", "revenue_type", "list_price"])

CORE_TIER_BY_SIZE = {  # which core tier a size band tends to buy
    "Micro (1-9)":    [1, 1, 1, 2],
    "Small (10-49)":  [1, 2, 2, 2],
    "Medium (50-249)":[2, 2, 3, 3],
    "Large (250+)":   [3, 3, 3, 2],
}

# ----------------------------------------------------------------------
# 1. CUSTOMERS
# ----------------------------------------------------------------------
# Signups from 2017-01 (mature installed base) to 2025-12. Trend + seasonality.
SIGNUP_START = date(2017, 1, 1)
signup_months = month_range(SIGNUP_START, WINDOW_END)

def seasonal_factor(d):
    # stronger Q1 (new budgets) and Q4, softer summer
    m = d.month
    return {1:1.25,2:1.15,3:1.10,4:1.0,5:0.95,6:0.9,
            7:0.8,8:0.8,9:1.05,10:1.1,11:1.15,12:0.95}[m]

base_signups = 13.0           # customers/month at the start (mature business)
monthly_growth = 1.007        # ~0.7%/month compounding acquisition growth

customers, cust_id = [], 1000
for i, d in enumerate(signup_months):
    lam = base_signups * (monthly_growth ** i) * seasonal_factor(d)
    n = rng.poisson(lam)
    for _ in range(n):
        day = int(rng.integers(1, 28))
        size = rng.choice(SIZE_BANDS, p=SIZE_WEIGHTS)
        customers.append({
            "customer_id": f"C{cust_id:04d}",
            "customer_name": None,        # filled after we know the sector
            "signup_date": date(d.year, d.month, day),
            "industry": rng.choice(INDUSTRIES),
            "region": rng.choice(REGIONS, p=REGION_WEIGHTS),
            "company_size": size,
            "acquisition_channel": rng.choice(CHANNELS, p=CHANNEL_WEIGHTS),
            "account_manager": rng.choice(ACCOUNT_MANAGERS),
        })
        cust_id += 1

customers_df = pd.DataFrame(customers)

# Company-name generation
PREFIX = ["Aldridge","Brightwater","Cavendish","Dunmore","Everest","Fenwick",
          "Granville","Harlow","Ironbridge","Kingsmead","Larkfield","Merton",
          "Northgate","Oakhurst","Pemberton","Quorn","Redcliffe","Stanmore",
          "Thornbury","Uppingham","Vresper","Whitfield","Yarrow","Ashcombe",
          "Blakeney","Corfe","Dovedale","Elmsworth","Farnham","Grimsby"]
SUFFIX = ["Retail","Consulting","Foods","Logistics","Systems","Group","Trading",
          "Solutions","Partners","Holdings","Services","Labs","Works","Supplies",
          "Media","Care","Build","Digital","Textiles","Interiors"]
FORM = ["Ltd", "Limited", "LLP", "PLC", "& Co", "Group Ltd"]

used_names = set()
def make_name():
    for _ in range(50):
        nm = f"{rng.choice(PREFIX)} {rng.choice(SUFFIX)} {rng.choice(FORM)}"
        if nm not in used_names:
            used_names.add(nm)
            return nm
    return nm

customers_df["customer_name"] = [make_name() for _ in range(len(customers_df))]

# --- Planted enterprise ("whale") accounts: concentration risk -------------
# Force a handful of very large customers signed up early.
early = customers_df[customers_df["signup_date"] < date(2022, 1, 1)].index.to_list()
whale_ids = list(rng.choice(early, size=6, replace=False))
customers_df.loc[whale_ids, "company_size"] = "Large (250+)"
WHALES = customers_df.loc[whale_ids, "customer_id"].tolist()
TOP_WHALE = WHALES[0]   # this one will reduce spend late in the period
# Enterprise anchor contracts (net £/year) that create the concentration risk.
WHALE_ANNUAL = dict(zip(WHALES, [3_400_000, 2_300_000, 1_800_000,
                                 1_400_000, 1_100_000, 900_000]))

customers_df = customers_df.sort_values("customer_id").reset_index(drop=True)

# ----------------------------------------------------------------------
# 2. SUBSCRIPTIONS
# ----------------------------------------------------------------------
# Each customer starts with a Core tier; may add Analytics/Payments over time;
# may downgrade; churn ends all subscriptions. Price uplift at renewal 2024/25.
def size_discount(size, is_whale):
    base = {"Micro (1-9)":0.0,"Small (10-49)":0.03,
            "Medium (50-249)":0.08,"Large (250+)":0.15}[size]
    base += rng.normal(0, 0.02)
    if is_whale:
        base += 0.10   # whales negotiate hard
    return float(np.clip(base, 0, 0.45))

def channel_churn_mult(ch):
    return {"Direct Sales":0.8,"Inbound/Website":1.0,"Partner/Reseller":1.15,
            "Paid Search":1.5,"Referral":0.7}[ch]

def size_churn_mult(sz):
    return {"Micro (1-9)":1.6,"Small (10-49)":1.1,
            "Medium (50-249)":0.7,"Large (250+)":0.4}[sz]

def cohort_churn_mult(signup):
    # PLANTED: newer cohorts churn faster. Baseline monthly hazard multiplier
    # rises for later signup years.
    return {2017:0.55, 2018:0.55, 2019:0.6, 2020:0.7, 2021:0.8,
            2022:1.0, 2023:1.45, 2024:2.1, 2025:2.5}.get(signup.year, 1.0)

price_list = dict(zip(products_df.product_id, products_df.list_price))

subscriptions = []
sub_id = 50000

def add_sub(cid, pid, start, term, monthly, disc):
    global sub_id
    subscriptions.append({
        "subscription_id": f"S{sub_id:05d}",
        "customer_id": cid, "product_id": pid,
        "start_date": start, "end_date": None,
        "contract_term_months": term,
        "monthly_price": round(monthly, 2),
        "discount_pct": round(disc, 4),
    })
    sub_id += 1
    return len(subscriptions) - 1

def renewal_uplift(month):
    # price increases applied at renewal in 2024 (+5%) and 2025 (+7%)
    if month.year == 2024: return 1.05
    if month.year == 2025: return 1.07
    return 1.0

for _, c in customers_df.iterrows():
    cid = c.customer_id
    is_whale = cid in WHALES
    signup = c.signup_date
    size = c.company_size
    disc = size_discount(size, is_whale)

    # --- Core platform subscription
    core_pid = int(rng.choice(CORE_TIER_BY_SIZE[size]))
    term = int(rng.choice([12, 24, 36], p=[0.55, 0.30, 0.15]))
    core_monthly = price_list[core_pid] * (1 - disc)
    core_idx = add_sub(cid, core_pid, signup, term, core_monthly, disc)

    # whales are large enterprise contracts; monthly prices set in a post-pass
    if is_whale:
        subscriptions[core_idx]["product_id"] = 3

    # --- Add-ons at signup (cross-sell propensity by size)
    p_analytics = {"Micro (1-9)":0.10,"Small (10-49)":0.20,
                   "Medium (50-249)":0.40,"Large (250+)":0.65}[size]
    p_payments  = {"Micro (1-9)":0.08,"Small (10-49)":0.18,
                   "Medium (50-249)":0.30,"Large (250+)":0.55}[size]
    if is_whale:
        p_analytics, p_payments = 1.0, 1.0   # ensure rows exist for the post-pass

    if rng.random() < p_analytics:
        add_sub(cid, 4, signup, term, price_list[4]*(1-disc), disc)
    if rng.random() < p_payments:
        add_sub(cid, 5, signup, term, price_list[5]*(1-disc), disc)

    # --- Determine churn date (logo churn ends all subs)
    monthly_hazard = 0.010 * channel_churn_mult(c.acquisition_channel) \
        * size_churn_mult(size) * cohort_churn_mult(signup)
    if is_whale:
        monthly_hazard *= 0.15   # whales rarely fully churn

    churn_date = None
    if not is_whale:   # anchor accounts do not fully churn in the window
        d = signup + relativedelta(months=1)
        while d <= WINDOW_END:
            # ramp-up: very low churn in first 3 months
            h = monthly_hazard * (0.3 if (d - signup).days < 95 else 1.0)
            if rng.random() < h:
                churn_date = date(d.year, d.month, 1)
                break
            d += relativedelta(months=1)

    # --- Upsell / cross-sell events over the customer's life
    active_end = churn_date if churn_date else (WINDOW_END + relativedelta(months=1))
    m = signup + relativedelta(months=int(rng.integers(4, 10)))
    while m < active_end and m <= WINDOW_END:
        r = rng.random()
        existing_pids = {s["product_id"] for s in subscriptions
                         if s["customer_id"] == cid and s["end_date"] is None}
        # expansion: add a module not yet held
        if r < 0.04:
            for pid in (4, 5):
                if pid not in existing_pids:
                    add_sub(cid, pid, date(m.year, m.month, 1), 12,
                            price_list[pid]*(1-disc)*renewal_uplift(m), disc)
                    break
        # upgrade core tier
        elif r < 0.06:
            for s in subscriptions:
                if (s["customer_id"] == cid and s["end_date"] is None
                        and s["product_id"] in (1, 2)):
                    s["product_id"] = min(3, s["product_id"] + 1)
                    s["monthly_price"] = round(
                        price_list[s["product_id"]]*(1-disc)*renewal_uplift(m), 2)
                    break
        # downgrade: drop an add-on
        elif r < 0.075:
            for s in subscriptions:
                if (s["customer_id"] == cid and s["end_date"] is None
                        and s["product_id"] in (4, 5)):
                    s["end_date"] = date(m.year, m.month, 1)
                    break
        m += relativedelta(months=int(rng.integers(4, 12)))

    # --- Apply renewal price uplifts to still-active recurring subs
    for s in subscriptions:
        if s["customer_id"] == cid and s["product_id"] in (1,2,3,4,5):
            # simple model: uplift monthly_price once when crossing a renewal year
            pass  # uplift handled at invoice time via effective price schedule

    # --- Close out churned subscriptions
    if churn_date:
        for s in subscriptions:
            if s["customer_id"] == cid and s["end_date"] is None:
                s["end_date"] = churn_date

# --- Set whale contract values (concentration): split target across products
for cid, annual in WHALE_ANNUAL.items():
    core_m, an_m, pay_m = annual*0.70/12, annual*0.15/12, annual*0.15/12
    for s in subscriptions:
        if s["customer_id"] != cid:
            continue
        if s["product_id"] == 3:
            s["monthly_price"] = round(core_m, 2); s["contract_term_months"] = 36
        elif s["product_id"] == 4:
            s["monthly_price"] = round(an_m, 2); s["contract_term_months"] = 36
        elif s["product_id"] == 5:
            s["monthly_price"] = round(pay_m, 2); s["contract_term_months"] = 36

# --- PLANTED: top whale reduces spend late 2025 (downgrade, not full churn)
for s in subscriptions:
    if s["customer_id"] == TOP_WHALE and s["end_date"] is None:
        if s["product_id"] in (4, 5):          # drops both add-ons
            s["end_date"] = date(2025, 9, 1)
        elif s["product_id"] == 3:             # halves core platform spend
            s["monthly_price"] = round(s["monthly_price"] * 0.5, 2)

subscriptions_df = pd.DataFrame(subscriptions)

# ----------------------------------------------------------------------
# 3. INVOICES  (derived from subscriptions + one-off implementation)
# ----------------------------------------------------------------------
invoices = []
inv_id = 700000

def eff_price(base_monthly, month):
    # apply cumulative renewal uplifts: +5% from 2024, compounding +7% from 2025
    factor = 1.0
    if month.year >= 2024: factor *= 1.05
    if month.year >= 2025: factor *= 1.07
    return base_monthly * factor

# Recurring invoices: one per active subscription per active reported month
for s in subscriptions:
    start = s["start_date"]
    end = s["end_date"]  # exclusive month of churn
    for mth in REPORTED_MONTHS:
        if mth < date(start.year, start.month, 1):
            continue
        if end is not None and mth >= date(end.year, end.month, 1):
            continue
        amt = eff_price(s["monthly_price"], mth)
        invoices.append({
            "invoice_id": f"INV{inv_id}",
            "customer_id": s["customer_id"],
            "product_id": s["product_id"],
            "invoice_date": date(mth.year, mth.month, int(rng.integers(1, 28))),
            "amount": round(amt, 2),
            "revenue_type": "recurring",
            "status": "paid",
        })
        inv_id += 1

# One-off implementation fees for customers acquired WITHIN the window (their
# go-live sits in-period). Pre-window customers were implemented historically,
# so no in-window implementation for them. Baseline one-off tracks new business.
for _, c in customers_df.iterrows():
    if c.signup_date < WINDOW_START:
        continue
    if c.customer_id in WHALES:
        continue   # anchor accounts pre-date the window
    core = subscriptions_df[(subscriptions_df.customer_id == c.customer_id)
                            & (subscriptions_df.product_id.isin([1,2,3]))]
    if core.empty:
        continue
    base = core.iloc[0]["monthly_price"]
    fee = base * rng.uniform(2.0, 4.5)   # ~2-4.5x MRR one-off
    m = c.signup_date
    invoices.append({
        "invoice_id": f"INV{inv_id}",
        "customer_id": c.customer_id, "product_id": 6,
        "invoice_date": date(m.year, m.month, int(rng.integers(1, 28))),
        "amount": round(fee, 2), "revenue_type": "one-off", "status": "paid",
    })
    inv_id += 1

# --- PLANTED: spike in one-off implementation revenue in 2025 -------------
# Extra "re-platforming / data migration" projects sold into the existing base
# through the final year. These inflate 2025 total growth even though they are
# non-recurring. ~45 sizeable projects (£30k-150k) across 2025.
existing_base = customers_df[customers_df.signup_date <= date(2024,12,1)].customer_id.tolist()
for _ in range(45):
    cid = rng.choice(existing_base)
    mth = int(rng.integers(1, 13))
    invoices.append({
        "invoice_id": f"INV{inv_id}",
        "customer_id": cid, "product_id": 6,
        "invoice_date": date(2025, mth, int(rng.integers(1, 28))),
        "amount": round(float(rng.uniform(30_000, 150_000)), 2),
        "revenue_type": "one-off", "status": "paid",
    })
    inv_id += 1

invoices_df = pd.DataFrame(invoices)

# --- Legitimate credit notes (negative) and overdue status ----------------
# Some recurring invoices credited (service issues) -> negative credit note rows.
paid_rec = invoices_df[(invoices_df.revenue_type=="recurring")
                       & (invoices_df.status=="paid")].index.to_numpy()
credit_idx = rng.choice(paid_rec, size=int(len(paid_rec)*0.012), replace=False)
credit_rows = []
for i in credit_idx:
    r = invoices_df.loc[i]
    credit_rows.append({
        "invoice_id": f"CN{inv_id}", "customer_id": r.customer_id,
        "product_id": r.product_id, "invoice_date": r.invoice_date,
        "amount": -round(r.amount, 2), "revenue_type": r.revenue_type,
        "status": "credited",
    })
    inv_id += 1
invoices_df = pd.concat([invoices_df, pd.DataFrame(credit_rows)], ignore_index=True)

# Mark some invoices overdue (unpaid at period end)
open_idx = invoices_df[invoices_df.status=="paid"].sample(
    frac=0.03, random_state=SEED).index
invoices_df.loc[open_idx, "status"] = "overdue"

# ----------------------------------------------------------------------
# PLANTED DATA-QUALITY ISSUES
# ----------------------------------------------------------------------
# (a) Duplicate invoices - exact re-issued rows with a NEW invoice_id
dup_src = invoices_df[invoices_df.amount > 0].sample(40, random_state=SEED)
dups = dup_src.copy()
dups["invoice_id"] = [f"INV{inv_id+i}" for i in range(len(dups))]
inv_id += len(dups)
invoices_df = pd.concat([invoices_df, dups], ignore_index=True)

# (b) A few erroneous negative amounts on 'paid' invoices (keying errors)
err_idx = invoices_df[(invoices_df.amount>0)&(invoices_df.status=="paid")]\
    .sample(15, random_state=SEED+1).index
invoices_df.loc[err_idx, "amount"] = -invoices_df.loc[err_idx, "amount"].abs()

# (c) Missing industry values on a slice of customers
miss_idx = customers_df.sample(frac=0.06, random_state=SEED+2).index
customers_df.loc[miss_idx, "industry"] = np.nan

# (d) Inconsistent customer-name spellings (same entity, variant strings).
# Create alias variants of ~25 customers by tweaking the legal form / spacing.
def variant(name):
    swaps = {" Limited":" Ltd", " Ltd":" Limited", " & Co":" and Co",
             " Group Ltd":" Grp Ltd"}
    for a, b in swaps.items():
        if name.endswith(a):
            return name.replace(a, b)
    return name + "."
alias_idx = customers_df.sample(25, random_state=SEED+3).index
for i in alias_idx:
    # flip the stored name on SOME of that customer's invoices to a variant,
    # simulating inconsistent capture across billing runs
    cid = customers_df.loc[i, "customer_id"]
    # store a variant name back on the customer master for a subset
    if rng.random() < 0.5:
        customers_df.loc[i, "customer_name"] = variant(customers_df.loc[i, "customer_name"])

invoices_df = invoices_df.sort_values(["invoice_date","invoice_id"]).reset_index(drop=True)

# ----------------------------------------------------------------------
# 4. COSTS  (monthly cost of delivery by product line)
# ----------------------------------------------------------------------
# Recurring revenue by product line by month (from clean invoice view, pre-noise
# would be ideal; we approximate off subscriptions to keep costs "management" grade)
rev_by_line_month = (
    invoices_df.merge(products_df[["product_id","product_line","revenue_type"]],
                      on="product_id", how="left")
    .assign(month=lambda d: pd.to_datetime(d.invoice_date).values.astype("datetime64[M]"))
)
# Use only positive, paid/overdue recurring+one-off for the cost driver
driver = rev_by_line_month[(rev_by_line_month.amount>0)]
line_month_rev = driver.groupby(["month","product_line"])["amount"].sum().reset_index()

COST_RATIO = {   # cost of delivery as a % of that line's revenue
    "Core Platform": 0.18,          # hosting-heavy, high margin
    "Analytics Add-on": 0.22,
    "Payments Module": 0.35,        # third-party payment licences
    "Implementation Services": 0.72,# labour-intensive, low margin
}
cost_rows = []
for _, r in line_month_rev.iterrows():
    ratio = COST_RATIO.get(r.product_line, 0.3)
    ratio_noisy = float(np.clip(ratio * rng.normal(1.0, 0.05), 0.05, 0.95))
    rev = r["amount"]
    total = rev * ratio_noisy
    if r.product_line in ("Core Platform","Analytics Add-on"):
        hosting = total*0.55; support=total*0.30; licences=total*0.15
    elif r.product_line=="Payments Module":
        hosting=total*0.15; support=total*0.20; licences=total*0.65
    else:
        hosting=total*0.05; support=total*0.90; licences=total*0.05
    cost_rows.append({
        "month": pd.Timestamp(r.month).date(),
        "product_line": r.product_line,
        "hosting_cost": round(hosting,2),
        "support_staff_cost": round(support,2),
        "third_party_licence_cost": round(licences,2),
        "total_cost_of_delivery": round(total,2),
    })
costs_df = pd.DataFrame(cost_rows).sort_values(["month","product_line"]).reset_index(drop=True)

# ----------------------------------------------------------------------
# 5. MANAGEMENT ACCOUNTS  (monthly P&L as the company reports it)
# ----------------------------------------------------------------------
# "True" recognised revenue = net invoices (incl. credit notes), positive+negative,
# excluding the planted duplicates and keying errors (management books are assumed
# broadly correct); we then inject a small recon gap in a few months.
inv_clean = invoices_df.drop_duplicates(
    subset=["customer_id","product_id","invoice_date","amount","revenue_type","status"],
    keep="first")
inv_clean = inv_clean[~((inv_clean.status=="paid") & (inv_clean.amount<0))]  # drop keying errors
mgmt_src = (inv_clean.merge(products_df[["product_id","product_line"]], on="product_id")
    .assign(month=lambda d: pd.to_datetime(d.invoice_date).values.astype("datetime64[M]")))
mgmt_rev = mgmt_src.groupby(["month","product_line"])["amount"].sum().reset_index()
mgmt_pivot = mgmt_rev.pivot(index="month", columns="product_line", values="amount").fillna(0)

cost_month = costs_df.groupby("month")["total_cost_of_delivery"].sum()

mgmt_rows = []
GAP_MONTHS = {date(2023,6,1): -18500, date(2024,3,1): 12000,
              date(2024,11,1): -9500, date(2025,2,1): 15000}
for m in REPORTED_MONTHS:
    mts = pd.Timestamp(m)
    row = {"month": m}
    total_rev = 0
    for line in ["Core Platform","Analytics Add-on","Payments Module","Implementation Services"]:
        v = float(mgmt_pivot.loc[mts, line]) if (mts in mgmt_pivot.index and line in mgmt_pivot.columns) else 0.0
        row[f"revenue_{line.replace(' ','_').lower()}"] = round(v,2)
        total_rev += v
    # PLANTED recon gap: management accounts differ from invoice cube in a few months
    gap = GAP_MONTHS.get(m, 0)
    total_rev_reported = total_rev + gap
    cos = float(cost_month.get(m, 0.0))
    row["total_revenue"] = round(total_rev_reported,2)
    row["cost_of_sales"] = round(cos,2)
    row["gross_profit"] = round(total_rev_reported - cos,2)
    row["gross_margin_pct"] = round((total_rev_reported-cos)/total_rev_reported,4) if total_rev_reported else 0
    mgmt_rows.append(row)
management_df = pd.DataFrame(mgmt_rows)

# ----------------------------------------------------------------------
# WRITE OUTPUTS
# ----------------------------------------------------------------------
customers_df.to_csv(f"{OUTDIR}/customers.csv", index=False)
products_df.to_csv(f"{OUTDIR}/products.csv", index=False)
subscriptions_df.to_csv(f"{OUTDIR}/subscriptions.csv", index=False)
invoices_df.to_csv(f"{OUTDIR}/invoices.csv", index=False)
costs_df.to_csv(f"{OUTDIR}/costs.csv", index=False)
management_df.to_csv(f"{OUTDIR}/management_accounts.csv", index=False)

# ----------------------------------------------------------------------
# CONSOLE SUMMARY (what to expect on run)
# ----------------------------------------------------------------------
def yr_rev(y):
    d = invoices_df.copy()
    d["yr"] = pd.to_datetime(d.invoice_date).dt.year
    return d[(d.yr==y)&(d.amount>0)]["amount"].sum()

print("="*64)
print("Northbridge Software Ltd - data room generated")
print("="*64)
print(f"customers        : {len(customers_df):>7,} rows")
print(f"products         : {len(products_df):>7,} rows")
print(f"subscriptions    : {len(subscriptions_df):>7,} rows")
print(f"invoices         : {len(invoices_df):>7,} rows")
print(f"costs            : {len(costs_df):>7,} rows")
print(f"management_accts : {len(management_df):>7,} rows")
print("-"*64)
for y in (2022,2023,2024,2025):
    tot = management_df[pd.to_datetime(management_df.month).dt.year==y]["total_revenue"].sum()
    print(f"  mgmt revenue {y}: £{tot:,.0f}")
print("-"*64)
print(f"Files written to {OUTDIR}/")
