# BMI Calculator (Advanced Level)

**Oasis Infobyte SIP – Python Programming – Task 2** project[span_0](start_span)[span_0](end_span).

A desktop application built with **tkinter** that calculates Body Mass Index (BMI), saves each user's history in a SQLite database, and visualizes BMI trends over time using `matplotlib`.

## Features

- Graphical User Interface (no command line)
- Labeled input fields: username, weight (kg), height (m) + **Calculate** button
- Formula: $\text{BMI} = \text{weight} / \text{height}^2$, result rounded to 2 decimal places
- Color-coded categories:
  - $< 18.5$: Underweight (Blue)
  - $18.5 – 24.9$: Normal (Green)
  - $25 – 29.9$: Overweight (Orange)
  - $\geq 30$: Obesity (Red)
- Validation: handles empty fields, non-numeric text, negative or unrealistic values (decimal commas are accepted)
- Multi-user support: each name maintains its own history
- History stored in `bmi_records.db` (SQLite)
- Graphical trend chart of BMI over time with color-coded category zones
- Error handling for database read/write operations via dialog boxes

## Installation

bash
pip install -r requirements.txt
Run
python bmi_calculator.py
Usage
Type a username (or select an existing one).
Enter your weight and height, then click Calculate.
The history is displayed at the bottom. Click View Chart to see the trend graph.
Structure
Python-Task2-BMICalculator/
├── bmi_calculator.py
├── requirements.txt
├── README.md
└── screenshots/   (add your screenshots here)
Author
Lopamba Vodieu Vodieu – Python Intern, Oasis Infobyte  
