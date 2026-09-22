import calendar

import pandas as pd

TS = "%Y-%m-%d %H:%M:%S"


def iso(d):
    return d.isoformat() if hasattr(d, "isoformat") else str(d)


def pareto(df, label, value):
    if df is None or df.empty:
        return pd.DataFrame(columns=[label, value, "pct", "cum_pct"])
    g = df.groupby(label)[value].sum().sort_values(ascending=False).reset_index()
    tot = g[value].sum()
    g["pct"] = g[value] / tot if tot else 0.0
    g["cum_pct"] = g.pct.cumsum()
    return g


def month_label(ym):
    y, m = ym.split("-")
    return f"{calendar.month_abbr[int(m)]} {y}"


def add_month(df, date_col="date"):
    df = df.copy()
    df["month"] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m")
    return df


def all_months(year):
    return [f"{year}-{m:02d}" for m in range(1, 13)]
