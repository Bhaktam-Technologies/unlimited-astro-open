# astro-wrapper — Copyright (C) 2026 Bhaktam Technologies
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE and NOTICE in the project root for full terms.

"""Input validation for Flask request bodies."""

from datetime import datetime
import pytz


class ValidationError(ValueError):
    pass


def _require(body, field):
    if body.get(field) is None:
        raise ValidationError(f"Missing field: {field}")
    return body[field]


def _as_int(v, field, lo=None, hi=None):
    try:
        n = int(v)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be an integer, got {v!r}")
    if lo is not None and n < lo:
        raise ValidationError(f"{field} must be >= {lo}")
    if hi is not None and n > hi:
        raise ValidationError(f"{field} must be <= {hi}")
    return n


def _as_float(v, field, lo=None, hi=None):
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be a number, got {v!r}")
    if lo is not None and x < lo:
        raise ValidationError(f"{field} must be >= {lo}")
    if hi is not None and x > hi:
        raise ValidationError(f"{field} must be <= {hi}")
    return x


def _resolve_timezone(tz_value, year, month, day, hour, minute):
    """
    Accept either a numeric UTC offset in hours (e.g. 5.5) or an IANA
    timezone name (e.g. 'Asia/Kolkata'). Returns (offset_hours, tz_name_or_none).
    IANA names are resolved against the birth moment so DST is handled.
    """
    if tz_value is None:
        raise ValidationError("Missing field: timezone_offset")

    if isinstance(tz_value, (int, float)):
        return float(tz_value), None

    if isinstance(tz_value, str):
        s = tz_value.strip()
        try:
            return float(s), None
        except ValueError:
            pass
        try:
            tz = pytz.timezone(s)
        except pytz.UnknownTimeZoneError:
            raise ValidationError(f"Unknown timezone: {s!r}")
        naive = datetime(year, month, day, hour, minute)
        localized = tz.localize(naive, is_dst=None) if hasattr(tz, "localize") else naive.replace(tzinfo=tz)
        offset = localized.utcoffset().total_seconds() / 3600.0
        return offset, s

    raise ValidationError(f"timezone_offset must be a number or IANA name, got {tz_value!r}")


def extract_birth_params(body):
    """Validate and coerce the standard birth-detail payload.
    Raises ValidationError on bad input.
    """
    body = body or {}
    year = _as_int(_require(body, "year"), "year", 1800, 2400)
    month = _as_int(_require(body, "month"), "month", 1, 12)
    day = _as_int(_require(body, "day"), "day", 1, 31)
    hour = _as_int(_require(body, "hour"), "hour", 0, 23)
    minute = _as_int(_require(body, "minute"), "minute", 0, 59)
    latitude = _as_float(_require(body, "latitude"), "latitude", -90.0, 90.0)
    longitude = _as_float(_require(body, "longitude"), "longitude", -180.0, 180.0)

    tz_offset, tz_name = _resolve_timezone(
        body.get("timezone_offset"), year, month, day, hour, minute
    )

    location_name = body.get("location_name")
    if not location_name or not str(location_name).strip():
        raise ValidationError("Missing field: location_name")

    try:
        datetime(year, month, day, hour, minute)
    except ValueError as e:
        raise ValidationError(f"Invalid date/time: {e}")

    return {
        "year": year,
        "month": month,
        "day": day,
        "hour": hour,
        "minute": minute,
        "latitude": latitude,
        "longitude": longitude,
        "timezone_offset": tz_offset,
        "location_name": str(location_name).strip(),
        "_tz_name": tz_name,
    }


def extract_match_params(body):
    body = body or {}
    return {
        "boy_nakshatra": _as_int(_require(body, "boy_nakshatra"), "boy_nakshatra", 1, 27),
        "boy_pada": _as_int(_require(body, "boy_pada"), "boy_pada", 1, 4),
        "girl_nakshatra": _as_int(_require(body, "girl_nakshatra"), "girl_nakshatra", 1, 27),
        "girl_pada": _as_int(_require(body, "girl_pada"), "girl_pada", 1, 4),
        "method": (body.get("method") or "North").strip(),
    }


def extract_session_config(body):
    """Optional per-request overrides for ayanamsa/language/etc."""
    body = body or {}
    cfg = {}
    if "ayanamsa" in body:
        cfg["ayanamsa_mode"] = str(body["ayanamsa"]).strip()
    if "language" in body:
        cfg["language"] = str(body["language"]).strip()
    if "use_true_nodes" in body:
        cfg["use_true_nodes"] = bool(body["use_true_nodes"])
    if "bhaava_madhya_method" in body:
        cfg["bhaava_madhya_method"] = _as_int(
            body["bhaava_madhya_method"], "bhaava_madhya_method", 1, 17
        )
    return cfg
