"""
Calculateur d'IMC - Niveau Avance (Oasis Infobyte SIP, Python Task 2)

Fonctionnalites :
- Interface graphique tkinter (aucune ligne de commande)
- Champs avec etiquettes + bouton "Calculer"
- Resultat colore selon la categorie
- Multi-utilisateurs (noms)
- Historique stocke dans SQLite
- Graphique de l'evolution de l'IMC (matplotlib)
- Gestion des erreurs de lecture/ecriture de la base de donnees
"""

import sqlite3
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

DB_PATH = Path(__file__).with_name("bmi_records.db")

# Limites raisonnables pour la validation
WEIGHT_MIN, WEIGHT_MAX = 1.0, 500.0  # kg
HEIGHT_MIN, HEIGHT_MAX = 0.3, 2.5    # m


# ----------------------------------------------------------------------
# Logique metier
# ----------------------------------------------------------------------
def calculate_bmi(weight: float, height: float) -> float:
    """IMC = poids / taille^2"""
    return weight / (height ** 2)


def classify_bmi(bmi: float):
    """Retourne (categorie, couleur) selon les seuils standards."""
    if bmi < 18.5:
        return "Maigreur (Underweight)", "#1f77b4"
    if bmi < 25:
        return "Normal", "#2e9e44"
    if bmi < 30:
        return "Surpoids (Overweight)", "#e08a00"
    return "Obésité (Obese)", "#d62728"


def parse_positive_number(text: str, label: str, low: float, high: float) -> float:
    """Convertit un texte en nombre et valide la valeur. Leve ValueError."""
    text = text.strip().replace(",", ".")
    if not text:
        raise ValueError(f"Le champ « {label} » est vide.")
    try:
        value = float(text)
    except ValueError:
        raise ValueError(f"« {label} » doit être un nombre (ex : 70 ou 1.75).")
    if value <= 0:
        raise ValueError(f"« {label} » doit être positif.")
    if not (low <= value <= high):
        raise ValueError(f"« {label} » doit être entre {low} et {high}.")
    return value


# ----------------------------------------------------------------------
# Base de donnees SQLite
# ----------------------------------------------------------------------
class Database:
    def __init__(self, path: Path):
        self.path = path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS users (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT NOT NULL UNIQUE
                   )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS records (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       user_id INTEGER NOT NULL,
                       weight REAL NOT NULL,
                       height REAL NOT NULL,
                       bmi REAL NOT NULL,
                       category TEXT NOT NULL,
                       created_at TEXT NOT NULL,
                       FOREIGN KEY (user_id) REFERENCES users(id)
                   )"""
            )

    def add_record(self, name, weight, height, bmi, category):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            conn.execute("INSERT OR IGNORE INTO users (name) VALUES (?)", (name,))
            user_id = conn.execute(
                "SELECT id FROM users WHERE name = ?", (name,)
            ).fetchone()[0]
            conn.execute(
                """INSERT INTO records
                   (user_id, weight, height, bmi, category, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, weight, height, round(bmi, 2), category, now),
            )

    def get_users(self):
        with self._connect() as conn:
            rows = conn.execute("SELECT name FROM users ORDER BY name").fetchall()
        return [r[0] for r in rows]

    def get_records(self, name):
        with self._connect() as conn:
            return conn.execute(
                """SELECT r.created_at, r.weight, r.height, r.bmi, r.category
                   FROM records r JOIN users u ON u.id = r.user_id
                   WHERE u.name = ?
                   ORDER BY r.created_at""",
                (name,),
            ).fetchall()


# ----------------------------------------------------------------------
# Interface graphique
# ----------------------------------------------------------------------
class BMIApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Calculateur d'IMC")
        self.geometry("620x680")
        self.minsize(560, 620)

        try:
            self.db = Database(DB_PATH)
        except sqlite3.Error as e:
            messagebox.showerror(
                "Erreur base de données",
                f"Impossible d'ouvrir la base de données :\n{e}",
            )
            self.destroy()
            raise SystemExit(1)

        self._build_ui()
        self.refresh_users()

    # ---------- construction de l'interface ----------
    def _build_ui(self):
        style = ttk.Style(self)
        style.configure("Title.TLabel", font=("Helvetica", 18, "bold"))
        style.configure("Big.TButton", font=("Helvetica", 11, "bold"), padding=6)

        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Calculateur d'IMC", style="Title.TLabel").pack(pady=(0, 12))

        form = ttk.LabelFrame(main, text="Nouvelle mesure", padding=12)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Utilisateur :").grid(row=0, column=0, sticky="w", pady=4)
        self.user_var = tk.StringVar()
        self.user_box = ttk.Combobox(form, textvariable=self.user_var)
        self.user_box.grid(row=0, column=1, sticky="ew", pady=4, padx=(8, 0))
        self.user_box.bind("<<ComboboxSelected>>", lambda e: self.refresh_history())

        ttk.Label(form, text="Poids (kg) :").grid(row=1, column=0, sticky="w", pady=4)
        self.weight_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.weight_var).grid(
            row=1, column=1, sticky="ew", pady=4, padx=(8, 0)
        )

        ttk.Label(form, text="Taille (m) :").grid(row=2, column=0, sticky="w", pady=4)
        self.height_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.height_var).grid(
            row=2, column=1, sticky="ew", pady=4, padx=(8, 0)
        )

        buttons = ttk.Frame(form)
        buttons.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky="ew")
        buttons.columnconfigure((0, 1), weight=1)
        ttk.Button(
            buttons, text="Calculer", style="Big.TButton", command=self.on_calculate
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(
            buttons, text="Voir le graphique", style="Big.TButton", command=self.show_graph
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # Resultat colore
        self.result_label = tk.Label(
            main,
            text="Entrez vos données puis cliquez sur « Calculer »",
            font=("Helvetica", 14, "bold"),
            fg="white",
            bg="#7f7f7f",
            pady=14,
            wraplength=540,
        )
        self.result_label.pack(fill="x", pady=12)

        # Historique
        hist = ttk.LabelFrame(main, text="Historique de l'utilisateur", padding=8)
        hist.pack(fill="both", expand=True)

        columns = ("date", "poids", "taille", "imc", "categorie")
        self.tree = ttk.Treeview(hist, columns=columns, show="headings", height=8)
        for col, text, width in [
            ("date", "Date", 130),
            ("poids", "Poids (kg)", 75),
            ("taille", "Taille (m)", 75),
            ("imc", "IMC", 60),
            ("categorie", "Catégorie", 160),
        ]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="center")
        scroll = ttk.Scrollbar(hist, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    # ---------- actions ----------
    def refresh_users(self):
        try:
            self.user_box["values"] = self.db.get_users()
        except sqlite3.Error as e:
            self._db_error("lecture des utilisateurs", e)

    def refresh_history(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        name = self.user_var.get().strip()
        if not name:
            return
        try:
            records = self.db.get_records(name)
        except sqlite3.Error as e:
            self._db_error("lecture de l'historique", e)
            return
        for date, weight, height, bmi, category in reversed(records):
            self.tree.insert("", "end", values=(date, weight, height, f"{bmi:.2f}", category))

    def on_calculate(self):
        name = self.user_var.get().strip()
        if not name:
            messagebox.showwarning("Utilisateur manquant", "Entrez ou choisissez un nom d'utilisateur.")
            return
        try:
            weight = parse_positive_number(self.weight_var.get(), "Poids", WEIGHT_MIN, WEIGHT_MAX)
            height = parse_positive_number(self.height_var.get(), "Taille", HEIGHT_MIN, HEIGHT_MAX)
        except ValueError as e:
            messagebox.showerror("Entrée invalide", str(e))
            return

        bmi = calculate_bmi(weight, height)
        category, color = classify_bmi(bmi)
        self.result_label.config(text=f"IMC : {bmi:.2f}\n{category}", bg=color)

        try:
            self.db.add_record(name, weight, height, bmi, category)
        except sqlite3.Error as e:
            self._db_error("enregistrement de la mesure", e)
            return

        self.refresh_users()
        self.refresh_history()

    def show_graph(self):
        name = self.user_var.get().strip()
        if not name:
            messagebox.showwarning("Utilisateur manquant", "Choisissez un utilisateur pour voir son graphique.")
            return
        try:
            records = self.db.get_records(name)
        except sqlite3.Error as e:
            self._db_error("lecture de l'historique", e)
            return
        if not records:
            messagebox.showinfo("Pas de données", f"Aucune mesure enregistrée pour « {name} ».")
            return

        dates = [datetime.strptime(r[0], "%Y-%m-%d %H:%M:%S") for r in records]
        values = [r[3] for r in records]

        win = tk.Toplevel(self)
        win.title(f"Évolution de l'IMC - {name}")
        win.geometry("700x480")

        fig = Figure(figsize=(7, 4.5), dpi=100)
        ax = fig.add_subplot(111)
        top = max(35, max(values) + 3)
        bottom = min(15, min(values) - 2)
        ax.axhspan(bottom, 18.5, color="#1f77b4", alpha=0.12)
        ax.axhspan(18.5, 25, color="#2e9e44", alpha=0.12)
        ax.axhspan(25, 30, color="#e08a00", alpha=0.12)
        ax.axhspan(30, top, color="#d62728", alpha=0.12)
        ax.plot(dates, values, marker="o", color="#333333", linewidth=2)
        ax.set_ylim(bottom, top)
        ax.set_title(f"Évolution de l'IMC de {name}")
        ax.set_xlabel("Date")
        ax.set_ylabel("IMC")
        ax.grid(True, alpha=0.3)
        fig.autofmt_xdate()
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _db_error(self, action, error):
        messagebox.showerror(
            "Erreur base de données",
            f"Erreur lors de la {action} :\n{error}",
        )


if __name__ == "__main__":
    BMIApp().mainloop()