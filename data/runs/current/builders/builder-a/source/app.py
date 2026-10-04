from flask import Flask, render_template, request
import base64
from io import BytesIO

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


app = Flask(__name__)


# =========================================================
# RAINFALL DATA
# =========================================================

MONTHS = [
    "Jan", "Feb", "Mar", "Apr",
    "May", "Jun", "Jul", "Aug",
    "Sep", "Oct", "Nov", "Dec"
]

RAINFALL_DATA = {
    "Mumbai": {
        2025: [2,1,1,1,12,493,840,585,312,97,20,5],
        2024: [0,1,2,1,10,450,790,610,330,90,18,4],
        2023: [1,0,1,2,15,480,820,600,290,85,20,3],
    },
    "Pune": {
        2025: [1,2,5,8,35,160,210,175,120,55,20,5],
        2024: [2,1,4,7,40,150,225,180,110,50,18,6],
        2023: [1,2,6,10,32,145,205,170,115,48,17,4],
    },
    "Delhi": {
        2025: [18,20,15,8,30,85,210,190,125,45,5,10],
        2024: [15,18,20,6,35,90,195,180,120,40,8,12],
        2023: [20,15,12,9,28,80,220,175,110,42,6,9],
    },
    "Bengaluru": {
        2025: [2,4,10,35,70,85,105,110,150,170,90,25],
        2024: [3,5,12,30,65,90,100,120,140,160,85,30],
        2023: [2,6,15,32,72,82,108,105,145,155,95,28],
    },
    "Chennai": {
        2025: [20,10,5,8,40,65,90,110,130,280,310,180],
        2024: [18,12,6,7,38,70,85,105,125,260,295,190],
        2023: [22,11,7,9,35,60,95,105,140,270,300,175],
    },
    "Kolkata": {
        2025: [10,20,35,45,120,290,330,310,250,160,35,12],
        2024: [12,18,38,42,115,280,350,300,245,155,30,15],
        2023: [11,22,30,48,125,300,320,305,255,150,40,10],
    },
    "Hyderabad": {
        2025: [5,8,10,15,35,120,180,160,140,80,25,8],
        2024: [6,7,12,14,32,115,175,155,135,75,28,9],
        2023: [4,9,11,16,38,125,165,150,130,82,22,7],
    },
    "Ahmedabad": {
        2025: [2,1,2,3,10,70,180,160,120,50,10,3],
        2024: [1,2,2,4,12,65,170,150,115,45,12,2],
        2023: [2,1,3,2,9,72,175,155,125,48,11,3],
    },
    "Jaipur": {
        2025: [5,5,4,3,15,55,170,145,80,30,5,3],
        2024: [4,6,5,3,18,60,160,150,75,28,6,2],
        2023: [6,4,4,4,14,52,165,140,85,32,5,3],
    },
}


# =========================================================
# STATISTICAL ANALYSIS
# =========================================================

def analyze_monthly_data(values):
    series = pd.Series(values, dtype=float)

    total = float(series.sum())
    mean = float(series.mean())
    median = float(series.median())

    modes = series.mode()
    mode_text = "No repeated value" if modes.empty else ", ".join(
        f"{int(v)}" for v in modes.tolist()
    )

    variance = float(np.var(values, ddof=0))
    std_dev = float(np.std(values, ddof=0))
    minimum = float(series.min())
    maximum = float(series.max())
    data_range = maximum - minimum

    max_index = int(np.argmax(values))
    min_index = int(np.argmin(values))

    return {
        "total": total,
        "mean": mean,
        "median": median,
        "mode": mode_text,
        "variance": variance,
        "std_dev": std_dev,
        "minimum": minimum,
        "maximum": maximum,
        "range": data_range,
        "highest_month": MONTHS[max_index],
        "lowest_month": MONTHS[min_index],
    }


def annual_total(city, year):
    return float(np.sum(RAINFALL_DATA[city][year]))


def rainfall_status(total):
    if total < 500:
        return "Low"
    if total < 1500:
        return "Moderate"
    return "High"


# =========================================================
# MODERATE STATISTICAL PREDICTION
# =========================================================

def predict_next_year(city):
    y2023 = annual_total(city, 2023)
    y2024 = annual_total(city, 2024)
    y2025 = annual_total(city, 2025)

    # Recent years have greater importance.
    weighted_prediction = (
        y2023 * 0.20 +
        y2024 * 0.30 +
        y2025 * 0.50
    )

    trend_1 = y2024 - y2023
    trend_2 = y2025 - y2024
    average_trend = (trend_1 + trend_2) / 2

    # Small controlled adjustment so the trend does not dominate.
    trend_adjustment = average_trend * 0.10

    prediction = max(
        0.0,
        weighted_prediction + trend_adjustment
    )

    return {
        "prediction": prediction,
        "weighted_prediction": weighted_prediction,
        "average_trend": average_trend,
        "trend_adjustment": trend_adjustment,
    }


# =========================================================
# MATPLOTLIB CHART HELPERS
# =========================================================

def figure_to_base64(fig):
    buffer = BytesIO()
    fig.savefig(
        buffer,
        format="png",
        dpi=180,
        bbox_inches="tight",
        facecolor="white"
    )
    plt.close(fig)
    buffer.seek(0)
    return "data:image/png;base64," + base64.b64encode(
        buffer.read()
    ).decode("utf-8")


def monthly_bar_chart(city, year):
    values = RAINFALL_DATA[city][year]

    fig, ax = plt.subplots(figsize=(10.5, 4.8))

    bars = ax.bar(
        MONTHS,
        values,
        edgecolor="black",
        linewidth=0.7
    )

    ax.set_title(
        f"{city} - Monthly Rainfall ({year})",
        fontsize=14,
        fontweight="bold"
    )
    ax.set_xlabel("Month")
    ax.set_ylabel("Rainfall (mm)")
    ax.grid(
        axis="y",
        linestyle="--",
        alpha=0.30
    )

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(values) * 0.02,
            str(value),
            ha="center",
            va="bottom",
            fontsize=8
        )

    fig.tight_layout()
    return figure_to_base64(fig)


def yearly_trend_chart(city):
    years = np.array([2023, 2024, 2025])
    totals = np.array([
        annual_total(city, 2023),
        annual_total(city, 2024),
        annual_total(city, 2025)
    ])

    fig, ax = plt.subplots(figsize=(8.5, 4.5))

    ax.plot(
        years,
        totals,
        marker="o",
        linewidth=2.5,
        markersize=7
    )

    ax.set_title(
        f"{city} - 3-Year Annual Rainfall Trend",
        fontsize=14,
        fontweight="bold"
    )
    ax.set_xlabel("Year")
    ax.set_ylabel("Annual Rainfall (mm)")
    ax.set_xticks(years)
    ax.grid(
        linestyle="--",
        alpha=0.30
    )

    for x, y in zip(years, totals):
        ax.annotate(
            f"{y:.0f} mm",
            (x, y),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=9
        )

    fig.tight_layout()
    return figure_to_base64(fig)


def city_comparison_chart():
    cities = list(RAINFALL_DATA.keys())
    totals = [annual_total(city, 2025) for city in cities]

    order = np.argsort(totals)
    cities_sorted = np.array(cities)[order]
    totals_sorted = np.array(totals)[order]

    fig, ax = plt.subplots(figsize=(10.5, 5.5))

    bars = ax.barh(
        cities_sorted,
        totals_sorted,
        edgecolor="black",
        linewidth=0.7
    )

    ax.set_title(
        "2025 Annual Rainfall Comparison Across Cities",
        fontsize=14,
        fontweight="bold"
    )
    ax.set_xlabel("Annual Rainfall (mm)")
    ax.set_ylabel("City")
    ax.grid(
        axis="x",
        linestyle="--",
        alpha=0.30
    )

    for bar, value in zip(bars, totals_sorted):
        ax.text(
            value + max(totals_sorted) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.0f}",
            va="center",
            fontsize=8
        )

    fig.tight_layout()
    return figure_to_base64(fig)


# =========================================================
# YEAR TABLE
# =========================================================

def make_year_table(city):
    rows = []

    for year in [2025, 2024, 2023]:
        values = RAINFALL_DATA[city][year]
        stats = analyze_monthly_data(values)

        rows.append({
            "year": year,
            "annual": stats["total"],
            "average": stats["mean"],
            "std_dev": stats["std_dev"],
            "status": rainfall_status(stats["total"]),
        })

    return rows


# =========================================================
# ROUTE
# =========================================================

@app.route("/")
def index():

    city = request.args.get(
        "city",
        "Mumbai"
    )

    try:
        year = int(
            request.args.get(
                "year",
                "2025"
            )
        )
    except ValueError:
        year = 2025

    if city not in RAINFALL_DATA:
        city = "Mumbai"

    if year not in [2023, 2024, 2025]:
        year = 2025


    values = RAINFALL_DATA[city][year]

    stats = analyze_monthly_data(values)

    status = rainfall_status(
        stats["total"]
    )

    prediction = predict_next_year(
        city
    )

    city_2025_totals = {
        current_city: annual_total(
            current_city,
            2025
        )
        for current_city in RAINFALL_DATA
    }


    # Real Matplotlib visualizations.
    monthly_chart = monthly_bar_chart(
        city,
        year
    )

    trend_chart = yearly_trend_chart(
        city
    )

    comparison_chart = city_comparison_chart()


    return render_template(
        "index.html",
        cities=list(RAINFALL_DATA.keys()),
        years=[2025, 2024, 2023],
        city=city,
        year=year,
        stats=stats,
        status=status,
        prediction=prediction,
        year_rows=make_year_table(city),
        city_totals=city_2025_totals,
        monthly_chart=monthly_chart,
        trend_chart=trend_chart,
        comparison_chart=comparison_chart,
    )


if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
