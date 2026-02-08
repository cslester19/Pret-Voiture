import streamlit as st
import pandas as pd
from datetime import date
import calendar

# ===================== PAGE CONFIG =====================
st.set_page_config(page_title="Prêt voiture", page_icon="🚗", layout="wide")

# ===================== STYLE (force WHITE + couleurs) =====================
st.markdown(
    """
<style>
/* Force blanc + bloque "dark" visuellement */
html, body, [class*="stApp"] { background:#ffffff !important; color:#0f172a !important; }
header, footer { visibility:hidden; height:0; }
section[data-testid="stSidebar"] { display:none !important; } /* on n'utilise pas la sidebar */

/* Container spacing */
.block-container { padding-top: 1.4rem; padding-bottom: 2.2rem; max-width: 1280px; }

/* Titles */
h1 { margin-bottom: .2rem; letter-spacing: -0.4px; }
.smallcap { color:#475569; margin-top:0; }

/* Cards */
.card{
  border: 1px solid rgba(15,23,42,.10);
  border-radius: 18px;
  padding: 16px 18px;
  background: #ffffff;
  box-shadow: 0 10px 30px rgba(15,23,42,.06);
}
.card h3{
  margin: 0 0 8px 0;
  font-size: 12px;
  color: #64748b;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: .9px;
}
.big{
  font-size: 28px;
  font-weight: 950;
  color: #0f172a;
}
.mini{
  font-size: 12px;
  color: #64748b;
}

/* Divider */
.hr{ height:1px; background: rgba(15,23,42,.10); margin: 14px 0; }

/* Inputs rounding */
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stSelectbox"] div[role="combobox"]{
  border-radius: 14px !important;
}

/* Table nicer + scroll */
[data-testid="stDataFrame"]{
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(15,23,42,.10);
}
div[data-testid="stDataFrame"] .stDataFrame { overflow-x: auto !important; }

/* Buttons */
.stButton>button{
  width: 100%;
  border-radius: 16px;
  padding: .75rem 1rem;
  background: #0f172a;
  color: white;
  font-weight: 900;
  border: 1px solid rgba(15,23,42,.12);
}
.stButton>button:hover{ background:#0b1220; }

/* Soft note */
.note{
  background: rgba(2,132,199,.08);
  border: 1px solid rgba(2,132,199,.18);
  padding: 12px 14px;
  border-radius: 14px;
  color: #075985;
}

/* Analysis colored cards */
.card-blue{ background: rgba(2,132,199,.08); border-color: rgba(2,132,199,.22); }
.card-green{ background: rgba(34,197,94,.10); border-color: rgba(34,197,94,.22); }
.card-amber{ background: rgba(245,158,11,.12); border-color: rgba(245,158,11,.24); }
.card-slate{ background: rgba(15,23,42,.04); border-color: rgba(15,23,42,.10); }

/* “left panel” container */
.panel{
  border: 1px solid rgba(15,23,42,.10);
  border-radius: 18px;
  padding: 16px 18px;
  background: #ffffff;
  box-shadow: 0 10px 30px rgba(15,23,42,.06);
  position: sticky;
  top: 14px;
}
.panel h2{
  font-size: 16px;
  margin: 0 0 10px 0;
  color:#0f172a;
}
.panel .hint{ color:#475569; font-size: 12px; margin-bottom: 10px; }
</style>
""",
    unsafe_allow_html=True,
)

# ===================== HELPERS =====================
def money(x: float) -> str:
    try:
        return f"{float(x):,.2f} $".replace(",", " ").replace(".", ",")
    except Exception:
        return "—"

def periods_per_year(freq: str) -> int:
    return {"Hebdomadaire": 52, "Aux 2 semaines": 26, "Mensuel": 12}[freq]

def add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    last_day = calendar.monthrange(y, m)[1]
    day = min(d.day, last_day)
    return date(y, m, day)

def schedule_dates(start: date, n: int, freq: str):
    out = []
    if freq == "Mensuel":
        for i in range(n):
            out.append(add_months(start, i))
    elif freq == "Aux 2 semaines":
        cur = pd.Timestamp(start)
        for _ in range(n):
            out.append(cur.date())
            cur = cur + pd.Timedelta(days=14)
    else:  # Hebdomadaire
        cur = pd.Timestamp(start)
        for _ in range(n):
            out.append(cur.date())
            cur = cur + pd.Timedelta(days=7)
    return out

def amortization(principal: float, annual_rate_pct: float, n: int, freq: str, start: date):
    ppy = periods_per_year(freq)
    r = (annual_rate_pct / 100.0) / ppy  # periodic rate

    if n <= 0:
        return 0.0, pd.DataFrame(), {"interets_totaux": 0.0, "total_paye": 0.0}

    if principal <= 0:
        dates = schedule_dates(start, n, freq)
        df = pd.DataFrame(
            {
                "Période": list(range(1, n + 1)),
                "Date": dates,
                "Paiement": [0.0] * n,
                "Intérêt": [0.0] * n,
                "Principal": [0.0] * n,
                "Solde": [0.0] * n,
                "Intérêts cumulés": [0.0] * n,
                "Cap. remboursé (cumul)": [0.0] * n,
            }
        )
        return 0.0, df, {"interets_totaux": 0.0, "total_paye": 0.0}

    # Payment formula
    if r == 0:
        payment = principal / n
    else:
        payment = principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

    dates = schedule_dates(start, n, freq)

    balance = principal
    cum_int = 0.0
    cum_principal = 0.0
    rows = []

    for i in range(1, n + 1):
        interest = balance * r
        principal_part = payment - interest

        if i == n:
            # last line adjustment
            principal_part = balance
            payment_i = principal_part + interest
        else:
            payment_i = payment

        balance = max(balance - principal_part, 0.0)
        cum_int += interest
        cum_principal += principal_part

        rows.append(
            {
                "Période": i,
                "Date": dates[i - 1],
                "Paiement": float(payment_i),
                "Intérêt": float(interest),
                "Principal": float(principal_part),
                "Solde": float(balance),
                "Intérêts cumulés": float(cum_int),
                "Cap. remboursé (cumul)": float(cum_principal),
            }
        )

    df = pd.DataFrame(rows)
    totals = {"interets_totaux": float(df["Intérêt"].sum()), "total_paye": float(df["Paiement"].sum())}
    return float(payment), df, totals

# ===================== STATE =====================
if "calculated" not in st.session_state:
    st.session_state.calculated = False

# ===================== HEADER =====================
st.title("🚗 Calculateur de prêt voiture — version détaillée")
st.caption("👇 Remplis les champs en bas puis clique sur **Calculer**.")

# ===================== LAYOUT =====================
col_inputs, col_results = st.columns([1.05, 1.95], gap="large")

# ===================== INPUTS (à gauche, pas de sidebar) =====================
with col_inputs:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("<h2>Saisir les différentes informations</h2>", unsafe_allow_html=True)

    prix_avant = st.number_input("Prix véhicule avant taxes ($)", min_value=0.0, value=0.0, step=100.0)
    options = st.number_input("Autres options ($)", min_value=0.0, value=0.0, step=50.0)
    taxes_pct = st.number_input("Taxes (%) (TPS+TVQ total)", min_value=0.0, value=0.0, step=0.01)
    depot = st.number_input("Dépôt ($)", min_value=0.0, value=0.0, step=100.0)

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    taux_annuel = st.number_input("Taux annuel (%)", min_value=0.0, value=0.0, step=0.01)
    duree_mois = st.number_input("Durée (mois)", min_value=1, value=60, step=1)
    freq = st.selectbox("Fréquence de paiement", ["Mensuel", "Aux 2 semaines", "Hebdomadaire"])
    debut = st.date_input("Date de début", value=date.today())

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ Calculer"):
            st.session_state.calculated = True
    with c2:
        if st.button("↩️ Réinitialiser"):
            st.session_state.calculated = False
            st.rerun()

    st.markdown(
        '<div class="note">✅ Astuce : tu peux laisser des champs à 0 si tu ne les utilises pas (ex: options).</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ===================== RESULTS (à droite) =====================
with col_results:
    if not st.session_state.calculated:
        st.info("Aucun calcul n’est affiché tant que tu n’as pas cliqué sur **Calculer**.")
    else:
        # ===== CALCULS =====
        prix_total_avant = prix_avant + options
        taxes = prix_total_avant * (taxes_pct / 100.0)
        prix_apres = prix_total_avant + taxes
        emprunt_total = max(prix_apres - depot, 0.0)

        ppy = periods_per_year(freq)
        nb_paiements = int(round((duree_mois / 12.0) * ppy))

        paiement, df, totals = amortization(emprunt_total, taux_annuel, nb_paiements, freq, debut)
        interets_totaux = totals.get("interets_totaux", 0.0)
        total_paye = totals.get("total_paye", 0.0)

        # ===== SUMMARY CARDS =====
        r1, r2, r3 = st.columns(3, gap="medium")
        with r1:
            st.markdown(
                f"""
            <div class="card">
              <h3>Prix après taxes</h3>
              <div class="big">{money(prix_apres)}</div>
              <div class="mini">Avant taxes: {money(prix_total_avant)} • Taxes: {money(taxes)}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        with r2:
            st.markdown(
                f"""
            <div class="card">
              <h3>Emprunt total</h3>
              <div class="big">{money(emprunt_total)}</div>
              <div class="mini">Dépôt: {money(depot)} • Fréquence: {freq}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        with r3:
            st.markdown(
                f"""
            <div class="card">
              <h3>Paiement</h3>
              <div class="big">{money(paiement)}</div>
              <div class="mini">Nb paiements: {nb_paiements} • Périodes/an: {ppy}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        st.markdown("")

        r4, r5 = st.columns(2, gap="medium")
        with r4:
            st.markdown(
                f"""
            <div class="card">
              <h3>Intérêts totaux</h3>
              <div class="big">{money(interets_totaux)}</div>
              <div class="mini">Total payé (approx): {money(total_paye)}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        with r5:
            st.markdown(
                f"""
            <div class="card">
              <h3>Durée</h3>
              <div class="big">{int(duree_mois)} mois</div>
              <div class="mini">Taux annuel: {taux_annuel:.2f}%</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
      

        st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

        # ===== AMORT TABLE =====
        st.subheader("Tableau d’amortissement")
        if df.empty:
            st.warning("Aucun tableau (emprunt à 0).")
        else:
            df_display = df.copy()

            # format propre (mais garde le scroll)
            for col in ["Paiement", "Intérêt", "Principal", "Solde", "Intérêts cumulés", "Cap. remboursé (cumul)"]:
                df_display[col] = df_display[col].astype(float)

            # colonnes plus compactes pour que la dernière soit visible
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                height=440,
                column_config={
                    "Période": st.column_config.NumberColumn(width="small"),
                    "Date": st.column_config.DateColumn(width="small"),
                    "Paiement": st.column_config.NumberColumn(format="%.2f", width="small"),
                    "Intérêt": st.column_config.NumberColumn(format="%.2f", width="small"),
                    "Principal": st.column_config.NumberColumn(format="%.2f", width="small"),
                    "Solde": st.column_config.NumberColumn(format="%.2f", width="small"),
                    "Intérêts cumulés": st.column_config.NumberColumn(format="%.2f", width="small"),
                    "Cap. remboursé (cumul)": st.column_config.NumberColumn(format="%.2f", width="small"),
                },
            )

            st.caption("Astuce : tu peux **scroller horizontalement** dans le tableau si ton écran est petit.")

        st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

        # ===== ANALYSE À UNE DATE (avec couleurs) =====
        st.subheader("Analyse à une date")
        if df.empty:
            st.info("Analyse indisponible (emprunt à 0).")
        else:
            # date picker
            chosen = st.date_input("Choisis une date (pour voir le cumul)", value=df["Date"].iloc[0])

            df2 = df.copy()
            df2["Date"] = pd.to_datetime(df2["Date"]).dt.date

            mask = df2["Date"] <= chosen
            if mask.any():
                last_row = df2[mask].iloc[-1]
                interets_payes = float(last_row["Intérêts cumulés"])
                capital_restant = float(last_row["Solde"])
                capital_remb = float(last_row["Cap. remboursé (cumul)"])
            else:
                interets_payes = 0.0
                capital_restant = float(df2["Solde"].iloc[0])
                capital_remb = 0.0

            interets_restants = max(float(interets_totaux) - interets_payes, 0.0)

            a1, a2, a3, a4 = st.columns(4, gap="medium")
            with a1:
                st.markdown(
                    f"""<div class="card card-blue"><h3>Intérêts payés (cumul)</h3><div class="big">{money(interets_payes)}</div></div>""",
                    unsafe_allow_html=True,
                )
            with a2:
                st.markdown(
                    f"""<div class="card card-amber"><h3>Intérêts restants</h3><div class="big">{money(interets_restants)}</div><div class="mini">Totaux − payés</div></div>""",
                    unsafe_allow_html=True,
                )
            with a3:
                st.markdown(
                    f"""<div class="card card-slate"><h3>Capital restant</h3><div class="big">{money(capital_restant)}</div></div>""",
                    unsafe_allow_html=True,
                )
            with a4:
                st.markdown(
                    f"""<div class="card card-green"><h3>Capital remboursé</h3><div class="big">{money(capital_remb)}</div></div>""",
                    unsafe_allow_html=True,
                )

        # ✅ demandé : enlever export Excel / CSV => rien ici.
