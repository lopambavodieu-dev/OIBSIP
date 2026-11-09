# Application météo (niveau Avancé)

Projet **Oasis Infobyte SIP – Python Programming – Task 4**.

Application de bureau en **tkinter** qui affiche la météo en temps réel grâce à l'API **OpenWeatherMap** (offre gratuite).

## Fonctionnalités

- Fenêtre avec champ ville, bouton **Obtenir la météo** et panneau de résultats
- Météo actuelle : température (°C et °F), humidité, description, vitesse du vent
- Icônes météo officielles OpenWeatherMap (via `requests` et `Pillow`)
- Prévisions des **6 prochaines heures**
- Prévisions des **5 prochains jours** (min / max)
- Bouton pour basculer **Celsius / Fahrenheit**
- Bonus : bouton **📍 Ma position** (ville détectée via `ipinfo.io`)
- Erreurs affichées dans la fenêtre : ville introuvable, délai dépassé, pas de connexion, clé API invalide, champ vide
- Les appels réseau tournent dans un thread : la fenêtre ne se fige pas

## Remarque sur les prévisions horaires

L'API gratuite fournit des prévisions toutes les 3 heures. Les 6 points horaires sont obtenus par **interpolation linéaire** de la température entre ces points ; ce sont donc des estimations.

## Installation

```bash
pip install -r requirements.txt
```

tkinter est inclus avec Python (Linux : `sudo apt install python3-tk`).

## Clé API (gratuite)

1. Créez un compte sur [openweathermap.org](https://openweathermap.org) et récupérez votre clé dans « API keys ».
2. Copiez `config.example.json` en `config.json` et remplacez `VOTRE_CLE_ICI` par votre clé.
   (Autre option : définir la variable d'environnement `OPENWEATHER_API_KEY`.)
3. Une clé neuve peut mettre jusqu'à 2 heures avant de fonctionner.

`config.json` est dans `.gitignore` : **votre clé n'est jamais envoyée sur GitHub**.

## Lancer

```bash
python weather_app.py
```

## Confidentialité

Le nom de la ville est envoyé à OpenWeatherMap. Avec « Ma position », votre adresse IP est envoyée à ipinfo.io pour deviner votre ville. Rien n'est enregistré sur le disque.

## Structure

```
Python-Task4-WeatherApp/
├── weather_app.py
├── requirements.txt
├── config.example.json
├── .gitignore
├── README.md
└── screenshots/
```

## Auteur

Lopamba Vodieu Vodieu – Stagiaire Python, Oasis Infobyte
