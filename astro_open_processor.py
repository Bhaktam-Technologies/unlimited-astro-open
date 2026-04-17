# unlimited-astro-open — Copyright (C) 2026 Bhaktam Technologies
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE and NOTICE in the project root for full terms.

from flask import Flask, jsonify, request, Response, send_file
import traceback
import logging
import io

app = Flask(__name__)

from logger import logger

app_logger = logger.getLoggerForApp()

from helpers import pyjhora_helper
from helpers import chart_image


# ---------------------------------------------------------------------------
# Security middleware
# ---------------------------------------------------------------------------
LOCALHOST_IPS = {"127.0.0.1", "::1", "0.0.0.0:5002"}


@app.before_request
def enforce_security():
    remote_ip = request.remote_addr
    if remote_ip not in LOCALHOST_IPS:
        return jsonify({"status": -1, "message": "Forbidden"}), 403


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route('/')
def hello_world():
    return 'unlimited-astro-open is running!'


@app.route('/source')
def source():
    return jsonify({
        "project": "unlimited-astro-open",
        "license": "AGPL-3.0-or-later",
        "source": "https://github.com/ketanbhaktam/unlimited-astro-open",
        "notice": "This service is offered under the GNU Affero General Public License v3.0. "
                  "You may obtain the Corresponding Source at the URL above."
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_birth_params(body):
    """Extract and validate birth details for PyJHora endpoints."""
    required = ["year", "month", "day", "hour", "minute", "latitude", "longitude", "timezone_offset", "location_name"]
    missing = [f for f in required if body.get(f) is None]
    if missing:
        return None, missing
    return {
        "year": int(body["year"]),
        "month": int(body["month"]),
        "day": int(body["day"]),
        "hour": int(body["hour"]),
        "minute": int(body["minute"]),
        "latitude": float(body["latitude"]),
        "longitude": float(body["longitude"]),
        "timezone_offset": float(body["timezone_offset"]),
        "location_name": body["location_name"],
    }, None


# ---------------------------------------------------------------------------
# PyJHora Endpoints
# ---------------------------------------------------------------------------

@app.route("/jhora/rasi-chart", methods=['POST'])
def jhora_rasi_chart():
    try:
        body = request.get_json() or {}
        params, missing = _extract_birth_params(body)
        if missing:
            return jsonify({'status': -1, 'message': f'Missing fields: {", ".join(missing)}'}), 400
        data = pyjhora_helper.get_rasi_chart(**params)
        return jsonify({'status': 1, 'data': data})
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__))
        logging.exception("Exception in jhora rasi-chart")
        return jsonify({'status': -1, 'message': str(e)})


@app.route("/jhora/divisional-charts", methods=['POST'])
def jhora_divisional_charts():
    try:
        body = request.get_json() or {}
        params, missing = _extract_birth_params(body)
        if missing:
            return jsonify({'status': -1, 'message': f'Missing fields: {", ".join(missing)}'}), 400
        data = pyjhora_helper.get_divisional_charts(**params)
        return jsonify({'status': 1, 'data': data})
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__))
        logging.exception("Exception in jhora divisional-charts")
        return jsonify({'status': -1, 'message': str(e)})


@app.route("/jhora/panchanga", methods=['POST'])
def jhora_panchanga():
    try:
        body = request.get_json() or {}
        params, missing = _extract_birth_params(body)
        if missing:
            return jsonify({'status': -1, 'message': f'Missing fields: {", ".join(missing)}'}), 400
        data = pyjhora_helper.get_panchanga(**params)
        return jsonify({'status': 1, 'data': data})
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__))
        logging.exception("Exception in jhora panchanga")
        return jsonify({'status': -1, 'message': str(e)})


@app.route("/jhora/bhava-chart", methods=['POST'])
def jhora_bhava_chart():
    try:
        body = request.get_json() or {}
        params, missing = _extract_birth_params(body)
        if missing:
            return jsonify({'status': -1, 'message': f'Missing fields: {", ".join(missing)}'}), 400
        data = pyjhora_helper.get_bhava_chart(**params)
        return jsonify({'status': 1, 'data': data})
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__))
        logging.exception("Exception in jhora bhava-chart")
        return jsonify({'status': -1, 'message': str(e)})


@app.route("/jhora/vimsottari-dasa", methods=['POST'])
def jhora_vimsottari_dasa():
    try:
        body = request.get_json() or {}
        params, missing = _extract_birth_params(body)
        if missing:
            return jsonify({'status': -1, 'message': f'Missing fields: {", ".join(missing)}'}), 400
        data = pyjhora_helper.get_vimsottari_dasa(**params)
        return jsonify({'status': 1, 'data': data})
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__))
        logging.exception("Exception in jhora vimsottari-dasa")
        return jsonify({'status': -1, 'message': str(e)})


@app.route("/jhora/yogini-dasa", methods=['POST'])
def jhora_yogini_dasa():
    try:
        body = request.get_json() or {}
        params, missing = _extract_birth_params(body)
        if missing:
            return jsonify({'status': -1, 'message': f'Missing fields: {", ".join(missing)}'}), 400
        data = pyjhora_helper.get_yogini_dasa(**params)
        return jsonify({'status': 1, 'data': data})
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__))
        logging.exception("Exception in jhora yogini-dasa")
        return jsonify({'status': -1, 'message': str(e)})


@app.route("/jhora/ashtottari-dasa", methods=['POST'])
def jhora_ashtottari_dasa():
    try:
        body = request.get_json() or {}
        params, missing = _extract_birth_params(body)
        if missing:
            return jsonify({'status': -1, 'message': f'Missing fields: {", ".join(missing)}'}), 400
        data = pyjhora_helper.get_ashtottari_dasa(**params)
        return jsonify({'status': 1, 'data': data})
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__))
        logging.exception("Exception in jhora ashtottari-dasa")
        return jsonify({'status': -1, 'message': str(e)})


@app.route("/jhora/shad-bala", methods=['POST'])
def jhora_shad_bala():
    try:
        body = request.get_json() or {}
        params, missing = _extract_birth_params(body)
        if missing:
            return jsonify({'status': -1, 'message': f'Missing fields: {", ".join(missing)}'}), 400
        data = pyjhora_helper.get_shad_bala(**params)
        return jsonify({'status': 1, 'data': data})
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__))
        logging.exception("Exception in jhora shad-bala")
        return jsonify({'status': -1, 'message': str(e)})


@app.route("/jhora/benefics-malefics", methods=['POST'])
def jhora_benefics_malefics():
    try:
        body = request.get_json() or {}
        params, missing = _extract_birth_params(body)
        if missing:
            return jsonify({'status': -1, 'message': f'Missing fields: {", ".join(missing)}'}), 400
        data = pyjhora_helper.get_benefics_malefics(**params)
        return jsonify({'status': 1, 'data': data})
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__))
        logging.exception("Exception in jhora benefics-malefics")
        return jsonify({'status': -1, 'message': str(e)})


@app.route("/jhora/retrograde-combustion", methods=['POST'])
def jhora_retrograde_combustion():
    try:
        body = request.get_json() or {}
        params, missing = _extract_birth_params(body)
        if missing:
            return jsonify({'status': -1, 'message': f'Missing fields: {", ".join(missing)}'}), 400
        data = pyjhora_helper.get_retrograde_combustion(**params)
        return jsonify({'status': 1, 'data': data})
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__))
        logging.exception("Exception in jhora retrograde-combustion")
        return jsonify({'status': -1, 'message': str(e)})


@app.route("/jhora/kp-chart", methods=['POST'])
def jhora_kp_chart():
    try:
        body = request.get_json() or {}
        params, missing = _extract_birth_params(body)
        if missing:
            return jsonify({'status': -1, 'message': f'Missing fields: {", ".join(missing)}'}), 400
        data = pyjhora_helper.get_kp_chart(**params)
        return jsonify({'status': 1, 'data': data})
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__))
        logging.exception("Exception in jhora kp-chart")
        return jsonify({'status': -1, 'message': str(e)})


@app.route("/jhora/muhurta", methods=['POST'])
def jhora_muhurta():
    try:
        body = request.get_json() or {}
        params, missing = _extract_birth_params(body)
        if missing:
            return jsonify({'status': -1, 'message': f'Missing fields: {", ".join(missing)}'}), 400
        data = pyjhora_helper.get_muhurta_data(**params)
        return jsonify({'status': 1, 'data': data})
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__))
        logging.exception("Exception in jhora muhurta")
        return jsonify({'status': -1, 'message': str(e)})


@app.route("/jhora/ashtakoota-match", methods=['POST'])
def jhora_ashtakoota_match():
    try:
        body = request.get_json() or {}
        required = ["boy_nakshatra", "boy_pada", "girl_nakshatra", "girl_pada"]
        missing = [f for f in required if body.get(f) is None]
        if missing:
            return jsonify({'status': -1, 'message': f'Missing fields: {", ".join(missing)}'}), 400
        data = pyjhora_helper.get_ashtakoota_match(
            boy_nakshatra=int(body["boy_nakshatra"]),
            boy_pada=int(body["boy_pada"]),
            girl_nakshatra=int(body["girl_nakshatra"]),
            girl_pada=int(body["girl_pada"]),
            method=body.get("method", "North"),
        )
        return jsonify({'status': 1, 'data': data})
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__))
        logging.exception("Exception in jhora ashtakoota-match")
        return jsonify({'status': -1, 'message': str(e)})


@app.route("/jhora/complete-horoscope", methods=['POST'])
def jhora_complete_horoscope():
    try:
        body = request.get_json() or {}
        params, missing = _extract_birth_params(body)
        if missing:
            return jsonify({'status': -1, 'message': f'Missing fields: {", ".join(missing)}'}), 400
        data = pyjhora_helper.get_complete_horoscope(**params)
        return jsonify({'status': 1, 'data': data})
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__))
        logging.exception("Exception in jhora complete-horoscope")
        return jsonify({'status': -1, 'message': str(e)})


@app.route("/jhora/chart-image", methods=['POST'])
def jhora_chart_image():
    """Generate a South Indian style chart image (PNG).
    Optional body params: chart_type (default "D1_Rasi"), size (default 600)
    """
    try:
        body = request.get_json() or {}
        params, missing = _extract_birth_params(body)
        if missing:
            return jsonify({'status': -1, 'message': f'Missing fields: {", ".join(missing)}'}), 400

        chart_type = body.get("chart_type", "D1_Rasi")
        size = int(body.get("size", 600))

        if chart_type == "D1_Rasi":
            data = pyjhora_helper.get_rasi_chart(**params)
            title = "Rasi Chart (D1)"
        else:
            all_charts = pyjhora_helper.get_divisional_charts(**params)
            if chart_type not in all_charts:
                return jsonify({'status': -1, 'message': f'Unknown chart_type: {chart_type}. Available: {list(all_charts.keys())}'}), 400
            data = all_charts[chart_type]
            title = chart_type.replace("_", " ")

        png_bytes = chart_image.generate_chart_image(data, chart_name=title, size=size)
        return send_file(io.BytesIO(png_bytes), mimetype='image/png', download_name=f'{chart_type}.png')
    except Exception as e:
        print(traceback.format_exception(None, e, e.__traceback__))
        logging.exception("Exception in jhora chart-image")
        return jsonify({'status': -1, 'message': str(e)})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
