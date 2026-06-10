"""Build a one-page PDF handout (and markdown) from the live results.json."""
import json, os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "discovery"))
import tiering as T, build_dashboard as B, macro_stress as MS
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

HERE = os.path.dirname(os.path.abspath(__file__))
res = B._load(B.RESULTS)
st = MS.compute(res.get("macro", {}))
rows = T.build_rows(res)
tiers = T.tier_rows(rows)

def shortn(n):
    return (n.split(" (")[0])[:20]
def tcol(t):
    return colors.HexColor("#0f6e56") if t <= 0.22 else (colors.HexColor("#854f0b") if t <= 0.26 else colors.HexColor("#a32d2d"))

styles = getSampleStyleSheet()
H = ParagraphStyle('H', parent=styles['Title'], fontSize=15, spaceAfter=2, textColor=colors.HexColor("#1c1c1a"))
sub = ParagraphStyle('s', parent=styles['Normal'], fontSize=8.5, textColor=colors.HexColor("#6b6a64"))
dis = ParagraphStyle('d', parent=styles['Normal'], fontSize=7.5, textColor=colors.HexColor("#a32d2d"))
h2 = ParagraphStyle('h2', parent=styles['Normal'], fontSize=9.5, leading=12, textColor=colors.HexColor("#185fa5"), spaceBefore=6, spaceAfter=2)
body = ParagraphStyle('b', parent=styles['Normal'], fontSize=8, leading=10.5)
small = ParagraphStyle('sm', parent=styles['Normal'], fontSize=7, leading=8.5, textColor=colors.HexColor("#6b6a64"))

doc = SimpleDocTemplate(os.path.join(HERE, "Systemic_TAM_onepager.pdf"), pagesize=letter,
                        leftMargin=14*mm, rightMargin=14*mm, topMargin=12*mm, bottomMargin=10*mm)
story = []
story.append(Paragraph("Systemic + TAM Risk — one-page summary", H))
story.append(Paragraph(f"US AI / semiconductor names &amp; ETFs · growth tier vs drawdown-recovery risk · model as of {res.get('as_of')} · generated {dt.date.today()}", sub))
story.append(Paragraph(f"<b>Macro-stress index {round(st['score']*100)}/100</b> ({MS.stress_label(st['score'])}) — structural fragility {round(st['structural']*100)}, acute trigger {round(st['acute']*100)}; scales the crisis odds x{MS.crisis_mult(st['score']):.2f} vs neutral.", body))
story.append(Paragraph("Research model — not investment advice. Read tiers and ranges, not decimals.", dis))
story.append(Spacer(1, 4))

# three tier columns
def tier_block(label, members):
    data = [["Name", "Gw", "Tail"]]
    styl = [("FONT",(0,0),(-1,-1),"Helvetica",6.6),
            ("FONT",(0,0),(-1,0),"Helvetica-Bold",6.6),
            ("TEXTCOLOR",(0,0),(-1,0),colors.HexColor("#6b6a64")),
            ("LINEBELOW",(0,0),(-1,0),0.4,colors.HexColor("#888")),
            ("ALIGN",(1,0),(-1,-1),"RIGHT"),("TOPPADDING",(0,0),(-1,-1),1.2),
            ("BOTTOMPADDING",(0,0),(-1,-1),1.2),("LEFTPADDING",(0,0),(-1,-1),2)]
    for i, r in enumerate(members, 1):
        data.append([shortn(r["name"]), f"{round(r['growth']*100)}%", f"{round(r['p_deep_permanent']*100)}%"])
        styl.append(("TEXTCOLOR",(2,i),(2,i),tcol(r["p_deep_permanent"])))
        styl.append(("FONT",(2,i),(2,i),"Helvetica-Bold",6.6))
    t = Table(data, colWidths=[34*mm, 9*mm, 9*mm])
    t.setStyle(TableStyle(styl))
    head = Paragraph(f"<b>{label}</b>", ParagraphStyle('th',parent=body,fontSize=8,textColor=colors.HexColor("#1c1c1a")))
    return [head, Spacer(1,2), t]

cols = []
labels = ["TIER 1 · High >40%", "TIER 2 · Moderate 15–40%", "TIER 3 · Safe <15%"]
for (lbl, mem), label in zip(tiers, labels):
    cols.append(tier_block(label, mem))
outer = Table([[cols[0], cols[1], cols[2]]], colWidths=[58*mm, 60*mm, 58*mm])
outer.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),2),("RIGHTPADDING",(0,0),(-1,-1),2)]))
story.append(outer)
story.append(Paragraph("Gw = expected 18-month growth.  Tail = P(a &gt;25% fall that takes &gt;3 years to recover) — the permanent-loss tail; green &lt;22%, amber 22–26%, red &gt;26%. Lower is safer.", small))
story.append(Spacer(1, 6))

story.append(Paragraph("The three risk layers", h2))
story.append(Paragraph("<b>1. Macro stress → tail.</b> Probability of a &gt;40% S&amp;P drawdown over 18 months: ~5% in a benign environment, ~7% now, ~12% in a critical one. Driven by valuation, record margin debt, real rates, credit spreads and liquidity — not a hand-set number. The current read is stretched-but-calm (high structural fragility, low acute trigger).", body))
story.append(Paragraph("<b>2. Concentration.</b> 36 names, but ~1 effective independent bet (average pairwise correlation ~0.90). This list is essentially one bet on the AI-capex cycle; a specialized ETF (SMH, DRAM, CHAT) is ~0.95 correlated with its lead holding and barely diversifies. Only the broad funds (VOO, SCHD) add real diversification.", body))
story.append(Paragraph("<b>3. Recovery.</b> Growth and survivability trade off almost monotonically: the fastest growers (IonQ, CoreWeave ~30% tail) carry the fattest permanent-loss tails; the slow, durable names (IBM 17%, Cisco/SCHD 19%, VOO/Microsoft 21%) the thinnest.", body))
story.append(Spacer(1, 4))
story.append(Paragraph("Bottom line", h2))
story.append(Paragraph("Beta sets how deep a name falls in a panic; TAM-penetration sets whether it recovers. The high-growth tier offers the most upside and the fattest never-recovers tail; the safe tier the reverse. And because the whole list is ~one correlated bet, spreading across these names buys far less protection than the count implies — size to the bet, not the ticker count.", body))
story.append(Spacer(1, 4))
story.append(Paragraph("Full interactive dashboard, ETF view, tables, and per-name analysis tools are in the shared package — open index.html.", small))

doc.build(story)
print("Wrote Systemic_TAM_onepager.pdf")
