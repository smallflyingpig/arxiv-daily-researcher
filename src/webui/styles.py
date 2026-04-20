"""Custom CSS styles for the Streamlit config panel.

Design: Space-Age Science Magazine Configuration Journal
Aesthetic: Warm paper tones with elegant typography, matching
the Report Viewer's magazine-style interface. Like configuring
a sophisticated research instrument in a classic study.
"""

CUSTOM_CSS = """
<style>
/* ==================== FONTS ==================== */
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700;800;900&family=Libre+Baskerville:wght@400;700&family=DM+Sans:wght@400;500;600;700&family=Crimson+Pro:wght@400;600&display=swap');

:root {
    --ink-deep: #1a1f3c;
    --ink-medium: #2d3555;
    --paper-cream: #f5f0e6;
    --paper-warm: #ebe4d4;
    --paper-vellum: #faf8f3;
    --coral-fire: #e85d75;
    --coral-soft: #f28b9d;
    --gold-glint: #d4a574;
    --gold-bright: #e8c49a;
    --cyan-glow: #4ecdc4;
    --navy-shadow: #0d1321;
    --display-font: 'Playfair Display', serif;
    --body-font: 'Libre Baskerville', Georgia, serif;
    --ui-font: 'DM Sans', sans-serif;
    --reading-font: 'Crimson Pro', serif;
}

/* ==================== Global Background ==================== */
.stApp, [data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, var(--paper-vellum) 0%, var(--paper-cream) 15%, var(--paper-warm) 85%, var(--paper-cream) 100%);
}

.block-container {
    max-width: 1100px;
    margin: 0 auto;
    padding: 48px 32px;
}

/* ==================== Typography ==================== */
.main-header {
    font-family: var(--display-font);
    font-size: 2.6rem;
    font-weight: 700;
    color: var(--ink-deep);
    margin-top: 0;
    margin-bottom: 0.5rem;
    line-height: 1.2;
    position: relative;
}

.main-header::before {
    content: '◈';
    color: var(--coral-fire);
    margin-right: 0.5rem;
}

.sub-header {
    font-family: var(--ui-font);
    color: var(--ink-deep);
    font-size: 0.9rem;
    margin-bottom: 1.5rem;
    letter-spacing: 0.08em;
    border-left: 3px solid var(--gold-glint);
    padding-left: 1rem;
    opacity: 0.85;
}

/* ==================== Sidebar - Control Panel ==================== */
[data-testid="stSidebar"] {
    background: linear-gradient(135deg, var(--navy-shadow) 0%, var(--ink-deep) 40%, var(--ink-medium) 100%);
    border-right: 4px solid var(--gold-glint);
    min-width: 280px;
}

[data-testid="stSidebar"] * {
    font-family: var(--ui-font);
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-family: var(--display-font);
    color: var(--gold-bright) !important;
}

[data-testid="stSidebar"] [data-testid="stMarkdown"] p,
[data-testid="stSidebar"] [data-testid="stMarkdown"] li,
[data-testid="stSidebar"] [data-testid="stMarkdown"] span {
    color: var(--paper-cream) !important;
}

[data-testid="stSidebar"] hr {
    border-color: var(--gold-glint);
    margin: 1rem 0;
}

/* Sidebar buttons */
[data-testid="stSidebar"] button {
    font-family: var(--ui-font);
    background: transparent;
    border: 1px solid rgba(212, 165, 116, 0.6);
    color: var(--gold-bright) !important;
    border-radius: 4px;
    letter-spacing: 0.03em;
}

[data-testid="stSidebar"] button:hover {
    background: rgba(232, 93, 117, 0.25);
    border-color: var(--coral-fire);
    color: var(--paper-vellum) !important;
}

[data-testid="stSidebar"] button[kind="primary"] {
    background: linear-gradient(135deg, var(--coral-fire) 0%, var(--coral-soft) 100%);
    border: none;
    color: var(--paper-vellum) !important;
}

[data-testid="stSidebar"] button[kind="primary"]:hover {
    box-shadow: 0 0 15px rgba(232, 93, 117, 0.4);
}

/* Sidebar caption */
[data-testid="stSidebar"] .stCaption {
    color: var(--paper-cream) !important;
    font-size: 0.75rem;
    opacity: 0.9;
}

/* Sidebar file status indicators */
[data-testid="stSidebar"] [data-testid="stMarkdown"] p {
    color: var(--paper-cream) !important;
    opacity: 1;
}

/* Sidebar toggle button - HIGH VISIBILITY */
[data-testid="collapsedControl"] {
    background-color: var(--gold-bright) !important;
    border: 2px solid var(--coral-fire) !important;
    border-radius: 0 12px 12px 0 !important;
    box-shadow: 3px 3px 10px rgba(0,0,0,0.4) !important;
}

[data-testid="collapsedControl"] svg {
    color: var(--navy-shadow) !important;
    fill: var(--navy-shadow) !important;
}

[data-testid="collapsedControl"]:hover {
    background-color: var(--coral-fire) !important;
    box-shadow: 3px 3px 15px rgba(0,0,0,0.5) !important;
}

/* ==================== Tab Styling ==================== */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: transparent;
    border-bottom: 2px solid var(--gold-glint);
    padding-bottom: 8px;
}

.stTabs [data-baseweb="tab"] {
    font-family: var(--ui-font);
    font-weight: 600;
    color: var(--ink-medium);
    background: var(--paper-warm);
    border-radius: 4px 4px 0 0;
    padding: 12px 20px;
    border: 1px solid var(--paper-warm);
    border-bottom: none;
    transition: all 0.2s ease;
}

.stTabs [data-baseweb="tab"]:hover {
    color: var(--coral-fire);
    background: var(--paper-cream);
    border-color: var(--paper-cream);
}

.stTabs [aria-selected="true"] {
    background: var(--ink-deep);
    color: var(--gold-bright) !important;
    border: 1px solid var(--ink-deep);
    border-bottom: none;
}

/* ==================== Section Headers ==================== */
.section-title {
    font-family: var(--display-font);
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--ink-deep);
    margin-top: 1.5rem;
    margin-bottom: 0.8rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--coral-fire);
    display: flex;
    align-items: center;
}

.section-title::before {
    content: '◆';
    color: var(--coral-fire);
    margin-right: 0.5rem;
    font-size: 0.8em;
}

/* ==================== Hint Text ==================== */
.hint-text {
    font-family: var(--reading-font);
    color: var(--ink-deep);
    font-size: 0.85rem;
    margin-top: -0.4rem;
    margin-bottom: 1rem;
    padding-left: 1.2rem;
    border-left: 2px dashed var(--gold-glint);
    line-height: 1.6;
    opacity: 0.95;
}

/* ==================== Form Elements ==================== */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div {
    font-family: var(--ui-font);
    border-radius: 4px;
    background: var(--paper-vellum);
    border: 1px solid var(--gold-glint);
    color: var(--ink-deep);
    transition: all 0.2s ease;
}

.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: var(--coral-fire);
    box-shadow: 0 0 0 2px rgba(232, 93, 117, 0.2);
    outline: none;
}

/* Labels - more visible */
.stTextInput label,
.stNumberInput label,
.stSelectbox label,
.stCheckbox label,
.stToggle label,
.stSlider label {
    font-family: var(--ui-font);
    color: var(--ink-deep);
    font-size: 0.9rem;
    font-weight: 600;
    opacity: 1;
}

/* Input placeholder */
.stTextInput input::placeholder,
.stNumberInput input::placeholder {
    color: var(--ink-medium);
    opacity: 0.7;
}

/* Checkbox */
.stCheckbox {
    font-family: var(--ui-font);
}

/* ==================== Selectbox ==================== */
[data-baseweb="select"] {
    font-family: var(--ui-font);
}

[data-baseweb="select"] > div {
    background: var(--paper-vellum);
    border: 1px solid var(--gold-glint);
    color: var(--ink-deep);
}

[data-baseweb="select"] > div:hover {
    border-color: var(--coral-fire);
}

/* ==================== Status Messages ==================== */
.stSuccess {
    font-family: var(--ui-font);
    background: rgba(212, 165, 116, 0.15);
    border: 1px solid var(--gold-glint);
    color: var(--ink-deep);
    border-radius: 4px;
    font-weight: 500;
}

.stSuccess::before {
    content: '✓ ';
    color: var(--coral-fire);
}

.stError {
    font-family: var(--ui-font);
    background: rgba(232, 93, 117, 0.15);
    border: 1px solid var(--coral-fire);
    color: var(--ink-deep);
    border-radius: 4px;
    font-weight: 500;
}

.stError::before {
    content: '✗ ';
}

.stWarning {
    font-family: var(--ui-font);
    background: rgba(212, 165, 116, 0.2);
    border: 1px solid var(--gold-bright);
    color: var(--ink-deep);
    border-radius: 4px;
    font-weight: 500;
}

.stWarning::before {
    content: '⚠ ';
}

/* ==================== Button Styling ==================== */
.stButton button {
    font-family: var(--ui-font);
    border-radius: 4px;
    border: 1px solid var(--gold-glint);
    background: var(--paper-vellum);
    color: var(--ink-deep);
    transition: all 0.2s ease;
}

.stButton button:hover {
    border-color: var(--coral-fire);
    color: var(--coral-fire);
    background: var(--paper-cream);
}

.stButton button[kind="primary"] {
    background: linear-gradient(135deg, var(--coral-fire) 0%, var(--coral-soft) 100%);
    border: none;
    color: var(--paper-vellum);
}

.stButton button[kind="primary"]:hover {
    box-shadow: 0 0 15px rgba(232, 93, 117, 0.4);
}

/* ==================== Expander ==================== */
[data-testid="stExpander"] {
    background: var(--paper-vellum);
    border: 1px solid var(--gold-glint);
    border-radius: 4px;
    margin-bottom: 1rem;
}

[data-testid="stExpander"] summary {
    font-family: var(--ui-font);
    font-weight: 600;
    color: var(--ink-deep);
    padding: 12px 16px;
}

[data-testid="stExpander"] summary:hover {
    color: var(--coral-fire);
}

[data-testid="stExpander"] summary::before {
    content: '▸';
    color: var(--coral-fire);
    margin-right: 0.5rem;
}

/* ==================== Dataframe ==================== */
[data-testid="stDataFrame"] table {
    background: var(--paper-vellum);
    border: 1px solid var(--gold-glint);
}

[data-testid="stDataFrame"] th {
    background: var(--ink-deep);
    color: var(--gold-bright);
    border-bottom: 2px solid var(--coral-fire);
    font-family: var(--ui-font);
}

[data-testid="stDataFrame"] td {
    color: var(--ink-deep);
    border-bottom: 1px solid var(--paper-warm);
}

/* ==================== Divider ==================== */
hr {
    border: none;
    height: 2px;
    background: linear-gradient(90deg, transparent 0%, var(--coral-fire) 20%, var(--gold-glint) 80%, transparent 100%);
    margin: 2rem 0;
}

/* ==================== Scrollbar ==================== */
::-webkit-scrollbar {
    width: 10px;
    height: 10px;
}

::-webkit-scrollbar-track {
    background: var(--paper-warm);
}

::-webkit-scrollbar-thumb {
    background: var(--coral-fire);
    border-radius: 5px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--coral-soft);
}

/* ==================== Code Blocks ==================== */
code, pre {
    font-family: var(--ui-font);
    background: var(--paper-warm);
    border: 1px solid var(--gold-glint);
    color: var(--ink-deep);
    padding: 2px 6px;
    border-radius: 3px;
}

/* ==================== Toggle ==================== */
.stToggle {
    font-family: var(--ui-font);
}

/* ==================== Footer ==================== */
footer {
    font-family: var(--ui-font);
    color: var(--ink-medium);
}
</style>
"""