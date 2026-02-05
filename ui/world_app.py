import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.world_scraper import search_products

st.set_page_config(page_title="Global Procurement AI", page_icon="🌍", layout="wide")

st.title("🌍 Global Smart Procurement AI")
st.markdown("Multi-Agent Marketplace Intelligence System")

def extract_keywords(query):
    """Extract simple product keywords from complex natural language query"""
    query = query.lower()
    filler_words = ['i', 'want', 'cheap', 'from', 'usa', 'china', 'kenya', 'the', 'a', 'an', 'for', 'to', 'in', 'on', 'with', 'and', 'or', 'ebay', 'amazon', 'alibaba', 'aliexpress', 'kilimall', 'jumia', 'masoko']
    words = query.split()
    keywords = [w for w in words if w not in filler_words and len(w) > 2]
    return ' '.join(keywords[:3]) if keywords else query

with st.sidebar:
    st.header("Search Configuration")
    query = st.text_input("What product are you looking for?", placeholder="e.g., hp laptop, iphone, samsung tv...")
    
    st.subheader("Select Regions")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Africa (Kenya)**")
        kilimall = st.checkbox("Kilimall", value=True)
        jumia = st.checkbox("Jumia", value=True)
        masoko = st.checkbox("Masoko", value=True)
    with col2:
        st.markdown("**Global**")
        amazon = st.checkbox("Amazon USA", value=True)
        alibaba = st.checkbox("Alibaba China", value=True)
        ebay = st.checkbox("eBay USA", value=True)
        aliexpress = st.checkbox("AliExpress", value=True)
    
    max_price = st.number_input("Maximum Budget (KES)", min_value=0, value=1000000, step=5000)
    search_btn = st.button("Search Worldwide", type="primary", use_container_width=True)

if search_btn and query:
    search_query = extract_keywords(query)
    st.info(f"Searching for: **{search_query}**")
    
    markets = []
    if kilimall: markets.append("Kilimall")
    if jumia: markets.append("Jumia")
    if masoko: markets.append("Masoko")
    if amazon: markets.append("Amazon")
    if alibaba: markets.append("Alibaba")
    if ebay: markets.append("eBay")
    if aliexpress: markets.append("AliExpress")
    
    if not markets:
        st.warning("Please select at least one marketplace!")
    else:
        with st.spinner("AI Agents searching worldwide..."):
            results = search_products(search_query, markets)
        
        if max_price > 0:
            results = [r for r in results if r["price"] <= max_price]
        
        if results:
            st.success(f"Found {len(results)} products across {len(set(r['marketplace'] for r in results))} marketplaces!")
            
            df = pd.DataFrame(results)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Cheapest", f"KES {min(r['price'] for r in results):,.0f}")
            with col2:
                st.metric("Average", f"KES {sum(r['price'] for r in results)/len(results):,.0f}")
            with col3:
                st.metric("Marketplaces", f"{len(set(r['marketplace'] for r in results))}")
            with col4:
                st.metric("Products", len(results))
            
            st.subheader("Price Analysis")
            fig = px.bar(df, x="name", y="price", color="marketplace", facet_col="country", 
                        title=f"Price Comparison: {search_query}", height=500)
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Product Listings")
            results.sort(key=lambda x: x["price"])
            
            cols = st.columns(3)
            badge_colors = {"Kilimall": "#ff6b00", "Jumia": "#f68b1e", "Masoko": "#00a650", 
                          "Amazon": "#232f3e", "Alibaba": "#ff6a00", "eBay": "#e53238", "AliExpress": "#e43225"}
            
            for idx, product in enumerate(results):
                with cols[idx % 3]:
                    # Display product image with error handling
                    try:
                        if product["image_url"] and product["image_url"].startswith("http"):
                            st.image(product["image_url"], use_container_width=True)
                        else:
                            st.image("https://via.placeholder.com/300?text=No+Image", use_container_width=True)
                    except:
                        st.image("https://via.placeholder.com/300?text=No+Image", use_container_width=True)
                    
                    # Marketplace badge
                    badge_color = badge_colors.get(product["marketplace"], "#666")
                    st.markdown(f"<span style='background-color:{badge_color};color:white;padding:4px 8px;border-radius:4px;font-size:0.8rem;font-weight:bold;'>{product['marketplace']}</span> ({product['country']})", unsafe_allow_html=True)
                    
                    # Product name
                    name = product['name'][:55] + '...' if len(product['name']) > 55 else product['name']
                    st.markdown(f"**{name}**")
                    
                    # Price
                    st.markdown(f"<h3 style='color:#28a745;margin:0;'>KES {product['price']:,.0f}</h3>", unsafe_allow_html=True)
                    st.markdown(f"<p style='color:#666;font-size:0.75rem;margin:0;'>{product['currency']}</p>", unsafe_allow_html=True)
                    
                    # Direct link button
                    st.link_button("🛒 View Product", product["link"], use_container_width=True)
                    st.markdown("---")
            
            # Export
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Export to CSV", csv, f"procurement_{search_query.replace(' ', '_')}.csv", "text/csv")
        else:
            st.warning("No products found. Try:")
            st.markdown("- Enable more marketplaces in the sidebar")
            st.markdown("- Increase your budget")
            st.markdown("- Use simpler search terms like 'laptop', 'phone', 'shoes'")
else:
    st.info("Configure your search in the sidebar and click Search Worldwide!")
    
    st.markdown("### How to Search")
    st.markdown("1. **Enter product name** - e.g., 'laptop', 'iphone', 'shoes'")
    st.markdown("2. **Select marketplaces** - Choose from Kenya or Global")
    st.markdown("3. **Set budget** - Maximum price in KES")
    st.markdown("4. **Click Search**")