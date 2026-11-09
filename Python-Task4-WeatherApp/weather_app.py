"""
Application meteo - Niveau Avance (Oasis Infobyte SIP, Python Task 4)

- Interface tkinter : champ ville, bouton "Obtenir la meteo", panneau de resultats
- Donnees OpenWeatherMap (offre gratuite) : meteo actuelle + previsions
- Icones meteo (URLs OpenWeatherMap + Pillow)
- Previsions des 6 prochaines heures et des 5 prochains jours
- Bouton pour basculer entre Celsius et Fahrenheit
- Bonus : detection automatique de la ville via ipinfo.io
- Toutes les erreurs sont affichees dans la fenetre (pas de print dans le terminal)

La cle API n'est JAMAIS ecrite dans le code : variable d'environnement
OPENWEATHER_API_KEY ou fichier config.json (voir config.example.json).
"""

import json
import os
import queue
import threading
import tkinter as tk
from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from tkinter import ttk

import requests
from PIL import Image, ImageTk

BASE_URL = "https://api.openweathermap.org/data/2.5"
ICON_URL = "https://openweathermap.org/img/wn/{icon}@2x.png"
IPINFO_URL = "https://ipinfo.io/json"
TIMEOUT = 10
CONFIG_PATH = Path(__file__).with_name("config.json")
DAYS_FR = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


class WeatherError(Exception):
    """Erreur affichable directement a l'utilisateur."""


# ----------------------------------------------------------------------
# Acces a l'API
# ----------------------------------------------------------------------
def load_api_key():
    key = os.environ.get("OPENWEATHER_API_KEY", "").strip()
    if not key and CONFIG_PATH.exists():
        try:
            key = json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("api_key", "").strip()
        except (OSError, ValueError):
            raise WeatherError("Le fichier config.json est illisible ou mal formé.")
    if not key or key == "VOTRE_CLE_ICI":
        raise WeatherError(
            "Clé API manquante. Copiez config.example.json en config.json "
            "et collez votre clé OpenWeatherMap."
        )
    return key


def api_get(endpoint, city, api_key):
    """Appelle l'API et traduit les erreurs en messages clairs."""
    try:
        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            params={"q": city, "appid": api_key, "units": "metric", "lang": "fr"},
            timeout=TIMEOUT,
        )
    except requests.Timeout:
        raise WeatherError("Délai dépassé : le serveur météo ne répond pas. Réessayez.")
    except requests.ConnectionError:
        raise WeatherError("Pas de connexion internet. Vérifiez votre réseau.")
    except requests.RequestException as e:
        raise WeatherError(f"Erreur réseau : {e}")

    if response.status_code == 401:
        raise WeatherError(
            "Clé API invalide. Si elle est toute neuve, attendez jusqu'à 2 heures "
            "qu'OpenWeatherMap l'active."
        )
    if response.status_code == 404:
        raise WeatherError(f"Ville introuvable : « {city} ». Vérifiez l'orthographe.")
    if response.status_code == 429:
        raise WeatherError("Trop de requêtes. Patientez une minute puis réessayez.")
    if response.status_code != 200:
        raise WeatherError(f"Erreur du serveur météo (code {response.status_code}).")
    try:
        return response.json()
    except ValueError:
        raise WeatherError("Réponse du serveur illisible.")


def get_city_from_ip():
    try:
        response = requests.get(IPINFO_URL, timeout=TIMEOUT)
        response.raise_for_status()
        city = response.json().get("city", "").strip()
    except requests.Timeout:
        raise WeatherError("Détection de la position : délai dépassé.")
    except (requests.RequestException, ValueError):
        raise WeatherError("Impossible de détecter votre position automatiquement.")
    if not city:
        raise WeatherError("Votre ville n'a pas pu être déterminée.")
    return city


# ----------------------------------------------------------------------
# Traitement des donnees (fonctions pures)
# ----------------------------------------------------------------------
def to_local(ts, tz_offset):
    """Timestamp UTC -> datetime a l'heure locale de la ville."""
    return datetime.fromtimestamp(ts + tz_offset, tz=timezone.utc)


def build_hourly(current, forecast_items, hours=6):
    """
    L'API gratuite donne des prevision toutes les 3 h.
    On interpole lineairement la temperature pour obtenir 6 points horaires.
    """
    first = current["weather"][0]
    anchor = {
        "dt": current["dt"],
        "temp": current["main"]["temp"],
        "icon": first["icon"],
        "description": first["description"],
    }
    points = [anchor] + [
        {
            "dt": it["dt"],
            "temp": it["main"]["temp"],
            "icon": it["weather"][0]["icon"],
            "description": it["weather"][0]["description"],
        }
        for it in forecast_items
        if it["dt"] > anchor["dt"]
    ]
    points.sort(key=lambda p: p["dt"])

    result = []
    for h in range(1, hours + 1):
        t = anchor["dt"] + h * 3600
        for a, b in zip(points, points[1:]):
            if b["dt"] == a["dt"]:
                continue
            if a["dt"] <= t <= b["dt"]:
                ratio = (t - a["dt"]) / (b["dt"] - a["dt"])
                nearest = a if ratio < 0.5 else b
                result.append(
                    {
                        "dt": t,
                        "temp": a["temp"] + (b["temp"] - a["temp"]) * ratio,
                        "icon": nearest["icon"],
                        "description": nearest["description"],
                    }
                )
                break
    return result


def build_daily(forecast_items, tz_offset, today, days=5):
    """Regroupe les previsions par jour : min, max, icone proche de midi."""
    groups = defaultdict(list)
    for it in forecast_items:
        local = to_local(it["dt"], tz_offset)
        groups[local.date()].append((local, it))

    result = []
    for date in sorted(groups):
        if date <= today:
            continue
        entries = groups[date]
        tmin = min(it["main"]["temp_min"] for _, it in entries)
        tmax = max(it["main"]["temp_max"] for _, it in entries)
        _, noon = min(entries, key=lambda e: abs(e[0].hour - 12))
        result.append(
            {
                "date": date,
                "tmin": tmin,
                "tmax": tmax,
                "icon": noon["weather"][0]["icon"].replace("n", "d"),
                "description": noon["weather"][0]["description"],
            }
        )
        if len(result) == days:
            break
    return result


def fmt_temp(celsius, unit):
    if unit == "F":
        return f"{celsius * 9 / 5 + 32:.0f}°F"
    return f"{celsius:.0f}°C"


def fetch_weather(city):
    key = load_api_key()
    current = api_get("weather", city, key)
    forecast = api_get("forecast", city, key)
    items = forecast.get("list", [])
    tz = current.get("timezone", 0)
    today = to_local(current["dt"], tz).date()
    return {
        "current": current,
        "hourly": build_hourly(current, items),
        "daily": build_daily(items, tz, today),
        "tz": tz,
    }


def download_icons(data):
    codes = {data["current"]["weather"][0]["icon"]}
    codes |= {h["icon"] for h in data["hourly"]}
    codes |= {d["icon"] for d in data["daily"]}
    icons = {}
    for code in codes:
        try:
            r = requests.get(ICON_URL.format(icon=code), timeout=TIMEOUT)
            if r.status_code == 200:
                icons[code] = r.content
        except requests.RequestException:
            pass  # une icone manquante n'empeche pas l'affichage
    return icons


# ----------------------------------------------------------------------
# Interface
# ----------------------------------------------------------------------
class WeatherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Application météo")
        self.geometry("800x720")
        self.minsize(720, 660)

        self.unit = "C"
        self.data = None
        self.icon_bytes = {}
        self.photos = {}
        self.queue = queue.Queue()
        self.city_var = tk.StringVar()

        self._build_ui()
        self.after(100, self._poll_queue)

    def _build_ui(self):
        style = ttk.Style(self)
        style.configure("Big.TButton", font=("Helvetica", 11, "bold"), padding=5)
        main = ttk.Frame(self, padding=14)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Application météo", font=("Helvetica", 20, "bold")).pack(pady=(0, 10))

        top = ttk.Frame(main)
        top.pack(fill="x")
        top.columnconfigure(0, weight=1)
        self.entry = ttk.Entry(top, textvariable=self.city_var, font=("Helvetica", 12))
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 6), ipady=4)
        self.entry.bind("<Return>", lambda e: self.on_get_weather())
        self.entry.focus()
        self.btn_get = ttk.Button(top, text="Obtenir la météo", style="Big.TButton", command=self.on_get_weather)
        self.btn_get.grid(row=0, column=1, padx=3)
        self.btn_ip = ttk.Button(top, text="📍 Ma position", style="Big.TButton", command=self.on_locate)
        self.btn_ip.grid(row=0, column=2, padx=3)
        self.btn_unit = ttk.Button(top, text="Passer en °F", style="Big.TButton", command=self.toggle_unit)
        self.btn_unit.grid(row=0, column=3, padx=(3, 0))

        # messages (erreurs / chargement) dans la fenetre
        self.message = tk.Label(main, text="", fg="#d62728", font=("Helvetica", 11), wraplength=720, justify="left")
        self.message.pack(fill="x", pady=6)

        # meteo actuelle
        cur = ttk.LabelFrame(main, text="Météo actuelle", padding=10)
        cur.pack(fill="x")
        self.cur_icon = tk.Label(cur)
        self.cur_icon.pack(side="left", padx=(0, 14))
        info = ttk.Frame(cur)
        info.pack(side="left", fill="x", expand=True)
        self.lbl_city = ttk.Label(info, text="—", font=("Helvetica", 16, "bold"))
        self.lbl_city.pack(anchor="w")
        self.lbl_temp = ttk.Label(info, text="", font=("Helvetica", 34, "bold"))
        self.lbl_temp.pack(anchor="w")
        self.lbl_desc = ttk.Label(info, text="", font=("Helvetica", 13))
        self.lbl_desc.pack(anchor="w")
        self.lbl_details = ttk.Label(info, text="", font=("Helvetica", 11), justify="left")
        self.lbl_details.pack(anchor="w", pady=(6, 0))

        self.hourly_frame = ttk.LabelFrame(main, text="Prochaines 6 heures", padding=8)
        self.hourly_frame.pack(fill="x", pady=10)
        self.daily_frame = ttk.LabelFrame(main, text="5 prochains jours", padding=8)
        self.daily_frame.pack(fill="x")

    # ---------- actions ----------
    def on_get_weather(self):
        city = self.city_var.get().strip()
        if not city:
            self._show_error("Veuillez entrer le nom d'une ville.")
            return
        self._start(city, use_ip=False)

    def on_locate(self):
        self._start(None, use_ip=True)

    def toggle_unit(self):
        self.unit = "F" if self.unit == "C" else "C"
        self.btn_unit.config(text="Passer en °C" if self.unit == "F" else "Passer en °F")
        if self.data:
            self.render()

    def _start(self, city, use_ip):
        self._set_busy(True)
        self.message.config(text="Chargement…", fg="#555555")
        threading.Thread(target=self._worker, args=(city, use_ip), daemon=True).start()

    def _worker(self, city, use_ip):
        """Tourne dans un thread pour ne pas figer la fenetre."""
        try:
            if use_ip:
                city = get_city_from_ip()
            data = fetch_weather(city)
            data["icons"] = download_icons(data)
            data["query"] = city
            self.queue.put(("ok", data))
        except WeatherError as e:
            self.queue.put(("error", str(e)))
        except Exception as e:  # filet de securite
            self.queue.put(("error", f"Erreur inattendue : {e}"))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                self._set_busy(False)
                if kind == "ok":
                    self.data = payload
                    self.icon_bytes.update(payload["icons"])
                    self.city_var.set(payload["query"])
                    self.message.config(text="")
                    self.render()
                else:
                    self._show_error(payload)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _set_busy(self, busy):
        state = "disabled" if busy else "normal"
        self.btn_get.config(state=state)
        self.btn_ip.config(state=state)

    def _show_error(self, text):
        self.message.config(text=f"⚠ {text}", fg="#d62728")

    # ---------- affichage ----------
    def _photo(self, code, size):
        raw = self.icon_bytes.get(code)
        if raw is None:
            return None
        key = (code, size)
        if key not in self.photos:
            img = Image.open(BytesIO(raw)).convert("RGBA").resize((size, size))
            self.photos[key] = ImageTk.PhotoImage(img)
        return self.photos[key]

    def render(self):
        d = self.data
        cur = d["current"]
        weather = cur["weather"][0]
        temp_c = cur["main"]["temp"]
        other = "F" if self.unit == "C" else "C"

        country = cur.get("sys", {}).get("country", "")
        self.lbl_city.config(text=f"{cur.get('name', '')}, {country}".strip(", "))
        self.lbl_temp.config(text=fmt_temp(temp_c, self.unit))
        self.lbl_desc.config(text=weather["description"].capitalize())
        wind = cur.get("wind", {}).get("speed", 0)
        self.lbl_details.config(
            text=(
                f"Température : {fmt_temp(temp_c, self.unit)} ({fmt_temp(temp_c, other)})\n"
                f"Humidité : {cur['main']['humidity']} %\n"
                f"Vent : {wind:.1f} m/s ({wind * 3.6:.0f} km/h)"
            )
        )
        photo = self._photo(weather["icon"], 100)
        self.cur_icon.config(image=photo if photo else "", text="" if photo else "?")
        self.cur_icon.image = photo

        self._fill_row(
            self.hourly_frame,
            [
                (to_local(h["dt"], d["tz"]).strftime("%Hh%M"), h["icon"], fmt_temp(h["temp"], self.unit))
                for h in d["hourly"]
            ],
        )
        self._fill_row(
            self.daily_frame,
            [
                (
                    f"{DAYS_FR[x['date'].weekday()]} {x['date'].strftime('%d/%m')}",
                    x["icon"],
                    f"{fmt_temp(x['tmax'], self.unit)} / {fmt_temp(x['tmin'], self.unit)}",
                )
                for x in d["daily"]
            ],
        )

    def _fill_row(self, frame, items):
        for child in frame.winfo_children():
            child.destroy()
        for i, (title, icon, temp) in enumerate(items):
            frame.columnconfigure(i, weight=1)
            cell = ttk.Frame(frame)
            cell.grid(row=0, column=i, sticky="n", padx=4)
            ttk.Label(cell, text=title, font=("Helvetica", 10, "bold")).pack()
            photo = self._photo(icon, 56)
            lbl = tk.Label(cell, image=photo) if photo else tk.Label(cell, text="?")
            lbl.image = photo
            lbl.pack()
            ttk.Label(cell, text=temp, font=("Helvetica", 11)).pack()


if __name__ == "__main__":
    WeatherApp().mainloop()
