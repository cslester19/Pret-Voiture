import streamlit as st
import pandas as pd
from datetime import date, timedelta

st.set_page_config(page_title="Prêt voiture", page_icon="🚗", layout="wide")
st.title("🚗 Calculateur de prêt voiture — version détaillée")

# ---------- Helpers ----------
def periods_per_year(freq: str) -> int:
    return {"Hebdomadaire": 52, "Aux 2 semaines": 26, "Mensuel": 12}[freq]

def add_period(d: date, freq: str) -> date:
    if freq == "Mensuel":
        y, m = d.year, d.month + 1
        if m == 13:
            y += 1
            m = 1
        # clamp jour
        dim = [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28,
               31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m-1]
        day = min(d.day, dim)
        return date(y, m, day)
    return d + timedelta(days=7 if freq == "Hebdomadaire" else 14)

def pmt(rate_per_period: float, nper: int, pv: float) -> float:
    if nper <= 0:
        return 0.0
    if rate_per_period == 0:
        return pv / nper
    return (rate_per_period * pv) / (1 - (1 + rate_per_period) ** (-nper))

def build_schedule(principal: float, annual_rate: float, freq: str, duration_months: int, start_date: date):
    per_year = periods_per_year(freq)
    nper = int(round((duration_months / 12) * per_year))
    r = annual_rate / per_year
    payment = pmt(r, nper, principal)

    rows = []
    bal = principal
    d = start_date
    total_interest = 0.0

    for k in range(1, nper + 1):
        interest = bal * r
        principal_paid = payment - interest

        # ajuster dernière période
        if principal_paid > bal:
            principal_paid = bal
            payment_eff = principal_paid + interest
        else:
            payment_eff = payment

        bal = bal - principal_paid
        total_interest += interest

        rows.append({
            "Période": k,
            "Date": d,
            "Paiement": round(payment_eff, 2),
            "Intérêt": round(interest, 2),
            "Principal": round(principal_paid, 2),
            "Solde": round(bal, 2),
            "Intérêts cumulés": round(total_interest, 2),
            "Capital remboursé (cumul)": round(principal - bal, 2),
        })

        d = add_period(d, freq)

    df = pd.DataFrame(rows)
    return df, round(payment, 2), nper, round(total_interest, 2)

def pick_stats_at_date(df: pd.DataFrame, chosen: date):
    # df["Date"] est un objet date; chosen aussi
    chosen_ts = pd.Timestamp(chosen)

    df_dates = pd.to_datetime(df["Date"])
    df2 = df[df_dates <= chosen_ts]

    if df2.empty:
        return None

    row = df2.iloc[-1]
    return {
        "Date choisie": chosen,
        "Intérêts payés (cumul)": float(row["Intérêts cumulés"]),
        "Capital restant (solde)": float(row["Solde"]),
        "Capital remboursé (cumul)": float(row["Capital remboursé (cumul)"]),
    }


# ---------- Inputs ----------
st.subheader("Entrées")

c1, c2, c3, c4 = st.columns(4)

with c1:
    prix_avant = st.number_input("Prix véhicule avant taxes ($)", min_value=0.0, value=32992.0, step=100.0)
    options = st.number_input("Autres options ($)", min_value=0.0, value=3759.5, step=50.0)

with c2:
    tps_tvq = st.number_input("Taxes (%) (TPS+TVQ total)", min_value=0.0, value=14.975, step=0.001)
    depot = st.number_input("Dépôt ($)", min_value=0.0, value=3000.0, step=100.0)

with c3:
    taux_annuel = st.number_input("Taux annuel (%)", min_value=0.0, value=6.99, step=0.01)
    duree_mois = st.number_input("Durée (mois)", min_value=1, value=60, step=1)

with c4:
    freq = st.selectbox("Fréquence de paiement", ["Mensuel", "Aux 2 semaines", "Hebdomadaire"], index=0)
    debut = st.date_input("Date de début", value=date.today())

# ---------- Calculs ----------
prix_total_avant = prix_avant + options
taxes = prix_total_avant * (tps_tvq / 100.0)
prix_apres = prix_total_avant + taxes
emprunt_total = max(prix_apres - depot, 0.0)

annual_rate = taux_annuel / 100.0
df, paiement, nb_paiements, interets_totaux = build_schedule(
    principal=emprunt_total,
    annual_rate=annual_rate,
    freq=freq,
    duration_months=int(duree_mois),
    start_date=debut
)

total_paye = paiement * nb_paiements

# ---------- Résumé ----------
st.subheader("Résumé")
r1, r2, r3, r4, r5 = st.columns(5)
r1.metric("Prix avant taxes", f"{prix_total_avant:,.2f} $")
r2.metric("Taxes", f"{taxes:,.2f} $")
r3.metric("Prix après taxes", f"{prix_apres:,.2f} $")
r4.metric("Emprunt total", f"{emprunt_total:,.2f} $")
r5.metric("Paiement", f"{paiement:,.2f} $")

s1, s2, s3 = st.columns(3)
s1.metric("Périodes/an", f"{periods_per_year(freq)}")
s2.metric("Nb paiements", f"{nb_paiements}")
s3.metric("Intérêts totaux", f"{interets_totaux:,.2f} $")

st.caption(f"Total payé (approx) : {total_paye:,.2f} $")

# ---------- Tableau ----------
st.subheader("Tableau d’amortissement")
df_show = df.copy()
df_show["Date"] = df_show["Date"].astype(str)
st.dataframe(df_show, use_container_width=True, height=520)

# ---------- Analyse à une date ----------
st.subheader("Analyse à une date")
date_choisie = st.date_input("Choisis une date (pour voir le cumul)", value=debut)
stats = pick_stats_at_date(df, date_choisie)

if stats is None:
    st.warning("La date choisie est avant la première date de paiement.")
else:
    a1, a2, a3 = st.columns(3)
    a1.metric("Intérêts payés (cumul)", f"{stats['Intérêts payés (cumul)']:,.2f} $")
    a2.metric("Capital restant", f"{stats['Capital restant (solde)']:,.2f} $")
    a3.metric("Capital remboursé", f"{stats['Capital remboursé (cumul)']:,.2f} $")

# ---------- Export Excel ----------
st.subheader("Export")
import io
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df_export = df.copy()
    df_export["Date"] = df_export["Date"].astype(str)
    df_export.to_excel(writer, index=False, sheet_name="Amortissement")

    resume = pd.DataFrame([{
        "Prix avant taxes": prix_avant,
        "Options": options,
        "Taxes %": tps_tvq,
        "Dépôt": depot,
        "Taux annuel %": taux_annuel,
        "Durée (mois)": duree_mois,
        "Fréquence": freq,
        "Prix après taxes": prix_apres,
        "Emprunt total": emprunt_total,
        "Paiement": paiement,
        "Nb paiements": nb_paiements,
        "Intérêts totaux": interets_totaux,
    }])
    resume.to_excel(writer, index=False, sheet_name="Résumé")

st.download_button(
    "⬇️ Télécharger l’Excel (amortissement + résumé)",
    data=buffer.getvalue(),
    file_name="pret_voiture_detail.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
