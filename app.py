import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import csv
from io import StringIO

@st.cache_data(show_spinner=False)
def fetch_price_data(card):
    """Fetch average sold price and lowest current listing price from eBay."""
    query_parts = [card.get("name"), card.get("set"), card.get("number"), card.get("edition")]
    if card.get("holo"):
        query_parts.append("holo")
    query = "+".join(str(part) for part in query_parts if part)
    headers = {"User-Agent": "Mozilla/5.0"}
    def parse_prices(url):
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        prices = []
        for el in soup.select(".s-item__price"):
            text = el.get_text()
            match = re.search(r"[\d,.]+", text)
            if match:
                try:
                    prices.append(float(match.group(0).replace(",", "")))
                except ValueError:
                    pass
        return prices
    try:
        sold_url = f"https://www.ebay.com/sch/i.html?_nkw={query}&LH_Sold=1&LH_Complete=1"
        sold_prices = parse_prices(sold_url)
        avg_price = sum(sold_prices)/len(sold_prices) if sold_prices else None
    except Exception:
        avg_price = None
    try:
        listing_url = f"https://www.ebay.com/sch/i.html?_nkw={query}&LH_BIN=1"
        listing_prices = parse_prices(listing_url)
        min_listing = min(listing_prices) if listing_prices else None
    except Exception:
        min_listing = None
    return avg_price, min_listing

def parse_cards(text):
    cards = []
    if not text:
        return cards
    reader = csv.DictReader(StringIO(text))
    for row in reader:
        card = {
            "name": row.get("name", "").strip(),
            "set": row.get("set", "").strip(),
            "number": row.get("number", "").strip(),
            "edition": row.get("edition", "").strip(),
            "holo": row.get("holo", "").strip().lower() in {"true", "1", "yes", "y"},
            "condition": row.get("condition", "").strip(),
        }
        cards.append(card)
    return cards

st.title("Pokémon Card Price Checker")
example = "name,set,number,edition,holo,condition\nPikachu,Base Set,58,1st Edition,true,NM"
input_text = st.text_area(
    "Enter cards (CSV format)",
    value=example,
    height=150,
)

if st.button("Fetch Prices"):
    cards = parse_cards(input_text)
    results = []
    for card in cards:
        avg_price, min_listing = fetch_price_data(card)
        result = {
            **card,
            "average_sold_price": avg_price,
            "lowest_listing_price": min_listing,
        }
        results.append(result)
    if results:
        df = pd.DataFrame(results)
        def highlight(row):
            if row["average_sold_price"] and row["lowest_listing_price"]:
                if row["lowest_listing_price"] < 0.8 * row["average_sold_price"]:
                    return ["background-color: #ffcccc"] * len(row)
            return [""] * len(row)
        st.dataframe(df.style.apply(highlight, axis=1))
