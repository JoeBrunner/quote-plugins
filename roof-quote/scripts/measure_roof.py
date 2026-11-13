#!/usr/bin/env python3
"""Measure a roof from its street address with Google's Solar API (satellite roof model).

    python3 measure_roof.py "123 Main St, Tampa, FL 33601" [--out roof.json]
    python3 measure_roof.py --lat 27.88 --lng -82.51 [--out roof.json]

The address is turned into a map point with the US Census geocoder (free, no key; US addresses only). Outside the US,
pass --lat and --lng. The Google key is read from the GOOGLE_SOLAR_API_KEY environment variable, or on a Mac from the
Keychain item named "roof-quote-google-key" (or the one named by --keychain-service). It is never printed.

Prints one JSON object: total roof area in square feet and squares, each roof face with its pitch (x/12), which faces
are low-slope (need flat-roof material), the photo date and quality, how far Google's building is from the address
point, and a top-down drawing of the faces (SVG). Exit code 2 means no usable roof was found; the message says why.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

CENSUS = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
SOLAR = "https://solar.googleapis.com/v1/buildingInsights:findClosest"
# FEMA's national map of every US building over 450 sq ft, with its address and use (free, no key).
FEMA = "https://services2.arcgis.com/FiaPA4ga0iQKduv3/ArcGIS/rest/services/USA_Structures_View/FeatureServer/0/query"
SQFT_PER_M2 = 10.7639
LOW_SLOPE_DEGREES = math.degrees(math.atan(2 / 12))  # under 2/12 needs flat-roof material, not shingles


def fail(message):
    print(json.dumps({"ok": False, "error": message}))
    sys.exit(2)


def get_json(url, timeout=30):
    request = urllib.request.Request(url, headers={"User-Agent": "roof-quote-plugin/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        try:
            body = json.load(error)
        except Exception:
            body = {}
        return {"_http_error": error.code, "_message": (body.get("error") or {}).get("message", str(error))}
    except urllib.error.URLError as error:
        fail(f"Couldn't reach {urllib.parse.urlparse(url).netloc} ({error.reason}). Check the internet connection.")


def geocode(address):
    query = urllib.parse.urlencode({"address": address, "benchmark": "Public_AR_Current", "format": "json"})
    answer = get_json(f"{CENSUS}?{query}")
    matches = ((answer.get("result") or {}).get("addressMatches")) or []
    if not matches:
        fail("The Census address lookup didn't recognize that address. Check the spelling and zip code, or pass the "
             "map point with --lat and --lng (right-click the roof in Google Maps to copy it).")
    best = matches[0]
    return best["coordinates"]["y"], best["coordinates"]["x"], tidy(best["matchedAddress"]), best["matchedAddress"].split(",")[0]


def tidy(address):
    """The Census answers in capitals: '4102 W MAIN ST, TAMPA, FL, 33616' -> '4102 W Main St, Tampa, FL 33616'."""
    parts = [p.strip() for p in address.split(",")]
    if len(parts) >= 4:
        parts = parts[:-2] + [f"{parts[-2]} {parts[-1]}"]
    keep = {"N", "S", "E", "W", "NE", "NW", "SE", "SW", "PO"}
    words = lambda text: " ".join(w if w in keep else (w.lower() if w[:1].isdigit() else w.capitalize()) for w in text.split())
    return ", ".join([words(p) for p in parts[:-1]] + [parts[-1].upper()])


def find_house(lat, lng, street):
    """The building at this address from FEMA's map: its center point and use. Address pins can sit by the street or,
    on about 1 address in 4, 100 m or more away, so sending Google the pin can measure someone else's roof."""
    clean = lambda text: " ".join((text or "").upper().replace(".", "").split())
    target = clean(street)

    def ask(extra, distance):
        query = urllib.parse.urlencode({"geometry": f"{lng},{lat}", "geometryType": "esriGeometryPoint", "inSR": 4326,
                                        "spatialRel": "esriSpatialRelIntersects", "distance": distance,
                                        "units": "esriSRUnit_Meter", "outFields": "PROP_ADDR,PRIM_OCC,LATITUDE,LONGITUDE",
                                        "returnGeometry": "false", "f": "json", **extra})
        try:
            return [f["attributes"] for f in (get_json(f"{FEMA}?{query}", timeout=20).get("features") or [])]
        except Exception:
            return []

    nearby = ask({}, 100)
    exact = [b for b in nearby if target and clean(b.get("PROP_ADDR")) == target]
    if not exact and target:
        # Same house number and street name anywhere within 3 km (handles "W Leila Ave" against "Leila Ave").
        words = target.split()
        number = words[0] if words and words[0].isdigit() else None
        name = max((w for w in words[1:] if w not in ("N", "S", "E", "W", "NE", "NW", "SE", "SW")), key=len, default="")
        if number and len(name) >= 3:
            like = f"PROP_ADDR LIKE '{number} %{name.replace(chr(39), '')}%'"
            exact = ask({"where": like}, 3000)
    if exact:
        best = min(exact, key=lambda b: meters_between(lat, lng, b["LATITUDE"], b["LONGITUDE"]))
        how = "address"
    elif nearby:
        best = min(nearby, key=lambda b: meters_between(lat, lng, b["LATITUDE"], b["LONGITUDE"]))
        how = "nearest"
    else:
        return None
    return {"lat": best["LATITUDE"], "lng": best["LONGITUDE"], "use": best.get("PRIM_OCC") or "", "matched": how}


def read_key(service):
    key = os.environ.get("GOOGLE_SOLAR_API_KEY", "").strip()
    if key:
        return key
    if sys.platform == "darwin":
        found = subprocess.run(["security", "find-generic-password", "-s", service, "-w"],
                               capture_output=True, text=True)
        if found.returncode == 0 and found.stdout.strip():
            return found.stdout.strip()
    fail("No Google key found. Run the roof-quote setup to add one, or measure from a report or your own numbers.")


def pitch_over_12(degrees):
    return round(math.tan(math.radians(degrees)) * 12, 1)


def meters_between(lat1, lng1, lat2, lng2):
    return math.hypot((lat1 - lat2) * 111320, (lng1 - lng2) * 111320 * math.cos(math.radians(lat1)))


def drawing(segments, center):
    """A simple top-down picture: each face's outline box, shaded by pitch, numbered to match the table."""
    boxes = []
    for number, segment in enumerate(segments, 1):
        box = segment.get("boundingBox")
        if not box:
            continue
        sw, ne = box["sw"], box["ne"]
        x1 = (sw["longitude"] - center[1]) * 111320 * math.cos(math.radians(center[0]))
        x2 = (ne["longitude"] - center[1]) * 111320 * math.cos(math.radians(center[0]))
        y1 = (center[0] - ne["latitude"]) * 111320
        y2 = (center[0] - sw["latitude"]) * 111320
        boxes.append((number, x1, y1, x2, y2, segment.get("pitchDegrees", 0)))
    if not boxes:
        return ""
    left, top = min(b[1] for b in boxes), min(b[2] for b in boxes)
    right, bottom = max(b[3] for b in boxes), max(b[4] for b in boxes)
    span = max(right - left, bottom - top, 1)
    scale, pad = 300 / span, 14
    width, height = (right - left) * scale + pad * 2, (bottom - top) * scale + pad * 2
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" role="img" '
             f'aria-label="Top-down drawing of the roof faces">']
    labels = []
    # Big faces first, so small ones sit on top and stay visible.
    for number, x1, y1, x2, y2, degrees in sorted(boxes, key=lambda b: -(b[3] - b[1]) * (b[4] - b[2])):
        low = degrees < LOW_SLOPE_DEGREES
        shade = "#9aa5b1" if low else f"hsl(18, 70%, {max(38, 70 - degrees * 1.2):.0f}%)"
        x, y = (x1 - left) * scale + pad, (y1 - top) * scale + pad
        w, h = (x2 - x1) * scale, (y2 - y1) * scale
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="3" fill="{shade}" '
                     f'fill-opacity="0.55" stroke="#1f2933" stroke-width="1.2"/>')
        labels.append(f'<circle cx="{x + w / 2:.1f}" cy="{y + h / 2:.1f}" r="9" fill="#fff" stroke="#1f2933" '
                      f'stroke-width="1"/><text x="{x + w / 2:.1f}" y="{y + h / 2 + 4:.1f}" text-anchor="middle" '
                      f'font-size="11" font-family="system-ui, sans-serif" font-weight="700" fill="#111">{number}</text>')
    parts += labels  # numbers last, so no face hides another's number
    parts.append("</svg>")
    return "".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("address", nargs="?")
    parser.add_argument("--lat", type=float)
    parser.add_argument("--lng", type=float)
    parser.add_argument("--keychain-service", default="roof-quote-google-key")
    parser.add_argument("--out")
    args = parser.parse_args()

    street = None
    if args.lat is not None and args.lng is not None:
        lat, lng, matched = args.lat, args.lng, args.address or f"{args.lat}, {args.lng}"
    elif args.address:
        lat, lng, matched, street = geocode(args.address)
    else:
        fail("Give an address, or --lat and --lng.")


    house = find_house(lat, lng, street) if street else None
    if house:
        lat, lng = house["lat"], house["lng"]

    key = read_key(args.keychain_service)
    query = urllib.parse.urlencode({"location.latitude": f"{lat:.7f}", "location.longitude": f"{lng:.7f}",
                                    "requiredQuality": "MEDIUM", "key": key})
    answer = get_json(f"{SOLAR}?{query}")
    del key, query
    if "_http_error" in answer:
        code, message = answer["_http_error"], answer["_message"]
        if code == 404:
            fail("Google has no roof model for this spot (common for new builds, rural areas and some regions). "
                 "Measure from a report or your own numbers instead.")
        if code in (401, 403):
            fail(f"Google refused the key: {message} Make sure the Solar API is turned on for that key's project.")
        if code == 429:
            fail("Google's daily or per-minute limit for this key is used up. Try again later.")
        fail(f"Google returned an error ({code}): {message}")

    potential = answer.get("solarPotential") or {}
    segments = potential.get("roofSegmentStats") or []
    if not segments:
        fail("Google found a building but no roof faces. Measure from a report or your own numbers instead.")
    center = answer.get("center") or {}
    offset = meters_between(lat, lng, center.get("latitude", lat), center.get("longitude", lng))

    faces = []
    for number, segment in enumerate(segments, 1):
        stats = segment.get("stats") or {}
        degrees = segment.get("pitchDegrees", 0.0)
        sqft = stats.get("areaMeters2", 0) * SQFT_PER_M2
        faces.append({
            "face": number,
            "sqft": round(sqft),
            "pitch": pitch_over_12(degrees),
            "pitch_degrees": round(degrees, 1),
            "facing": round(segment.get("azimuthDegrees", 0)),
            "low_slope": degrees < LOW_SLOPE_DEGREES,
        })
    total = sum(f["sqft"] for f in faces)
    sloped = sum(f["sqft"] for f in faces if not f["low_slope"])
    main_pitch = max((f for f in faces if not f["low_slope"]), key=lambda f: f["sqft"], default=faces[0])["pitch"]
    steepest = max(f["pitch"] for f in faces)
    date = answer.get("imageryDate") or {}
    result = {
        "ok": True,
        "address": matched,
        "lat": round(lat, 7), "lng": round(lng, 7),
        "roof_sqft": total,
        "squares": round(total / 100, 1),
        "sloped_sqft": sloped,
        "low_slope_sqft": total - sloped,
        "faces": faces,
        "face_count": len(faces),
        "main_pitch": main_pitch,
        "steepest_pitch": steepest,
        "footprint_sqft": round((potential.get("wholeRoofStats") or {}).get("groundAreaMeters2", 0) * SQFT_PER_M2),
        "photo_date": f"{date.get('year', '?')}-{date.get('month', 0):02d}-{date.get('day', 0):02d}",
        "photo_quality": answer.get("imageryQuality"),
        "building_offset_m": round(offset, 1),
        "warnings": [],
        "source": "Google Solar API roof model (satellite and aerial imagery)",
        "drawing_svg": drawing(segments, (center.get("latitude", lat), center.get("longitude", lng))),
    }
    # Address points usually sit near the street, 15 to 35 m from the middle of the house, so only a bigger gap is odd.
    if offset > 40:
        result["warnings"].append(f"Google's nearest building is {offset * 3.28:.0f} ft from the address point; it may "
                                  "be a neighbor's roof. Check the drawing against the house before quoting.")
    if date.get("year") and date["year"] < 2021:
        result["warnings"].append(f"The roof photo is from {date['year']}. Additions since then won't be in it.")
    if answer.get("imageryQuality") == "MEDIUM":
        result["warnings"].append("Google rates this photo medium quality; small faces may be missed.")
    if total < 600:
        result["warnings"].append("Under 600 sq ft is small for a house; Google may have found a shed or garage.")

    result["size_method"] = "Google's satellite roof model"
    if house:
        result["house_found_by"] = "FEMA building map, " + ("exact address" if house["matched"] == "address" else "nearest building")
        if house["use"] and "single family" not in house["use"].lower():
            result["warnings"].append(f"FEMA's building map lists this address as \"{house['use']}\", not a single-family "
                                      "home. Check it's the right building before sending.")
        if house["matched"] != "address":
            result["warnings"].append("Couldn't match the exact address on the building map, so it used the nearest "
                                      "building. Check the drawing against the house.")

    text = json.dumps(result, indent=2)
    if args.out:
        with open(args.out, "w") as handle:
            handle.write(text)
    print(text)


if __name__ == "__main__":
    main()
