# astro-wrapper — Copyright (C) 2026 Bhaktam Technologies
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE and NOTICE in the project root for full terms.


import io
import os
import logging
import traceback
from functools import wraps

from flask import Flask, jsonify, request, send_file

from logger import logger as logger_mod

from helpers import (
    jhora_config,
    pyjhora_helper,
    advanced_helper,
    kundali_extras,
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
SERVICE_NAME = "astro-wrapper"


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
        "source": "https://github.com/Bhaktam-Technologies/astro-wrapper",
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

@app.route("/jhora/chalit-table", methods=["POST"])
@endpoint()
def jhora_chalit_table(**p):
    body = request.get_json(silent=True) or {}
    method = body.get("bhaava_madhya_method", body.get("bhava_madhya_method"))
    return pyjhora_helper.get_chalit_table(
        bhava_madhya_method=int(method) if method is not None else None, **p,
    )


@app.route("/jhora/bhav-madhya-chart", methods=["POST"])
@endpoint()
def jhora_bhav_madhya_chart(**p):
    body = request.get_json(silent=True) or {}
    method = body.get("bhaava_madhya_method", body.get("bhava_madhya_method"))
    return pyjhora_helper.get_bhav_madhya_chart(
        bhava_madhya_method=int(method) if method is not None else None, **p,
    )


@app.route("/jhora/moon", methods=["POST"])
@endpoint()
def jhora_moon(**p): return pyjhora_helper.get_moon_data(**p)


@app.route("/jhora/panchanga", methods=["POST"])
@endpoint()
def jhora_panchanga(**p): return pyjhora_helper.get_panchanga(**p)


@app.route("/jhora/shad-bala", methods=["POST"])
@endpoint()
def jhora_shad_bala(**p): return pyjhora_helper.get_shad_bala(**p)





@app.route("/jhora/bhava-bala", methods=["POST"])
@endpoint()
def jhora_bhava_bala(**p): return pyjhora_helper.get_bhava_bala(**p)



@app.route("/jhora/retrograde-combustion", methods=["POST"])
@endpoint()
def jhora_retrograde_combustion(**p): return advanced_helper.get_retrograde_combustion(**p)


@app.route("/jhora/graha-yudh", methods=["POST"])
@endpoint()
def jhora_graha_yudh(**p): return advanced_helper.get_graha_yudh(**p)


@app.route("/jhora/kp-chart", methods=["POST"])
@endpoint()
def jhora_kp_chart(**p): return pyjhora_helper.get_kp_chart(**p)


@app.route("/jhora/ashtakavarga", methods=["POST"])
@endpoint()
def jhora_ashtakavarga(**p): return advanced_helper.get_ashtakavarga(**p)



@app.route("/jhora/karakamsa", methods=["POST"])
@endpoint()
def jhora_karakamsa(**p): return advanced_helper.get_karakamsa(**p)



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


@app.route("/jhora/friendship", methods=["POST"])
@endpoint()
def jhora_friendship(**p): return kundali_extras.get_friendship(**p)


@app.route("/jhora/avakhada-chakra", methods=["POST"])
@endpoint()
def jhora_avakhada_chakra(**p): return kundali_extras.get_avakhada_chakra(**p)


@app.route("/jhora/chart-image", methods=["POST"])
def jhora_chart_image():
    try:
        body = request.get_json(silent=True) or {}
        session_cfg = extract_session_config(body)
        if session_cfg:
            jhora_config.set_session_config(**session_cfg)
        chart_type = body.get("chart_type", "D1_Rasi")
        size = int(body.get("size", 600))
        label_mode = str(body.get("label_mode", "degrees")).lower()
        style = str(body.get("style", "north")).lower()

        # Accept pre-computed planets array (e.g. from /jhora/moon)
        planets_input = body.get("planets")
        if planets_input is not None:
            if not isinstance(planets_input, list):
                return _err("'planets' must be an array")
            if label_mode not in {"degrees", "sign_number", "both", "none"}:
                label_mode = "sign_number"
            png_bytes = chart_image.generate_chart_image(
                planets_input, chart_name=body.get("title", "Moon Chart"),
                size=size, label_mode=label_mode, style=style,
            )
            return send_file(io.BytesIO(png_bytes),
                             mimetype="image/png",
                             download_name="moon_chart.png")

        params = extract_birth_params(body)

        # Bhava/Chalit takes a separate renderer and its own label_mode vocabulary.
        if chart_type in {"Bhava", "Chalit", "bhava", "chalit"}:
            if label_mode == "degrees":
                label_mode = "house"
            if label_mode not in {"house", "cusp", "none"}:
                return _err(
                    f"Unknown label_mode for Bhava chart: {label_mode}. "
                    "Use one of: house, cusp, none"
                )
            method = body.get("bhaava_madhya_method", body.get("bhava_madhya_method"))
            bhava = pyjhora_helper.get_bhava_chart(
                bhava_madhya_method=int(method) if method is not None else None,
                **params,
            )
            png_bytes = chart_image.generate_bhava_chart(
                bhava, title="Bhava / Chalit Chart", size=size, label_mode=label_mode, style=style,
            )
            return send_file(io.BytesIO(png_bytes),
                             mimetype="image/png",
                             download_name="bhava_chart.png")

        if label_mode not in {"degrees", "sign_number", "both", "none"}:
            return _err(
                f"Unknown label_mode: {label_mode}. Use one of: "
                "degrees, sign_number, both, none"
            )

        if chart_type in {"Moon", "moon"}:
            data = pyjhora_helper.get_moon_data(**params)["planets"]
            title = "Moon Chart"
        elif chart_type == "D1_Rasi":
            data = pyjhora_helper.get_rasi_chart(**params)
            title = "Rasi Chart (D1)"
        else:
            all_charts = pyjhora_helper.get_divisional_charts(**params)
            if chart_type not in all_charts:
                return _err(f"Unknown chart_type: {chart_type}. Available: {list(all_charts.keys())}")
            data = all_charts[chart_type]
            title = chart_type.replace("_", " ")

        png_bytes = chart_image.generate_chart_image(
            data, chart_name=title, size=size, label_mode=label_mode, style=style,
        )
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
