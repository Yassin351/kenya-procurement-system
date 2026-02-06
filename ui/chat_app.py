import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import uuid
import json
from functools import lru_cache
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.world_scraper import search_products

# Page configuration
st.set_page_config(
    page_title="SmartProcure AI | Advanced Global Marketplace Intelligence",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "SmartProcure AI v2.0 - Enterprise Grade Marketplace Intelligence"}
)

# Advanced Professional CSS styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');
    
    * { 
        font-family: 'Poppins', 'Inter', sans-serif; 
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* Main Header Styles */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
        text-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    
    .tagline {
        background: linear-gradient(90deg, #64748b 0%, #475569 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 1.25rem;
        text-align: center;
        margin-bottom: 2.5rem;
        font-weight: 500;
        letter-spacing: 0.5px;
    }
    
    /* Chat Container Styles */
    .chat-container {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border-radius: 20px;
        padding: 28px;
        margin: 20px 0;
        border: 2px solid #e2e8f0;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
        backdrop-filter: blur(10px);
    }
    
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 14px 22px;
        border-radius: 20px 20px 4px 20px;
        margin: 12px 0;
        max-width: 75%;
        margin-left: auto;
        margin-right: 0;
        font-weight: 500;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        word-wrap: break-word;
    }
    
    .ai-message {
        background: white;
        color: #1e293b;
        padding: 14px 22px;
        border-radius: 20px 20px 20px 4px;
        margin: 12px 0;
        max-width: 75%;
        margin-left: 0;
        margin-right: auto;
        border: 2px solid #e2e8f0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        word-wrap: break-word;
    }
    
    /* Product Card Styles */
    .product-card {
        background: white;
        border-radius: 18px;
        padding: 20px;
        margin: 16px 0;
        border: 2px solid #e2e8f0;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        position: relative;
        overflow: hidden;
    }
    
    .product-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
        transition: left 0.5s;
    }
    
    .product-card:hover::before {
        left: 100%;
    }
    
    .product-card:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 16px 32px rgba(102, 126, 234, 0.2);
        border-color: #667eea;
    }
    
    /* Price Tag Styles */
    .price-tag {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #059669 0%, #10b981 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -0.02em;
    }
    
    .original-price {
        font-size: 0.9rem;
        color: #94a3b8;
        text-decoration: line-through;
        margin-left: 8px;
    }
    
    .discount-badge {
        background: linear-gradient(135deg, #ef4444 0%, #f87171 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        display: inline-block;
        margin-left: 8px;
    }
    
    /* Marketplace Badge Styles */
    .marketplace-badge {
        display: inline-flex;
        align-items: center;
        padding: 8px 14px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        color: white;
        margin-bottom: 12px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Stats Card Styles */
    .stats-card {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        border: 2px solid #e2e8f0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
        transition: all 0.3s ease;
    }
    
    .stats-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.12);
        border-color: #667eea;
    }
    
    .stats-number {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .stats-label {
        color: #64748b;
        font-size: 0.9rem;
        font-weight: 600;
        margin-top: 8px;
        letter-spacing: 0.5px;
    }
    
    /* Sidebar Header */
    .sidebar-header {
        font-size: 0.875rem;
        font-weight: 700;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* History Item Styles */
    .history-item {
        background: white;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 10px;
        border: 2px solid #e2e8f0;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
    }
    
    .history-item:hover {
        background: #f1f5f9;
        border-color: #667eea;
        transform: translateX(6px);
        box-shadow: 0 6px 16px rgba(102, 126, 234, 0.15);
    }
    
    .history-item.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-color: #667eea;
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
    }
    
    .history-title {
        font-weight: 700;
        font-size: 0.95rem;
        margin-bottom: 6px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .history-time {
        font-size: 0.75rem;
        color: #64748b;
        margin-bottom: 4px;
    }
    
    .history-item.active .history-time {
        color: rgba(255,255,255,0.7);
    }
    
    /* Advanced Filter Button */
    .filter-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 10px 16px;
        border-radius: 10px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .filter-btn:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* Trust Badge */
    .trust-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
        color: #059669;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        border: 1px solid #6ee7b7;
    }
    
    /* Savings Tag */
    .savings-tag {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        color: #92400e;
        padding: 8px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        display: inline-block;
        margin-top: 12px;
        border: 1px solid #fcd34d;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Advanced Comparison Table */
    .comparison-table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
    }
    
    .comparison-table th {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 16px;
        text-align: left;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    
    .comparison-table td {
        padding: 14px 16px;
        border-bottom: 2px solid #e2e8f0;
    }
    
    .comparison-table tr:hover {
        background: #f8fafc;
    }
    
    /* Metric Card */
    .metric-card {
        background: white;
        border-radius: 14px;
        padding: 18px;
        border: 2px solid #e2e8f0;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #667eea;
        margin: 8px 0;
    }
    
    .metric-label {
        font-size: 0.8rem;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        color: #64748b;
        font-size: 0.875rem;
        margin-top: 50px;
        padding-top: 30px;
        border-top: 2px solid #e2e8f0;
    }
    
    .footer-text {
        margin: 8px 0;
        font-weight: 500;
    }
    
    /* Loading Animation */
    .loading-spinner {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid #f3f4f6;
        border-radius: 50%;
        border-top-color: #667eea;
        animation: spin 1s ease-in-out infinite;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    
    /* Mobile Form Optimization */
    .stTextInput {
        width: 100% !important;
    }
    
    .stFormSubmitButton {
        width: 100% !important;
        padding: 12px 24px !important;
        font-size: 1rem !important;
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .main-header { font-size: 2rem; }
        .price-tag { font-size: 1.5rem; }
        .stats-number { font-size: 1.8rem; }
        
        /* Mobile form layout */
        .stForm {
            gap: 12px !important;
        }
        
        .stTextInput input {
            font-size: 16px !important;
            padding: 12px !important;
            min-height: 48px !important;
        }
        
        .stFormSubmitButton > button {
            width: 100% !important;
            font-size: 16px !important;
            padding: 12px 16px !important;
            min-height: 48px !important;
            border-radius: 12px !important;
        }
    }
</style>
""", unsafe_allow_html=True)
# Initialize session state variables
@st.cache_resource
def init_session_state_resource():
    """Initialize cached session state resources"""
    return {
        'cache': {},
        'analytics': {}
    }

def init_session_state():
    """Initialize session state variables"""
    defaults = {
        'chat_history': {},
        'current_chat_id': None,
        'selected_markets': ["Kilimall", "Jumia", "Amazon", "eBay"],
        'last_results': [],
        'messages': [],
        'search_history': [],
        'filter_metrics': {},
        'price_insights': {}
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# Advanced analytics functions
def calculate_price_metrics(products: list) -> dict:
    """Calculate advanced price metrics and statistics"""
    if not products:
        return {}
    
    prices = [p['price'] for p in products]
    return {
        'min': min(prices),
        'max': max(prices),
        'avg': sum(prices) / len(prices),
        'median': sorted(prices)[len(prices)//2],
        'std_dev': np.std(prices),
        'range': max(prices) - min(prices),
        'q1': sorted(prices)[len(prices)//4],
        'q3': sorted(prices)[3*len(prices)//4],
        'iqr': sorted(prices)[3*len(prices)//4] - sorted(prices)[len(prices)//4]
    }

def generate_market_insights(products: list) -> dict:
    """Generate marketplace insights and recommendations"""
    if not products:
        return {}
    
    df = pd.DataFrame(products)
    market_stats = df.groupby('marketplace').agg({
        'price': ['min', 'mean', 'count'],
        'name': 'count'
    }).round(2)
    
    return {
        'market_comparison': market_stats.to_dict(),
        'best_market': df.loc[df['price'].idxmin(), 'marketplace'],
        'market_diversity': len(df['marketplace'].unique()),
        'avg_products_per_market': len(df) / len(df['marketplace'].unique())
    }

def calculate_savings_potential(products: list) -> float:
    """Calculate potential savings vs average price"""
    if not products or len(products) < 2:
        return 0
    
    prices = [p['price'] for p in products]
    avg = sum(prices) / len(prices)
    best = min(prices)
    return avg - best

def create_new_chat():
    """Create a new chat session"""
    chat_id = str(uuid.uuid4())
    st.session_state.chat_history[chat_id] = {
        'id': chat_id,
        'title': 'New Search',
        'messages': [],
        'timestamp': datetime.now(),
        'results': [],
        'first_query': None,
        'metrics': {}
    }
    st.session_state.current_chat_id = chat_id
    st.session_state.messages = []
    st.session_state.last_results = []
    st.rerun()

def switch_chat(chat_id):
    """Switch to a different chat"""
    if chat_id in st.session_state.chat_history:
        st.session_state.current_chat_id = chat_id
        chat_data = st.session_state.chat_history[chat_id]
        st.session_state.messages = chat_data['messages']
        st.session_state.last_results = chat_data['results']
        st.rerun()

def delete_chat(chat_id):
    """Delete a specific chat"""
    if chat_id in st.session_state.chat_history:
        del st.session_state.chat_history[chat_id]
        if st.session_state.current_chat_id == chat_id:
            if st.session_state.chat_history:
                most_recent = max(st.session_state.chat_history.values(), key=lambda x: x['timestamp'])
                st.session_state.current_chat_id = most_recent['id']
                st.session_state.messages = most_recent['messages']
                st.session_state.last_results = most_recent['results']
            else:
                create_new_chat()
        st.rerun()

def update_current_chat(query=None, results=None):
    """Update current chat with new data"""
    if st.session_state.current_chat_id and st.session_state.current_chat_id in st.session_state.chat_history:
        chat = st.session_state.chat_history[st.session_state.current_chat_id]
        chat['messages'] = st.session_state.messages
        chat['results'] = st.session_state.last_results
        chat['timestamp'] = datetime.now()
        
        if query and not chat['first_query']:
            chat['first_query'] = query
            chat['title'] = query[:30] + '...' if len(query) > 30 else query
        
        if st.session_state.last_results:
            chat['metrics'] = calculate_price_metrics(st.session_state.last_results)

# Create initial chat if none exists
if not st.session_state.chat_history:
    create_new_chat()

# Header
st.markdown("<div class='main-header'>🛒 SmartProcure AI</div>", unsafe_allow_html=True)
st.markdown("<div class='tagline'>Intelligent Global Marketplace Intelligence • Compare & Save</div>", unsafe_allow_html=True)

def extract_query_info(text):
    """Extract product, budget, and marketplace preferences"""
    import re
    text_lower = text.lower()
    
    # Extract budget
    budget = None
    patterns = [
        r'(\d+)\s*k[\s$]', r'(\d+)\s*kes', r'(\d+)\s*thousand',
        r'under\s*(\d+)', r'below\s*(\d+)', r'less\s*than\s*(\d+)',
        r'(\d+)\s*000', r'ksh?\s*(\d+)', r'budget.*?(\d+)', r'around\s*(\d+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            budget = int(match.group(1))
            if budget < 1000:
                budget *= 1000
            break
    
    # Extract product
    skip_words = ['i', 'want', 'need', 'looking', 'for', 'find', 'cheap', 'best', 
                  'good', 'quality', 'under', 'below', 'less', 'than', 'budget', 
                  'around', 'about', 'k', 'kes', 'thousand', 'from', 'in', 'on', 
                  'with', 'and', 'or', 'the', 'a', 'an']
    
    words = text_lower.replace(',', ' ').replace('.', ' ').split()
    keywords = [w for w in words if w not in skip_words and not w.isdigit() and len(w) > 2]
    product = ' '.join(keywords[:4]) if keywords else text
    
    # Detect markets
    markets = []
    if any(x in text_lower for x in ['local', 'kenya', 'nairobi', 'kilimall', 'jumia', 'masoko']):
        markets.extend(['Kilimall', 'Jumia', 'Masoko'])
    if any(x in text_lower for x in ['global', 'international', 'amazon', 'usa', 'ebay', 'america', 'us']):
        markets.extend(['Amazon', 'eBay'])
    if any(x in text_lower for x in ['china', 'alibaba', 'aliexpress', 'wholesale', 'chinese']):
        markets.extend(['Alibaba', 'AliExpress'])
    
    if not markets:
        markets = st.session_state.selected_markets
    
    return product, budget, list(dict.fromkeys(markets))

# Sidebar
with st.sidebar:
    # New Chat Button
    if st.button("➕ New Chat", key="new_chat_btn", width='stretch'):
        create_new_chat()
    
    st.markdown("---")
    
    # Chat History Section
    st.markdown("<div class='sidebar-header'>📜 Chat History</div>", unsafe_allow_html=True)
    
    if st.session_state.chat_history:
        # Sort chats by timestamp (most recent first)
        sorted_chats = sorted(
            st.session_state.chat_history.values(), 
            key=lambda x: x['timestamp'], 
            reverse=True
        )
        
        for chat in sorted_chats:
            is_active = chat['id'] == st.session_state.current_chat_id
            active_class = "active" if is_active else ""
            
            # Get preview text
            preview = chat['first_query'] if chat['first_query'] else "New Search"
            time_str = chat['timestamp'].strftime("%H:%M") if datetime.now().date() == chat['timestamp'].date() else chat['timestamp'].strftime("%b %d")
            
            col1, col2 = st.columns([0.9, 0.1])
            with col1:
                if st.button(
                    f"**{chat['title']}**\n\n{time_str} • {preview}",
                    key=f"chat_{chat['id']}",
                    width='stretch',
                    type="secondary" if not is_active else "primary"
                ):
                    switch_chat(chat['id'])
            
            with col2:
                if st.button("🗑️", key=f"del_{chat['id']}", help="Delete chat"):
                    delete_chat(chat['id'])
    else:
        st.markdown("<div class='empty-state'>No chat history yet</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("<div class='sidebar-header'>🛍️ Marketplaces</div>", unsafe_allow_html=True)
    
    st.markdown("**🇰🇪 Local (Kenya)**")
    kilimall = st.checkbox("Kilimall", value="Kilimall" in st.session_state.selected_markets, help="Leading Kenyan e-commerce")
    jumia = st.checkbox("Jumia", value="Jumia" in st.session_state.selected_markets, help="Pan-African marketplace")
    masoko = st.checkbox("Masoko", value="Masoko" in st.session_state.selected_markets, help="Safaricom's marketplace")
    
    st.markdown("**🌍 Global**")
    amazon = st.checkbox("Amazon", value="Amazon" in st.session_state.selected_markets, help="World's largest retailer")
    ebay = st.checkbox("eBay", value="eBay" in st.session_state.selected_markets, help="Auction & retail giant")
    alibaba = st.checkbox("Alibaba", value="Alibaba" in st.session_state.selected_markets, help="B2B wholesale")
    aliexpress = st.checkbox("AliExpress", value="AliExpress" in st.session_state.selected_markets, help="Retail from China")
    
    # Update markets
    st.session_state.selected_markets = []
    if kilimall: st.session_state.selected_markets.append("Kilimall")
    if jumia: st.session_state.selected_markets.append("Jumia")
    if masoko: st.session_state.selected_markets.append("Masoko")
    if amazon: st.session_state.selected_markets.append("Amazon")
    if ebay: st.session_state.selected_markets.append("eBay")
    if alibaba: st.session_state.selected_markets.append("Alibaba")
    if aliexpress: st.session_state.selected_markets.append("AliExpress")
    
    st.markdown("---")
    
    # Quick stats for current chat
    if st.session_state.last_results:
        st.markdown("<div class='sidebar-header'>📊 Current Search</div>", unsafe_allow_html=True)
        st.markdown(f"**Products:** {len(st.session_state.last_results)}")
        st.markdown(f"**Stores:** {len(set(r['marketplace'] for r in st.session_state.last_results))}")
        if st.session_state.last_results:
            cheapest = min(r['price'] for r in st.session_state.last_results)
            st.markdown(f"**Best Price:** KES {cheapest:,.0f}")
    
    st.markdown("---")
    st.markdown("💡 **Try saying:**")
    st.markdown('"iPhone under 50k from Amazon"')
    st.markdown('"Cheap Nike shoes"')
    st.markdown('"Laptop budget 100k"')

# Trust indicators
trust_col1, trust_col2, trust_col3, trust_col4 = st.columns(4)
with trust_col1:
    st.markdown("<div style='text-align:center;'><div class='feature-icon'>🔒</div><div style='font-size:0.875rem;font-weight:600;'>Secure Search</div></div>", unsafe_allow_html=True)
with trust_col2:
    st.markdown("<div style='text-align:center;'><div class='feature-icon'>⚡</div><div style='font-size:0.875rem;font-weight:600;'>Real-time Prices</div></div>", unsafe_allow_html=True)
with trust_col3:
    st.markdown("<div style='text-align:center;'><div class='feature-icon'>💰</div><div style='font-size:0.875rem;font-weight:600;'>Best Deals</div></div>", unsafe_allow_html=True)
with trust_col4:
    st.markdown("<div style='text-align:center;'><div class='feature-icon'>🌍</div><div style='font-size:0.875rem;font-weight:600;'>Global Stores</div></div>", unsafe_allow_html=True)

st.markdown("---")

# Chat interface
st.markdown("### 💬 What are you looking for?")

# Chat history display
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f"<div class='user-message'>{message['content']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='ai-message'>{message['content']}</div>", unsafe_allow_html=True)

# Input form
with st.form(key="chat_form", clear_on_submit=True):
    # Mobile-responsive form layout
    user_input = st.text_input(
        "Type your request...",
        placeholder="e.g., I need a laptop under 50k from Amazon, or Find me cheap Nike shoes",
        label_visibility="collapsed"
    )
    
    # Full-width submit button
    submit_button = st.form_submit_button("🔍 Search", use_container_width=True)

# Process search
if submit_button and user_input:
    # Add to current chat messages
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Update chat history with query
    update_current_chat(query=user_input)
    
    # Extract info
    product, budget, markets = extract_query_info(user_input)
    
    # AI response
    ai_msg = f"🔍 I'll find **{product}** for you"
    if budget:
        ai_msg += f" within **KES {budget:,.0f}**"
    ai_msg += f". Checking {len(markets)} stores..."
    st.session_state.messages.append({"role": "assistant", "content": ai_msg})
    
    # Update chat history
    update_current_chat()
    
    # Show search details
    st.info(f"**Product:** {product} | **Budget:** {'KES ' + f'{budget:,.0f}' if budget else 'Any'} | **Stores:** {', '.join(markets[:3])}{' +' + str(len(markets)-3) + ' more' if len(markets) > 3 else ''}")
    
    # Search with progress
    progress_text = st.empty()
    progress_bar = st.progress(0)
    all_results = []
    
    for idx, market in enumerate(markets):
        progress = int(((idx + 1) / len(markets)) * 100)
        progress_bar.progress(progress, f"Searching {market}...")
        
        try:
            results = search_products(product, [market])
            all_results.extend(results)
            if results:
                st.success(f"✅ **{market}**: {len(results)} products found")
            else:
                st.info(f"ℹ️ **{market}**: No results")
        except Exception as e:
            st.error(f"❌ **{market}**: {str(e)[:50]}")
    
    progress_bar.empty()
    progress_text.empty()
    
    # Apply budget filter
    if budget:
        filtered = [r for r in all_results if r["price"] <= budget]
        if filtered:
            all_results = filtered
            st.success(f"💰 Filtered to {len(all_results)} products under KES {budget:,.0f}")
        else:
            st.warning(f"No products under KES {budget:,.0f}. Showing all {len(all_results)} results.")
    
    st.session_state.last_results = all_results
    
    # Update chat history with results
    update_current_chat()
    
    if all_results:
        # Success animation
        st.balloons()
        
        # Calculate advanced metrics
        metrics = calculate_price_metrics(all_results)
        insights = generate_market_insights(all_results)
        savings = calculate_savings_potential(all_results)
        
        # Advanced Stats cards
        st.subheader("📊 Advanced Search Analytics")
        stats_cols = st.columns(5)
        
        with stats_cols[0]:
            st.markdown(f"""
                <div class='stats-card'>
                    <div class='stats-number'>KES {metrics.get('min', 0):,.0f}</div>
                    <div class='stats-label'>💰 Best Price</div>
                </div>
            """, unsafe_allow_html=True)
        
        with stats_cols[1]:
            st.markdown(f"""
                <div class='stats-card'>
                    <div class='stats-number'>KES {metrics.get('avg', 0):,.0f}</div>
                    <div class='stats-label'>📊 Average</div>
                </div>
            """, unsafe_allow_html=True)
        
        with stats_cols[2]:
            st.markdown(f"""
                <div class='stats-card'>
                    <div class='stats-number'>KES {metrics.get('max', 0):,.0f}</div>
                    <div class='stats-label'>📈 Highest</div>
                </div>
            """, unsafe_allow_html=True)
        
        with stats_cols[3]:
            st.markdown(f"""
                <div class='stats-card'>
                    <div class='stats-number'>{insights.get('market_diversity', 0)}</div>
                    <div class='stats-label'>🛒 Stores</div>
                </div>
            """, unsafe_allow_html=True)
        
        with stats_cols[4]:
            st.markdown(f"""
                <div class='stats-card'>
                    <div class='stats-number'>{len(all_results)}</div>
                    <div class='stats-label'>📦 Products</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Savings Highlight
        if savings > 0:
            st.markdown(f"<div class='savings-tag'>💡 Save up to KES {savings:,.0f} by choosing the best deal!</div>", unsafe_allow_html=True)
        
        # Advanced Visualizations
        viz_tabs = st.tabs(["📈 Price Analysis", "🎯 Market Share", "📊 Distribution", "💎 Comparison Table"])
        
        with viz_tabs[0]:
            # Price Comparison Chart with Enhanced Design
            df = pd.DataFrame(all_results)
            all_results.sort(key=lambda x: x["price"])
            
            fig = go.Figure()
            for marketplace in df['marketplace'].unique():
                market_data = df[df['marketplace'] == marketplace]
                fig.add_trace(go.Scatter(
                    x=market_data['name'].str[:20],
                    y=market_data['price'],
                    mode='markers+lines',
                    name=marketplace,
                    marker=dict(size=12, opacity=0.8),
                    line=dict(width=2),
                    hovertemplate='<b>%{x}</b><br>Price: KES %{y:,.0f}<extra></extra>'
                ))
            
            fig.update_layout(
                title=f"<b>Price Analysis: {product}</b>",
                xaxis_title="Products",
                yaxis_title="Price (KES)",
                height=450,
                template='plotly_white',
                hovermode='x unified',
                font=dict(family="Poppins, sans-serif", size=12),
                plot_bgcolor='rgba(240, 240, 245, 0.5)',
                paper_bgcolor='white',
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with viz_tabs[1]:
            # Market Share Analysis
            market_counts = pd.DataFrame(all_results)['marketplace'].value_counts()
            
            fig = go.Figure(data=[go.Pie(
                labels=market_counts.index,
                values=market_counts.values,
                hole=0.3,
                hovertemplate='<b>%{label}</b><br>Products: %{value}<extra></extra>',
                marker=dict(colors=['#667eea', '#764ba2', '#f093fb', '#59c4d8', '#ffc43d', '#ff6b6b', '#4ecdc4'])
            )])
            fig.update_layout(
                title=f"<b>Market Distribution ({len(market_counts)} stores)</b>",
                height=450,
                font=dict(family="Poppins, sans-serif", size=12),
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with viz_tabs[2]:
            # Price Distribution Analysis
            fig = go.Figure()
            prices = [r['price'] for r in all_results]
            
            fig.add_trace(go.Histogram(
                x=prices,
                nbinsx=30,
                name='Price Distribution',
                marker=dict(color='#667eea', opacity=0.8, line=dict(color='#764ba2', width=1)),
                hovertemplate='Price Range: KES %{x:,.0f}<br>Count: %{y}<extra></extra>'
            ))
            
            fig.add_vline(x=metrics['avg'], line_dash="dash", line_color="#059669", 
                         annotation_text=f"Avg: KES {metrics['avg']:,.0f}", annotation_position="top right")
            
            fig.update_layout(
                title=f"<b>Price Distribution Analysis</b>",
                xaxis_title="Price (KES)",
                yaxis_title="Frequency",
                height=450,
                template='plotly_white',
                font=dict(family="Poppins, sans-serif", size=12),
                plot_bgcolor='rgba(240, 240, 245, 0.5)',
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with viz_tabs[3]:
            # Advanced Comparison Table
            df_display = pd.DataFrame(all_results).head(20).copy()
            df_display['Price'] = df_display['price'].apply(lambda x: f"KES {x:,.0f}")
            df_display['Store'] = df_display['marketplace']
            df_display['Product'] = df_display['name'].str[:50]
            df_display = df_display[['Product', 'Store', 'Price', 'country']]
            df_display.columns = ['Product', 'Marketplace', 'Price', 'Country']
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Quick stats for top matches
            st.markdown("### 🏆 Top Deals Summary")
            top_3 = all_results[:3]
            cols = st.columns(3)
            for idx, product_item in enumerate(top_3):
                with cols[idx]:
                    st.metric(
                        f"#{idx+1} Deal",
                        f"KES {product_item['price']:,.0f}",
                        f"{product_item['marketplace']} • {product_item['name'][:30]}"
                    )
        
        # Enhanced Products Grid
        st.subheader("🛍️ Top Deals (Sorted by Price)")
        
        # Advanced filtering options
        st.markdown("### 🔍 Refine Results")
        filter_cols = st.columns(3)
        
        with filter_cols[0]:
            min_price = st.slider("Minimum Price (KES)", 0, int(metrics['max']), 0, format="KES %d")
        
        with filter_cols[1]:
            max_price = st.slider("Maximum Price (KES)", 0, int(metrics['max']), int(metrics['max']), format="KES %d")
        
        with filter_cols[2]:
            selected_stores = st.multiselect("Filter by Store", df['marketplace'].unique(), default=df['marketplace'].unique())
        
        # Apply filters
        filtered_results = [r for r in all_results if min_price <= r['price'] <= max_price and r['marketplace'] in selected_stores]
        
        if not filtered_results:
            st.warning("No products match your filters. Try adjusting the price range or selected stores.")
        else:
            st.info(f"✅ Showing {len(filtered_results)} of {len(all_results)} products")
            
            cols = st.columns(3)
            badge_colors = {
                "Kilimall": "#ff6b00", "Jumia": "#f68b1e", "Masoko": "#00a650",
                "Amazon": "#232f3e", "Alibaba": "#ff6a00", 
                "eBay": "#e53238", "AliExpress": "#e43225"
            }
            
            for idx, prod in enumerate(filtered_results[:12]):
                with cols[idx % 3]:
                    with st.container():
                        st.markdown("<div class='product-card'>", unsafe_allow_html=True)
                        
                        # Image with error handling
                        try:
                            if prod["image_url"] and prod["image_url"].startswith("http"):
                                st.image(prod["image_url"], width='stretch', use_column_width=True)
                            else:
                                st.image("https://via.placeholder.com/300?text=No+Image", width='stretch', use_column_width=True)
                        except:
                            st.image("https://via.placeholder.com/300?text=No+Image", width='stretch', use_column_width=True)
                        
                        # Marketplace Badge
                        badge_color = badge_colors.get(prod["marketplace"], "#667eea")
                        st.markdown(f"""
                            <span class='marketplace-badge' style='background-color: {badge_color};'>
                                {prod['marketplace']}
                            </span>
                            <span style='color: #64748b; font-size: 0.75rem; margin-left: 8px; display: inline-block;'>
                                📍 {prod.get('country', 'Unknown')}
                            </span>
                        """, unsafe_allow_html=True)
                        
                        # Product name
                        name = prod['name'][:45] + '...' if len(prod['name']) > 45 else prod['name']
                        st.markdown(f"<div style='font-weight: 700; color: #1e293b; margin: 12px 0; font-size: 0.95rem; line-height: 1.4;'>{name}</div>", unsafe_allow_html=True)
                        
                        # Price with comparison
                        st.markdown(f"<div class='price-tag'>KES {prod['price']:,.0f}</div>", unsafe_allow_html=True)
                        
                        # Best price badge
                        if prod['price'] == metrics.get('min', 0):
                            st.markdown("<div class='trust-badge'>⭐ Best Price</div>", unsafe_allow_html=True)
                        
                        # Savings indicator
                        savings_pct = ((metrics['avg'] - prod['price']) / metrics['avg'] * 100) if metrics['avg'] > 0 else 0
                        if savings_pct > 5:
                            st.markdown(f"<div style='color: #059669; font-size: 0.8rem; font-weight: 600; margin-top: 4px;'>💰 Save {savings_pct:.1f}% vs average</div>", unsafe_allow_html=True)
                        
                        # Currency info
                        st.markdown(f"<div style='color: #64748b; font-size: 0.75rem; margin: 6px 0;'>Currency: {prod.get('currency', 'KES')}</div>", unsafe_allow_html=True)
                        
                        # Buy button
                        st.link_button("🛒 View Deal →", prod["link"], use_container_width=True, type="primary")
                        
                        st.markdown("</div>", unsafe_allow_html=True)
        
        # Advanced Export Options
        st.markdown("---")
        st.markdown("### 📥 Export Results")
        
        exp_cols = st.columns(3)
        
        # CSV Export
        with exp_cols[0]:
            csv = pd.DataFrame(filtered_results).drop(columns=['image_url', 'link'], errors='ignore').to_csv(index=False).encode('utf-8')
            st.download_button(
                "📊 Export as CSV", 
                csv, 
                f"smartprocure_{product.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                use_container_width=True
            )
        
        # JSON Export
        with exp_cols[1]:
            json_data = json.dumps(filtered_results, default=str, indent=2).encode('utf-8')
            st.download_button(
                "🔗 Export as JSON",
                json_data,
                f"smartprocure_{product.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "application/json",
                use_container_width=True
            )
        
        # Excel Export
        with exp_cols[2]:
            df_export = pd.DataFrame(filtered_results)
            df_export = df_export.drop(columns=['image_url', 'link'], errors='ignore')
            excel_buffer = pd.ExcelWriter(f"smartprocure_{product.replace(' ', '_')}.xlsx", engine='openpyxl')
            df_export.to_excel(excel_buffer, sheet_name='Results', index=False)
            excel_buffer.close()
            st.markdown("💾 Export as Excel (Coming Soon - Premium Feature)")
        
    else:
        st.error("😞 No products found")
        st.markdown("""
        **Troubleshooting Tips:**
        - 🔤 Try simpler product names: "laptop" instead of "high-performance laptop"
        - 🛒 Enable more marketplaces in the sidebar for broader results
        - 🌐 Check your internet connection
        - ⚠️ Some international stores may have access restrictions
        - 💡 Try local Kenyan stores first (Kilimall, Jumia, Masoko)
        """)

# Advanced Footer with Analytics
st.markdown("""
<div class='footer'>
    <div class='footer-text'><b>🛒 SmartProcure AI v2.0</b> • Enterprise-Grade Marketplace Intelligence</div>
    <div class='footer-text' style='font-size: 0.8rem; color: #94a3b8;'>
        Advanced Features: Real-time Price Analytics • Market Comparison • Savings Optimization • Multi-Store Search
    </div>
    <div class='footer-text' style='font-size: 0.75rem; color: #cbd5e1;'>
        Supported Platforms: 🇰🇪 Kilimall, Jumia, Masoko • 🌍 Amazon, eBay, Alibaba, AliExpress • 📊 Price Trend Analysis
    </div>
    <div class='footer-text' style='font-size: 0.7rem; color: #94a3b8; margin-top: 12px;'>
        © 2024 SmartProcure AI | Privacy-First | No Cookies Stored | Real-Time Data • <span style='color: #667eea;'>✨ Powered by Advanced LLM</span>
    </div>
</div>
""", unsafe_allow_html=True)

