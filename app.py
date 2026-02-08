import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date, timedelta

# ------------------ PAGE / STYLE ------------------
st.set_page_config(page_title="Prêt voiture", page_icon="🚗", layout="wide")

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.6rem; padding-bottom: 2.2rem; }
      h1 { margin-bottom: .15rem; letter-spacing: -0.3px; }
      .subtle { color: #6b7280; margin-top: 0; }

      .pill {
        display:inline-block;
        padding:4px 10px;
        border-radius:999px;
        background: rgba(2,132,199,.10);
        color:#075985;
        font-weight:700;
        font-size:12px;
      }

      .card {
        padding: 16px 18px;
        border: 1px solid rgba(15,23,42,.10);
        border-radius: 16px;
        background: linear-gradient(180deg, rgba(255,255,255,.92), rgba(255,255,255,.78));
        box-shadow: 0 10px 30px rgba(15,23,42,.06);
      }
      .card h3 {
        margin: 0 0 6px 0;
        font-size: 13px;
        color: #64748b;
        font-weight: 700;
      }
      .card .big {
        font-size: 26px;
        font-weight: 900;
        color: #0f172a;
      }
      .accent {
        border-left: 6px solid var(--accent);
        background: var(--bg);
      }

      .divider { height: 1px; background: rgba(15,23,42,.10); margin: 14px 0 10px; }
      .spacer { height: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🚗 Calculateur de prêt voiture")
st.markdown(
    '<p class="subtle">Style banque • amortissement complet • analyse à une date • export Excel</p>',
    unsafe_allow_html=True,
)

# ------------------ HELPERS ------------------
def money(x: float) -> str:
    return f"{x:,.2f} $"

def periods_per_year(freq: str) -> int:
    return {"Hebdomadaire": 52, "Aux 2 semaines": 26, "Mensuel": 12}[freq]

def add_period(d: date, freq: str) -> date:
    if freq == "Mensuel":
        y, m = d.year, d.month + 1
        if m == 13:
            y += 1
            m = 1
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

        # Ajuster dernière période
        if principal_paid > bal:
            principal_paid = bal
            payment_eff = principal_paid + interest
        else:
            payment_eff = payment

        bal -= principal_paid
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
    chosen_ts = pd.Timestamp(chosen)
    df_dates = pd.to_datetime(df["Date"])
    df2 = df[df_dates <= chosen_ts]
    if df2.empty:
        return None
    row = df2.iloc[-1]
    return {
        "Intérêts payés (cumul)": float(row["Intérêts cumulés"]),
        "Capital restant": float(row["Solde"]),
        "Capital remboursé": float(row["Capital remboursé (cumul)"]),
    }

# ------------------ CARDS ------------------
def card(col, title, value):
    col.markdown(f"""
      <div class="card">
        <h3>{title}</h3>
        <div class="big">{value}</div>
      </div>
    """, unsafe_allow_html=True)

def card_color(col, title, value, accent="#2563eb", bg="rgba(37,99,235,.12)"):
    col.markdown(f"""
      <div class="card accent" style="--accent:{accent}; --bg:{bg};">
        <h3>{title}</h3>
        <div class="big">{value}</div>
      </div>
    """, unsafe_allow_html=True)

# ------------------ SESSION STATE ------------------
if "calculated" not in st.session_state:
    st.session_state.calculated = False

# ------------------ SIDEBAR INPUTS ------------------
with st.sidebar:
    st.markdown("### ⚙️ Paramètres")
    st.markdown('<span class="pill">Remplis puis clique “Calculer”</span>', unsafe_allow_html=True)
    st.write("")

    prix_avant = st.number_input("Prix véhicule avant taxes ($)", min_value=0.0, value=0.0, step=100.0)
    options = st.number_input("Autres options ($)", min_value=0.0, value=0.0, step=50.0)

    taxes_pct = st.number_input("Taxes (%) (TPS+TVQ total)", min_value=0.0, value=0.0, step=0.001)
    depot = st.number_input("Dépôt ($)", min_value=0.0, value=0.0, step=100.0)

    taux_annuel = st.number_input("Taux annuel (%)", min_value=0.0, value=0.0, step=0.01)
    duree_mois = st.number_input("Durée (mois)", min_value=1, value=60, step=1)

    freq = st.selectbox("Fréquence de paiement", ["Mensuel", "Aux 2 semaines", "Hebdomadaire"])
    debut = st.date_input("Date de début", value=date.today())

    cA, cB = st.columns(2)
    with cA:
        calc = st.button("✅ Calculer", use_container_width=True)
    with cB:
        reset = st.button("🧹 Reset", use_container_width=True)

    if reset:
        st.session_state.calculated = False
        st.rerun()

    if calc:
        st.session_state.calculated = True

# ------------------ MAIN AREA (EMPTY ON FIRST LOAD) ------------------
if not st.session_state.calculated:
    st.markdown("### 👇 Remplis les champs à gauche")
    st.info("Aucun calcul n’est affiché tant que tu n’as pas cliqué sur **Calculer**.")
    st.markdown("✅ Astuce : tu peux laisser des champs à 0 si tu ne les utilises pas (ex: options).")
    st.stop()

# ------------------ CALCULATIONS ------------------
prix_total_avant = prix_avant + options
taxes_val = prix_total_avant * (taxes_pct / 100.0)
prix_apres = prix_total_avant + taxes_val
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

# ------------------ SUMMARY ------------------
st.markdown("## Résumé")
c1, c2, c3, c4, c5 = st.columns(5)
card(c1, "Prix avant taxes", money(prix_total_avant))
card(c2, "Taxes", money(taxes_val))
card(c3, "Prix après taxes", money(prix_apres))
card(c4, "Emprunt total", money(emprunt_total))
card(c5, "Paiement", money(paiement))

st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)

c6, c7, c8, c9 = st.columns(4)
card(c6, "Périodes/an", str(periods_per_year(freq)))
card(c7, "Nb paiements", str(nb_paiements))
card(c8, "Intérêts totaux", money(interets_totaux))
card(c9, "Total payé (approx.)", money(total_paye))

# ------------------ TABS ------------------
tab1, tab2, tab3 = st.tabs(["📋 Amortissement", "📌 Analyse à une date", "⬇️ Export Excel"])

with tab1:
    st.markdown("### Tableau d’amortissement")
    df_show = df.copy()
    df_show["Date"] = df_show["Date"].astype(str)
    st.dataframe(df_show, use_container_width=True, height=560)

    st.markdown("### Graphique — Solde restant")
    chart_df = df[["Date", "Solde"]].copy()
    chart_df["Date"] = pd.to_datetime(chart_df["Date"])
    chart_df = chart_df.set_index("Date")
    st.line_chart(chart_df)

with tab2:
    st.markdown("### Analyse à une date")
    date_choisie = st.date_input("Choisis une date (pour voir le cumul)", value=debut)
    stats = pick_stats_at_date(df, date_choisie)

    if stats is None:
        st.warning("La date choisie est avant la première date de paiement.")
    else:
        interets_payes = float(stats["Intérêts payés (cumul)"])
        interets_restants = max(float(interets_totaux) - interets_payes, 0.0)

        st.markdown(
            f'<span class="pill">Analyse au {date_choisie.strftime("%Y-%m-%d")}</span>',
            unsafe_allow_html=True
        )
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        a1, a2, a3, a4 = st.columns(4)

        # Orange = intérêts payés
        card_color(a1, "Intérêts payés (cumul)", money(interets_payes),
                   accent="#f59e0b", bg="rgba(245,158,11,.14)")

        # Bleu = capital restant
        card_color(a2, "Capital restant", money(float(stats["Capital restant"])),
                   accent="#2563eb", bg="rgba(37,99,235,.12)")

        # Vert = capital remboursé
        card_color(a3, "Capital remboursé", money(float(stats["Capital remboursé"])),
                   accent="#16a34a", bg="rgba(22,163,74,.14)")

        # Rouge = intérêts restants
        card_color(a4, "Intérêts restants", money(interets_restants),
                   accent="#dc2626", bg="rgba(220,38,38,.12)")

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown("### Intérêts — Payés vs Restants")

        values = [interets_payes, interets_restants]

        fig, ax = plt.subplots(figsize=(4.6, 4.6))
        ax.pie(values, startangle=90, wedgeprops=dict(width=0.42))
        ax.set(aspect="equal")

        ax.text(0, 0.05, "Intérêts\nTotaux", ha="center", va="center", fontsize=12, fontweight="bold")
        ax.text(0, -0.12, money(float(interets_totaux)), ha="center", va="center", fontsize=12)

        st.pyplot(fig, clear_figure=True)

        recap = pd.DataFrame({
            "Type": ["Intérêts payés", "Intérêts restants", "Intérêts totaux"],
            "Montant": [money(interets_payes), money(interets_restants), money(float(interets_totaux))]
        })
        st.dataframe(recap, use_container_width=True, hide_index=True)

with tab3:
    st.markdown("### Export")
    import io

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer) as writer:
        df_export = df.copy()
        df_export["Date"] = df_export["Date"].astype(str)
        df_export.to_excel(writer, index=False, sheet_name="Amortissement")

        resume = pd.DataFrame([{
            "Prix avant taxes": prix_avant,
            "Options": options,
            "Taxes %": taxes_pct,
            "Dépôt": depot,
            "Taux annuel %": taux_annuel,
            "Durée (mois)": duree_mois,
            "Fréquence": freq,
            "Date début": str(debut),
            "Prix après taxes": prix_apres,
            "Emprunt total": emprunt_total,
            "Paiement": paiement,
            "Nb paiements": nb_paiements,
            "Intérêts totaux": interets_totaux,
            "Total payé": total_paye,
        }])
        resume.to_excel(writer, index=False, sheet_name="Résumé")

    st.download_button(
        "⬇️ Télécharger l’Excel (amortissement + résumé)",
        data=buffer.getvalue(),
        file_name="pret_voiture_detail.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
