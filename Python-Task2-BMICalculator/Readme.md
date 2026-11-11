Calculateur d'IMC (niveau Avancé)

Projet Oasis Infobyte SIP – Python Programming – Task 2.

Application de bureau en tkinter qui calcule l'indice de masse corporelle (IMC), enregistre l'historique de chaque utilisateur dans une base SQLite et affiche l'évolution de l'IMC avec matplotlib.

Fonctionnalités
Interface graphique (aucune ligne de commande)
Champs avec étiquettes : utilisateur, poids (kg), taille (m) + bouton Calculer
Formule : IMC = poids / taille², résultat arrondi à 2 décimales
Catégories avec couleurs :
< 18.5 : Maigreur (bleu)
18.5 – 24.9 : Normal (vert)
25 – 29.9 : Surpoids (orange)
≥ 30 : Obésité (rouge)
Validation : champs vides, texte non numérique, valeurs négatives ou irréalistes (la virgule décimale est acceptée)
Multi-utilisateurs : chaque nom a son propre historique
Historique stocké dans bmi_records.db (SQLite)
Graphique de la tendance de l'IMC dans le temps, avec zones colorées par catégorie
Gestion des erreurs de lecture/écriture de la base (boîtes de dialogue)
Installation
bash
pip install -r requirements.txt

tkinter est inclus avec Python (sous Linux : sudo apt install python3-tk).

Lancer
bash
python bmi_calculator.py
Utilisation
Tapez un nom d'utilisateur (ou choisissez-en un existant).
Entrez le poids et la taille, puis cliquez sur Calculer.
L'historique s'affiche en bas. Cliquez sur Voir le graphique pour la courbe.
Structure
Python-Task2-BMICalculator/
├── bmi_calculator.py
├── requirements.txt
├── README.md
└── screenshots/   (ajoutez vos captures d'écran ici)
Auteur

Lopamba Vodieu Vodieu – Stagiaire Python, Oasis Infobyte