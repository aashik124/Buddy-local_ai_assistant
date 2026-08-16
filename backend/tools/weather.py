import httpx


async def get_weather(location: str) -> str:
    async with httpx.AsyncClient(timeout=20) as client:
        geo_response = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": location, "count": 1},
        )
        geo_response.raise_for_status()
        geo = geo_response.json()
        results = geo.get("results") or []
        if not results:
            return f"No weather location found for {location}."

        place = results[0]
        weather_response = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current_weather": "true",
            },
        )
        weather_response.raise_for_status()
        weather = weather_response.json().get("current_weather")
        if not weather:
            return "Weather data is unavailable right now."

        return (
            f"{place['name']}, {place.get('country', '')}: "
            f"{weather['temperature']} C, wind {weather['windspeed']} km/h."
        )
