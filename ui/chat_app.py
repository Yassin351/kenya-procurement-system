import streamlit as st
if not hasattr(st, '_is_running_with_streamlit'):
    st._is_running_with_streamlit = lambda: True
import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import random
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.world_scraper import search_products

# Page configuration
st.set_page_config(
    page_title="SmartProcure AI | Global Marketplace Intelligence",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
    }
    
    .tagline {
        color: #64748b;
        font-size: 1.1rem;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    
    .chat-container {
        background: #f8fafc;
        border-radius: 16px;
        padding: 24px;
        margin: 20px 0;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 12px 20px;
        border-radius: 20px 20px 4px 20px;
        margin: 8px 0;
        max-width: 75%;
        float: right;
        clear: both;
        font-weight: 500;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .ai-message {
        background: white;
        color: #1e293b;
        padding: 12px 20px;
        border-radius: 20px 20px 20px 4px;
        margin: 8px 0;
        max-width: 75%;
        float: left;
        clear: both;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .product-card {
        background: white;
        border-radius: 16px;
        padding: 20px;
        margin: 12px 0;
        border: 1px solid #e2e8f0;
        transition: all 0.3s ease;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .product-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 24px rgba(0,0,0,0.15);
        border-color: #667eea;
    }
    
    .price-tag {
        font-size: 1.75rem;
        font-weight: 700;
        color: #059669;
        letter-spacing: -0.02em;
    }
    
    .marketplace-badge {
        display: inline-flex;
        align-items: center;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        color: white;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .stats-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .stats-number {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
    }
    
    .stats-label {
        color: #64748b;
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    .sidebar-header {
        font-size: 0.875rem;
        font-weight: 600;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 12px;
    }
    
    .search-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .search-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    .feature-icon {
        font-size: 2rem;
        margin-bottom: 8px;
    }
    
    .trust-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #ecfdf5;
        color: #059669;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .savings-tag {
        background: #fef3c7;
        color: #d97706;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
        margin-top: 8px;
    }
    
    /* History Sidebar Styles */
    .history-item {
        background: white;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        border: 1px solid #e2e8f0;
        cursor: pointer;
        transition: all 0.2s ease;
        position: relative;
    }
    
    .history-item:hover {
        background: #f1f5f9;
        border-color: #667eea;
        transform: translateX(4px);
    }
    
    .history-item.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-color: #667eea;
    }
    
    .history-item.active .history-time,
    .history-item.active .history-preview {
        color: rgba(255,255,255,0.8);
    }
    
    .history-title {
        font-weight: 600;
        font-size: 0.9rem;
        margin-bottom: 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .history-time {
        font-size: 0.75rem;
        color: #64748b;
        margin-bottom: 4px;
    }
    
    .history-preview {
        font-size: 0.8rem;
        color: #94a3b8;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .new-chat-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 10px 16px;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
        width: 100%;
        margin-bottom: 16px;
        transition: all 0.3s ease;
    }
    
    .new-chat-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    .delete-btn {
        position: absolute;
        right: 8px;
        top: 50%;
        transform: translateY(-50%);
        background: transparent;
        border: none;
        color: inherit;
        cursor: pointer;
        opacity: 0;
        transition: opacity 0.2s;
        padding: 4px;
    }
    
    .history-item:hover .delete-btn {
        opacity: 1;
    }
    
    .history-item.active .delete-btn:hover {
        background: rgba(255,255,255,0.2);
        border-radius: 4px;
    }
    
    .empty-state {
        text-align: center;
        color: #94a3b8;
        padding: 40px 20px;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state variables
def init_session_state():
    defaults = {
        'chat_history': {},  # Store all chats: {chat_id: {title, messages, timestamp, results}}
        'current_chat_id': None,
        'selected_markets': ["Kilimall", "Jumia", "Amazon", "eBay"],
        'last_results': [],
        'messages': [],
        'search_history': []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

def create_new_chat():
    """Create a new chat session"""
    chat_id = str(uuid.uuid4())
    st.session_state.chat_history[chat_id] = {
        'id': chat_id,
        'title': 'New Search',
        'messages': [],
        'timestamp': datetime.now(),
        'results': [],
        'first_query': None
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
                # Switch to most recent chat
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
            # Update title based on first query
            chat['title'] = query[:30] + '...' if len(query) > 30 else query

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
    col1, col2 = st.columns([4, 1])
    with col1:
        user_input = st.text_input(
            "Type your request...",
            placeholder="e.g., I need a laptop under 50k from Amazon, or Find me cheap Nike shoes",
            label_visibility="collapsed"
        )
    with col2:
        submit_button = st.form_submit_button("🔍 Search", width='stretch')

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
        
        # Stats cards
        st.subheader("📊 Search Summary")
        stats_cols = st.columns(4)
        
        cheapest_price = min(r['price'] for r in all_results)
        avg_price = sum(r['price'] for r in all_results) / len(all_results)
        total_stores = len(set(r['marketplace'] for r in all_results))
        
        with stats_cols[0]:
            st.markdown(f"""
                <div class='stats-card'>
                    <div class='stats-number'>KES {cheapest_price:,.0f}</div>
                    <div class='stats-label'>💰 Best Price</div>
                </div>
            """, unsafe_allow_html=True)
        
        with stats_cols[1]:
            st.markdown(f"""
                <div class='stats-card'>
                    <div class='stats-number'>KES {avg_price:,.0f}</div>
                    <div class='stats-label'>📊 Average</div>
                </div>
            """, unsafe_allow_html=True)
        
        with stats_cols[2]:
            st.markdown(f"""
                <div class='stats-card'>
                    <div class='stats-number'>{total_stores}</div>
                    <div class='stats-label'>🛒 Stores</div>
                </div>
            """, unsafe_allow_html=True)
        
        with stats_cols[3]:
            st.markdown(f"""
                <div class='stats-card'>
                    <div class='stats-number'>{len(all_results)}</div>
                    <div class='stats-label'>📦 Products</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Price comparison chart
        st.subheader("📈 Price Comparison")
        df = pd.DataFrame(all_results)
        
        fig = go.Figure()
        for marketplace in df['marketplace'].unique():
            market_data = df[df['marketplace'] == marketplace]
            fig.add_trace(go.Scatter(
                x=market_data['name'],
                y=market_data['price'],
                mode='markers+lines',
                name=marketplace,
                marker=dict(size=12),
                line=dict(width=2)
            ))
        
        fig.update_layout(
            title=f"Price Analysis: {product}",
            xaxis_title="Product",
            yaxis_title="Price (KES)",
            height=400,
            template='plotly_white',
            hovermode='x unified'
        )
        st.plotly_chart(fig, width='stretch')
        
        # Products grid
        st.subheader("🛍️ Top Deals (Sorted by Price)")
        all_results.sort(key=lambda x: x["price"])
        
        # Calculate savings
        if len(all_results) > 1:
            savings = all_results[-1]['price'] - all_results[0]['price']
            st.markdown(f"<div class='savings-tag'>💡 Save up to KES {savings:,.0f} by choosing the best deal!</div>", unsafe_allow_html=True)
        
        cols = st.columns(3)
        badge_colors = {
            "Kilimall": "#ff6b00", "Jumia": "#f68b1e", "Masoko": "#00a650",
            "Amazon": "#232f3e", "Alibaba": "#ff6a00", 
            "eBay": "#e53238", "AliExpress": "#e43225"
        }
        
        for idx, prod in enumerate(all_results[:12]):
            with cols[idx % 3]:
                with st.container():
                    st.markdown("<div class='product-card'>", unsafe_allow_html=True)
                    
                    # Image with error handling
                    try:
                        if prod["image_url"] and prod["image_url"].startswith("http"):
                            st.image(prod["image_url"], width='stretch')
                        else:
                            st.image("https://via.placeholder.com/300?text=No+Image", width='stretch')
                    except:
                        st.image("https://via.placeholder.com/300?text=No+Image", width='stretch')
                    
                    # Badge
                    badge_color = badge_colors.get(prod["marketplace"], "#667eea")
                    st.markdown(f"""
                        <span class='marketplace-badge' style='background-color: {badge_color};'>
                            {prod['marketplace']}
                        </span>
                        <span style='color: #64748b; font-size: 0.8rem; margin-left: 8px;'>
                            {prod['country']}
                        </span>
                    """, unsafe_allow_html=True)
                    
                    # Product name
                    name = prod['name'][:45] + '...' if len(prod['name']) > 45 else prod['name']
                    st.markdown(f"<div style='font-weight: 600; color: #1e293b; margin: 8px 0; font-size: 0.95rem;'>{name}</div>", unsafe_allow_html=True)
                    
                    # Price
                    st.markdown(f"<div class='price-tag'>KES {prod['price']:,.0f}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='color: #64748b; font-size: 0.75rem;'>{prod['currency']}</div>", unsafe_allow_html=True)
                    
                    # Trust badge for best price
                    if prod['price'] == cheapest_price:
                        st.markdown("<div class='trust-badge'>⭐ Best Price</div>", unsafe_allow_html=True)
                    
                    # Buy button
                    st.link_button("🛒 View Deal →", prod["link"], width='stretch')
                    
                    st.markdown("</div>", unsafe_allow_html=True)
        
        # Export
        st.markdown("---")
        csv = df.to_csv(index=False).encode('utf-8')
        col1, col2 = st.columns([3, 1])
        with col2:
            st.download_button(
                "📥 Export Results", 
                csv, 
                f"smartprocure_{product.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                width='stretch'
            )
        
    else:
        st.error("😞 No products found")
        st.markdown("""
        **Suggestions:**
        - Try simpler terms: "laptop" instead of "high-performance laptop"
        - Enable more marketplaces in the sidebar
        - Check your internet connection
        - Global stores may block scrapers - try local Kenyan stores first
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #64748b; font-size: 0.875rem;'>
    <p>🛒 <strong>SmartProcure AI</strong> • Compare prices across 7+ global marketplaces • Save time & money</p>
    <p style='font-size: 0.75rem;'>Supported: Kilimall, Jumia, Masoko (Kenya) • Amazon, eBay (USA) • Alibaba, AliExpress (China)</p>
</div>
""", unsafe_allow_html=True)

