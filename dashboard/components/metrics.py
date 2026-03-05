# dashboard/components/metrics.py
DARK_THEME = {
    "primary": "#2d5a2d",
    "secondary": "#4a7c4a",
    "accent": "#68a368",
    "bg": "#1a1f1a",
    "card": "#252a25",
    "text": "#e8f0e8",
    "text_secondary": "#b8c9b8"
}


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
