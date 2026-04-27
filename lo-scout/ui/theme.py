"""
UI theme module for lo-scout application.
Provides CSS styling with dark seductive theme.
"""


def get_css() -> str:
    """
    Generate complete CSS with dark seductive theme.
    
    Returns:
        CSS string for Streamlit rendering
    """
    return """
    <style>
    /* ===== CSS VARIABLES - Dark Seductive Theme ===== */
    :root {
        /* Primary Colors */
        --bg-primary: #0F0A1A;
        --bg-secondary: #1A1025;
        --bg-tertiary: #251535;
        --bg-card: #1E1230;
        
        /* Accent Colors */
        --accent-purple: #8B5CF6;
        --accent-purple-light: #A78BFA;
        --accent-purple-dark: #7C3AED;
        --accent-magenta: #EC4899;
        --accent-magenta-light: #F472B6;
        --accent-magenta-dark: #DB2777;
        
        /* Text Colors */
        --text-primary: #F5F3FF;
        --text-secondary: #C4B5FD;
        --text-muted: #8B7EC8;
        --text-link: #A78BFA;
        
        /* Border Colors */
        --border-primary: #3D2C5E;
        --border-hover: #8B5CF6;
        
        /* External Site Colors */
        --xvideos-color: #E8442F;
        --eporner-color: #009688;
        --sxyprn-color: #FF6B35;
        --xmovies-color: #4CAF50;
        
        /* Spacing */
        --spacing-xs: 4px;
        --spacing-sm: 8px;
        --spacing-md: 16px;
        --spacing-lg: 24px;
        --spacing-xl: 32px;
        
        /* Border Radius */
        --radius-sm: 4px;
        --radius-md: 8px;
        --radius-lg: 12px;
        --radius-xl: 16px;
        
        /* Shadows */
        --shadow-sm: 0 2px 4px rgba(0, 0, 0, 0.3);
        --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
        --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.5);
        --shadow-glow: 0 0 20px rgba(139, 92, 246, 0.3);
        
        /* Transitions */
        --transition-fast: 150ms ease-in-out;
        --transition-normal: 250ms ease-in-out;
        --transition-slow: 400ms ease-in-out;
    }
    
    /* ===== GLOBAL STYLES ===== */
    .stApp {
        background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 50%, var(--bg-primary) 100%);
        min-height: 100vh;
    }
    
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* ===== SIDEBAR STYLES ===== */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-primary) 100%);
        border-right: 1px solid var(--border-primary);
    }
    
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: var(--accent-purple-light);
        font-weight: 700;
    }
    
    /* Sidebar filter labels */
    section[data-testid="stSidebar"] label {
        color: var(--text-secondary) !important;
        font-size: 0.9rem;
        font-weight: 500;
    }
    
    /* Sidebar selectbox */
    section[data-testid="stSidebar"] .stSelectbox > div > div {
        background-color: var(--bg-tertiary) !important;
        border: 1px solid var(--border-primary) !important;
        border-radius: var(--radius-md) !important;
    }
    
    section[data-testid="stSidebar"] .stSelectbox > div > div:hover {
        border-color: var(--accent-purple) !important;
    }
    
    /* Sidebar sliders */
    section[data-testid="stSidebar"] .stSlider > div > div {
        background-color: var(--accent-purple) !important;
    }
    
    section[data-testid="stSidebar"] .stSlider span {
        color: var(--text-secondary) !important;
    }
    
    /* ===== PERFORMER CARD STYLES ===== */
    .performer-card {
        background: linear-gradient(145deg, var(--bg-card) 0%, var(--bg-tertiary) 100%);
        border: 1px solid var(--border-primary);
        border-radius: var(--radius-lg);
        padding: var(--spacing-md);
        margin-bottom: var(--spacing-lg);
        transition: all var(--transition-normal);
        overflow: hidden;
        position: relative;
    }
    
    .performer-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--accent-purple), var(--accent-magenta));
        opacity: 0;
        transition: opacity var(--transition-normal);
    }
    
    .performer-card:hover {
        border-color: var(--border-hover);
        transform: translateY(-4px);
        box-shadow: var(--shadow-lg), var(--shadow-glow);
    }
    
    .performer-card:hover::before {
        opacity: 1;
    }
    
    /* Image container */
    .img-box {
        width: 100%;
        height: 280px;
        overflow: hidden;
        border-radius: var(--radius-md);
        margin-bottom: var(--spacing-md);
        background: linear-gradient(135deg, var(--bg-tertiary) 0%, var(--bg-secondary) 100%);
        position: relative;
    }
    
    .img-box img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform var(--transition-slow);
    }
    
    .performer-card:hover .img-box img {
        transform: scale(1.05);
    }
    
    /* Placeholder for missing images */
    .img-placeholder {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, var(--bg-tertiary) 0%, var(--bg-secondary) 100%);
        color: var(--text-muted);
        font-size: 3rem;
    }
    
    /* Performer name */
    .performer-name {
        color: var(--text-primary);
        font-size: 1.1rem;
        font-weight: 600;
        text-align: center;
        margin: var(--spacing-sm) 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    /* ===== EXTERNAL SITE LINK BUTTONS ===== */
    .external-links {
        display: flex;
        gap: var(--spacing-xs);
        justify-content: center;
        flex-wrap: wrap;
        margin-top: var(--spacing-sm);
    }
    
    .tube-link {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 6px 12px;
        border-radius: var(--radius-sm);
        font-size: 0.75rem;
        font-weight: 700;
        text-decoration: none;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        transition: all var(--transition-fast);
        min-width: 40px;
    }
    
    .tube-link:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-sm);
        text-decoration: none;
    }
    
    /* Site-specific colors */
    .tube-link.xvideos {
        background: linear-gradient(135deg, var(--xvideos-color), #C63928);
        color: white !important;
    }
    .tube-link.xvideos:hover {
        background: linear-gradient(135deg, #F5503A, var(--xvideos-color));
        box-shadow: 0 4px 12px rgba(232, 68, 47, 0.4);
    }
    
    .tube-link.eporner {
        background: linear-gradient(135deg, var(--eporner-color), #00796B);
        color: white !important;
    }
    .tube-link.eporner:hover {
        background: linear-gradient(135deg, #26A69A, var(--eporner-color));
        box-shadow: 0 4px 12px rgba(0, 150, 136, 0.4);
    }
    
    .tube-link.sxyprn {
        background: linear-gradient(135deg, var(--sxyprn-color), #E55A2B);
        color: white !important;
    }
    .tube-link.sxyprn:hover {
        background: linear-gradient(135deg, #FF8555, var(--sxyprn-color));
        box-shadow: 0 4px 12px rgba(255, 107, 53, 0.4);
    }
    
    .tube-link.xmovies {
        background: linear-gradient(135deg, var(--xmovies-color), #388E3C);
        color: white !important;
    }
    .tube-link.xmovies:hover {
        background: linear-gradient(135deg, #66BB6A, var(--xmovies-color));
        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
    }
    
    /* ===== PAGINATION STYLES ===== */
    .pagination-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: var(--spacing-md);
        padding: var(--spacing-xl) 0;
    }
    
    .page-info {
        color: var(--text-secondary);
        font-size: 0.9rem;
        text-align: center;
    }
    
    .page-info span {
        color: var(--accent-purple-light);
        font-weight: 600;
    }
    
    .load-more-btn {
        background: linear-gradient(135deg, var(--accent-purple), var(--accent-magenta)) !important;
        color: white !important;
        border: none !important;
        padding: 12px 32px !important;
        border-radius: var(--radius-lg) !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        cursor: pointer !important;
        transition: all var(--transition-normal) !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .load-more-btn:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-glow) !important;
    }
    
    .load-more-btn:disabled {
        opacity: 0.5 !important;
        cursor: not-allowed !important;
        transform: none !important;
    }
    
    /* ===== LOADING SPINNER ===== */
    .loading-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: var(--spacing-xl) * 2;
        gap: var(--spacing-md);
    }
    
    .loading-spinner {
        width: 50px;
        height: 50px;
        border: 4px solid var(--border-primary);
        border-top: 4px solid var(--accent-purple);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .loading-text {
        color: var(--text-secondary);
        font-size: 1rem;
        text-align: center;
    }
    
    .loading-text span {
        animation: pulse 1.5s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    /* ===== FILTER BADGE ===== */
    .filter-badge {
        display: inline-flex;
        align-items: center;
        gap: var(--spacing-xs);
        background: var(--bg-tertiary);
        border: 1px solid var(--border-primary);
        border-radius: var(--radius-md);
        padding: 4px 12px;
        font-size: 0.8rem;
        color: var(--text-secondary);
        margin: var(--spacing-xs);
    }
    
    .filter-badge .badge-label {
        color: var(--accent-purple-light);
        font-weight: 600;
    }
    
    /* ===== RESPONSIVE GRID ===== */
    @media (max-width: 1200px) {
        .performer-grid {
            grid-template-columns: repeat(3, 1fr) !important;
        }
    }
    
    @media (max-width: 900px) {
        .performer-grid {
            grid-template-columns: repeat(2, 1fr) !important;
        }
    }
    
    @media (max-width: 600px) {
        .performer-grid {
            grid-template-columns: 1fr !important;
        }
        
        .img-box {
            height: 220px !important;
        }
        
        .external-links {
            gap: 4px;
        }
        
        .tube-link {
            padding: 5px 8px;
            font-size: 0.7rem;
        }
    }
    
    /* ===== TITLE STYLING ===== */
    .main-title {
        background: linear-gradient(90deg, var(--accent-purple-light), var(--accent-magenta-light));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: var(--spacing-lg);
        text-shadow: 0 0 40px rgba(139, 92, 246, 0.3);
    }
    
    .subtitle {
        color: var(--text-muted);
        font-size: 1rem;
        text-align: center;
        margin-top: calc(var(--spacing-lg) * -1);
        margin-bottom: var(--spacing-xl);
    }
    
    /* ===== STATUS MESSAGES ===== */
    .status-message {
        padding: var(--spacing-md);
        border-radius: var(--radius-md);
        margin-bottom: var(--spacing-lg);
        font-size: 0.9rem;
    }
    
    .status-success {
        background: rgba(76, 175, 80, 0.1);
        border: 1px solid rgba(76, 175, 80, 0.3);
        color: var(--text-secondary);
    }
    
    .status-error {
        background: rgba(232, 68, 47, 0.1);
        border: 1px solid rgba(232, 68, 47, 0.3);
        color: var(--text-secondary);
    }
    
    .status-info {
        background: rgba(139, 92, 246, 0.1);
        border: 1px solid rgba(139, 92, 246, 0.3);
        color: var(--text-secondary);
    }
    </style>
    """