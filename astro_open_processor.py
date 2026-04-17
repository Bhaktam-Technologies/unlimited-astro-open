# unlimited-astro-open — Copyright (C) 2026 Bhaktam Technologies
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE and NOTICE in the project root for full terms.

"""Flask dispatcher for the PyJHora-backed Vedic astrology API.

The endpoint count grew from ~14 to ~50 once the expanded helpers landed; to
keep this file readable we use a small `endpoint(...)` decorator that handles
body parsing, validation, per-request config overrides, and response framing
uniformly. Each route body is now one line invoking its helper."""

import io
import os
import logging
import traceback
from functools import wraps

from flask import Flask, jsonify, request, send_file

from logger import logger as logger_mod

# Importing this module runs init_pyjhora_defaults() as a side-effect.
from helpers import (
    jhora_config,
    pyjhora_helper,
    advanced_helper,
    dashas_helper,
    panchanga_extras,
    transits_helper,
    vratha_helper,
    chart_image,
)
from helpers.validators import (
    ValidationError,
    extract_birth_params,
    extract_match_params,
    extract_session_config,
)

try:
    from flask_cors import CORS
except ImportError:  # pragma: no cover
    CORS = None


app = Flask(__name__)
app_logger = logger_mod.getLoggerForApp()

SERVICE_VERSION = "1.0.0"
SERVICE_NAME = "unlimited-astro-open"


# ---------------------------------------------------------------------------
# App configuration (env-driven)
# ---------------------------------------------------------------------------

def _truthy(v):
    return str(v).lower() in {"1", "true", "yes", "on"}


ALLOW_PUBLIC_ACCESS = _truthy(os.environ.get("ALLOW_PUBLIC_ACCESS", "0"))
ENABLE_CORS = _truthy(os.environ.get("ENABLE_CORS", "1"))
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
LOCALHOST_IPS = {"127.0.0.1", "::1"}

if ENABLE_CORS and CORS is not None:
    CORS(app, resources={r"/*": {"origins": CORS_ORIGINS}})


@app.before_request
def enforce_security():
    if ALLOW_PUBLIC_ACCESS:
        return None
    if request.remote_addr not in LOCALHOST_IPS:
        return jsonify({"status": -1, "message": "Forbidden"}), 403
    return None


# ---------------------------------------------------------------------------
# Response framing
# ---------------------------------------------------------------------------

def _ok(data=None, **extra):
    payload = {"status": 1}
    if data is not None:
        payload["data"] = data
    payload.update(extra)
    return jsonify(payload)


def _err(message, http_status=400, **extra):
    payload = {"status": -1, "message": message}
    payload.update(extra)
    return jsonify(payload), http_status


def endpoint(kind="birth"):
    """Decorator handling body parse → validation → session config → error framing.

    `kind` selects the validator:
      * "birth"  — standard birth-detail payload
      * "match"  — boy/girl nakshatra + pada
      * "none"   — free-form; no required fields
    The wrapped function receives validated params as kwargs.
    """

    extractors = {
        "birth": extract_birth_params,
        "match": extract_match_params,
        "none": lambda body: dict(body or {}),
    }

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                body = request.get_json(silent=True) or {}
                session_cfg = extract_session_config(body)
                if session_cfg:
                    jhora_config.set_session_config(**session_cfg)
                params = extractors[kind](body) if kind != "none" else (body or {})
                data = fn(params, body) if kind == "none" else fn(**params)
                response = {"data": data, "config": jhora_config.get_current_config()}
                if params and kind == "birth" and params.get("_tz_name"):
                    response["resolved_timezone"] = params["_tz_name"]
                return _ok(**response)
            except ValidationError as ve:
                return _err(str(ve), 400)
            except ValueError as ve:
                app_logger.warning("ValueError in %s: %s", fn.__name__, ve)
                return _err(str(ve), 400)
            except Exception as e:
                logging.exception("Exception in %s", fn.__name__)
                app_logger.error(
                    "Exception in %s: %s", fn.__name__,
                    "".join(traceback.format_exception(None, e, e.__traceback__)),
                )
                return _err(str(e), 500)
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Meta endpoints
# ---------------------------------------------------------------------------

@app.route("/")
def root():
    return f"{SERVICE_NAME} is running!"


@app.route("/version")
def version():
    try:
        import swisseph as swe
        swe_version = getattr(swe, "version", None)
    except Exception:
        swe_version = None
    try:
        import importlib.metadata as _md
        jhora_version = _md.version("PyJHora")
    except Exception:
        try:
            from jhora import _package_info
            jhora_version = getattr(_package_info, "version", None)
        except Exception:
            jhora_version = None
    return jsonify({
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "pyjhora": jhora_version,
        "swisseph": swe_version,
        "config": jhora_config.get_current_config(),
    })


@app.route("/source")
def source():
    return jsonify({
        "project": SERVICE_NAME,
        "license": "AGPL-3.0-or-later",
        "source": "https://github.com/Bhaktam-Technologies/unlimited-astro-open",
        "notice": "This service is offered under the GNU Affero General Public License v3.0. "
                  "You may obtain the Corresponding Source at the URL above."
    })


# ---------------------------------------------------------------------------
# Core PyJHora charts
# ---------------------------------------------------------------------------

@app.route("/jhora/rasi-chart", methods=["POST"])
@endpoint()
def jhora_rasi_chart(**p): return pyjhora_helper.get_rasi_chart(**p)


@app.route("/jhora/divisional-chart", methods=["POST"])
@endpoint()
def jhora_divisional_chart(**p):
    body = request.get_json(silent=True) or {}
    factor = body.get("divisional_chart_factor", 1)
    return pyjhora_helper.get_divisional_chart(divisional_chart_factor=int(factor), **p)


@app.route("/jhora/divisional-charts", methods=["POST"])
@endpoint()
def jhora_divisional_charts(**p): return pyjhora_helper.get_divisional_charts(**p)


@app.route("/jhora/custom-divisional-chart", methods=["POST"])
@endpoint()
def jhora_custom_divisional_chart(**p):
    body = request.get_json(silent=True) or {}
    factor = body.get("divisional_chart_factor")
    if factor is None:
        raise ValidationError("Missing field: divisional_chart_factor (1..300)")
    return pyjhora_helper.get_custom_divisional_chart(
        divisional_chart_factor=int(factor),
        chart_method=int(body.get("chart_method", 0)),
        base_rasi=body.get("base_rasi"),
        count_from_end_of_sign=bool(body.get("count_from_end_of_sign", False)),
        **p,
    )


@app.route("/jhora/mixed-chart", methods=["POST"])
@endpoint()
def jhora_mixed_chart(**p):
    body = request.get_json(silent=True) or {}
    varga1 = body.get("varga_factor_1")
    varga2 = body.get("varga_factor_2")
    if varga1 is None or varga2 is None:
        raise ValidationError("Missing fields: varga_factor_1, varga_factor_2")
    return pyjhora_helper.get_mixed_chart(
        varga_factor_1=int(varga1), varga_factor_2=int(varga2),
        chart_method_1=int(body.get("chart_method_1", 1)),
        chart_method_2=int(body.get("chart_method_2", 1)),
        **p,
    )


@app.route("/jhora/bhava-chart", methods=["POST"])
@endpoint()
def jhora_bhava_chart(**p):
    body = request.get_json(silent=True) or {}
    method = body.get("bhaava_madhya_method", body.get("bhava_madhya_method"))
    return pyjhora_helper.get_bhava_chart(
        bhava_madhya_method=int(method) if method is not None else None, **p,
    )


# ---------------------------------------------------------------------------
# Panchanga
# ---------------------------------------------------------------------------

@app.route("/jhora/panchanga", methods=["POST"])
@endpoint()
def jhora_panchanga(**p): return pyjhora_helper.get_panchanga(**p)


@app.route("/jhora/panchanga-extras", methods=["POST"])
@endpoint()
def jhora_panchanga_extras(**p): return panchanga_extras.get_panchanga_extras(**p)


@app.route("/jhora/muhurta", methods=["POST"])
@endpoint()
def jhora_muhurta(**p): return pyjhora_helper.get_muhurta_data(**p)


# ---------------------------------------------------------------------------
# Strengths and chart diagnostics
# ---------------------------------------------------------------------------

@app.route("/jhora/shad-bala", methods=["POST"])
@endpoint()
def jhora_shad_bala(**p): return pyjhora_helper.get_shad_bala(**p)


@app.route("/jhora/harsha-bala", methods=["POST"])
@endpoint()
def jhora_harsha_bala(**p): return pyjhora_helper.get_harsha_bala(**p)


@app.route("/jhora/bhava-bala", methods=["POST"])
@endpoint()
def jhora_bhava_bala(**p): return pyjhora_helper.get_bhava_bala(**p)


@app.route("/jhora/benefics-malefics", methods=["POST"])
@endpoint()
def jhora_benefics_malefics(**p): return pyjhora_helper.get_benefics_malefics(**p)


@app.route("/jhora/retrograde-combustion", methods=["POST"])
@endpoint()
def jhora_retrograde_combustion(**p): return pyjhora_helper.get_retrograde_combustion(**p)


@app.route("/jhora/graha-yudh", methods=["POST"])
@endpoint()
def jhora_graha_yudh(**p): return advanced_helper.get_graha_yudh(**p)


@app.route("/jhora/marana-karaka-sthana", methods=["POST"])
@endpoint()
def jhora_marana_karaka_sthana(**p):
    return advanced_helper.get_marana_karaka_sthana(**p)


# ---------------------------------------------------------------------------
# Advanced charts
# ---------------------------------------------------------------------------

@app.route("/jhora/kp-chart", methods=["POST"])
@endpoint()
def jhora_kp_chart(**p): return pyjhora_helper.get_kp_chart(**p)


@app.route("/jhora/ashtakavarga", methods=["POST"])
@endpoint()
def jhora_ashtakavarga(**p): return advanced_helper.get_ashtakavarga(**p)


@app.route("/jhora/arudhas", methods=["POST"])
@endpoint()
def jhora_arudhas(**p): return advanced_helper.get_arudhas(**p)


@app.route("/jhora/chara-karakas", methods=["POST"])
@endpoint()
def jhora_chara_karakas(**p): return advanced_helper.get_chara_karakas(**p)


@app.route("/jhora/upagrahas", methods=["POST"])
@endpoint()
def jhora_upagrahas(**p): return advanced_helper.get_upagrahas(**p)


@app.route("/jhora/special-lagnas", methods=["POST"])
@endpoint()
def jhora_special_lagnas(**p): return advanced_helper.get_special_lagnas(**p)


@app.route("/jhora/sphutas", methods=["POST"])
@endpoint()
def jhora_sphutas(**p): return advanced_helper.get_sphutas(**p)


@app.route("/jhora/yogas", methods=["POST"])
@endpoint()
def jhora_yogas(**p): return advanced_helper.get_yogas(**p)


@app.route("/jhora/raja-yogas", methods=["POST"])
@endpoint()
def jhora_raja_yogas(**p): return advanced_helper.get_raja_yogas(**p)


@app.route("/jhora/doshas", methods=["POST"])
@endpoint()
def jhora_doshas(**p): return advanced_helper.get_doshas(**p)


# ---------------------------------------------------------------------------
# Dashas
# ---------------------------------------------------------------------------

@app.route("/jhora/dashas/available", methods=["GET"])
def jhora_dashas_available():
    return _ok({"dashas": dashas_helper.available_dashas()})


@app.route("/jhora/dasha", methods=["POST"])
@endpoint()
def jhora_dasha(**p):
    body = request.get_json(silent=True) or {}
    dasha = body.get("dasha")
    if not dasha:
        raise ValidationError("Missing field: dasha")
    options = body.get("options") or {}
    depth = body.get("depth")
    if depth is not None:
        options.setdefault("depth", depth)
    return dashas_helper.run_dasha(dasha, options=options, **p)


# Convenience routes for the three most common dashas.
@app.route("/jhora/vimsottari-dasa", methods=["POST"])
@endpoint()
def jhora_vimsottari_dasa(**p): return pyjhora_helper.get_vimsottari_dasa(**p)


@app.route("/jhora/yogini-dasa", methods=["POST"])
@endpoint()
def jhora_yogini_dasa(**p): return pyjhora_helper.get_yogini_dasa(**p)


@app.route("/jhora/ashtottari-dasa", methods=["POST"])
@endpoint()
def jhora_ashtottari_dasa(**p): return pyjhora_helper.get_ashtottari_dasa(**p)


# ---------------------------------------------------------------------------
# Transits, Sahams, Tajaka, Eclipses
# ---------------------------------------------------------------------------

@app.route("/jhora/sahams", methods=["POST"])
@endpoint()
def jhora_sahams(**p):
    body = request.get_json(silent=True) or {}
    night = body.get("night_time_birth")
    return transits_helper.get_sahams(night_time_birth=night, **p)


@app.route("/jhora/annual-chart", methods=["POST"])
@endpoint()
def jhora_annual_chart(**p):
    body = request.get_json(silent=True) or {}
    years = body.get("years", 1)
    dcf = body.get("divisional_chart_factor", 1)
    return transits_helper.get_annual_chart(years=int(years),
                                            divisional_chart_factor=int(dcf), **p)


@app.route("/jhora/monthly-chart", methods=["POST"])
@endpoint()
def jhora_monthly_chart(**p):
    body = request.get_json(silent=True) or {}
    years = body.get("years", 1)
    months = body.get("months", 1)
    dcf = body.get("divisional_chart_factor", 1)
    return transits_helper.get_monthly_chart(
        years=int(years), months=int(months),
        divisional_chart_factor=int(dcf), **p,
    )


@app.route("/jhora/sixty-hour-chart", methods=["POST"])
@endpoint()
def jhora_sixty_hour_chart(**p):
    body = request.get_json(silent=True) or {}
    return transits_helper.get_sixty_hour_chart(
        years=int(body.get("years", 1)),
        months=int(body.get("months", 1)),
        sixty_hour_count=int(body.get("sixty_hour_count", 1)),
        divisional_chart_factor=int(body.get("divisional_chart_factor", 1)),
        **p,
    )


@app.route("/jhora/tajaka-yogas", methods=["POST"])
@endpoint()
def jhora_tajaka_yogas(**p): return transits_helper.get_tajaka_yogas(**p)


@app.route("/jhora/eclipses", methods=["POST"])
@endpoint()
def jhora_eclipses(**p):
    body = request.get_json(silent=True) or {}
    years = int(body.get("search_forward_years", 10))
    return transits_helper.get_eclipses(search_forward_years=years, **p)


# ---------------------------------------------------------------------------
# Vratha / festivals
# ---------------------------------------------------------------------------

@app.route("/jhora/vratha/types", methods=["GET"])
def vratha_types():
    return _ok(vratha_helper.list_vratha_types())


@app.route("/jhora/vratha/dates", methods=["POST"])
@endpoint()
def jhora_vratha_dates(**p):
    body = request.get_json(silent=True) or {}
    vtype = body.get("vratha_type")
    start = body.get("start_date")
    end = body.get("end_date")
    if not vtype or not start:
        raise ValidationError("Missing fields: vratha_type, start_date")
    return vratha_helper.get_vratha_dates(vtype, start, end, **p)


@app.route("/jhora/festivals/day", methods=["POST"])
@endpoint()
def jhora_festivals_day(**p):
    body = request.get_json(silent=True) or {}
    return vratha_helper.get_festivals_on_day(
        language=body.get("language", "en"),
        festival_name_contains=body.get("festival_name_contains"),
        **p,
    )


@app.route("/jhora/festivals/between", methods=["POST"])
@endpoint()
def jhora_festivals_between(**p):
    body = request.get_json(silent=True) or {}
    start = body.get("start_date")
    end = body.get("end_date")
    if not start or not end:
        raise ValidationError("Missing fields: start_date, end_date")
    return vratha_helper.get_festivals_between(
        start, end,
        language=body.get("language", "en"),
        festival_name_contains=body.get("festival_name_contains"),
        **p,
    )


@app.route("/jhora/tithi-pravesha", methods=["POST"])
@endpoint()
def jhora_tithi_pravesha(**p):
    body = request.get_json(silent=True) or {}
    year_number = body.get("year_number")
    if year_number is None:
        raise ValidationError("Missing field: year_number")
    return vratha_helper.get_tithi_pravesha(
        int(year_number),
        plus_or_minus_duration_in_days=int(body.get("plus_or_minus_duration_in_days", 30)),
        **p,
    )


# ---------------------------------------------------------------------------
# Match
# ---------------------------------------------------------------------------

@app.route("/jhora/ashtakoota-match", methods=["POST"])
def jhora_ashtakoota_match():
    try:
        body = request.get_json(silent=True) or {}
        session_cfg = extract_session_config(body)
        if session_cfg:
            jhora_config.set_session_config(**session_cfg)
        params = extract_match_params(body)
        data = pyjhora_helper.get_ashtakoota_match(**params)
        return _ok(data)
    except ValidationError as ve:
        return _err(str(ve), 400)
    except Exception as e:
        logging.exception("ashtakoota-match failed")
        return _err(str(e), 500)


# ---------------------------------------------------------------------------
# Complete horoscope (everything-in-one)
# ---------------------------------------------------------------------------

@app.route("/jhora/complete-horoscope", methods=["POST"])
@endpoint()
def jhora_complete_horoscope(**p): return pyjhora_helper.get_complete_horoscope(**p)


# ---------------------------------------------------------------------------
# Chart image rendering (PNG)
# ---------------------------------------------------------------------------

@app.route("/jhora/chart-image", methods=["POST"])
def jhora_chart_image():
    try:
        body = request.get_json(silent=True) or {}
        session_cfg = extract_session_config(body)
        if session_cfg:
            jhora_config.set_session_config(**session_cfg)
        params = extract_birth_params(body)
        chart_type = body.get("chart_type", "D1_Rasi")
        size = int(body.get("size", 600))

        if chart_type == "D1_Rasi":
            data = pyjhora_helper.get_rasi_chart(**params)
            title = "Rasi Chart (D1)"
        else:
            all_charts = pyjhora_helper.get_divisional_charts(**params)
            if chart_type not in all_charts:
                return _err(f"Unknown chart_type: {chart_type}. Available: {list(all_charts.keys())}")
            data = all_charts[chart_type]
            title = chart_type.replace("_", " ")

        png_bytes = chart_image.generate_chart_image(data, chart_name=title, size=size)
        return send_file(io.BytesIO(png_bytes),
                         mimetype="image/png",
                         download_name=f"{chart_type}.png")
    except ValidationError as ve:
        return _err(str(ve), 400)
    except Exception as e:
        logging.exception("chart-image failed")
        return _err(str(e), 500)


# ---------------------------------------------------------------------------
# Global 404 / 405 handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(_e):
    return _err("Not found", 404)


@app.errorhandler(405)
def method_not_allowed(_e):
    return _err("Method not allowed", 405)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5002)))
