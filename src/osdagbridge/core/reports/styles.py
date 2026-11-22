# =============================================================================
# OsdagBridge Report Generator — Centralized Style System
# Single source of truth for all formatting, colors, and layout settings.
# =============================================================================
# Phase 3.6: Created as part of LaTeX Report Generator Refactoring
# All chapter files should import formatting constants exclusively from here.
# =============================================================================

# ---------------------------------------------------------------------------
# PAGE SETTINGS
# ---------------------------------------------------------------------------
# Used in the preamble geometry package call.
PAGE_SETTINGS = {
    "paper": "a4paper",
    "top": "25mm",
    "bottom": "30mm",
    "left": "20mm",
    "right": "20mm",
    "headheight": "15pt",
    "footskip": "15mm",
}

# ---------------------------------------------------------------------------
# TABLE SETTINGS
# ---------------------------------------------------------------------------
# Applied via LaTeX \setlength and \renewcommand in the preamble.
TABLE_SETTINGS = {
    "tabcolsep": "6pt",         # horizontal cell padding
    "arraystretch": "1.15",     # row height multiplier
    "arrayrulewidth": "0.5pt",  # table rule thickness
    "extrarowheight": "1pt",    # extra vertical space per row
    "LTpre": "0pt",             # space before longtable
    "LTpost": "8pt",            # space after longtable
    "needspace_rows": 5,        # min baseline skips before starting a table
}

# ---------------------------------------------------------------------------
# COLORS
# ---------------------------------------------------------------------------
COLORS = {
    "primary_green": "91B014",    # Osdag brand green
    "ur_safe": "2E8B57",          # Sea green — UR <= 1.0
    "ur_fail": "CC0000",          # Red — UR > 1.0
    "ur_limit_line": "CC0000",    # Red dashed line at UR = 1.0
    "chart_bg": "F9F9F9",         # Light chart background
    "header_bg": "E8F0D0",        # Light green table header background
    "text_dark": "1A1A1A",        # Near-black body text
}

# ---------------------------------------------------------------------------
# FONT SETTINGS
# ---------------------------------------------------------------------------
FONT_SETTINGS = {
    "document_font_size": "12pt",
    "line_stretch": "1.15",
    "caption_font": "bf",         # LaTeX font for caption label
    "caption_justify": "raggedright",
}

# ---------------------------------------------------------------------------
# CHART STYLE (matplotlib rcParams dict)
# ---------------------------------------------------------------------------
CHART_STYLE = {
    "figure.dpi": 150,
    "figure.facecolor": "#F9F9F9",
    "axes.facecolor": "#FFFFFF",
    "axes.edgecolor": "#333333",
    "axes.labelcolor": "#1A1A1A",
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "font.family": "DejaVu Sans",
    "axes.grid": True,
    "grid.color": "#DDDDDD",
    "grid.linestyle": "--",
    "grid.alpha": 0.7,
}

# Colors used in bar charts (bar fill for safe/fail UR)
BAR_COLOR_SAFE = "#2E8B57"
BAR_COLOR_FAIL = "#CC0000"
BAR_COLOR_STEEL = "#4472C4"   # blue — structural steel
BAR_COLOR_CONCRETE = "#ED7D31"  # orange — concrete
BAR_COLOR_REBAR = "#A5A5A5"   # grey — reinforcement

# ---------------------------------------------------------------------------
# HEADER / FOOTER CONFIGURATION (LaTeX strings, used in preamble())
# ---------------------------------------------------------------------------
FOOTER_LEFT = r"Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay"
FOOTER_RULE_COLOR = "osdagGreen"
HEAD_RULE_HEIGHT = "1pt"

# ---------------------------------------------------------------------------
# LONGTABLE HEADER BUILDER
# ---------------------------------------------------------------------------

def configure_document() -> str:
    """
    Return full document configuration preamble string including geometry,
    table settings, and font/line spacing settings.
    """
    return (
        f"\\usepackage[{build_geometry_options()}]{{geometry}}\n"
        f"{build_table_preamble_commands()}"
        f"\\setstretch{{{FONT_SETTINGS['line_stretch']}}}\n"
    )


def create_table_style(col_spec: str, tabcolsep: str = None, arraystretch: str = None) -> str:
    """
    Return LaTeX snippet to set local table formatting overrides before a table.
    """
    cmds = []
    if tabcolsep:
        cmds.append(f"\\setlength{{\\tabcolsep}}{{{tabcolsep}}}")
    if arraystretch:
        cmds.append(f"\\renewcommand{{\\arraystretch}}{{{arraystretch}}}")
    return "\n".join(cmds) + ("\n" if cmds else "")


def build_longtable_header(caption: str, header_row: str, col_spec: str) -> str:
    """
    Return the standard longtable opening block with proper repeated-header
    support (\\endfirsthead / \\endhead).

    Parameters
    ----------
    caption    : table caption text (without \\textbf wrapper — added here)
    header_row : LaTeX row string for column titles, e.g.
                 r"\textbf{Col A} & \textbf{Col B} \\[6pt]"
    col_spec   : column specification, e.g. "|L{4cm}|C{3cm}|"

    Returns
    -------
    str  — LaTeX longtable opening through \\endlastfoot
    """
    cap = r"\textbf{" + caption + r"}"
    cont_cap = r"\textbf{" + caption + r" (continued)}"
    return (
        r"\begin{longtable}{" + col_spec + "}\n"
        r"\caption{" + cap + r"}\\" + "\n"
        r"\hline" + "\n"
        + header_row + "\n"
        r"\hline" + "\n"
        r"\endfirsthead" + "\n"
        r"\caption[]{" + cont_cap + r"}\\" + "\n"
        r"\hline" + "\n"
        + header_row + "\n"
        r"\hline" + "\n"
        r"\endhead" + "\n"
        r"\hline" + "\n"
        r"\endfoot" + "\n"
        r"\endlastfoot" + "\n"
    )


def build_longtable_footer() -> str:
    """Return the standard longtable closing block."""
    return r"\end{longtable}" + "\n"


# ---------------------------------------------------------------------------
# PREAMBLE GEOMETRY BLOCK BUILDER
# ---------------------------------------------------------------------------

def build_geometry_options() -> str:
    """
    Return the geometry package option string for use in the preamble.
    Example output:
        a4paper, top=25mm, bottom=30mm, left=20mm, right=20mm, ...
    """
    ps = PAGE_SETTINGS
    return (
        f"{ps['paper']}, "
        f"top={ps['top']}, "
        f"bottom={ps['bottom']}, "
        f"left={ps['left']}, "
        f"right={ps['right']}, "
        f"headheight={ps['headheight']}, "
        f"footskip={ps['footskip']}"
    )


def build_table_preamble_commands() -> str:
    """
    Return LaTeX commands that apply TABLE_SETTINGS globally.
    Inserted once in the document preamble.
    """
    ts = TABLE_SETTINGS
    return (
        f"\\setlength{{\\tabcolsep}}{{{ts['tabcolsep']}}}\n"
        f"\\renewcommand{{\\arraystretch}}{{{ts['arraystretch']}}}\n"
        f"\\setlength{{\\LTpre}}{{{ts['LTpre']}}}\n"
        f"\\setlength{{\\LTpost}}{{{ts['LTpost']}}}\n"
        f"\\setlength{{\\arrayrulewidth}}{{{ts['arrayrulewidth']}}}\n"
        f"\\setlength{{\\extrarowheight}}{{{ts['extrarowheight']}}}\n"
        f"\\BeforeBeginEnvironment{{table}}{{\\needspace{{{ts['needspace_rows']}\\baselineskip}}}}\n"
        f"\\BeforeBeginEnvironment{{longtable}}{{\\needspace{{{ts['needspace_rows']}\\baselineskip}}}}\n"
    )
