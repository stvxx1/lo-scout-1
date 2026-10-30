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
        color: var(--text-primary);
    }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-track {
        background: var(--bg-primary);
    }
    ::-webkit-scrollbar-thumb {
        background: var(--bg-tertiary);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: var(--accent-purple);
    }
    
    /* ===== PERFORMER CARD STYLES ===== */
    .performer-card {
        background: rgba(30, 18, 48, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid var(--border-primary);
        border-radius: var(--radius-lg);
        padding: var(--spacing-md);
        margin-bottom: var(--spacing-lg);
        transition: all var(--transition-normal);
        overflow: hidden;
        position: relative;
        display: flex;
        flex-direction: column;
        height: 100%;
    }
    
    .performer-card:hover {
        border-color: var(--accent-purple);
        transform: translateY(-5px);
        box-shadow: var(--shadow-lg), var(--shadow-glow);
    }
    
    /* Info Overlay */
    .info-overlay {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(to top, rgba(15, 10, 26, 0.95), transparent);
        padding: 40px 15px 15px;
        transform: translateY(100%);
        transition: transform var(--transition-normal);
        color: var(--text-secondary);
        font-size: 0.8rem;
    }
    
    .performer-card:hover .info-overlay {
        transform: translateY(0);
    }
    
    .info-item {
        display: flex;
        justify-content: space-between;
        margin-bottom: 4px;
        border-bottom: 1px solid rgba(139, 92, 246, 0.1);
    }
    
    .info-label {
        color: var(--accent-purple-light);
        font-weight: 600;
    }

    /* Grid layout fixes */
    [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
        gap: 1.5rem;
    }
    
    /* Image container */
    .img-box {
        width: 100%;
        /* Freeones portraits are 350x466. Matching that ratio means the image
           is never cropped, and the grid does not shift while 48 lazy images
           stream in. */
        aspect-ratio: 350 / 466;
        height: auto;
        overflow: hidden;
        border-radius: var(--radius-md);
        margin-bottom: var(--spacing-md);
        background: linear-gradient(135deg, var(--bg-tertiary) 0%, var(--bg-secondary) 100%);
        position: relative;
    }
    
    .img-box img {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
        /* Keep faces in frame if the box is ever shorter than the source. */
        object-position: center top;
        transition: transform var(--transition-slow);
        z-index: 1;
    }
    
    .performer-card:hover .img-box img {
        transform: scale(1.05);
    }

    /* Initials tile painted behind every portrait. A failed load hides the
       <img> (see thumbnails.portrait_html) and reveals this, so a dead CDN
       URL degrades to a tinted monogram instead of a broken-image icon. */
    .img-fallback {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(150deg, var(--tint, var(--bg-tertiary)), var(--bg-secondary));
        color: rgba(245, 243, 255, 0.55);
        font-size: 2.4rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        user-select: none;
    }

    .img-box img.img-broken {
        display: none;
    }

    /* Clip panel thumbnails (ui/video_panel.py): 16:9, same treatment as the
       portrait tiles so the modal does not look like a different app. */
    .clip-thumb {
        display: block;
        aspect-ratio: 16 / 9;
        overflow: hidden;
        border-radius: var(--radius-sm);
        margin-bottom: var(--spacing-sm);
        background: var(--bg-tertiary);
        border: 1px solid var(--border-primary);
    }

    .clip-thumb img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
    }

    .clip-thumb:hover {
        border-color: var(--accent-purple);
    }

    /* Profile dialog (ui/profile_panel.py) */
    .profile-head {
        display: flex;
        gap: var(--spacing-md);
        align-items: flex-end;
        margin-bottom: var(--spacing-md);
    }

    .profile-portrait {
        width: 120px;
        aspect-ratio: 350 / 466;
        object-fit: cover;
        object-position: center top;
        border-radius: var(--radius-md);
        border: 1px solid var(--border-primary);
        flex-shrink: 0;
    }

    .profile-name {
        margin: 0;
        font-size: 1.6rem;
        line-height: 1.2;
    }

    .profile-source {
        color: var(--text-muted);
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .profile-stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: var(--spacing-sm);
        margin-bottom: var(--spacing-md);
    }

    .profile-stat {
        background: var(--bg-tertiary);
        border: 1px solid var(--border-primary);
        border-radius: var(--radius-sm);
        padding: 6px 10px;
    }

    .profile-stat-label {
        display: block;
        color: var(--text-muted);
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    .profile-stat-value {
        font-size: 0.9rem;
    }

    .profile-bio {
        color: var(--text-secondary);
        font-size: 0.9rem;
        line-height: 1.5;
        margin-bottom: var(--spacing-md);
    }

    .profile-aliases {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }

    .alias-chip {
        background: rgba(139, 92, 246, 0.15);
        border: 1px solid var(--border-primary);
        border-radius: 999px;
        padding: 2px 10px;
        font-size: 0.75rem;
        color: var(--text-secondary);
    }

    /* Similar-performer cells: portrait over name, sized to the dialog grid */
    .similar-head {
        display: flex;
        flex-direction: column;
        gap: 6px;
        margin-bottom: 6px;
    }

    .similar-portrait {
        width: 100%;
        aspect-ratio: 350 / 466;
        object-fit: cover;
        object-position: center top;
        border-radius: var(--radius-md);
        border: 1px solid var(--border-primary);
        background: var(--bg-tertiary);
    }

    .similar-portrait-empty {
        background: linear-gradient(135deg, var(--bg-tertiary) 0%, var(--bg-secondary) 100%);
    }

    .similar-name {
        color: var(--text-primary);
        font-weight: 600;
        font-size: 0.9rem;
        line-height: 1.3;
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
        /* Wrap instead of clipping: real names are long, and an ellipsis made
           two performers with the same prefix indistinguishable. The min-height
           keeps a one-line and a two-line card the same height. */
        white-space: normal;
        overflow-wrap: anywhere;
        line-height: 1.2;
        min-height: 2.4em;
    }

    /* Age · height · weight under the name. The min-height reserves the line
       whether the stats arrived or not, so a row of four buttons stays aligned
       when ThePornDB knows some performers and not others. */
    .performer-stats {
        color: var(--text-muted);
        font-size: 0.75rem;
        text-align: center;
        line-height: 1.2;
        margin: 0 0 var(--spacing-xs);
        min-height: 1.2em;
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
    
    /* ===== RESPONSIVE ADJUSTMENTS ===== */
    @media (max-width: 600px) {
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