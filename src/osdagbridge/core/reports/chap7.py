# =============================================================================
# Chapter 7: Material Take-off & Quantity Summary
# =============================================================================
# Phase 3 Changes:
#   - Added longtable header repetition (\endfirsthead / \endhead)
#   - Added Chart 1: Structural Steel Quantity bar chart
#   - Added Chart 2: Concrete Volume vs Reinforcement Steel Weight chart
#   - Charts generated via chart_generator.py and embedded as LaTeX figures
# =============================================================================

import os
import logging

logger = logging.getLogger(__name__)


def ch7_quantities(input_dict, output_dict=None, temp_dir=None):
    """
    Generate Chapter 7 LaTeX content including BOM table and two material charts.

    Parameters
    ----------
    input_dict  : dict — merged inputs + quantities dict
    output_dict : dict — backend output_dict (used for chart data extraction)
    temp_dir    : str  — directory for temporary chart PNGs; if None charts are skipped
    """
    # ------------------------------------------------------------------
    # Generate charts if temp_dir is available
    # ------------------------------------------------------------------
    steel_chart_path = None
    matl_chart_path  = None
    if temp_dir:
        try:
            from osdagbridge.core.reports.chart_generator import generate_material_charts
            chart_results = generate_material_charts(input_dict, temp_dir)
            steel_chart_path = chart_results.get("steel_chart")
            matl_chart_path  = chart_results.get("matl_chart")
        except Exception as exc:
            logger.warning("Material chart generation failed: %s", exc)

    # ------------------------------------------------------------------
    # LaTeX figure helper
    # ------------------------------------------------------------------
    def _fig(path, caption, width=r"0.9\textwidth"):
        if path and os.path.exists(path):
            p = path.replace("\\", "/")
            return (
                r"\begin{figure}[H]" + "\n"
                r"\centering" + "\n"
                r"\includegraphics[width=" + width + "]{" + p + "}\n"
                r"\caption*{\small " + caption + "}\n"
                r"\end{figure}" + "\n"
            )
        return ""  # skip figure if not generated

    steel_fig_tex = _fig(
        steel_chart_path,
        r"\textbf{Figure 7.1 — Structural Steel Quantity by Component (MT)}"
    )
    matl_fig_tex = _fig(
        matl_chart_path,
        r"\textbf{Figure 7.2 — Concrete Volume vs Reinforcement Steel Weight}"
    )

    # ------------------------------------------------------------------
    # Bill of Materials table rows helper
    # ------------------------------------------------------------------
    def _q(key):
        v = input_dict.get(key, "N.A.")
        return str(v) if v else "N.A."

    return r"""
\chapter{Material Take-off \& Quantity Summary}
\label{ch:material-takeoff}

This chapter provides the complete bill of materials (BOM) for all primary
structural components of the bridge, including steel girders, cross bracing,
concrete deck slab, reinforcement steel, shear studs, and crash barriers.

\vspace{1em}
\begingroup
\setlength{\tabcolsep}{3.5pt}
\begin{longtable}{|C{1.0cm}|L{3.8cm}|C{2.6cm}|C{1.8cm}|C{1.8cm}|C{1.8cm}|C{1.8cm}|}
\caption{\textbf{Bill of Materials --- Steel, Concrete, and Reinforcement Quantities}}\\
\hline
\textbf{S.N.} & \textbf{Item Description} & \textbf{Volume Formula} & \textbf{Qty} &
\textbf{Total Vol.} & \textbf{Wt. (MT)} & \textbf{Total Wt. (MT)} \\[6pt]
\hline
\endfirsthead
\caption[]{\textbf{Bill of Materials (continued)}}\\
\hline
\textbf{S.N.} & \textbf{Item Description} & \textbf{Volume Formula} & \textbf{Qty} &
\textbf{Total Vol.} & \textbf{Wt. (MT)} & \textbf{Total Wt. (MT)} \\[6pt]
\hline
\endhead
\hline
\endfoot
\endlastfoot
1 & Structural Steel (IS 2062) for Girders & """ + _q("steel_girders_vol_formula") + r""" & """ + _q("steel_girders_qty") + r""" & """ + _q("steel_girders_vol_total") + r""" & """ + _q("steel_girders_wt_single") + r""" & """ + _q("steel_girders_wt_total") + r""" \\[4pt]
\hline
2(a) & Cross Bracing --- Top Chord & """ + _q("bracing_top_vol_formula") + r""" & """ + _q("bracing_top_qty") + r""" & """ + _q("bracing_top_vol_total") + r""" & """ + _q("bracing_top_wt_single") + r""" & """ + _q("bracing_top_wt_total") + r""" \\[4pt]
\hline
2(b) & Cross Bracing --- Bottom Chord & """ + _q("bracing_bot_vol_formula") + r""" & """ + _q("bracing_bot_qty") + r""" & """ + _q("bracing_bot_vol_total") + r""" & """ + _q("bracing_bot_wt_single") + r""" & """ + _q("bracing_bot_wt_total") + r""" \\[4pt]
\hline
2(c) & Cross Bracing --- Diagonal & """ + _q("bracing_diag_vol_formula") + r""" & """ + _q("bracing_diag_qty") + r""" & """ + _q("bracing_diag_vol_total") + r""" & """ + _q("bracing_diag_wt_single") + r""" & """ + _q("bracing_diag_wt_total") + r""" \\[4pt]
\hline
3 & Concrete (M40) for Deck Slab & """ + _q("concrete_deck_vol_formula") + r""" & """ + _q("concrete_deck_qty") + r""" & """ + _q("concrete_deck_vol_total") + r""" & """ + _q("concrete_deck_wt_single") + r""" & """ + _q("concrete_deck_wt_total") + r""" \\[4pt]
\hline
4 & Reinforcement Steel (Fe 500) & """ + _q("rebar_deck_vol_formula") + r""" & """ + _q("rebar_deck_qty") + r""" & """ + _q("rebar_deck_vol_total") + r""" & """ + _q("rebar_deck_wt_single") + r""" & """ + _q("rebar_deck_wt_total") + r""" \\[4pt]
\hline
5 & Shear Stud Connectors & """ + _q("shear_studs_vol_formula") + r""" & """ + _q("shear_studs_qty") + r""" & """ + _q("shear_studs_vol_total") + r""" & """ + _q("shear_studs_wt_single") + r""" & """ + _q("shear_studs_wt_total") + r""" \\[4pt]
\hline
6 & Crash Barrier & """ + _q("crash_barrier_vol_formula") + r""" & """ + _q("crash_barrier_qty") + r""" & """ + _q("crash_barrier_vol_total") + r""" & """ + _q("crash_barrier_wt_single") + r""" & """ + _q("crash_barrier_wt_total") + r""" \\[4pt]
\hline
\end{longtable}
\endgroup

\noindent\textit{Note: Weights computed using density of steel = 7850 kg/m\textsuperscript{3} and
concrete = 2500 kg/m\textsuperscript{3}. Quantities derived from final design geometry.}

\section{Structural Steel Quantity Chart}
\label{sec:steel-chart}

""" + steel_fig_tex + r"""
\noindent\textit{Figure 7.1 shows the structural steel weight distribution across the main girders,
cross bracing members, and end diaphragms (all units in metric tonnes, MT).}

\section{Concrete and Reinforcement Quantity Chart}
\label{sec:concrete-chart}

""" + matl_fig_tex + r"""
\noindent\textit{Figure 7.2 compares the concrete deck volume (m\textsuperscript{3}) against the
total reinforcement steel weight (MT) to assist with procurement and cost estimation.}
"""
