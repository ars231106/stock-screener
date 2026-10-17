"""The default screening universe.

Kept as data rather than config so the seed is reproducible and reviewable.
The `universe` table is the runtime source of truth -- this list only seeds
it, and symbols can be added there without a deploy.

Indian tickers use Yahoo's suffixes: `.NS` for NSE, `.BO` for BSE. Including
them is the point of moving off Alpha Vantage, whose free tier published no
fundamentals for Indian listings at all.
"""

US = [
    ("AAPL", "Apple"), ("MSFT", "Microsoft"), ("GOOGL", "Alphabet"),
    ("AMZN", "Amazon"), ("NVDA", "NVIDIA"), ("META", "Meta Platforms"),
    ("TSLA", "Tesla"), ("NFLX", "Netflix"), ("AMD", "AMD"),
    ("INTC", "Intel"), ("AVGO", "Broadcom"), ("QCOM", "Qualcomm"),
    ("TXN", "Texas Instruments"), ("MU", "Micron"), ("ADBE", "Adobe"),
    ("CRM", "Salesforce"), ("ORCL", "Oracle"), ("CSCO", "Cisco"),
    ("IBM", "IBM"), ("NOW", "ServiceNow"), ("UBER", "Uber"),
    ("JPM", "JPMorgan Chase"), ("BAC", "Bank of America"),
    ("WFC", "Wells Fargo"), ("GS", "Goldman Sachs"), ("MS", "Morgan Stanley"),
    ("V", "Visa"), ("MA", "Mastercard"), ("AXP", "American Express"),
    ("BRK-B", "Berkshire Hathaway"), ("BLK", "BlackRock"),
    ("JNJ", "Johnson & Johnson"), ("PFE", "Pfizer"), ("MRK", "Merck"),
    ("ABBV", "AbbVie"), ("LLY", "Eli Lilly"), ("UNH", "UnitedHealth"),
    ("TMO", "Thermo Fisher"), ("ABT", "Abbott"),
    ("WMT", "Walmart"), ("COST", "Costco"), ("TGT", "Target"),
    ("HD", "Home Depot"), ("LOW", "Lowe's"), ("NKE", "Nike"),
    ("SBUX", "Starbucks"), ("MCD", "McDonald's"),
    ("PG", "Procter & Gamble"), ("KO", "Coca-Cola"), ("PEP", "PepsiCo"),
    ("PM", "Philip Morris"), ("MDLZ", "Mondelez"),
    ("XOM", "Exxon Mobil"), ("CVX", "Chevron"), ("COP", "ConocoPhillips"),
    ("CAT", "Caterpillar"), ("DE", "Deere"), ("BA", "Boeing"),
    ("GE", "GE Aerospace"), ("HON", "Honeywell"), ("UPS", "UPS"),
    ("DIS", "Disney"), ("CMCSA", "Comcast"), ("T", "AT&T"),
    ("VZ", "Verizon"), ("TMUS", "T-Mobile"),
    ("LIN", "Linde"), ("SHW", "Sherwin-Williams"), ("NEE", "NextEra Energy"),
    ("DUK", "Duke Energy"), ("SO", "Southern Company"),
]

INDIA = [
    ("RELIANCE.NS", "Reliance Industries"), ("TCS.NS", "Tata Consultancy Services"),
    ("HDFCBANK.NS", "HDFC Bank"), ("ICICIBANK.NS", "ICICI Bank"),
    ("INFY.NS", "Infosys"), ("SBIN.NS", "State Bank of India"),
    ("BHARTIARTL.NS", "Bharti Airtel"), ("ITC.NS", "ITC"),
    ("LT.NS", "Larsen & Toubro"), ("KOTAKBANK.NS", "Kotak Mahindra Bank"),
    ("HINDUNILVR.NS", "Hindustan Unilever"), ("AXISBANK.NS", "Axis Bank"),
    ("BAJFINANCE.NS", "Bajaj Finance"), ("ASIANPAINT.NS", "Asian Paints"),
    ("MARUTI.NS", "Maruti Suzuki"), ("TITAN.NS", "Titan Company"),
    ("SUNPHARMA.NS", "Sun Pharmaceutical"), ("ULTRACEMCO.NS", "UltraTech Cement"),
    ("WIPRO.NS", "Wipro"), ("HCLTECH.NS", "HCL Technologies"),
    ("TECHM.NS", "Tech Mahindra"), ("NESTLEIND.NS", "Nestle India"),
    ("POWERGRID.NS", "Power Grid Corporation"), ("NTPC.NS", "NTPC"),
    ("ONGC.NS", "Oil & Natural Gas Corporation"), ("COALINDIA.NS", "Coal India"),
    ("TATAMOTORS.NS", "Tata Motors"), ("TATASTEEL.NS", "Tata Steel"),
    ("JSWSTEEL.NS", "JSW Steel"), ("HINDALCO.NS", "Hindalco Industries"),
    ("ADANIENT.NS", "Adani Enterprises"), ("ADANIPORTS.NS", "Adani Ports"),
    ("BEL.NS", "Bharat Electronics"), ("HAL.NS", "Hindustan Aeronautics"),
    ("IRCTC.NS", "IRCTC"), ("DMART.NS", "Avenue Supermarts"),
    ("BAJAJFINSV.NS", "Bajaj Finserv"), ("DRREDDY.NS", "Dr. Reddy's Laboratories"),
    ("CIPLA.NS", "Cipla"), ("DIVISLAB.NS", "Divi's Laboratories"),
    ("GRASIM.NS", "Grasim Industries"), ("BRITANNIA.NS", "Britannia Industries"),
    ("EICHERMOT.NS", "Eicher Motors"), ("HEROMOTOCO.NS", "Hero MotoCorp"),
    ("BAJAJ-AUTO.NS", "Bajaj Auto"), ("M&M.NS", "Mahindra & Mahindra"),
    ("SHRIRAMFIN.NS", "Shriram Finance"), ("INDUSINDBK.NS", "IndusInd Bank"),
    ("APOLLOHOSP.NS", "Apollo Hospitals"), ("TRENT.NS", "Trent"),
]


def seed_rows() -> list[dict]:
    """Rows for an upsert into the `universe` table."""
    rows = [
        {"symbol": s, "name": n, "market": "US", "currency": "USD", "active": True}
        for s, n in US
    ]
    rows += [
        {"symbol": s, "name": n, "market": "IN", "exchange": "NSE",
         "currency": "INR", "active": True}
        for s, n in INDIA
    ]
    return rows


ALL_SYMBOLS = [s for s, _ in US] + [s for s, _ in INDIA]
