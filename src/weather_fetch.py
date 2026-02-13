import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENWEATHER_API_KEY")
CITY = "Arlington"
URL = f"https://api.openweathermap.org/data/2.5/weather?q={CITY},us&units=metric&appid={API_KEY}"


def get_weather():
    response = requests.get(URL)
    data = response.json()
    return {
        "temperature": data["main"]["temp"],
        "condition": data["weather"][0]["main"],
        "description": data["weather"][0]["description"]
    }


if __name__ == "__main__":
    print(get_weather())
