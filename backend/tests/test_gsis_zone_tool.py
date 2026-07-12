"""
tests/test_web_search.py - Unit tests for the GSIS objective zone price tool. All HTTP calls are mocked.
"""
import pytest
from unittest.mock import MagicMock, patch

from app.tools.gsis_zone_tool import get_objective_zone_price

@pytest.fixture
def mock_http():
    """
    Fixture that mocks httpx.Client and returns a configured mock response.
    Usage: 
        mock_response = mock_http()
        mock_response.json.return_value = [...]  # Configure for your test
    """
    # Create the mock response
    mock_response = MagicMock(status_code=200)
    
    # Create the mock client with context manager support
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_response
    
    # Patch httpx.Client to return our mock client
    with patch("httpx.Client", return_value=mock_client):
        yield mock_response  
    

class TestGSISTool:
    """Test suite for GSIS objective zone price tool."""

    def test_latlon_to_mercator_known_point(self):
        """Zografou center should map to approx the coordinates in your URL."""
        from app.tools.gsis_zone_tool import _latlon_to_mercator
        # Known: lat=37.9748, lon=23.7717 -> center of the Zografou bbox you found
        x, y = _latlon_to_mercator(37.9748, 23.7717)
        assert abs(x - 2646260) < 200   # within 200m of expected
        assert abs(y - 4575877) < 200

    def test_build_bbox_correct_size(self):
        from app.tools.gsis_zone_tool import _build_bbox
        bbox = _build_bbox(1000.0, 2000.0, half=30)
        assert bbox["xmin"] == 970.0
        assert bbox["xmax"] == 1030.0
        assert bbox["ymin"] == 1970.0
        assert bbox["ymax"] == 2030.0
        assert bbox["spatialReference"]["wkid"] == 102100

    def test_parse_zone_price_standard_format(self):
        from app.tools.gsis_zone_tool import _parse_zone_price
        code, price = _parse_zone_price("ΑΘ1234/2900")
        assert code == "ΑΘ1234"
        assert price == 2900

    def test_parse_zone_price_no_slash(self):
        from app.tools.gsis_zone_tool import _parse_zone_price
        code, price = _parse_zone_price("ΑΘ1234")
        assert code == "ΑΘ1234"
        assert price is None

    def test_parse_zone_price_empty(self):
        from app.tools.gsis_zone_tool import _parse_zone_price
        code, price = _parse_zone_price("")
        assert price is None

    def test_geocode_not_found_raises_value_error(self):
        """Test that geocoding a non-existent address raises ValueError."""
        from app.tools.gsis_zone_tool import _geocode_address
        mock_resp = mock_http
        mock_resp.json.return_value = []  # empty Nominatim result

        with pytest.raises(ValueError, match="Δεν βρέθηκε"):
            _geocode_address("Fake Address 999, Atlantis")

    def test_geocode_success_returns_lat_lon(self, mock_http):
        from app.tools.gsis_zone_tool import _geocode_address
        mock_resp = mock_http
        mock_resp.json.return_value = [{
            "lat": "37.9748", "lon": "23.7717",
            "display_name": "Ζωγράφου, Αθήνα"
        }]

        lat, lon = _geocode_address("Αρχιμήδους 12, Ζωγράφου")
        assert abs(lat - 37.9748) < 0.001
        assert abs(lon - 23.7717) < 0.001

    def test_full_tool_returns_price_on_success(self, mock_http):
        """End-to-end mock: geocode → GSIS query → formatted output."""
        geocode_resp = mock_http
        geocode_resp.json.return_value = [{"lat": "37.9748", "lon": "23.7717", "display_name": "Ζωγράφου"}]

        gsis_resp = MagicMock(status_code=200)
        gsis_resp.json.return_value = {
            "features": [{
                "attributes": {
                    "OBJECTID": 1,
                    "SE": "ΑΘ0142/2750",
                    "DESCRIPTIO": "ΖΩΓΡΑΦΟΥ ΚΕΝΤΡΟ",
                    "CLUSTER_ID": "ATH01"
                }
            }]
        }

        with patch("httpx.Client") as MockClient:
            instance = MockClient.return_value.__enter__.return_value
            # First call returns geocode response, second returns GSIS response
            instance.get.side_effect = [geocode_resp, gsis_resp]
            result = get_objective_zone_price.invoke({"address": "Αρχιμήδους 12, Ζωγράφου"})

        assert "2,750" in result or "2750" in result
        assert "ΑΘ0142" in result
        assert "αντικειμενική αξία" in result.lower() or "Αντικειμενική" in result

    def test_full_tool_no_features_returns_guidance(self, mock_http):
        geocode_resp = mock_http
        geocode_resp.json.return_value = [{"lat": "37.9", "lon": "23.7", "display_name": "Test"}]
        gsis_resp = MagicMock(status_code=200)
        gsis_resp.json.return_value = {"features": []}

        with patch("httpx.Client") as MockClient:
            instance = MockClient.return_value.__enter__.return_value
            # First call returns geocode response, second returns GSIS response
            instance.get.side_effect = [geocode_resp, gsis_resp]
            result = get_objective_zone_price.invoke({"address": "Κάπου μακριά 1"})

        assert "maps.gsis.gr" in result
        assert "Δεν βρέθηκε" in result

    def test_full_tool_geocode_failure_returns_message(self, mock_http):
        geocode_resp= mock_http
        geocode_resp.json.return_value = []  # not found

        with patch("httpx.Client") as MockClient:
            instance = MockClient.return_value.__enter__.return_value
            instance.get.return_value = geocode_resp
            result = get_objective_zone_price.invoke({"address": "Fake Street 999, Atlantis"})

        assert "Δεν βρέθηκε" in result