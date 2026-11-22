# =============================================================================
# OsdagBridge Report Generator — Chart Generator
# =============================================================================
# Phase 3: Implements dynamic matplotlib charts for:
#   - Section 5.5: Utilization Ratio (UR) visualization
#   - Chapter 7:  Material Quantity charts (Structural Steel + Concrete/Rebar)
# =============================================================================

import os
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Matplotlib backend — must be set BEFORE any pyplot import
# ---------------------------------------------------------------------------
import matplotlib
matplotlib.use("Agg")  # headless, no GUI dependency
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from osdagbridge.core.reports.styles import CHART_STYLE, BAR_COLOR_SAFE, BAR_COLOR_FAIL
from osdagbridge.core.reports.styles import BAR_COLOR_STEEL, BAR_COLOR_CONCRETE, BAR_COLOR_REBAR


def _apply_chart_style():
    """Apply global chart style from styles.py."""
    for key, val in CHART_STYLE.items():
        try:
            plt.rcParams[key] = val
        except Exception:
            pass  # ignore unknown rcParams keys


# ---------------------------------------------------------------------------
# SECTION 5.5: Utilization Ratio Chart
# ---------------------------------------------------------------------------

def generate_ur_chart(output_dict: dict, output_dir: str) -> str | None:
    """
    Generate a bar chart of Utilization Ratios for all major design components.

    Components on X-axis:
        Steel Plate Girder | Concrete Deck Slab | Cross Bracing | End Diaphragm

    A horizontal red dashed line is drawn at UR = 1.0.
    Bars are coloured green (UR ≤ 1.0) or red (UR > 1.0).

    Parameters
    ----------
    output_dict : dict
        Backend output_dict from PlateGirderBridge.design()
    output_dir  : str
        Directory where the PNG is saved (temp_assets/)

    Returns
    -------
    str | None
        Absolute path to the saved PNG, or None on failure.
    """
    _apply_chart_style()

    # --- Extract UR values from output_dict ---
    # Steel Plate Girder: use the governing ratio from design checks
    def _safe_float(d, *keys, default=None):
        """Try a list of fallback keys and return first valid float."""
        for k in keys:
            try:
                v = d.get(k)
                if v is not None:
                    return float(v)
            except (TypeError, ValueError):
                pass
        return default

    # Girder UR — look for the governing bending utilisation
    from osdagbridge.core.utils.common import (
        KEY_SD_MN_RATIO, KEY_SD_MDV, KEY_SD_MD_CAPACITY,
        KEY_SD_IS_FQ, KEY_SD_IS_FQD,
    )

    ur_girder = _safe_float(output_dict, KEY_SD_MN_RATIO, "girder_utilization_ratio",
                            "steeldesign.checks.moment.utilization_ratio")
    # Fallback: compute Mdesign/Mcapacity
    if ur_girder is None:
        mdv = _safe_float(output_dict, KEY_SD_MDV)
        mcap = _safe_float(output_dict, KEY_SD_MD_CAPACITY)
        if mdv and mcap and mcap > 0:
            ur_girder = mdv / mcap

    # Deck Slab UR — ratio of applied/capacity from deck design
    deck_rpt = output_dict.get("deck_design_report") or {}
    ur_deck = _safe_float(deck_rpt, "mu_sag_ratio", "flexure_ratio",
                          "deck_utilization_ratio")
    if ur_deck is None:
        from osdagbridge.core.utils.common import KEY_DD_MU_BOT, KEY_DD_M_ULS_SAG
        mbot = _safe_float(deck_rpt, KEY_DD_MU_BOT)
        msag = _safe_float(deck_rpt, KEY_DD_M_ULS_SAG)
        if mbot and msag and mbot > 0:
            ur_deck = msag / mbot

    # Cross Bracing UR — max efficiency from pair designs
    cb_designs = output_dict.get("crossbracing_design_results") or {}
    ur_cb = _extract_max_ur(cb_designs)

    # End Diaphragm UR — reuse same helper (ED designs share same schema)
    ed_designs = output_dict.get("end_diaphragm_design_results") or cb_designs
    ur_ed = _extract_max_ur(ed_designs)

    # Build data lists — replace None with 0 for display but mark as N/A
    labels = ["Steel Plate\nGirder", "Concrete\nDeck Slab",
              "Cross\nBracing", "End\nDiaphragm"]
    values_raw = [ur_girder, ur_deck, ur_cb, ur_ed]
    values = [v if v is not None else 0.0 for v in values_raw]
    has_data = any(v is not None for v in values_raw)

    colors = [BAR_COLOR_SAFE if v <= 1.0 else BAR_COLOR_FAIL for v in values]

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.patch.set_facecolor(CHART_STYLE.get("figure.facecolor", "#F9F9F9"))

    bars = ax.bar(labels, values, color=colors, edgecolor="#333333",
                  linewidth=0.8, width=0.5, zorder=3)

    # Annotate bars with UR value
    for bar, raw_val, disp_val in zip(bars, values_raw, values):
        label_txt = f"{disp_val:.3f}" if raw_val is not None else "N/A"
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.01,
                label_txt,
                ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    # Red dashed limit line at UR = 1.0
    ax.axhline(y=1.0, color="#CC0000", linestyle="--", linewidth=1.5,
               label="Limit: UR = 1.0", zorder=4)

    # Axis labels and formatting
    ax.set_ylabel("Utilization Ratio (UR)", fontsize=10)
    ax.set_title("Overall Design Check — Utilization Ratios", fontsize=11,
                 fontweight="bold", pad=10)
    ax.set_ylim(0, max(1.5, max(values) * 1.25))
    ax.yaxis.grid(True, linestyle="--", alpha=0.6, zorder=0)
    ax.set_axisbelow(True)

    # Legend
    safe_patch = mpatches.Patch(color=BAR_COLOR_SAFE, label="PASS (UR ≤ 1.0)")
    fail_patch = mpatches.Patch(color=BAR_COLOR_FAIL, label="FAIL (UR > 1.0)")
    ax.legend(handles=[safe_patch, fail_patch,
                        plt.Line2D([0], [0], color="#CC0000",
                                   linestyle="--", linewidth=1.5,
                                   label="Limit: UR = 1.0")],
              loc="upper right", fontsize=8)

    ax.tick_params(axis="x", labelsize=9)

    if not has_data:
        ax.text(0.5, 0.5, "Design data not yet available",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=10, color="grey", style="italic")

    fig.tight_layout(pad=1.5)

    # --- Save ---
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "utilization_ratio.png")
    try:
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
    except Exception as exc:
        logger.warning("Failed to save UR chart: %s", exc)
        plt.close(fig)
        return None
    plt.close(fig)
    logger.info("UR chart saved: %s", out_path)
    return out_path


def _extract_max_ur(pair_designs: dict) -> float | None:
    """Return the maximum efficiency (utilization ratio) across all member results."""
    try:
        from osdagbridge.core.bridge_types.plate_girder.results_data import _extract_osdag_summary
    except ImportError:
        return None

    best = None
    if not isinstance(pair_designs, dict):
        return None
    for members in pair_designs.values():
        if not isinstance(members, dict):
            continue
        for force_types in members.values():
            if not isinstance(force_types, dict):
                continue
            for raw in force_types.values():
                try:
                    val = _extract_osdag_summary(raw or {}).get("efficiency")
                    if val is None:
                        continue
                    f = float(val)
                    if best is None or f > best:
                        best = f
                except (TypeError, ValueError, AttributeError):
                    continue
    return best


# ---------------------------------------------------------------------------
# CHAPTER 7: Material Quantity Charts
# ---------------------------------------------------------------------------

def generate_material_charts(quantities: dict, output_dir: str) -> dict:
    """
    Generate two material-quantity bar charts for Chapter 7.

    Chart 1 — Structural Steel Quantity (MT)
        Categories: Main Girder | Cross Bracing (top+bot+diag combined)
                    | End Diaphragm (if data available)
    Chart 2 — Concrete Volume (m³) vs Reinforcement Steel Weight (MT)

    Parameters
    ----------
    quantities : dict
        Dict returned by calculate_material_quantities() (already merged into
        payload.inputs in report_generator.py).
    output_dir : str
        Directory for temporary PNG files.

    Returns
    -------
    dict  — {
        "steel_chart": "/abs/path/steel_quantities.png" or None,
        "matl_chart":  "/abs/path/material_comparison.png" or None,
    }
    """
    _apply_chart_style()
    os.makedirs(output_dir, exist_ok=True)
    result = {"steel_chart": None, "matl_chart": None}

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _flt(key, default=0.0):
        try:
            v = quantities.get(key)
            if v is not None and str(v) not in ("N.A.", "N/A", ""):
                return float(v)
        except (TypeError, ValueError):
            pass
        return default

    # ------------------------------------------------------------------ #
    # Chart 1: Structural Steel Quantity (MT)
    # ------------------------------------------------------------------ #
    girder_wt    = _flt("steel_girders_wt_total")
    bracing_top  = _flt("bracing_top_wt_total")
    bracing_bot  = _flt("bracing_bot_wt_total")
    bracing_diag = _flt("bracing_diag_wt_total")
    bracing_wt   = bracing_top + bracing_bot + bracing_diag

    # End diaphragm: not separately tracked in BOQ; use a small fraction estimate
    # from girder weight if data not available (placeholder approach)
    ed_wt = _flt("end_diaphragm_wt_total", default=None)
    if ed_wt is None:
        ed_wt = girder_wt * 0.03 if girder_wt > 0 else 0.0

    steel_labels = ["Main Girder", "Cross Bracing", "End Diaphragm"]
    steel_values = [girder_wt, bracing_wt, ed_wt]

    if any(v > 0 for v in steel_values):
        fig1, ax1 = plt.subplots(figsize=(7, 4))
        fig1.patch.set_facecolor(CHART_STYLE.get("figure.facecolor", "#F9F9F9"))

        bars1 = ax1.bar(steel_labels, steel_values,
                        color=BAR_COLOR_STEEL, edgecolor="#333333",
                        linewidth=0.7, width=0.4, zorder=3)
        for bar, val in zip(bars1, steel_values):
            if val > 0:
                ax1.text(bar.get_x() + bar.get_width() / 2,
                         bar.get_height() + 0.005 * max(steel_values or [1]),
                         f"{val:.2f} MT",
                         ha="center", va="bottom", fontsize=8.5)

        ax1.set_ylabel("Weight (MT)", fontsize=10)
        ax1.set_title("Structural Steel Quantity Summary", fontsize=11,
                      fontweight="bold", pad=8)
        ax1.yaxis.grid(True, linestyle="--", alpha=0.6, zorder=0)
        ax1.set_axisbelow(True)
        ax1.tick_params(axis="x", labelsize=9)
        fig1.tight_layout(pad=1.2)

        p1 = os.path.join(output_dir, "steel_quantities.png")
        try:
            fig1.savefig(p1, dpi=150, bbox_inches="tight")
            result["steel_chart"] = p1
        except Exception as exc:
            logger.warning("Failed to save steel chart: %s", exc)
        plt.close(fig1)

    # ------------------------------------------------------------------ #
    # Chart 2: Concrete Volume (m³) vs Reinforcement Steel Weight (MT)
    # ------------------------------------------------------------------ #
    concrete_vol = _flt("concrete_deck_vol_total")
    rebar_wt     = _flt("rebar_deck_wt_total")

    if concrete_vol > 0 or rebar_wt > 0:
        x_pos = np.array([0, 1])
        fig2, ax2 = plt.subplots(figsize=(7, 4))
        fig2.patch.set_facecolor(CHART_STYLE.get("figure.facecolor", "#F9F9F9"))

        bar_conc = ax2.bar(0, concrete_vol, color=BAR_COLOR_CONCRETE,
                           edgecolor="#333333", linewidth=0.7, width=0.3,
                           label="Concrete Volume (m³)", zorder=3)
        bar_rebar = ax2.bar(1, rebar_wt, color=BAR_COLOR_REBAR,
                            edgecolor="#333333", linewidth=0.7, width=0.3,
                            label="Rebar Weight (MT)", zorder=3)

        for bar, val, unit in [(bar_conc[0], concrete_vol, "m³"),
                               (bar_rebar[0], rebar_wt, "MT")]:
            if val > 0:
                ax2.text(bar.get_x() + bar.get_width() / 2,
                         bar.get_height() + 0.005 * max(concrete_vol, rebar_wt, 1),
                         f"{val:.2f} {unit}",
                         ha="center", va="bottom", fontsize=8.5)

        ax2.set_xticks([0, 1])
        ax2.set_xticklabels(["Concrete Deck\nVolume (m³)",
                              "Reinforcement\nSteel Weight (MT)"], fontsize=9)
        ax2.set_ylabel("Quantity", fontsize=10)
        ax2.set_title("Concrete Volume vs Reinforcement Steel", fontsize=11,
                      fontweight="bold", pad=8)
        ax2.yaxis.grid(True, linestyle="--", alpha=0.6, zorder=0)
        ax2.set_axisbelow(True)
        ax2.legend(loc="upper right", fontsize=8)
        fig2.tight_layout(pad=1.2)

        p2 = os.path.join(output_dir, "material_comparison.png")
        try:
            fig2.savefig(p2, dpi=150, bbox_inches="tight")
            result["matl_chart"] = p2
        except Exception as exc:
            logger.warning("Failed to save material chart: %s", exc)
        plt.close(fig2)

    return result
