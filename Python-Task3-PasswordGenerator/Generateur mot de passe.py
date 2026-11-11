"""
Generateur de mots de passe - Niveau Avance (Oasis Infobyte SIP, Python Task 3)

- Interface tkinter (curseur + spinbox pour la longueur, cases a cocher pour les types)
- Module `secrets` (generation cryptographiquement sure)
- Indicateur de force (Faible / Moyen / Fort) avec barre coloree
- Au moins un caractere de chaque type selectionne est garanti
- Copie automatique dans le presse-papiers (pyperclip) + bouton "Copier"
- Option pour exclure les caracteres ambigus (0, O, o, 1, l, I, |)
- Historique des 5 derniers mots de passe (session uniquement, jamais ecrit sur disque)
"""

import math
import secrets
import string
import tkinter as tk
from collections import deque
from tkinter import messagebox, ttk

try:
    import pyperclip
except ImportError:  # pyperclip est optionnel : on bascule sur le presse-papiers tkinter
    pyperclip = None

MIN_LENGTH = 8
MAX_LENGTH = 64
SYMBOLS = "!@#$%^&*()-_=+[]{};:,.<>?/~"
AMBIGUOUS = "0Oo1lI|"


# ----------------------------------------------------------------------
# Logique
# ----------------------------------------------------------------------
def build_character_sets(upper, lower, digits, symbols, exclude_ambiguous):
    """Retourne la liste des jeux de caracteres selectionnes (sans les ambigus si demande)."""
    sets = []
    if upper:
        sets.append(string.ascii_uppercase)
    if lower:
        sets.append(string.ascii_lowercase)
    if digits:
        sets.append(string.digits)
    if symbols:
        sets.append(SYMBOLS)
    if exclude_ambiguous:
        sets = ["".join(c for c in s if c not in AMBIGUOUS) for s in sets]
    return sets


def generate_password(length, char_sets):
    """Genere un mot de passe avec `secrets`, avec au moins 1 caractere par jeu."""
    if length < MIN_LENGTH:
        raise ValueError(f"La longueur minimale est de {MIN_LENGTH} caractères.")
    if length > MAX_LENGTH:
        raise ValueError(f"La longueur maximale est de {MAX_LENGTH} caractères.")
    if len(char_sets) < 2:
        raise ValueError("Sélectionnez au moins 2 types de caractères.")

    # 1 caractere garanti de chaque type selectionne
    chars = [secrets.choice(s) for s in char_sets]
    pool = "".join(char_sets)
    chars += [secrets.choice(pool) for _ in range(length - len(chars))]
    secrets.SystemRandom().shuffle(chars)  # melange securise
    return "".join(chars)


def evaluate_strength(password, char_sets):
    """Retourne (label, couleur, ratio 0-1) selon l'entropie estimee."""
    pool_size = len(set("".join(char_sets)))
    entropy = len(password) * math.log2(pool_size) if pool_size > 1 else 0
    if entropy < 50:
        return "Faible", "#d62728", 0.33
    if entropy < 80:
        return "Moyen", "#e08a00", 0.66
    return "Fort", "#2e9e44", 1.0


# ----------------------------------------------------------------------
# Interface
# ----------------------------------------------------------------------
class PasswordApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Générateur de mots de passe")
        self.geometry("520x640")
        self.minsize(480, 600)

        self.length_var = tk.IntVar(value=16)
        self.upper_var = tk.BooleanVar(value=True)
        self.lower_var = tk.BooleanVar(value=True)
        self.digits_var = tk.BooleanVar(value=True)
        self.symbols_var = tk.BooleanVar(value=True)
        self.ambiguous_var = tk.BooleanVar(value=False)
        self.password_var = tk.StringVar()
        self.history = deque(maxlen=5)  # en memoire uniquement

        self._build_ui()

    def _build_ui(self):
        style = ttk.Style(self)
        style.configure("Title.TLabel", font=("Helvetica", 18, "bold"))
        style.configure("Big.TButton", font=("Helvetica", 11, "bold"), padding=6)

        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="Générateur de mots de passe", style="Title.TLabel").pack(pady=(0, 12))

        # --- Longueur ---
        length_frame = ttk.LabelFrame(main, text="Longueur", padding=10)
        length_frame.pack(fill="x")
        length_frame.columnconfigure(0, weight=1)
        self.scale = ttk.Scale(
            length_frame, from_=MIN_LENGTH, to=MAX_LENGTH, orient="horizontal",
            command=self._on_scale,
        )
        self.scale.set(self.length_var.get())
        self.scale.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.spin = ttk.Spinbox(
            length_frame, from_=MIN_LENGTH, to=MAX_LENGTH, width=5,
            textvariable=self.length_var, command=self._on_spin,
        )
        self.spin.grid(row=0, column=1)
        self.spin.bind("<KeyRelease>", lambda e: self._on_spin())

        # --- Types de caracteres ---
        types_frame = ttk.LabelFrame(main, text="Types de caractères (au moins 2)", padding=10)
        types_frame.pack(fill="x", pady=10)
        ttk.Checkbutton(types_frame, text="Majuscules (A-Z)", variable=self.upper_var).pack(anchor="w")
        ttk.Checkbutton(types_frame, text="Minuscules (a-z)", variable=self.lower_var).pack(anchor="w")
        ttk.Checkbutton(types_frame, text="Chiffres (0-9)", variable=self.digits_var).pack(anchor="w")
        ttk.Checkbutton(types_frame, text="Symboles (!@#$...)", variable=self.symbols_var).pack(anchor="w")
        ttk.Separator(types_frame).pack(fill="x", pady=6)
        ttk.Checkbutton(
            types_frame, text="Exclure les caractères ambigus (0, O, o, 1, l, I, |)",
            variable=self.ambiguous_var,
        ).pack(anchor="w")

        ttk.Button(main, text="Générer", style="Big.TButton", command=self.on_generate).pack(fill="x")

        # --- Resultat ---
        result_frame = ttk.LabelFrame(main, text="Mot de passe", padding=10)
        result_frame.pack(fill="x", pady=10)
        entry = ttk.Entry(
            result_frame, textvariable=self.password_var,
            font=("Courier", 14), state="readonly", justify="center",
        )
        entry.pack(fill="x")
        ttk.Button(result_frame, text="Copier dans le presse-papiers", command=self.copy_password).pack(
            fill="x", pady=(8, 0)
        )

        # --- Force ---
        strength_frame = ttk.Frame(main)
        strength_frame.pack(fill="x")
        self.strength_label = ttk.Label(strength_frame, text="Force : -", font=("Helvetica", 11, "bold"))
        self.strength_label.pack(anchor="w")
        self.strength_canvas = tk.Canvas(strength_frame, height=14, bg="#dddddd", highlightthickness=0)
        self.strength_canvas.pack(fill="x", pady=(4, 0))
        self.strength_bar = self.strength_canvas.create_rectangle(0, 0, 0, 14, width=0, fill="#dddddd")

        self.status_label = ttk.Label(main, text="", foreground="#2e9e44")
        self.status_label.pack(anchor="w", pady=(6, 0))

        # --- Historique ---
        hist_frame = ttk.LabelFrame(main, text="Historique (5 derniers, session uniquement)", padding=8)
        hist_frame.pack(fill="both", expand=True, pady=(8, 0))
        self.history_list = tk.Listbox(hist_frame, height=5, font=("Courier", 11))
        self.history_list.pack(fill="both", expand=True)

    # ---------- synchronisation curseur / spinbox ----------
    def _on_scale(self, value):
        self.length_var.set(int(float(value)))

    def _on_spin(self):
        try:
            value = int(self.spin.get())
        except ValueError:
            return
        if MIN_LENGTH <= value <= MAX_LENGTH:
            self.scale.set(value)

    # ---------- actions ----------
    def on_generate(self):
        try:
            length = int(self.spin.get())
        except ValueError:
            messagebox.showerror("Longueur invalide", "La longueur doit être un nombre entier.")
            return

        char_sets = build_character_sets(
            self.upper_var.get(), self.lower_var.get(),
            self.digits_var.get(), self.symbols_var.get(),
            self.ambiguous_var.get(),
        )
        try:
            password = generate_password(length, char_sets)
        except ValueError as e:
            messagebox.showerror("Paramètres invalides", str(e))
            return

        self.password_var.set(password)
        label, color, ratio = evaluate_strength(password, char_sets)
        self.strength_label.config(text=f"Force : {label}")
        self.update_idletasks()
        width = self.strength_canvas.winfo_width()
        self.strength_canvas.coords(self.strength_bar, 0, 0, width * ratio, 14)
        self.strength_canvas.itemconfig(self.strength_bar, fill=color)

        self.history.appendleft(password)
        self.history_list.delete(0, "end")
        for p in self.history:
            self.history_list.insert("end", p)

        # copie automatique a la generation
        self.copy_password(auto=True)

    def copy_password(self, auto=False):
        password = self.password_var.get()
        if not password:
            messagebox.showinfo("Rien à copier", "Générez d'abord un mot de passe.")
            return
        try:
            if pyperclip is not None:
                pyperclip.copy(password)
            else:
                raise RuntimeError("pyperclip non installé")
        except Exception:
            # solution de secours : presse-papiers tkinter
            self.clipboard_clear()
            self.clipboard_append(password)
        self.status_label.config(text="✔ Copié dans le presse-papiers" if not auto else "✔ Généré et copié automatiquement")


if __name__ == "__main__":
    PasswordApp().mainloop()