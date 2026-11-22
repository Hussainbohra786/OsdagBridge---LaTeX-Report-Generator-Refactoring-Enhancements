# =============================================================================
# Chapter 3: Loads and Load Combinations
# Extracted from report_generator.py — DO NOT add business logic here.
# =============================================================================
# Phase 3 Changes:
#   - Separated Live Load table into Vehicle Live Load + Footway Load tables
#   - Added \endfirsthead / \endhead to all longtables for page-spanning headers
#   - Vehicle types dynamically read from UI input keys (no hardcoding)
# =============================================================================

from osdagbridge.core.utils.common import (
    KEY_CB_LOAD,
    KEY_LL_CUSTOM_VEHICLES,
    KEY_LL_FOOTPATH_PRESSURE_MODE,
    KEY_LL_FOOTPATH_PRESSURE_VALUE,
    KEY_LL_IRC_70R_BOGIE,
    KEY_LL_IRC_70R_TRACKED,
    KEY_LL_IRC_70R_WHEELED,
    KEY_LL_IRC_AA_TRACKED,
    KEY_LL_IRC_AA_WHEELED,
    KEY_LL_IRC_CLASS_A,
    KEY_LL_IRC_CLASS_FATIGUE,
    KEY_LL_IRC_CLASS_SV,
    KEY_MATERIAL_DECK_DENSITY,
    KEY_MATERIAL_GIRDER_DENSITY,
    KEY_PL_SELF_WEIGHT_FACTOR,
    KEY_RL_LOAD_VALUE,
    KEY_SL_DAMPING,
    KEY_SL_DEAD_LOAD_MODE,
    KEY_SL_DEAD_LOAD_VALUE,
    KEY_SL_HORIZONTAL_COEFF,
    KEY_SL_IMPORTANCE_FACTOR,
    KEY_SL_LIVE_LOAD_MODE,
    KEY_SL_LIVE_LOAD_VALUE,
    KEY_SL_SEISMIC_ZONE,
    KEY_SL_SOIL_TYPE,
    KEY_SL_SPECTRAL_COEFF,
    KEY_SL_TIME_PERIOD,
    KEY_SL_VERTICAL_COEFF,
    KEY_SL_ZONE_FACTOR,
    KEY_SPAN,
    KEY_TL_BRIDGE_TEMP_MAX,
    KEY_TL_BRIDGE_TEMP_MIN,
    KEY_TL_HIGHEST_MAX_TEMP,
    KEY_TL_LOWEST_MIN_TEMP,
    KEY_TL_TEMP_FALL,
    KEY_TL_TEMP_RISE,
    KEY_WC_LD_LANE_TABLE_COUNT,
    KEY_WC_MATERIAL,
    KEY_WC_THICKNESS,
    KEY_WL_AVG_EXPOSED_HEIGHT,
    KEY_WL_BASIC_WIND_SPEED,
    KEY_WL_HOURLY_MEAN_WIND,
    KEY_WL_HOURLY_WIND_PRESSURE,
    KEY_WL_LONGITUDINAL_WIND_FORCE,
    KEY_WL_TERRAIN_TYPE,
    KEY_WL_TRANSVERSE_WIND_FORCE,
    KEY_WL_VERTICAL_WIND_FORCE
)

from osdagbridge.core.reports.report_utils import _tex, _render_value


def _longtable_header(caption, header_row, continued=True):
    """Build standard longtable opening block with endfirsthead / endhead."""
    cont_cap = caption + " (continued)" if continued else caption
    return (
        r"\caption{\textbf{" + caption + r"}}\\" + "\n"
        r"\hline" + "\n"
        + header_row + "\n"
        r"\hline" + "\n"
        r"\endfirsthead" + "\n"
        r"\caption[]{\textbf{" + cont_cap + r"}}\\" + "\n"
        r"\hline" + "\n"
        + header_row + "\n"
        r"\hline" + "\n"
        r"\endhead" + "\n"
        r"\hline" + "\n"
        r"\endfoot" + "\n"
        r"\endlastfoot" + "\n"
    )


def ch3_loads(input_dict):
    # -----------------------------------------------------------------
    # 1. Identify active vehicle types from UI input keys (no hardcoding)
    # -----------------------------------------------------------------
    vehicle_data = []  # list of (name, load_key_or_None)

    if input_dict.get(KEY_LL_IRC_CLASS_A):
        vehicle_data.append({"name": "IRC Class A", "class": "Class A"})
    if input_dict.get(KEY_LL_IRC_70R_WHEELED):
        vehicle_data.append({"name": "IRC 70R (Wheeled)", "class": "70R Wheeled"})
    if input_dict.get(KEY_LL_IRC_70R_TRACKED):
        vehicle_data.append({"name": "IRC 70R (Tracked)", "class": "70R Tracked"})
    if input_dict.get(KEY_LL_IRC_AA_WHEELED):
        vehicle_data.append({"name": "IRC Class AA (Wheeled)", "class": "AA Wheeled"})
    if input_dict.get(KEY_LL_IRC_AA_TRACKED):
        vehicle_data.append({"name": "IRC Class AA (Tracked)", "class": "AA Tracked"})
    if input_dict.get(KEY_LL_IRC_CLASS_SV):
        vehicle_data.append({"name": "IRC Class SV", "class": "Class SV"})
    if input_dict.get(KEY_LL_IRC_70R_BOGIE):
        vehicle_data.append({"name": "IRC 70R (Bogie)", "class": "70R Bogie"})
    if input_dict.get(KEY_LL_IRC_CLASS_FATIGUE):
        vehicle_data.append({"name": "IRC Class Fatigue", "class": "Class Fatigue"})

    # Custom vehicles from UI
    custom = input_dict.get(KEY_LL_CUSTOM_VEHICLES)
    if custom and isinstance(custom, list):
        for c in custom:
            if isinstance(c, dict) and c.get("name"):
                vehicle_data.append({"name": c["name"], "class": "Custom",
                                     "load": c.get("load_kN", "")})
            elif isinstance(c, str):
                vehicle_data.append({"name": c, "class": "Custom"})

    # -----------------------------------------------------------------
    # 2. IRC 6 derived values
    # -----------------------------------------------------------------
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017

    span = input_dict.get(KEY_SPAN)
    span_m = None
    try:
        span_m = float(span) if span not in (None, "") else None
    except (ValueError, TypeError):
        pass

    lanes = input_dict.get(KEY_WC_LD_LANE_TABLE_COUNT)
    lanes_int = None
    try:
        lanes_int = int(lanes) if lanes not in (None, "") else None
    except (ValueError, TypeError):
        pass

    # Braking force (single value for the bridge based on lane count)
    braking_force_str = "N/A"
    braking_kN = None
    if lanes_int is not None:
        try:
            braking_t = IRC6_2017.cl_211_2_braking_force(lanes_int)
            braking_kN = braking_t * 9.81
            braking_force_str = f"{braking_kN:.2f} kN ({braking_t:.2f} t)"
        except Exception:
            pass

    # Centrifugal force — typically 0 for straight bridges (IRC 6 Cl. 212)
    centrifugal_str = "0.00 kN (Straight Bridge)"

    # -----------------------------------------------------------------
    # 3. Per-vehicle Impact Factor lookup
    # -----------------------------------------------------------------
    def _impact_str(veh_class):
        if span_m is None:
            return "N/A"
        try:
            if "A" in veh_class and "AA" not in veh_class:
                im = IRC6_2017.cl_208_2_impact_factor(span_m)
            else:
                im = IRC6_2017.cl_208_3_impact_factor(span_m)
            return f"{1.0 + im:.3f}"
        except Exception:
            return "N/A"

    def _braking_str(veh_class):
        """Return braking force string — same bridge-level value for all vehicles."""
        return braking_force_str

    # -----------------------------------------------------------------
    # 4. Build Vehicle Live Load table rows
    # -----------------------------------------------------------------
    if vehicle_data:
        veh_rows = []
        for vd in vehicle_data:
            name = vd.get("name", "")
            cls  = vd.get("class", "")
            # Load value: use custom load if provided, else "Per IRC 6"
            load_val = vd.get("load", "Per IRC 6")
            impact   = _impact_str(cls)
            braking  = _braking_str(cls)
            veh_rows.append(
                _tex(name) + r" & "
                + _tex(str(load_val)) + r" & "
                + _tex(impact) + r" & "
                + _tex(braking) + r" & "
                + _tex(centrifugal_str) + r" & kN \\[6pt]" + "\n"
                + r"\hline"
            )
        vehicle_rows_str = "\n".join(veh_rows)
    else:
        vehicle_rows_str = (
            r"\multicolumn{6}{|c|}{\textit{No vehicles selected}} \\[6pt]" + "\n"
            + r"\hline"
        )

    # -----------------------------------------------------------------
    # 5. Footway Load table values
    # -----------------------------------------------------------------
    fp_mode  = input_dict.get(KEY_LL_FOOTPATH_PRESSURE_MODE, "")
    fp_value = input_dict.get(KEY_LL_FOOTPATH_PRESSURE_VALUE, "")
    if str(fp_mode).strip().lower() in ("as per irc 6", "as per irc6", "automatic"):
        try:
            fp_intensity_val = IRC6_2017.cl_206_1_footway_load()
            fp_intensity_str = f"{fp_intensity_val:.3f}"
            fp_ref = "IRC 6 Cl. 206.1"
        except Exception:
            fp_intensity_str = "N/A"
            fp_ref = "IRC 6 Cl. 206.1"
    elif fp_value not in (None, ""):
        fp_intensity_str = str(fp_value)
        fp_ref = "User Defined"
    else:
        fp_intensity_str = "N/A"
        fp_ref = "---"

    # Footway dimensions from input (may not always be present)
    fp_width_str = _render_value(input_dict, "footway_width", " m") or "---"

    # -----------------------------------------------------------------
    # 6. Wind load values
    # -----------------------------------------------------------------
    vz_val = input_dict.get(KEY_WL_HOURLY_MEAN_WIND)
    pz_val = input_dict.get(KEY_WL_HOURLY_WIND_PRESSURE)
    if not vz_val or not pz_val:
        try:
            _vb  = input_dict.get(KEY_WL_BASIC_WIND_SPEED) or input_dict.get("wind_speed")
            _h   = input_dict.get(KEY_WL_AVG_EXPOSED_HEIGHT)
            _ter = {
                "Plain Terrain": "plain",
                "Terrain with Obstructions": "obstructed",
            }.get(str(input_dict.get(KEY_WL_TERRAIN_TYPE, "")).strip(), "plain")
            _res = IRC6_2017.table_12(float(_h), _ter, float(_vb))
            if not vz_val:
                vz_val = _res.get("Vz")
            if not pz_val:
                pz_val = _res.get("Pz")
        except Exception:
            pass
    vz_str = f"{float(vz_val):.2f} m/s" if vz_val not in (None, "") else "N/A"
    pz_str = f"{float(pz_val):.2f} N/m²" if pz_val not in (None, "") else "N/A"

    # -----------------------------------------------------------------
    # 7. Seismic load values
    # -----------------------------------------------------------------
    sl_zone_factor = input_dict.get(KEY_SL_ZONE_FACTOR)
    sl_spectral    = input_dict.get(KEY_SL_SPECTRAL_COEFF)
    sl_ah          = input_dict.get(KEY_SL_HORIZONTAL_COEFF)
    sl_av          = input_dict.get(KEY_SL_VERTICAL_COEFF)
    if not sl_ah or not sl_zone_factor:
        try:
            _zone = input_dict.get(KEY_SL_SEISMIC_ZONE) or input_dict.get("seismic_zone")
            _zmap = {"1": "I", "2": "II", "3": "III", "4": "IV", "5": "V"}
            _z    = str(_zone).strip().upper()
            if _z.isdigit():
                _z = _zmap.get(_z)
            _smap = {"Type I – Rocky or Hard": 1, "Type II – Medium Soil": 2,
                     "Type III – Soft Soil": 3}
            _st   = _smap.get(str(input_dict.get(KEY_SL_SOIL_TYPE, "")), 1)
            _tp   = input_dict.get(KEY_SL_TIME_PERIOD)
            _damp = input_dict.get(KEY_SL_DAMPING) or "5"
            _dl_v = input_dict.get(KEY_SL_DEAD_LOAD_VALUE)
            _ll_v = input_dict.get(KEY_SL_LIVE_LOAD_VALUE)
            _dead = float(_dl_v) if str(input_dict.get(KEY_SL_DEAD_LOAD_MODE, "")) == "Custom" and _dl_v else 0.0
            _live = float(_ll_v) if str(input_dict.get(KEY_SL_LIVE_LOAD_MODE, "")) == "Custom" and _ll_v else 0.0
            _res  = IRC6_2017.cl_218_5_1(
                zone=f"Zone {_z}", soil_type=_st,
                dead_load_kN=_dead, live_load_kN=_live,
                period_T=float(_tp) if _tp else None,
                damping_percent=float(_damp))
            if not sl_zone_factor:
                sl_zone_factor = _res.get("Z")
            if not sl_spectral:
                sl_spectral    = _res.get("Sa_g_adjusted")
            if not sl_ah:
                sl_ah          = _res.get("Ah")
            if not sl_av:
                sl_av          = round(_res.get("Ah", 0) * 2 / 3, 4)
        except Exception:
            pass

    def _sl(v, unit=""):
        return f"{float(v):.4f}{unit}" if v not in (None, "") else "N/A"

    # -----------------------------------------------------------------
    # 8. Temperature load values
    # -----------------------------------------------------------------
    tl_temp_min = tl_temp_max = tl_rise = tl_fall = "N/A"
    try:
        _tmax = input_dict.get(KEY_TL_HIGHEST_MAX_TEMP) or input_dict.get("shade_temp_max")
        _tmin = input_dict.get(KEY_TL_LOWEST_MIN_TEMP)  or input_dict.get("shade_temp_min")
        if _tmax and _tmin:
            _res    = IRC6_2017.cl_215_2_effective_bridge_temperature(
                          float(_tmax), float(_tmin), "metallic", False)
            _bt_min = _res.get("T_min", 0)
            _bt_max = _res.get("T_max", 0)
            _mean   = (_bt_max + _bt_min) / 2.0
            tl_temp_min = f"{_bt_min:.2f}"
            tl_temp_max = f"{_bt_max:.2f}"
            tl_rise     = f"{_bt_max - _mean:.2f}"
            tl_fall     = f"{_mean - _bt_min:.2f}"
    except Exception:
        pass

    # -----------------------------------------------------------------
    # 9. Load Combinations (dynamically from IRC 6)
    # -----------------------------------------------------------------
    _LOAD_LABEL_MAP = {
        "dead_load":         "DL",
        "surfacing":         "SIDL",
        "live_load":         "LL",
        "wind_load":         "WL",
        "thermal_load":      "TL",
        "vehicle_collision": "VC",
        "barge_impact":      "BI",
        "floating_bodies":   "FB",
        "seismic":           "EQ",
    }

    def _fmt_factors(factors):
        parts = []
        for load, val in factors.items():
            label = _LOAD_LABEL_MAP.get(load, load.upper())
            if isinstance(val, dict):
                add = val.get("adding")
                rel = val.get("relieving")
                add_s = f"{add:.2f}" if add is not None else "--"
                rel_s = f"{rel:.2f}" if rel is not None else "--"
                parts.append(f"{label}({add_s}/{rel_s})")
            else:
                if val is None:
                    continue
                parts.append(f"{label}({val:.2f})")
        return " + ".join(parts)

    uls_combos = IRC6_2017.uls_load_combinations()
    sls_combos = IRC6_2017.sls_load_combinations()
    lc_rows = []
    for i, combo in enumerate(uls_combos, start=1):
        cases = _fmt_factors(combo["factors"])
        lc_rows.append(
            f"ULS-{i:02d}" + r" & " + cases + r" \\[6pt]" + "\n"
            + r"\hline"
        )
    for i, combo in enumerate(sls_combos, start=1):
        cases = _fmt_factors(combo["factors"])
        lc_rows.append(
            f"SLS-{i:02d}" + r" & " + cases + r" \\[6pt]" + "\n"
            + r"\hline"
        )
    lc_rows_str = "\n".join(lc_rows)

    # Shared longtable header helper
    def _hdr2(caption, col1, col2):
        """Two-column table header block."""
        return _longtable_header(
            caption,
            r"\textbf{" + col1 + r"} & \textbf{" + col2 + r"} \\[6pt]",
        )

    return r"""
\chapter{Loads and Load Combinations}

This section summarises all loads applied to the bridge and the load
combinations considered for analysis and design per IRC~6:2017.

\vspace{1em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
""" + _longtable_header(
        "Dead Load --- Self Weight",
        r"\textbf{Parameter} & \textbf{Value} \\[6pt]",
    ) + r"""
\textnormal{Steel Self-Weight Applied} & """ + _render_value(input_dict, KEY_MATERIAL_GIRDER_DENSITY, r' kN/m\textsuperscript{3}') + r""" \\[6pt]
\hline
\textnormal{Concrete Deck Weight} & """ + _render_value(input_dict, KEY_MATERIAL_DECK_DENSITY, r' kN/m\textsuperscript{3}') + r""" \\[6pt]
\hline
\textnormal{Self-Weight Factor} & """ + _render_value(input_dict, KEY_PL_SELF_WEIGHT_FACTOR) + r""" \\[6pt]
\hline
\end{longtable}

\vspace{1em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
""" + _longtable_header(
        "Dead Load for Surfacing (DW)",
        r"\textbf{Parameter} & \textbf{Value} \\[6pt]",
    ) + r"""
\textnormal{Wearing Course Material} & """ + _render_value(input_dict, KEY_WC_MATERIAL) + r""" \\[6pt]
\hline
\textnormal{Wearing Course Thickness} & """ + _render_value(input_dict, KEY_WC_THICKNESS) + r""" mm \\[6pt]
\hline
\textnormal{Additional SIDL (Crash Barrier)} & """ + _render_value(input_dict, KEY_CB_LOAD) + r""" kN/m per barrier \\[6pt]
\hline
\textnormal{Railing Load} & """ + _render_value(input_dict, KEY_RL_LOAD_VALUE) + r""" kN/m\sdstar{} \\[6pt]
\hline
\end{longtable}

% ============================================================
% TABLE 3.3 — Vehicle Live Loads (separate table per vehicle)
% ============================================================
\vspace{1em}
\begin{longtable}{|L{3.5cm}|C{2.0cm}|C{2.5cm}|C{2.5cm}|C{2.8cm}|C{1.3cm}|}
""" + _longtable_header(
        "Vehicle Live Loads (LL) --- per IRC 6:2017",
        (r"\textbf{Vehicle Class} & \textbf{Load Value} & "
         r"\textbf{Impact Factor} & \textbf{Braking Force} & "
         r"\textbf{Centrifugal Force} & \textbf{Unit} \\[6pt]"),
    ) + vehicle_rows_str + r"""
\end{longtable}
\noindent\textit{Note: Impact factors per IRC~6 Cl.~208. Braking force per IRC~6 Cl.~211 based on number of lanes.}

% ============================================================
% TABLE 3.4 — Footway Load (separate table)
% ============================================================
\vspace{1em}
\begin{longtable}{|L{6.0cm}|C{4.5cm}|C{3.5cm}|}
""" + _longtable_header(
        "Footway Live Load (FWL) --- per IRC 6 Cl. 206",
        r"\textbf{Parameter} & \textbf{Value} & \textbf{Reference / Unit} \\[6pt]",
    ) + r"""
\textnormal{Footpath Width} & """ + fp_width_str + r""" & m \\[6pt]
\hline
\textnormal{Design Intensity} & """ + _tex(fp_intensity_str) + r""" & kN/m² \\[6pt]
\hline
\textnormal{Reference Clause} & """ + _tex(fp_ref) + r""" & --- \\[6pt]
\hline
\end{longtable}

\vspace{1em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
""" + _longtable_header(
        "Wind Load (WL) --- per IRC 6",
        r"\textbf{Parameter} & \textbf{Value} \\[6pt]",
    ) + r"""
\textnormal{Basic Wind Speed, Vb} & """ + _render_value(input_dict, "wind_speed", " m/s") + r""" [from Project Location] \\[6pt]
\hline
\textnormal{Terrain Type} & """ + _render_value(input_dict, KEY_WL_TERRAIN_TYPE) + r""" \\[6pt]
\hline
\textnormal{Average Exposed Height, H} & """ + _render_value(input_dict, KEY_WL_AVG_EXPOSED_HEIGHT, " m") + r""" \\[6pt]
\hline
\textnormal{Hourly Mean Wind Speed, Vz} & """ + _tex(vz_str) + r""" \\[6pt]
\hline
\textnormal{Hourly Wind Pressure, Pz} & """ + _tex(pz_str) + r""" \\[6pt]
\hline
\textnormal{Transverse Wind Force} & """ + _render_value(input_dict, KEY_WL_TRANSVERSE_WIND_FORCE, " kN") + r""" \\[6pt]
\hline
\textnormal{Longitudinal Wind Force} & """ + _render_value(input_dict, KEY_WL_LONGITUDINAL_WIND_FORCE, " kN") + r""" \\[6pt]
\hline
\textnormal{Vertical Wind Force} & """ + _render_value(input_dict, KEY_WL_VERTICAL_WIND_FORCE, " kN") + r""" \\[6pt]
\hline
\end{longtable}

\vspace{1em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
""" + _longtable_header(
        "Earthquake Load (EL) --- per IRC 6",
        r"\textbf{Parameter} & \textbf{Value} \\[6pt]",
    ) + r"""
\textnormal{Seismic Zone} & """ + _render_value(input_dict, "seismic_zone") + r""" [from Project Location] \\[6pt]
\hline
\textnormal{Zone Factor, Z} & """ + _render_value(input_dict, KEY_SL_ZONE_FACTOR) + r""" \\[6pt]
\hline
\textnormal{Importance Factor, I} & """ + _render_value(input_dict, KEY_SL_IMPORTANCE_FACTOR) + r""" \\[6pt]
\hline
\textnormal{Type of Soil} & """ + _render_value(input_dict, KEY_SL_SOIL_TYPE) + r""" \\[6pt]
\hline
\textnormal{Sa/g} & """ + _render_value(input_dict, KEY_SL_SPECTRAL_COEFF) + r""" \\[6pt]
\hline
\textnormal{Horizontal Seismic Coefficient, Ah} & """ + _render_value(input_dict, KEY_SL_HORIZONTAL_COEFF) + r""" \\[6pt]
\hline
\textnormal{Vertical Seismic Coefficient, Av} & """ + _render_value(input_dict, KEY_SL_VERTICAL_COEFF) + r""" \\[6pt]
\hline
\textnormal{Horizontal Seismic Force (longitudinal)} & --- kN \\[6pt]
\hline
\textnormal{Horizontal Seismic Force (transverse)} & --- kN \\[6pt]
\hline
\end{longtable}

\vspace{1em}
\begin{longtable}{|L{5.5cm}|p{10.0cm}|}
""" + _longtable_header(
        "Temperature Load (TL) --- per IRC 6",
        r"\textbf{Parameter} & \textbf{Value} \\[6pt]",
    ) + r"""
\textnormal{Maximum Shade Temperature} & """ + _render_value(input_dict, "shade_temp_max") + r""" $^\circ$C \\[6pt]
\hline
\textnormal{Minimum Shade Temperature} & """ + _render_value(input_dict, "shade_temp_min") + r""" $^\circ$C \\[6pt]
\hline
\textnormal{Effective Bridge Temp.\ Range} & """ + _tex(tl_temp_min) + r""" to """ + _tex(tl_temp_max) + r""" $^\circ$C \\[6pt]
\hline
\textnormal{Temperature Rise / Fall for Design} & +""" + _tex(tl_rise) + r""" $^\circ$C / \textminus{}""" + _tex(tl_fall) + r""" $^\circ$C \\[6pt]
\hline
\end{longtable}

\vspace{1em}
\begin{longtable}{|C{4.0cm}|p{11.5cm}|}
""" + _longtable_header(
        "Load Combinations (IRC 6:2017)",
        r"\textbf{Combination ID} & \textbf{Load Cases} \\[6pt]",
    ) + lc_rows_str + r"""
\end{longtable}

\noindent\textit{Note: All IRC~6 load combinations are auto-generated by OsdagBridge. User-defined custom combinations, if any, are appended.}
"""
