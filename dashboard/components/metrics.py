from dashboard.config import DARK_THEME


def metric_card(title, value, col):
    html = f"""
    <div style='background: linear-gradient(135deg, {DARK_THEME["card"]} 0%, #2a332a 100%); 
                border: 1px solid {DARK_THEME["secondary"]}; border-radius: 12px; padding: 20px; 
                box-shadow: 0 4px 12px rgba(0,0,0,0.3); border-left: 4px solid {DARK_THEME["accent"]};'>
        <h4 style='color: {DARK_THEME["text_secondary"]}; margin: 0 0 8px 0;'>{title}</h4>
        <h1 style='color: {DARK_THEME["accent"]}; margin: 0; font-size: 2.5rem;'>{value}</h1>
    </div>
    """
    col.markdown(html, unsafe_allow_html=True)
