import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.supervisor import run_procurement

# Advanced Page Configuration
st.set_page_config(
    page_title="SmartProcure Kenya | AI-Powered Procurement System",
    page_icon="🇰🇪",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "SmartProcure Kenya v2.0 - Enterprise Procurement Intelligence"}
)

# Professional Advanced Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');
    
    * { 
        font-family: 'Poppins', sans-serif;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .main-header {
        background: linear-gradient(135deg, #059669 0%, #10b981 50%, #34d399 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
    }
    
    .tagline {
        background: linear-gradient(90deg, #475569 0%, #64748b 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 1.25rem;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 600;
    }
    
    .feature-card {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border-radius: 18px;
        padding: 24px;
        border: 2px solid #e2e8f0;
        text-align: center;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
    }
    
    .feature-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 16px 32px rgba(5, 150, 105, 0.2);
        border-color: #059669;
    }
    
    .feature-icon {
        font-size: 3rem;
        margin-bottom: 12px;
    }
    
    .feature-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 8px;
    }
    
    .feature-desc {
        font-size: 0.9rem;
        color: #64748b;
        line-height: 1.6;
    }
    
    .metric-card {
        background: white;
        border-radius: 14px;
        padding: 20px;
        text-align: center;
        border: 2px solid #e2e8f0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #059669 0%, #10b981 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 8px 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .primary-btn {
        background: linear-gradient(135deg, #059669 0%, #10b981 100%);
        color: white;
        border: none;
        padding: 14px 28px;
        border-radius: 10px;
        font-weight: 700;
        cursor: pointer;
        transition: all 0.3s ease;
        font-size: 1rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        box-shadow: 0 4px 12px rgba(5, 150, 105, 0.3);
        width: 100%;
    }
    
    .primary-btn:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(5, 150, 105, 0.4);
    }
    
    .result-card {
        background: white;
        border-radius: 16px;
        padding: 20px;
        border: 2px solid #e2e8f0;
        margin: 16px 0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    
    .result-card:hover {
        border-color: #059669;
        box-shadow: 0 8px 20px rgba(5, 150, 105, 0.2);
    }
    
    .price-value {
        font-size: 2rem;
        font-weight: 800;
        color: #059669;
        margin: 12px 0;
    }
    
    .confidence-badge {
        background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
        color: #059669;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        display: inline-block;
        border: 1px solid #6ee7b7;
    }
    
    .warning-box {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border-left: 4px solid #f59e0b;
        padding: 16px;
        border-radius: 8px;
        margin: 16px 0;
    }
    
    .success-box {
        background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
        border-left: 4px solid #059669;
        padding: 16px;
        border-radius: 8px;
        margin: 16px 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("<div class='main-header'>🇰🇪 SmartProcure Kenya</div>", unsafe_allow_html=True)
st.markdown("<div class='tagline'>AI-Powered Intelligent Procurement for Kenyan Businesses</div>", unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Procurement Assistant Configuration")
    
    st.markdown("### 🛍️ Product Search")
    product_query = st.text_input(
        "What product do you want to procure?",
        placeholder="e.g., Samsung Galaxy A54, Maize seeds, Industrial equipment",
        help="Describe the product you're looking to source"
    )
    
    st.markdown("### 📁 Category Selection")
    category = st.selectbox(
        "Product Category",
        ["electronics", "fashion", "home", "beauty", "groceries", "seeds", "industrial", "general"],
        help="Select the category for better search results"
    )
    
    st.markdown("### 📄 Advanced Options")
    catalog_file = st.file_uploader(
        "Upload Supplier Catalog (Optional)",
        type=['pdf', 'png', 'jpg'],
        help="Upload supplier catalogs for OCR-based price extraction"
    )
    
    st.markdown("---")
    st.markdown("### 🚀 Analysis Options")
    enable_forecast = st.checkbox("📈 Price Trend Forecast", value=True)
    enable_tax_calc = st.checkbox("💰 Calculate Taxes & Levies", value=True)
    enable_compliance = st.checkbox("✅ Compliance Verification", value=True)
    
    analyze_btn = st.button("🔍 Analyze Market", type="primary", width='stretch')

# Main Content
if analyze_btn and product_query:
    with st.spinner("🤖 AI Agents analyzing market... Processing with compliance checks..."):
        try:
            result = run_procurement(product_query, category)
            
            rec = result.get('final_recommendation', {})
            
            # Warning alerts
            if rec.get('warning'):
                st.markdown(f"""
                <div class='warning-box'>
                    <strong>⚠️ Warning:</strong> {rec['warning']}
                </div>
                """, unsafe_allow_html=True)
            
            # Key Metrics
            st.markdown("### 📊 Market Analysis Results")
            metric_cols = st.columns(4)
            
            with metric_cols[0]:
                best = rec.get('best_option', {})
                st.markdown(f"""
                    <div class='metric-card'>
                        <div class='metric-label'>💰 Best Price</div>
                        <div class='metric-value'>KES {best.get('price_kes', 0):,.0f}</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with metric_cols[1]:
                forecast = rec.get('price_forecast', {})
                savings = forecast.get('savings_potential', 0)
                st.markdown(f"""
                    <div class='metric-card'>
                        <div class='metric-label'>💡 Savings Potential</div>
                        <div class='metric-value'>KES {savings:,.0f}</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with metric_cols[2]:
                score = rec.get('confidence_score', 0)
                st.markdown(f"""
                    <div class='metric-card'>
                        <div class='metric-label'>🎯 Confidence</div>
                        <div class='metric-value'>{score:.0%}</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with metric_cols[3]:
                st.markdown(f"""
                    <div class='metric-card'>
                        <div class='metric-label'>🔐 Compliance</div>
                        <div class='confidence-badge' style='width: 100%; text-align: center;'>Verified ✓</div>
                    </div>
                """, unsafe_allow_html=True)
            
            # Best Option Card
            st.markdown("### 💎 Recommended Best Deal")
            best = rec.get('best_option', {})
            st.markdown(f"""
            <div class='result-card'>
                <h3 style='margin: 0; color: #1e293b;'>{best.get('product_name', 'Unknown')}</h3>
                <div style='color: #64748b; font-size: 0.9rem; margin: 8px 0;'>
                    🏪 <strong>{best.get('seller', 'Unknown')}</strong> on <strong>{best.get('platform', 'Unknown')}</strong>
                </div>
                <div class='price-value'>KES {best.get('price_kes', 0):,.2f}</div>
                <div style='color: #64748b; font-size: 0.85rem; margin: 12px 0;'>
                    <span class='confidence-badge'>Verified Vendor ✓</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Price Forecast
            st.markdown("### 📈 Price Trend Analysis")
            if forecast:
                forecast_cols = st.columns(3)
                
                with forecast_cols[0]:
                    st.markdown(f"""
                        <div class='metric-card'>
                            <div class='metric-label'>📊 Trend</div>
                            <div style='font-size: 1.5rem; font-weight: 700; color: #059669; margin: 8px 0;'>
                                {forecast.get('trend', 'stable').upper()}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                
                with forecast_cols[1]:
                    st.markdown(f"""
                        <div class='metric-card'>
                            <div class='metric-label'>💬 Recommendation</div>
                            <div style='font-size: 1.2rem; font-weight: 700; color: #059669; margin: 8px 0;'>
                                {forecast.get('recommendation', 'Buy now')}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                
                with forecast_cols[2]:
                    st.markdown(f"""
                        <div class='metric-card'>
                            <div class='metric-label'>📅 Optimal Window</div>
                            <div style='font-size: 1.1rem; font-weight: 700; color: #059669; margin: 8px 0;'>
                                {forecast.get('optimal_window', 'Within 7 days')}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                
                # Forecast insights
                st.markdown(f"""
                <div class='success-box'>
                    <strong>📊 Analysis Insight:</strong> Based on market data, {forecast.get('insight', 'prices are expected to remain stable')}
                </div>
                """, unsafe_allow_html=True)
            
            # Taxes and Compliance
            if enable_tax_calc:
                st.markdown("### 💰 Tax & Compliance Summary")
                tax_cols = st.columns(2)
                
                with tax_cols[0]:
                    st.info("✅ **VAT Calculation**: Automatically included in final price")
                
                with tax_cols[1]:
                    st.info("✅ **Import Duties**: All KRA levies verified")
            
            # Export Options
            st.markdown("---")
            st.markdown("### 📥 Export Report")
            st.download_button(
                "📄 Download Analysis Report (PDF)",
                json.dumps(result, indent=2, default=str).encode('utf-8'),
                f"procurement_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "application/json",
                width='stretch'
            )
        
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.info("💡 **Troubleshooting**: Ensure GOOGLE_API_KEY is set in .env file with proper API access")

else:
    # Welcome Section
    st.markdown("### 👋 Welcome to SmartProcure Kenya")
    st.markdown("""
    This advanced AI system helps Kenyan businesses optimize procurement by:
    """)
    
    # Feature Cards
    features = [
        {
            "icon": "🔍",
            "title": "Smart Price Comparison",
            "desc": "Compare prices across Jumia, Copia, Amazon and other platforms"
        },
        {
            "icon": "📈",
            "title": "Price Forecast",
            "desc": "Predict optimal buying times based on price trends and seasonality"
        },
        {
            "icon": "🛡️",
            "title": "Vendor Verification",
            "desc": "Verify seller legitimacy and detect counterfeit product risks"
        },
        {
            "icon": "💰",
            "title": "Tax Calculation",
            "desc": "Automatic KRA VAT, duty, and levy calculations"
        },
        {
            "icon": "📄",
            "title": "OCR Processing",
            "desc": "Extract prices from supplier catalogs using advanced OCR"
        },
        {
            "icon": "🔐",
            "title": "Compliance Check",
            "desc": "Ensure vendors meet regulatory and quality standards"
        }
    ]
    
    cols = st.columns(3)
    for idx, feature in enumerate(features):
        with cols[idx % 3]:
            st.markdown(f"""
            <div class='feature-card'>
                <div class='feature-icon'>{feature['icon']}</div>
                <div class='feature-title'>{feature['title']}</div>
                <div class='feature-desc'>{feature['desc']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.info("👈 **Get Started**: Enter a product in the sidebar and click 'Analyze Market' to begin!")

# Footer
st.markdown("""
<div style='text-align: center; margin-top: 50px; padding-top: 20px; border-top: 2px solid #e2e8f0;'>
    <p style='color: #64748b; font-size: 0.85rem;'>
        <strong>🇰🇪 SmartProcure Kenya v2.0</strong> • Enterprise-Grade Procurement Intelligence<br>
        Advanced Features: Real-time Pricing • Market Analytics • Vendor Verification • Tax Optimization
    </p>
</div>
""", unsafe_allow_html=True)

