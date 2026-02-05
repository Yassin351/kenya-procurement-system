import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.supervisor import run_procurement

st.set_page_config(
    page_title="Kenya Smart Procurement AI",
    page_icon="🇰🇪",
    layout="wide"
)

st.markdown("<h1 style='text-align: center; color: #1f77b4;'>🇰🇪 Smart Procurement AI</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 18px;'>Intelligent sourcing for Kenyan businesses</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("🔧 Configuration")
    
    product_query = st.text_input(
        "What do you want to buy?",
        placeholder="e.g., Samsung Galaxy A54, Maize seeds, Office chairs"
    )
    
    category = st.selectbox(
        "Product Category",
        ["electronics", "fashion", "home", "beauty", "groceries", "seeds", "general"]
    )
    
    catalog_file = st.file_uploader(
        "Upload Supplier Catalog (Optional)",
        type=['pdf', 'png', 'jpg']
    )
    
    analyze_btn = st.button("🔍 Analyze Market", type="primary", use_container_width=True)

if analyze_btn and product_query:
    with st.spinner("🤖 AI Agents analyzing market... Please wait..."):
        try:
            result = run_procurement(product_query, category)
            
            rec = result.get('final_recommendation', {})
            
            if rec.get('warning'):
                st.error(f"⚠️ {rec['warning']}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                best = rec.get('best_option', {})
                st.metric("Best Price", f"KES {best.get('price_kes', 0):,.2f}")
            with col2:
                forecast = rec.get('price_forecast', {})
                savings = forecast.get('savings_potential', 0)
                st.metric("Potential Savings", f"KES {savings:,.2f}" if savings else "N/A")
            with col3:
                st.metric("Confidence", f"{rec.get('confidence_score', 0):.0%}")
            
            st.subheader("💰 Best Option")
            best = rec.get('best_option', {})
            st.success(f"**{best.get('product_name', 'Unknown')}**  
🏪 {best.get('seller', 'Unknown')} ({best.get('platform', 'Unknown')})  
💵 KES {best.get('price_kes', 0):,.2f}")
            
            st.subheader("📊 Price Forecast")
            if forecast:
                st.info(f"**Trend:** {forecast.get('trend', 'stable').upper()}  
**Recommendation:** {forecast.get('recommendation', 'Buy now')}")
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.info("Please check that GOOGLE_API_KEY is set in .env file")

else:
    st.markdown("### 👋 Welcome!")
    st.markdown("""
    This AI system helps Kenyan businesses:
    - 🔍 **Compare prices** across Jumia, Copia, and other platforms
    - 📈 **Forecast optimal buying times** (e.g., "Wait 3 days, price drops 12% on Fridays")
    - 🛡️ **Verify seller legitimacy** and detect counterfeit risks
    - 💰 **Calculate import taxes** (KRA VAT, duty, levies)
    - 📄 **Extract prices** from supplier catalogs using OCR
    """)
    
    st.info("👈 Enter a product in the sidebar and click 'Analyze Market' to start!")
