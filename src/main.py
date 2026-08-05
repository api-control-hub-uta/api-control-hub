from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import requests
import os
import time
from datetime import datetime 
from fastapi.staticfiles import StaticFiles
from src.database.db import get_conn, create_tables, DB_PATH
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

def c_to_f(c):
    return round((c * 9 / 5) + 32)

def f_to_c(f):
    return round((f - 32) * 5 / 9, 1)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR.parent / "static")), name="static")
create_tables()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

DEFAULT_WLED_IP = "192.168.1.165"

def get_wled_json_url(wled_ip):
    return f"http://{wled_ip}/json/state"

def get_wled_info_url(wled_ip):
    return f"http://{wled_ip}/json/info"

def get_closet_for_profile(profile_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT closet_name, wled_ip, status
        FROM closets
        WHERE user_id = ?
    """, (profile_id,))

    closet = cur.fetchone()
    conn.close()

    if closet:
        return closet

    return ("No Closet Connected", "", "unassigned") 


# HOME PAGE
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM users LIMIT 5")
    profiles = cur.fetchall()

    conn.close()

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "profiles": profiles
        }
    )


# MANAGE PROFILES PAGE
@app.get("/profiles", response_class=HTMLResponse)
def manage_profiles(request: Request):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM users LIMIT 5")
    profiles = cur.fetchall()

    conn.close()

    return templates.TemplateResponse(
        request,
        "manage_profiles.html",
        {
            "profiles": profiles
        }
    )


# CREATE PROFILE PAGE
@app.get("/profiles/new", response_class=HTMLResponse)
def create_profile_page(request: Request):
    return templates.TemplateResponse(
        request,
        "create_profile.html",
        {}
    )


# SAVE NEW PROFILE
@app.post("/profiles/new")
def save_profile(name: str = Form(...)):
    conn = get_conn()
    cur = conn.cursor()

    try:
        clean_name = name.strip()

        if not clean_name:
            return HTMLResponse(
                "<h2>Profile name cannot be empty.</h2>"
                '<a href="/profiles/new">Go Back</a>',
                status_code=400
            )

        cur.execute("SELECT COUNT(*) FROM users")
        profile_count = cur.fetchone()[0]

        if profile_count >= 5:
            return HTMLResponse(
                "<h2>Maximum of five profiles has already been reached.</h2>"
                '<a href="/">Go Back</a>',
                status_code=400
            )

        # Create the profile only.
        cur.execute(
            "INSERT INTO users (name) VALUES (?)",
            (clean_name,)
        )

        conn.commit()

    except Exception as error:
        conn.rollback()
        print("Create profile error:", error)

        return HTMLResponse(
            "<h2>Unable to create the profile.</h2>"
            '<a href="/profiles/new">Go Back</a>',
            status_code=500
        )

    finally:
        conn.close()

    return RedirectResponse(url="/", status_code=303)

# EDIT PROFILE PAGE
@app.get("/profiles/edit/{profile_id}", response_class=HTMLResponse)
def edit_profile_page(profile_id: int, request: Request):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM users WHERE id = ?", (profile_id,))
    profile = cur.fetchone()

    conn.close()

    return templates.TemplateResponse(
        request,
        "edit_profile.html",
        {
            "profile": profile
        }
    )


# SAVE EDITED PROFILE
@app.post("/profiles/edit/{profile_id}")
def update_profile(profile_id: int, name: str = Form(...)):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("UPDATE users SET name = ? WHERE id = ?", (name, profile_id))

    conn.commit()
    conn.close()

    return RedirectResponse(url="/profiles", status_code=303)


# DELETE PROFILE
@app.post("/profiles/delete/{profile_id}")
def delete_profile(profile_id: int):
    conn = get_conn()
    cur = conn.cursor()

    try:
        # Release the closet so another profile can use it.
        cur.execute("""
            UPDATE closets
            SET user_id = NULL,
                status = 'unassigned'
            WHERE user_id = ?
        """, (profile_id,))

        # Remove profile-specific data.
        cur.execute(
            "DELETE FROM preferences WHERE user_id = ?",
            (profile_id,)
        )

        cur.execute(
            "DELETE FROM settings WHERE user_id = ?",
            (profile_id,)
        )

        cur.execute(
            "DELETE FROM users WHERE id = ?",
            (profile_id,)
        )

        conn.commit()

    except Exception as error:
        conn.rollback()
        print("Delete profile error:", error)

        return HTMLResponse(
            "<h2>Unable to delete the profile.</h2>"
            '<a href="/profiles">Go Back</a>',
            status_code=500
        )

    finally:
        conn.close()

    return RedirectResponse(url="/profiles", status_code=303)


# LOCK PROFILE PLACEHOLDER
@app.get("/profiles/lock/{profile_id}", response_class=HTMLResponse)
def lock_profile(profile_id: int):
    return f"""
    <h1>Lock Profile {profile_id}</h1>
    <p>This feature will be built next.</p>
    <a href="/profiles">Go Back</a>
    """


# UPLOAD IMAGE PLACEHOLDER
@app.get("/profiles/upload/{profile_id}", response_class=HTMLResponse)
def upload_profile_image(profile_id: int):
    return f"""
    <h1>Upload Image for Profile {profile_id}</h1>
    <p>This feature will be built later.</p>
    <a href="/profiles">Go Back</a>
    """


# SETTINGS PAGE
@app.get("/settings/{profile_id}", response_class=HTMLResponse)
def settings_page(profile_id: int, request: Request):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM users WHERE id = ?", (profile_id,))
    profile = cur.fetchone()

    if not profile:
        conn.close()
        return HTMLResponse("<h1>Profile not found</h1>", status_code=404)

    cur.execute("""
        SELECT location, temperature_unit,
               led_hot_color, led_moderate_color, led_cold_color, led_extreme_cold_color,
               theme
        FROM settings
        WHERE user_id = ?
    """, (profile_id,))
    settings = cur.fetchone()

    conn.close()

    if not settings:
        settings = (
            "Arlington,TX,US",
            "fahrenheit",
            "red",
            "yellow",
            "blue",
            "purple",
            "dark"
        )

    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "profile": profile,
            "settings": settings
        }
    )
# MANAGE CLOSET PAGE
@app.get("/closet/{profile_id}", response_class=HTMLResponse)
def closet_page(request: Request, profile_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, name FROM users WHERE id = ?",
        (profile_id,)
    )
    profile = cur.fetchone()

    if not profile:
        conn.close()
        return HTMLResponse(
            "<h1>Profile not found</h1>",
            status_code=404
        )

    cur.execute("""
        SELECT closet_id, closet_name, wled_ip, status
        FROM closets
        WHERE user_id = ?
        LIMIT 1
    """, (profile_id,))

    closet = cur.fetchone()

    cur.execute("""
        SELECT theme
        FROM settings
        WHERE user_id = ?
    """, (profile_id,))
    theme_row = cur.fetchone()

    theme = theme_row[0] if theme_row else "dark"

    conn.close()

    # New profile with no closet yet
    if not closet:
        closet = (None, "", "", "unassigned")

    controller_online = False

    if closet[2]:
        controller_online = check_wled_online(closet[2])

    return templates.TemplateResponse(
        request,
        "closet.html",
        {
            "profile": profile,
            "closet": closet,
            "theme": theme,
            "controller_online": controller_online
        }
    )

@app.post("/closet/{profile_id}")
def update_closet(
    profile_id: int,
    closet_name: str = Form(...),
    wled_ip: str = Form(...)
):
    conn = get_conn()
    cur = conn.cursor()

    try:
        closet_name = closet_name.strip()
        wled_ip = wled_ip.strip()

        cur.execute("""
            SELECT closet_id
            FROM closets
            WHERE user_id = ?
            LIMIT 1
        """, (profile_id,))

        existing_closet = cur.fetchone()

        if existing_closet:
            cur.execute("""
                UPDATE closets
                SET closet_name = ?,
                    wled_ip = ?,
                    status = 'configured'
                WHERE user_id = ?
            """, (
                closet_name,
                wled_ip,
                profile_id
            ))
        else:
            cur.execute("""
                INSERT INTO closets (
                    user_id,
                    closet_name,
                    wled_ip,
                    status
                )
                VALUES (?, ?, ?, 'configured')
            """, (
                profile_id,
                closet_name,
                wled_ip
            ))

        conn.commit()

    except Exception as error:
        conn.rollback()
        print("Closet save error:", error)

    finally:
        conn.close()

    return RedirectResponse(
        url=f"/closet/{profile_id}",
        status_code=303
    )


@app.post("/closet/{profile_id}/test")
def test_closet(profile_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT wled_ip
        FROM closets
        WHERE user_id = ?
    """, (profile_id,))

    closet = cur.fetchone()
    conn.close()

    if not closet:
        return {"success": False, "error": "No closet assigned"}

    wled_ip = closet[0]

    payload_on = {
    "on": True,
    "bri": 255,
    "seg": [
        {
            "id": 0,
            "start": 0,
            "stop": 60,
            "on": True,
            "bri": 255,
            "col": [[0, 255, 0]],
            "fx": 0
        },
        {
            "id": 1,
            "start": 15,
            "stop": 30,
            "on": True,
            "bri": 255,
            "col": [[0, 255, 0]],
            "fx": 0
        },
        {
            "id": 2,
            "start": 30,
            "stop": 45,
            "on": True,
            "bri": 255,
            "col": [[0, 255, 0]],
            "fx": 0
        },
        {
            "id": 3,
            "start": 45,
            "stop": 60,
            "on": True,
            "bri": 255,
            "col": [[0, 255, 0]],
            "fx": 0
        }
    ]
}

    payload_off = {
    "on": True,
    "bri": 255,
    "seg": [
        {
            "id": 0,
            "start": 0,
            "stop": 15,
            "on": True,
            "bri": 255,
            "col": [[0, 0, 0]],
            "fx": 0
        },
        {
            "id": 1,
            "start": 15,
            "stop": 30,
            "on": True,
            "bri": 255,
            "col": [[0, 0, 0]],
            "fx": 0
        },
        {
            "id": 2,
            "start": 30,
            "stop": 45,
            "on": True,
            "bri": 255,
            "col": [[0, 0, 0]],
            "fx": 0
        },
        {
            "id": 3,
            "start": 45,
            "stop": 60,
            "on": True,
            "bri": 255,
            "col": [[0, 0, 0]],
            "fx": 0
        }
    ]
}

    try:
        set_wled_state(payload_on, wled_ip)
        time.sleep(2)
        set_wled_state(payload_off, wled_ip)

        return {
            "success": True,
            "message": "Closet test completed",
            "wled_ip": wled_ip
        }

    except Exception as e:
        return {"success": False, "error": str(e)}    

# Fetch Weather
def get_current_weather(location="Arlington,TX,US", temperature_unit="fahrenheit"):
    if not OPENWEATHER_API_KEY:
        print("API key missing")
        return None

    unit_param = "imperial" if temperature_unit == "fahrenheit" else "metric"

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": location,
        "appid": OPENWEATHER_API_KEY,
        "units": unit_param
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        print("Weather request params:", params)
        print("Status code:", response.status_code)
        print("Response text:", response.text)

        response.raise_for_status()
        data = response.json()

        city_name = data.get("name", "Unknown")
        sys_data = data.get("sys", {})
        country = sys_data.get("country", "")
        main_data = data.get("main", {})
        weather_list = data.get("weather", [])
        wind_data = data.get("wind", {})

        weather_main = "Unknown"
        weather_description = "No description"
        weather_icon = "01d"

        if weather_list:
            weather_main = weather_list[0].get("main", "Unknown")
            weather_description = weather_list[0].get("description", "No description").title()
            weather_icon = weather_list[0].get("icon", "01d")

        return {
            "city": city_name,
            "country": country,
            "temperature": round(main_data.get("temp", 0), 1),
            "feels_like": round(main_data.get("feels_like", 0), 1),
            "humidity": main_data.get("humidity", 0),
            "condition": weather_main,
            "description": weather_description,
            "icon": weather_icon,
            "wind_speed": round(wind_data.get("speed", 0), 1),
            "unit_symbol": "°F" if temperature_unit == "fahrenheit" else "°C"
        }

    except Exception as e:
        print("OpenWeather error:", e)
        return None

 #WLED
def get_wled_info(wled_ip=DEFAULT_WLED_IP):
    try:
        response = requests.get(get_wled_info_url(wled_ip), timeout=3)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("WLED info error:", e)
        return None

def check_wled_online(wled_ip):
    info = get_wled_info(wled_ip)
    return info is not None        


def get_wled_state(wled_ip=DEFAULT_WLED_IP):
    try:
        response = requests.get(get_wled_json_url(wled_ip), timeout=3)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("WLED state error:", e)
        return None


def set_wled_state(payload, wled_ip=DEFAULT_WLED_IP):
    try:
        response = requests.post(get_wled_json_url(wled_ip), json=payload, timeout=3)
        response.raise_for_status()
        return True
    except Exception as e:
        print("WLED set error:", e)
        return False


#Rgb Convertor
def color_name_to_rgb(color_name):
    color_map = {
        "red": [255, 0, 0],
        "orange": [255, 165, 0],
        "yellow": [255, 255, 0],
        "green": [0, 255, 0],
        "blue": [0, 0, 255],
        "purple": [128, 0, 128],
        "white": [255, 255, 255]
    }
    return color_map.get(color_name.lower(), [255, 255, 255])  


#Weather category Function
def get_weather_category(temp, preferences):
    if preferences is None or temp is None:
        return None

    hot_min = preferences[0]
    hot_max = preferences[1]
    moderate_min = preferences[2]
    moderate_max = preferences[3]
    cold_min = preferences[4]
    cold_max = preferences[5]

    if hot_min <= temp <= hot_max:
        return "hot"
    elif moderate_min <= temp <= moderate_max:
        return "moderate"
    elif cold_min <= temp <= cold_max:
        return "cold"
    else:
        return "extreme_cold"

#dashboard color to WLED
# dashboard weather category to WLED zone
def apply_dashboard_led_color(category, led_hot_color, led_moderate_color, led_cold_color, led_extreme_cold_color, wled_ip=DEFAULT_WLED_IP):
    led_zones = {
        "hot": (0, 15),
        "moderate": (15, 30),
        "cold": (30, 45),
        "extreme_cold": (45, 60)
    }

    color_map = {
        "hot": led_hot_color,
        "moderate": led_moderate_color,
        "cold": led_cold_color,
        "extreme_cold": led_extreme_cold_color
    }

    chosen_color = color_map.get(category, led_extreme_cold_color)
    rgb = color_name_to_rgb(chosen_color)

    segments = []

    for index, (zone_name, zone_range) in enumerate(led_zones.items()):
        start_led, stop_led = zone_range

        if zone_name == category:
            zone_color = rgb
        else:
            zone_color = [0, 0, 0]

        segments.append({
            "id": index,
            "start": start_led,
            "stop": stop_led,
            "on": True,
            "bri": 180,
            "col": [zone_color],
            "fx": 0
        })

    payload = {
        "on": True,
        "bri": 180,
        "seg": segments
    }

    success = set_wled_state(payload, wled_ip)
    return chosen_color, rgb, success    

# Recommendation logic
def get_clothing_recommendation(temp, preferences):
    if preferences is None or temp is None:
        return None

    hot_min = preferences[0]
    hot_max = preferences[1]
    moderate_min = preferences[2]
    moderate_max = preferences[3]
    cold_min = preferences[4]
    cold_max = preferences[5]

    hot_clothing = preferences[6]
    moderate_clothing = preferences[7]
    cold_clothing = preferences[8]
    extreme_cold_clothing = preferences[9]

    if hot_min <= temp <= hot_max:
        return preferences[6]
    elif moderate_min <= temp <= moderate_max:
        return preferences[7]
    elif cold_min <= temp <= cold_max:
        return preferences[8]
    else:
        return preferences[9]



# DASHBOARD PAGE
@app.get("/dashboard/{profile_id}", response_class=HTMLResponse)
def dashboard(profile_id: int, request: Request):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM users WHERE id = ?", (profile_id,))
    profile = cur.fetchone()

    cur.execute("""
        SELECT hot_min, hot_max,
               moderate_min, moderate_max,
               cold_min, cold_max,
               hot_clothing, moderate_clothing, cold_clothing, extreme_cold_clothing
        FROM preferences
        WHERE user_id = ?
    """, (profile_id,))
    preferences = cur.fetchone()

    cur.execute("""
        SELECT location, temperature_unit,
               led_hot_color, led_moderate_color, led_cold_color, led_extreme_cold_color,
               theme
        FROM settings
        WHERE user_id = ?
    """, (profile_id,))
    settings = cur.fetchone()

    conn.close()

    if not settings:
        settings = (
            "Arlington,TX,US",
            "fahrenheit",
            "red",
            "yellow",
            "blue",
            "purple",
            "dark"
        )

    location = settings[0]
    temperature_unit = settings[1]
    led_hot_color = settings[2]
    led_moderate_color = settings[3]
    led_cold_color = settings[4]
    led_extreme_cold_color = settings[5]
    theme = settings[6]

    closet_name, wled_ip, closet_status = get_closet_for_profile(profile_id)

    controller_online = False

    if wled_ip:
        controller_online = check_wled_online(wled_ip)

    weather = get_current_weather(location, temperature_unit)

    recommendation_text = None
    city_name = "Unknown"
    selected_led_color = None
    selected_led_rgb = None
    wled_applied = False
    weather_category = None

    display_preferences = preferences
    display_unit_symbol = "°F"

    if weather:
        temp_for_logic = weather["temperature"]

        if temperature_unit == "celsius":
            temp_for_logic = c_to_f(temp_for_logic)

        recommendation_text = get_clothing_recommendation(temp_for_logic, preferences)
        weather_category = get_weather_category(temp_for_logic, preferences)
        city_name = f'{weather["city"]}, {weather["country"]}'

        if weather_category and wled_ip:
            selected_led_color, selected_led_rgb, wled_applied = apply_dashboard_led_color(
                weather_category,
                led_hot_color,
                led_moderate_color,
                led_cold_color,
                led_extreme_cold_color,
                wled_ip
            )

    if preferences and temperature_unit == "celsius":
        display_preferences = (
            round(f_to_c(preferences[0]), 1),
            round(f_to_c(preferences[1]), 1),
            round(f_to_c(preferences[2]), 1),
            round(f_to_c(preferences[3]), 1),
            round(f_to_c(preferences[4]), 1),
            round(f_to_c(preferences[5]), 1),
            preferences[6],
            preferences[7],
            preferences[8],
            preferences[9]
        )
        display_unit_symbol = "°C"
    elif preferences:
        display_unit_symbol = "°F"

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "profile": profile,
            "preferences": preferences,
            "display_preferences": display_preferences,
            "display_unit_symbol": display_unit_symbol,
            "weather": weather,
            "recommendation_text": recommendation_text,
            "city_name": city_name,
            "theme": theme,
            "temperature_unit": temperature_unit,
            "led_hot_color": led_hot_color,
            "led_moderate_color": led_moderate_color,
            "led_cold_color": led_cold_color,
            "led_extreme_cold_color": led_extreme_cold_color,
            "weather_category": weather_category,
            "closet_name": closet_name,
            "closet_status": closet_status,
            "wled_ip": wled_ip,
            "controller_online": controller_online,
            "temperature_unit": temperature_unit,
            "location": location,
            "last_weather_update": datetime.now().strftime("%I:%M %p"),
            "weather_api_status": "Connected" if weather else "Offline",
            "selected_led_color": selected_led_color,
            "selected_led_rgb": selected_led_rgb,
            "wled_applied": wled_applied,


        }
    )


@app.get("/preferences/{profile_id}", response_class=HTMLResponse)
def preferences_page(profile_id: int, request: Request):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM users WHERE id = ?", (profile_id,))
    profile = cur.fetchone()

    conn.close()

    return templates.TemplateResponse(
        request,
        "preferences.html",
        {
            "profile": profile
        }
    )

@app.post("/preferences/{profile_id}")
def save_preferences(
    profile_id: int,
    hot_min: int = Form(...),
    hot_max: int = Form(...),
    moderate_min: int = Form(...),
    moderate_max: int = Form(...),
    cold_min: int = Form(...),
    cold_max: int = Form(...),
    hot_clothing: str = Form(...),
    moderate_clothing: str = Form(...),
    cold_clothing: str = Form(...),
    extreme_cold_clothing: str = Form(...)
):
        # Validate each individual range.
    if hot_min > hot_max:
        return HTMLResponse(
            "<h2>Hot minimum cannot be greater than hot maximum.</h2>"
            f'<a href="/preferences/{profile_id}">Go Back</a>',
            status_code=400
        )

    if moderate_min > moderate_max:
        return HTMLResponse(
            "<h2>Moderate minimum cannot be greater than moderate maximum.</h2>"
            f'<a href="/preferences/{profile_id}">Go Back</a>',
            status_code=400
        )

    if cold_min > cold_max:
        return HTMLResponse(
            "<h2>Cold minimum cannot be greater than cold maximum.</h2>"
            f'<a href="/preferences/{profile_id}">Go Back</a>',
            status_code=400
        )

    # Require continuous ranges with no gaps or overlaps.
    if hot_min != moderate_max + 1:
        return HTMLResponse(
            "<h2>Hot minimum must be exactly one degree above Moderate maximum.</h2>"
            f'<a href="/preferences/{profile_id}">Go Back</a>',
            status_code=400
        )

    if moderate_min != cold_max + 1:
        return HTMLResponse(
            "<h2>Moderate minimum must be exactly one degree above Cold maximum.</h2>"
            f'<a href="/preferences/{profile_id}">Go Back</a>',
            status_code=400
        )

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT temperature_unit FROM settings WHERE user_id = ?", (profile_id,))
    unit_row = cur.fetchone()
    temperature_unit = unit_row[0] if unit_row else "fahrenheit"

    if temperature_unit == "celsius":
        hot_min = c_to_f(hot_min)
        hot_max = c_to_f(hot_max)
        moderate_min = c_to_f(moderate_min)
        moderate_max = c_to_f(moderate_max)
        cold_min = c_to_f(cold_min)
        cold_max = c_to_f(cold_max)

    cur.execute("SELECT user_id FROM preferences WHERE user_id = ?", (profile_id,))
    existing = cur.fetchone()

    if existing:
        cur.execute("""
            UPDATE preferences
            SET hot_min = ?,
                hot_max = ?,
                moderate_min = ?,
                moderate_max = ?,
                cold_min = ?,
                cold_max = ?,
                hot_clothing = ?,
                moderate_clothing = ?,
                cold_clothing = ?,
                extreme_cold_clothing = ?
            WHERE user_id = ?
        """, (
            hot_min,
            hot_max,
            moderate_min,
            moderate_max,
            cold_min,
            cold_max,
            hot_clothing,
            moderate_clothing,
            cold_clothing,
            extreme_cold_clothing,
            profile_id
        ))
    else:
        cur.execute("""
            INSERT INTO preferences (
                user_id,
                hot_min,
                hot_max,
                moderate_min,
                moderate_max,
                cold_min,
                cold_max,
                hot_clothing,
                moderate_clothing,
                cold_clothing,
                extreme_cold_clothing
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile_id,
            hot_min,
            hot_max,
            moderate_min,
            moderate_max,
            cold_min,
            cold_max,
            hot_clothing,
            moderate_clothing,
            cold_clothing,
            extreme_cold_clothing
        ))

    conn.commit()
    conn.close()

    return RedirectResponse(url=f"/dashboard/{profile_id}", status_code=303)


# RECOMMENDATION PLACEHOLDER
@app.get("/recommendation/{profile_id}", response_class=HTMLResponse)
def recommendation(profile_id: int):
    return f"""
    <h1>Recommendation Page for Profile {profile_id}</h1>
    <p>This page will be built later.</p>
    <a href="/">Go Back</a>
    """


@app.get("/debug-db")
def debug_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(preferences)")
    columns = cur.fetchall()

    conn.close()
    return {
        "message": "Connected Sucessfully",
        "columns": columns
    }


def get_user_settings(profile_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT location, temperature_unit,
               led_hot_color, led_moderate_color, led_cold_color, led_extreme_cold_color,
               theme
        FROM settings
        WHERE user_id = ?
    """, (profile_id,))
    settings = cur.fetchone()

    conn.close()

    if settings:
        return settings

    return (
        "Arlington,TX,US",
        "fahrenheit",
        "red",
        "yellow",
        "blue",
        "purple",
        "dark"
    )


# ROUTE TO SAVE SETTING
@app.post("/settings/{profile_id}")
def save_settings(
    profile_id: int,
    location: str = Form(...),
    temperature_unit: str = Form(...),
    led_hot_color: str = Form(...),
    led_moderate_color: str = Form(...),
    led_cold_color: str = Form(...),
    led_extreme_cold_color: str = Form(...),
    theme: str = Form(...)
):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM settings WHERE user_id = ?", (profile_id,))
    existing = cur.fetchone()

    if existing:
        cur.execute("""
            UPDATE settings
            SET location = ?,
                temperature_unit = ?,
                led_hot_color = ?,
                led_moderate_color = ?,
                led_cold_color = ?,
                led_extreme_cold_color = ?,
                theme = ?
            WHERE user_id = ?
        """, (
            location,
            temperature_unit,
            led_hot_color,
            led_moderate_color,
            led_cold_color,
            led_extreme_cold_color,
            theme,
            profile_id
        ))
    else:
        cur.execute("""
            INSERT INTO settings (
                user_id, location, temperature_unit,
                led_hot_color, led_moderate_color, led_cold_color, led_extreme_cold_color,
                theme
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile_id,
            location,
            temperature_unit,
            led_hot_color,
            led_moderate_color,
            led_cold_color,
            led_extreme_cold_color,
            theme
        ))

    conn.commit()
    conn.close()

    return RedirectResponse(url=f"/dashboard/{profile_id}", status_code=303)


@app.get("/test-wled-zone/{category}")
def test_wled_zone(category: str, color: str = "white"):
    led_zones = {
        "hot": (0, 15),
        "moderate": (15, 30),
        "cold": (30, 45),
        "extreme_cold": (45, 60)
    }

    if category not in led_zones:
        return {"success": False, "error": "Invalid category"}

    rgb = color_name_to_rgb(color)

    segments = []

    for index, (zone_name, zone_range) in enumerate(led_zones.items()):
        start_led, stop_led = zone_range
        zone_color = rgb if zone_name == category else [0, 0, 0]

        segments.append({
            "id": index,
            "start": start_led,
            "stop": stop_led,
            "on": True,
            "bri": 255,
            "col": [zone_color],
            "fx": 0
        })

    payload = {
        "on": True,
        "bri": 255,
        "seg": segments
    }

    success = set_wled_state(payload)

    return {
        "success": success,
        "category": category,
        "color": color,
        "rgb": rgb,
        "zones": led_zones
    }

    #Temporary
@app.get("/test-wled")
def test_wled():
    info = get_wled_info()
    state = get_wled_state()

    return {
        "info_connected": info is not None,
        "state_connected": state is not None,
        "info": info,
        "state": state
    }