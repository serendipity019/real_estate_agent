"""
tools/gsis_zone_tool.py — LangChain @tool that queries the official Greek
government (GSIS/AADE) ArcGIS MapServer for objective zone prices
(αντικειμενικές αξίες / τιμές ζώνης) given a Greek address.

Pipeline:
  1. Address → (lat, lon)  via OpenStreetMap Nominatim (free, no key needed)
  2. (lat, lon) → Web Mercator (x, y)  via standard projection math
  3. Build 20m bounding box around the point
  4. POST to GSIS ArcGIS proxy → returns matching zone(s)
  5. Extract SE (zone code + price in €/m²) and DESCRIPTIO (zone name)

The SE field format is: "ZONE_CODE/PRICE" e.g. "ΑΘ-1234/2900"
The numeric part after "/" is the official objective price in €/m².

Data source: ΑΑΔΕ / Υπουργείο Οικονομικών
Endpoint:    https://maps.gsis.gr/arcgis/rest/services/APAA_PUBLIC/PUBLIC_ZONES_SE_SAO_PRJ/MapServer/dynamicLayer/query
Proxy:       https://maps.gsis.gr/valuemaps2/PHP/proxy.php?<arcgis_url>
"""
import json
import math
import logging
import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Constants where we use
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {"User-Agent": "SmartRealEstateAssistant/1.0"}

GSIS_PROXY    = "https://maps.gsis.gr/valuemaps2/PHP/proxy.php?"
GSIS_ENDPOINT = (
    "https://maps.gsis.gr/arcgis/rest/services/APAA_PUBLIC/"
    "PUBLIC_ZONES_SE_SAO_PRJ/MapServer/dynamicLayer/query"
)

BBOX_HALF_METERS = 30   # search radius around the address point
TIMEOUT = httpx.Timeout(15.0)

# Helping functions that have to do with the coordination

def _latlon_to_mercator(lat: float, lon: float) -> tuple[float, float]:
    """
    Convert WGS84 (lat/lon) to Web Mercator (EPSG:3857 / wkid 102100).
    lat for latitude.
    lon for longitude. 
    Simply this function convert from degrees to meters.
    """
    x = lon * 20037508.34 / 180 # The hulf circumference of the earth in meters. The distance from the center of the earth if you show the earth as map.  
    y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180) # Mercator projection stretches the map near the poles.
    y = y * 20037508.34 / 180 # End convert again to meters
    return x, y

def _build_bbox(x: float, y: float, half: float = BBOX_HALF_METERS) -> dict:
    """Build an ArcGIS envelope geometry dict around a Web Mercator point."""
    return {
        "xmin": x - half,
        "ymin": y - half,
        "xmax": x + half,
        "ymax": y + half,
        "spatialReference": {"wkid": 102100},
    }

# ---- Step 1: Geocode ------

def _geocode_address(address: str) -> tuple[float, float]:
    """
    Convert a Greek address string to (lat, lon) using OSM (Open Street Map) Nominatim.
    Appends 'Greece' if not already present to improve result quality.
    Raises ValueError if no result found.
    """
    query = address if "ελλάδa" in address.lower() or "greece" in address.lower() \
    else f"{address}, Greece"

    with httpx.Client(timeout=TIMEOUT, headers=NOMINATIM_HEADERS) as client:
        resp = client.get(NOMINATIM_URL, params={
            "q": query,
            "format": "json",
            "limit": 1,
            "countrycodes": "gr",
        })
        resp.raise_for_status()
        results = resp.json()

    if not results:
        raise ValueError(
            f"The address '{address}' didn't find in the OpenStreetMap."
            "Try more specific address (road + number + district)"
        )
    
    lat = float(results[0]["lat"])
    lon = float(results[0]["lon"])
    display = results[0].get("display_name", "")
    logger.info(f"Geocoded '{address}' -> lat={lat:.6f}, lon={lon:.6f} ({display[:60]}")
    return lat, lon

# --- Step 2: Query GSIS ------
def _query_gsis_zone(lat: float, lon: float) -> list[dict]:
    """
    Query the GSIS ArcGIS endpoint for zone(s) containing the given point.
    Returns a list of feature attribute dicts.
    """
    x,y = _latlon_to_mercator(lat, lon)
    bbox = _build_bbox(x, y)

    params = {
        "f": "json",
        "returnGeometry": "false",
        "spatialRel": "esriSpatialRelIntersects",
        "geometry": json,
        "geometryType": "esriGeometryEnvelope",
        "inSR": "102100",
        "outFields": "OBJECTID,SE,DESCRIPTIO,CLUSTER_ID",
        "outSR": "102100",
        "layer": json.dumps({
            "source": {"type": "mapLayer", "mapLayerId": 0}
        }),
    }

    # Build the proxied URL (GSIS requires their own proxy for CORS)
    arcgis_url = GSIS_ENDPOINT + "?" + "&".join(
        f"{k}={v}" for k, v in params.items()
    )
    proxy_url = GSIS_PROXY + arcgis_url

    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.get(proxy_url)
        resp.raise_for_status()

    data = resp.json()     

    if "error" in data:
        raise RuntimeError(f"GSIS API error: {data['error']}")
    
    features = data.get("features", [])
    return [fe["attributes"] for fe in features]

# --- Step 3: Parse zone price -----
def _parse_zone_price(se_field: str) -> tuple[str | None, int | None]:
    """
    Parse the SE field, format: "ZONE_CODE/PRICE" e.g. "ΑΘ1234/2900"
    Returns (zone_code, price_eur_per_sqm).
    """
    if not se_field or "/" not in se_field:
        return se_field, None
    parts = se_field.rsplit("/", 1)
    zone_code = parts[0].strip()
    try:
        price = int(parts[1].strip())
    except (ValueError, IndexError):
        price = None
    return zone_code, price

# --- The tool ----
@tool
def get_objective_zone_price(address: str) -> str:
    """
    Look up the official Greek government objective zone price (αντικειμενική αξία /
    τιμή ζώνης) for a Greek property address, using the GSIS/AADE ArcGIS service.

    Use this tool whenever the user asks about:
    - The official objective value (αντικειμενική αξία) of a property
    - The zone price (τιμή ζώνης) for a specific address or area
    - ENFIA tax base calculation for a property
    - The "government price" vs the market price of a property
    - Whether to use objective or market value for a transaction

    The objective zone price is the OFFICIAL government-set baseline price used for:
    - ENFIA (property tax) calculation
    - Transfer tax (φόρος μεταβίβασης) on property sales
    - Inheritance valuations
    - It is NOT the market price — the market price is usually higher.

    Args:
        address: Greek property address, e.g. "Αρχιμήδους 12, Ζωγράφου" or
                 "Υμηττού 50, Παγκράτι, Αθήνα". Include street number and
                 neighborhood/city for best results.

    Returns:
        A formatted string with the zone code, official price in €/m², and
        interpretation guidance. Returns an error message if the address
        cannot be found or the zone is not covered by the system.
    """
    logger.info(f"GSIS zone price lookup for : {address}")

    try:
        # Geocode the address
        lat, lon = _geocode_address(address=address)
    except ValueError as e:
        return str(e)
    except Exception as e:
        logger.exception("Geocoding failed.")
        return(
            f"Inability to geocode the address: '{address}'."
            f"Error: {e}"
        )
    
    try:
        # Query GSIS
        features = _query_gsis_zone(lat, lon)
    except Exception as e:
        logger.exception("GSIS query failed")
        return (
            f"Inability to connect in the GSIS/AADE DataBase."
            f"Error: {e}\n"
            "Try later or check manually in the GSIS site: **https://maps.gsis.gr/valuemaps/** "
        )
    
    # Format the results
    lines = [
        f"**Objectivity value / Zone Price** for: {address}",
        f"_(Source: AADE / Ministry of Finance - maps.gsis.gr)_",
        "",
    ]

    for feat in features:
        se = feat.get("SE", "")
        description = feat.get("DESCRIPTIO", "")
        zone_code, price = _parse_zone_price(se)

        if price:
            lines.append(f"🏛 **Zone:** {zone_code}")
            if description:
                lines.append(f"📍 **Description:** {description}")
            lines.append(f"💶 **Zone price:** {price:,}€/sqm.")
            lines.append("")
            lines.append(
                "**Note:** This is the *objective value* that the state defines as the tax base (ENFIA, transfer loyalty tax)"
                "The *commercial value* (market price) is usually **higher** ~ for comparison see the market prices"
                "by region from the Spitogatos index."
            )
        else:
            lines.append(f"Zone: {se} ~ {description}")
        
    return "\n".join(lines)