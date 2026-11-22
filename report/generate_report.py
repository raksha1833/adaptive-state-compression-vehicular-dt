"""
Builds report/report.pdf for the project.

Run from the repo root (after analysis/plots.py, analysis/results_by_scenario.py and
experiments/lane_aware_experiment.py have been run):

    python report/generate_report.py

Every number in the text and tables is read from the project's CSV files, so the
report always matches the data. Edit the team details just below if they change.
"""
import csv
import importlib.metadata as md
import os
import platform

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image, KeepTogether, ListFlowable, ListItem, Paragraph, Preformatted,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

# ----------------------------- team details -----------------------------
TITLE_LINES = ["Adaptive State Compression for", "Communication-Efficient Vehicular Digital Twins"]
TEAM = [
    ("Shreeraksha R J", "241CS155"),
    ("S Suhitha", "241CS156"),
    ("A Shanthi", "241CS206"),
    ("Deekshitha U M", "241CS224"),
]
TEAM_NUMBER = "15"
MENTOR = "Anshul"
REPORT_DATE = "17 November 2026"

# Optional: add your machine's details and a "Hardware" table appears in Section 5.1.
# Leave a value as "" to leave that row out; leave all empty to skip the table.
HARDWARE = {"Processor": "", "Memory": "", "Operating system": ""}
# -------------------------------------------------------------------------

REPORT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(REPORT_DIR)
PLOTS = os.path.join(REPO_ROOT, "analysis", "plots")

BODY, BOLD, ITALIC = "Times-Roman", "Times-Bold", "Times-Italic"

styles = getSampleStyleSheet()


def add_style(name, **kw):
    styles.add(ParagraphStyle(name=name, **kw))


add_style("RBody", fontName=BODY, fontSize=10.5, leading=14, alignment=TA_JUSTIFY, spaceAfter=8)
add_style("RH1", fontName=BOLD, fontSize=14, leading=17, spaceBefore=14, spaceAfter=6, keepWithNext=1)
add_style("RH2", fontName=BOLD, fontSize=11.5, leading=14, spaceBefore=10, spaceAfter=4, keepWithNext=1)
add_style("RCaption", fontName=BODY, fontSize=9, leading=11, alignment=TA_CENTER, spaceBefore=3, spaceAfter=12)
add_style("RTableCaption", fontName=BODY, fontSize=9, leading=11, alignment=TA_CENTER,
          spaceBefore=6, spaceAfter=4, keepWithNext=1)
add_style("RTitle", fontName=BOLD, fontSize=19, leading=23, alignment=TA_CENTER, spaceAfter=4)
add_style("RSub", fontName=ITALIC, fontSize=11, leading=14, alignment=TA_CENTER, spaceAfter=10)
add_style("RCenter", fontName=BODY, fontSize=10.5, leading=14, alignment=TA_CENTER, spaceAfter=2)
add_style("RAbstractHead", fontName=BOLD, fontSize=11, leading=14, alignment=TA_CENTER, spaceBefore=10, spaceAfter=4)
add_style("RAbstract", fontName=BODY, fontSize=10, leading=13, alignment=TA_JUSTIFY, leftIndent=24,
          rightIndent=24, spaceAfter=6)
add_style("RCell", fontName=BODY, fontSize=9, leading=11, alignment=TA_LEFT)
add_style("RCellC", fontName=BODY, fontSize=9, leading=11, alignment=TA_CENTER)
add_style("RRef", fontName=BODY, fontSize=10, leading=13, leftIndent=22, firstLineIndent=-22, spaceAfter=5)

# Table and figure numbers follow the order they appear in the report.
TABLES = ["strategies", "stack", "params", "comm", "acc", "bw", "scen", "lane", "valid"]
FIGS = ["arch", "tradeoff", "bytes", "overhead", "aoi", "channel", "maxveh"]


def tn(key):
    return TABLES.index(key) + 1


def fn(key):
    return FIGS.index(key) + 1


def P(text, style="RBody"):
    return Paragraph(text, styles[style])


def bullets(items):
    return ListFlowable([ListItem(P(t), leftIndent=14) for t in items], bulletType="bullet",
                        bulletFontName=BODY, leftIndent=14)


def num(x, digits=2):
    return f"{float(x):.{digits}f}"


def read_rows(path):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. Run the analysis steps first (plots.py, results_by_scenario.py, "
            "lane_aware_experiment.py).")
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


# ------------------------------ tables / figures ------------------------------
def bw_table(header, rows, widths, bold_rows=(), rules_after=(), left_cols=1):
    """Black-and-white 'rules only' table: heavy lines above and below, a thin line under the header."""
    def cell(text, col, bold=False):
        t = str(text).replace("\n", "<br/>")
        if bold:
            t = f"<b>{t}</b>"
        return Paragraph(t, styles["RCell" if col < left_cols else "RCellC"])

    data = [[cell(h, i, bold=True) for i, h in enumerate(header)]]
    for r, row in enumerate(rows):
        data.append([cell(c, i, bold=(r in bold_rows)) for i, c in enumerate(row)])

    table = Table(data, colWidths=[w * inch for w in widths], repeatRows=1)
    cmds = [
        ("LINEABOVE", (0, 0), (-1, 0), 1.2, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 1.2, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    for r in rules_after:
        cmds.append(("LINEBELOW", (0, r + 1), (-1, r + 1), 0.3, colors.black))
    table.setStyle(TableStyle(cmds))
    return table


def table_block(key, caption, table):
    return KeepTogether([P(f"<b>Table {tn(key)}:</b> {caption}", "RTableCaption"), table, Spacer(1, 8)])


def figure_block(key, filename, width, caption, path=None):
    img = Image(path or os.path.join(PLOTS, filename))
    aspect = img.imageHeight / float(img.imageWidth)  # read the size first: ReportLab loads images lazily
    img.drawWidth = width * inch
    img.drawHeight = width * inch * aspect
    return KeepTogether([img, P(f"<b>Figure {fn(key)}:</b> {caption}", "RCaption")])


def draw_architecture(path):
    """Block diagram of the project, drawn in grey and black so it prints well."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 62)
    ax.axis("off")

    def box(x, y, w, h, text, fill="#EDEDED", size=8, bold_first=True):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=1.2",
                                    fc=fill, ec="black", lw=1.0))
        lines = text.split("\n")
        ax.text(x + w / 2, y + h / 2, "\n".join(lines), ha="center", va="center", fontsize=size,
                family="serif", linespacing=1.35)

    def arrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color="black", lw=1.0, shrinkA=0, shrinkB=0))

    # row 1: left to right
    box(1, 46, 28, 13, "SUMO traffic simulation\n20 setups\n4 situations \u00d7 5 densities")
    box(36, 46, 28, 13, "TraCI (Python)\ntrue state of every car,\nonce per simulated second")
    box(71, 46, 28, 13, "Nearest-RSU assignment\n(distance to fixed\nroadside units)")
    arrow(29, 52.5, 36, 52.5)
    arrow(64, 52.5, 71, 52.5)

    # row 2: right to left
    box(58, 25, 41, 14, "Five strategies, 8 variants\nRaw \u00b7 Delta \u00b7 Quantization 8/12/16/32 bits\nEvent-triggered \u00b7 Adaptive")
    box(30, 25, 22, 14, "RSU digital twin\nrebuilds each car's\nstate from updates")
    box(1, 25, 23, 14, "Compare with\ntrue state: bytes,\nerrors, Age of Info.")
    arrow(85, 46, 85, 39)
    arrow(58, 32, 52, 32)
    arrow(30, 32, 24, 32)

    # row 3: left to right
    box(1, 4, 28, 13, "results/all_results.csv\n410,136 measurements")
    box(36, 4, 28, 13, "Analysis scripts\nmetrics, tables, plots,\nbandwidth model")
    box(71, 4, 28, 13, "Checks and report\nverify_results.py\ngenerate_report.py")
    arrow(12, 25, 12, 17)
    arrow(29, 10.5, 36, 10.5)
    arrow(64, 10.5, 71, 10.5)

    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def pkg(name):
    try:
        return md.version(name)
    except md.PackageNotFoundError:
        return "not installed"


# ------------------------------ page furniture ------------------------------
def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(BODY, 9)
    canvas.drawCentredString(A4[0] / 2, 0.5 * inch, str(doc.page))
    canvas.restoreState()


# ---------------------------------- build ----------------------------------
def build():
    summ = {r["strategy"]: r for r in read_rows(os.path.join(REPO_ROOT, "analysis", "summary_by_strategy.csv"))}
    bw_rows = read_rows(os.path.join(REPO_ROOT, "analysis", "bandwidth_analysis.csv"))
    scen_rows = read_rows(os.path.join(REPO_ROOT, "analysis", "results_by_scenario.csv"))
    lane_rows = read_rows(os.path.join(REPO_ROOT, "results", "lane_aware_comparison.csv"))

    budgets = sorted({int(r["budget_bytes_per_sec"]) for r in bw_rows})
    tight = budgets[0]
    bw = {(r["strategy"], int(r["budget_bytes_per_sec"])): r for r in bw_rows}
    most_cars = int(bw_rows[0]["most_cars_seen_on_one_rsu_in_tests"])
    scen = {(r["scenario"], r["strategy"]): r for r in scen_rows}
    lane = {(r["scenario"], r["strategy"]): r for r in lane_rows}

    order = ["raw", "quantization_32bit", "delta", "quantization_16bit",
             "quantization_12bit", "event_triggered", "quantization_8bit", "adaptive"]
    ad, ev, rw = summ["adaptive"], summ["event_triggered"], summ["raw"]
    ad_bw, rw_bw = bw[("adaptive", tight)], bw[("raw", tight)]
    cap_gain = float(ad_bw["max_vehicles_per_rsu"]) / float(rw_bw["max_vehicles_per_rsu"])
    rows_total = 0
    with open(os.path.join(REPO_ROOT, "results", "all_results.csv")) as f:
        rows_total = sum(1 for _ in f) - 1
    car_seconds = rows_total // 8

    situations = [("steady_speed", "Constant speed"), ("accel_decel", "Acceleration / deceleration"),
                  ("turning", "Junction / turning"), ("lane_change", "Lane changing")]
    ad_pcts = {k: float(scen[(k, "adaptive")]["pct_of_raw_bytes"]) for k, _ in situations}
    ad_errs = {k: float(scen[(k, "adaptive")]["avg_position_error_m"]) for k, _ in situations}
    ev_peaks = {k: float(scen[(k, "event_triggered")]["peak_aoi_s"]) for k, _ in situations}
    label = dict(situations)
    cheapest_everywhere = all(
        float(scen[(k, "adaptive")]["pct_of_raw_bytes"]) < min(
            float(scen[(k, s)]["pct_of_raw_bytes"]) for s in order if s != "adaptive")
        for k, _ in situations)
    max_pct_k, min_pct_k = max(ad_pcts, key=ad_pcts.get), min(ad_pcts, key=ad_pcts.get)
    max_err_k, min_err_k = max(ad_errs, key=ad_errs.get), min(ad_errs, key=ad_errs.get)
    ev_hi_k, ev_lo_k = max(ev_peaks, key=ev_peaks.get), min(ev_peaks, key=ev_peaks.get)

    arch_path = os.path.join(REPORT_DIR, "architecture.png")
    draw_architecture(arch_path)

    S = []

    # ============================ title block ============================
    for line in TITLE_LINES:
        S.append(P(line, "RTitle"))
    S.append(P("Cloud Computing course project report", "RSub"))
    team_cells = [[Paragraph(f"<b>{n}</b><br/>{r}", styles["RCenter"]) for n, r in TEAM]]
    team_tbl = Table(team_cells, colWidths=[1.6 * inch] * len(TEAM))
    team_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    S.append(team_tbl)
    S.append(Spacer(1, 6))
    S.append(P(f"Team No. {TEAM_NUMBER} &nbsp;&nbsp;|&nbsp;&nbsp; Mentor: {MENTOR}", "RCenter"))
    S.append(P(REPORT_DATE, "RCenter"))

    S.append(P("Abstract", "RAbstractHead"))
    S.append(P(
        "Vehicular digital twins kept at roadside units (RSUs) need a steady stream of state updates from every "
        "car, and sending the complete state every second wastes V2I bandwidth. This project compares five "
        "state-transmission strategies in a SUMO traffic simulation controlled through TraCI: raw transmission, "
        "delta encoding, quantization (8, 12, 16 and 32 bits), event-triggered transmission, and an adaptive scheme "
        "that changes its compression with the car's driving mode. Four driving situations (constant speed, "
        "acceleration and deceleration, junction turning, lane changing) were run at 5, 10, 20, 50 and 100 "
        f"vehicles. The 20 setups produced {rows_total:,} logged measurements across eight strategy variants. "
        f"Adaptive compression used {num(ad['pct_of_raw_bytes'], 1)}% of the raw bytes (a "
        f"{num(ad['compression_ratio'], 1)}:1 compression ratio) with an average digital twin position error of "
        f"{num(ad['avg_position_error'], 1)} m and a worst-case Age of Information of {num(ad['peak_aoi'], 0)} s, "
        f"while plain event-triggering reached {num(ev['peak_aoi'], 0)} s. Under an assumed budget of {tight} bytes "
        f"per second per RSU, one RSU can support {ad_bw['max_vehicles_per_rsu']} vehicles with Adaptive against "
        f"{rw_bw['max_vehicles_per_rsu']} with Raw. Saving bytes and keeping the twin accurate pull in different "
        "directions, so both are measured. All numbers describe simulated state updates, not a real radio network, "
        "and the bandwidth budgets are assumptions. Python computes every metric from saved CSV files, and 21 "
        "automated checks test the results.", "RAbstract"))
    S.append(P("<b>Keywords:</b> vehicular digital twin, state compression, delta encoding, quantization, "
               "event-triggered transmission, Age of Information, V2I communication, SUMO, TraCI, cloud computing.",
               "RAbstract"))

    # ============================ 1 Introduction ============================
    S.append(P("1 Introduction", "RH1"))
    S.append(P(
        "Digital Twin-assisted Vehicular Edge Computing systems maintain a live virtual replica of each vehicle at "
        "a nearby Roadside Unit (RSU), so the roadside infrastructure can support applications such as collision "
        "prediction and traffic coordination without waiting on a distant cloud server. Keeping that replica "
        "accurate requires vehicles to continuously report their state &mdash; position, speed, heading, and "
        "acceleration &mdash; to their RSU. Doing this naively, by transmitting the complete state at every "
        "timestep, produces V2I communication overhead that scales directly with the number of vehicles and the "
        "update frequency, which becomes a bottleneck as vehicle density grows."))
    S.append(P(
        "This project investigates whether <b>adaptive state compression</b> &mdash; combining reduced-precision "
        "encoding with transmitting only when a vehicle's behavior actually changes &mdash; can substantially cut "
        "this communication overhead while keeping the Digital Twin's accuracy within an acceptable range. Five "
        "strategies are implemented and compared: Raw transmission, Delta encoding, State Quantization (at four "
        "bit-depths), Event-triggered transmission, and an Adaptive strategy that combines the previous techniques "
        "and switches behavior based on whether a vehicle is driving predictably or maneuvering."))
    S.append(P(
        "The project has four goals. We implement the five strategies in Python on top of a SUMO/TraCI "
        "simulation, evaluate them under five vehicle densities and four driving situations, measure communication "
        "cost, digital twin accuracy, freshness and bandwidth use, and make every number reproducible from saved "
        "data. The project models state updates between cars and RSUs. It is not a deployed system: no radio "
        "network is simulated and no real data is sent anywhere."))

    # ============================ 2 Background ============================
    S.append(P("2 Background and Understanding of the Problem", "RH1"))
    S.append(P("2.1 The core trade-off", "RH2"))
    S.append(P(
        "The core tension in this problem is between three competing goals that cannot all be maximized "
        "simultaneously: <b>communication cost</b> (how much data is sent), <b>freshness</b> (how quickly the RSU "
        "learns about a change, measured as Age of Information), and <b>accuracy</b> (how closely the RSU's Digital "
        "Twin matches the vehicle's real state). Sending the complete state every timestep maximizes freshness and "
        "accuracy but wastes bandwidth on redundant information &mdash; a vehicle cruising at constant speed on a "
        "straight road is, from a communication standpoint, not doing anything worth reporting every second."))
    S.append(P(
        "The insight this project tests is that vehicle behavior is not uniformly unpredictable: steady cruising is "
        "easy to predict from a vehicle's last known speed and heading, while braking, accelerating, or turning is "
        "not. A compression scheme that recognizes this distinction can spend its communication budget where it is "
        "actually needed &mdash; coarse and infrequent updates during predictable driving, fine and frequent "
        "updates during maneuvers &mdash; rather than treating every moment as equally important."))

    S.append(P("2.2 Digital twins, RSUs and V2I communication", "RH2"))
    S.append(P(
        "A digital twin is a software copy of a physical object that is kept up to date from measurements. In a "
        "digital twin-assisted vehicular edge system, each car reports its state to a nearby roadside unit (RSU), "
        "which keeps one twin per car and can run applications such as collision warning or traffic coordination "
        "close to the road. The car-to-RSU link is called V2I (vehicle-to-infrastructure). Its capacity is shared "
        "by every car in range, so the number of bytes each car sends decides how many cars one RSU can serve."))

    S.append(P("2.3 SUMO and TraCI", "RH2"))
    S.append(P(
        "SUMO is an open-source microscopic traffic simulator in which every car is simulated individually [1]. "
        "TraCI (Traffic Control Interface) lets a Python program connect to a running SUMO simulation, step it "
        "second by second, and read or change the state of each car [2]. Here TraCI is used only to read the true "
        "state of every car (position, speed, heading, acceleration) once per simulated second. That true state is "
        "the ground truth against which each strategy's digital twin is compared."))

    S.append(P("2.4 State compression techniques", "RH2"))
    S.append(bullets([
        "<b>Delta encoding</b> sends the change since the last update instead of the full value. Changes between "
        "consecutive seconds are small, so fewer bits describe them.",
        "<b>Quantization</b> maps a continuous value onto one of 2<super>b</super> levels. A b-bit quantizer over a "
        "range R has a step of R / (2<super>b</super> &minus; 1) and can never be wrong by more than half a step.",
        "<b>Event-triggered transmission</b> sends an update only when the car's real state differs from what the "
        "RSU would already predict by more than a threshold. Between updates the RSU extrapolates the car's motion.",
        "<b>Adaptive compression</b> combines these ideas and changes the thresholds, the number of bits and the "
        "longest allowed gap between updates according to whether the car is driving steadily or maneuvering.",
    ]))

    S.append(P("2.5 Age of Information", "RH2"))
    S.append(P(
        "Age of Information (AoI) measures freshness: the time since the RSU last received an update from a car [3]. "
        "A strategy that sends rarely saves bytes but lets the age grow. We report the average age and the worst "
        "case (the peak)."))

    # ============================ 3 System design ============================
    S.append(P("3 System Design", "RH1"))
    S.append(P("3.1 Architecture", "RH2"))
    S.append(P(
        f"Figure {fn('arch')} shows how data moves through the project. SUMO runs once per setup. TraCI reads the "
        "true state of every car each second, the nearest RSU is chosen by distance, and all strategies watch the "
        "same stream of true states in parallel, so every strategy is compared on identical traffic. Each "
        "strategy decides what to send; the RSU rebuilds the car's state from the updates it receives; and the "
        "result is compared with the true state. Every measurement is written to one CSV file, which the analysis "
        "scripts, the verification script and the report generator read."))
    S.append(figure_block("arch", None, 6.0,
                          "Architecture and data flow of the project. SUMO runs once per setup and every strategy "
                          "sees the same car states.", path=arch_path))

    S.append(P("3.2 Simulation environment", "RH2"))
    S.append(P(
        "Vehicle mobility is simulated in SUMO (Simulation of Urban MObility) and controlled at runtime via TraCI. "
        "Two road networks are used and reused across four driving scenarios: a straight two-lane road (for the "
        "steady-speed and lane-change scenarios) and a signalized four-arm intersection (for the accel-decel and "
        "turning scenarios). Reusing two networks across four scenarios, rather than building four separate "
        "networks, keeps the setup simpler while still producing four behaviorally distinct traffic patterns."))

    S.append(P("3.3 RSU placement", "RH2"))
    S.append(P(
        "Roadside Units are placed at fixed coordinates: three along the straight road (start, midpoint, end) so no "
        "point on the road is far from an RSU, and one on each arm of the intersection. Each vehicle is assigned to "
        "its nearest RSU by Euclidean distance at every timestep, so a vehicle traveling the length of the road or "
        "through the intersection is handed off between RSUs as it would be in a real deployment."))

    S.append(P("3.4 Vehicle state model", "RH2"))
    S.append(P(
        "Each vehicle's state is defined by five fields extracted directly from TraCI at every simulation step: "
        "position (x, y in metres), speed (m/s), heading (degrees, compass convention), and acceleration "
        "(m/s<super>2</super>). These five fields are what every strategy encodes, compresses, or withholds."))

    S.append(P("3.5 The five strategies", "RH2"))
    S.append(bullets([
        "<b>Raw:</b> Transmits the complete state, in full precision, every timestep. Serves as the uncompressed "
        "baseline (24 bytes per update).",
        "<b>Delta encoding:</b> Transmits the change since the last update instead of absolute values, "
        "fixed-point encoded at 16 bits per field (14 bytes per update).",
        "<b>Quantization:</b> Transmits the absolute state every timestep, but with each field reduced to a fixed "
        "bit-depth (8, 12, 16, or 32 bits), trading precision for size.",
        "<b>Event-triggered:</b> Transmits only when the vehicle's actual state deviates from where the RSU would "
        "predict it to be (assuming constant velocity) by more than a threshold.",
        "<b>Adaptive:</b> Combines event-triggering, quantization, and a maximum staleness bound, all tuned by "
        "whether the vehicle is currently classified as stable or maneuvering.",
    ]))
    S.append(P(f"Table {tn('strategies')} gives the exact packet sizes and trigger rules."))
    S.append(table_block(
        "strategies", "What each strategy sends, how large a packet is, and when it sends.",
        bw_table(
            ["Strategy", "What is sent", "Bytes per\npacket", "When it sends"],
            [
                ["Raw", "x, y, speed, heading, acceleration at 32 bits each, plus a 4-byte header", "24", "every second"],
                ["Delta", "change since the last sent state, 16-bit fixed point per field, plus header", "14",
                 "every second"],
                ["Quantization", "absolute state with every field reduced to b bits, plus header", "9, 12, 14, 24\n(b = 8, 12, 16, 32)",
                 "every second"],
                ["Event-triggered", "full-precision state, as in Raw", "24",
                 "only when position differs from the RSU's prediction by more than 1 m, or speed by 0.5 m/s, "
                 "heading by 5 degrees, or acceleration by 0.5 m/s<super>2</super>"],
                ["Adaptive", "quantized state: 8 bits when stable, 16 bits when maneuvering", "9 (stable)\n14 (maneuvering)",
                 "stable: thresholds doubled, at least every 2 s. Maneuvering (acceleration above 1.5 m/s<super>2</super> "
                 "or heading change above 5 degrees): base thresholds, at least every 0.5 s"],
            ],
            [1.05, 2.25, 1.05, 2.1], bold_rows=(4,), rules_after=(0, 1, 2, 3))))

    S.append(P("3.6 RSU-side reconstruction", "RH2"))
    S.append(P(
        "When a vehicle's update is not received (Event-triggered and Adaptive strategies), the RSU does not simply "
        "freeze the last known position. Instead it extrapolates using a constant-velocity model based on the "
        "vehicle's last reported speed and heading, which is a meaningfully better estimate than holding position "
        "fixed and costs almost no extra computation."))

    S.append(P("3.7 Technology stack", "RH2"))
    S.append(table_block(
        "stack",
        "Software used in the environment that built this report. SUMO, TraCI and sumolib are pinned to 1.27.1 in "
        "requirements.txt; the other packages are not pinned.",
        bw_table(
            ["Component", "Technology", "Role"],
            [
                ["Traffic simulator", f"SUMO (eclipse-sumo {pkg('eclipse-sumo')})",
                 "simulates every car, the road networks and the traffic light"],
                ["Simulation control", f"TraCI {pkg('traci')}, sumolib {pkg('sumolib')}",
                 "reads each car's true state every simulated second; reads the map's coordinate offset"],
                ["Language", f"Python {platform.python_version()} on {platform.system()}",
                 "strategies, RSU logic, experiments and analysis"],
                ["Numerics and tables", f"NumPy {pkg('numpy')}, pandas {pkg('pandas')}",
                 "metric calculation and summary tables"],
                ["Figures", f"Matplotlib {pkg('matplotlib')}", "all charts and the architecture diagram"],
                ["Report", f"ReportLab {pkg('reportlab')}", "builds this PDF from the CSV files"],
                ["Statistics", f"SciPy {pkg('scipy')}",
                 "listed in the project brief and installed; no script uses it"],
                ["Version control", "Git and GitHub", "source code, README and results"],
            ],
            [1.35, 2.35, 2.75])))

    # ============================ 4 Workflow ============================
    S.append(P("4 Workflow", "RH1"))
    S.append(P("The project was built in the following order:"))
    S.append(bullets([
        "Defined field ranges, quantization bit-depths, event-trigger thresholds, and the adaptive mode-switching "
        "rule in a design specification before writing any code.",
        "Verified the SUMO + TraCI toolchain end-to-end on a minimal network before building the real one.",
        "Built two reusable road networks and generated traffic for all 5 densities (5/10/20/50/100 vehicles) "
        "across all 4 scenarios (20 configurations total), validating that each scenario actually produces its "
        "intended driving behavior (e.g. confirming that only the turning scenario's vehicles change heading, and "
        "that lane-change and accel-decel scenarios show measurably different lane-switching and acceleration "
        "variance than the steady-speed baseline).",
        "Placed RSUs and implemented nearest-RSU assignment.",
        "Implemented all five strategies against the design spec's parameters, with a shared vehicle-state data "
        "structure and RSU-reconstruction logic reused across all of them.",
        "Built an experiment runner that simulates each of the 20 configurations once and feeds the same "
        "vehicle-state stream to all strategy variants in parallel, rather than re-running the simulation once per "
        "strategy.",
        "Computed every metric listed in the project brief from the full result set, and produced the plots and "
        "tables discussed in Section 6.",
    ]))

    S.append(P("4.1 Running the project", "RH2"))
    S.append(P(
        "The README in the repository lists every step with the output to expect. On Windows (PowerShell) the "
        "main run is:"))
    S.append(Preformatted(
        "python -m venv .venv\n"
        ".venv/Scripts/Activate.ps1\n"
        "pip install -r requirements.txt\n"
        "python experiments/experiment_runner.py      # all 20 setups x all strategies\n"
        "python analysis/plots.py                      # every metric, 2 tables, 6 charts\n"
        "python analysis/verify_results.py             # 21 sanity checks on the results\n"
        "python analysis/results_by_scenario.py        # results per driving situation",
        ParagraphStyle("RCode", fontName="Courier", fontSize=8.3, leading=11, leftIndent=18, spaceAfter=8)))
    S.append(P(
        "Smaller steps check each stage on its own: <font face='Courier'>network/validate_scenarios.py</font> checks "
        "the four driving situations, <font face='Courier'>traci_scripts/extract_state_rsu.py</font> logs the true "
        "car states with their nearest RSU for one setup, and <font face='Courier'>strategies/test_strategies.py</font> "
        "compares the strategies on that one setup. The traffic files for all 20 setups are included in the "
        "repository."))

    S.append(P("4.2 Two issues found during testing", "RH2"))
    S.append(P(
        "Two design errors were caught by testing against real simulation output rather than trusting the code by "
        "inspection, and both are informative about the problem domain itself:"))
    S.append(P(
        "<b>Coordinate offset.</b> SUMO's <font face='Courier'>netconvert</font> tool shifts a network's internal "
        "coordinates so that none are negative, which does not match the coordinates originally used to design "
        "the network's layout. RSU positions were initially placed using the original design coordinates directly, "
        "which silently misplaced every RSU on the intersection network (the straight road was unaffected, since "
        "its coordinates were already non-negative). The fix reads the actual coordinate offset from the network "
        "file at runtime and applies it, rather than hardcoding post-shift values that would break again if the "
        "network geometry changed."))
    S.append(P(
        "<b>Event-trigger threshold reference point.</b> The Event-triggered strategy initially compared a "
        "vehicle's new position to its last <i>transmitted</i> position. Since a vehicle cruising at a typical "
        "15 m/s covers about 15 metres every second from ordinary motion alone, this comparison exceeded the "
        "1-metre threshold on essentially every timestep regardless of whether the vehicle's behavior had changed "
        "at all &mdash; producing zero communication savings on the steady-speed scenario. The fix compares the "
        "vehicle's actual position against where the RSU would <i>predict</i> it to be (constant-velocity "
        "extrapolation from the last transmitted state), which is both the conceptually correct comparison and "
        "the one that actually reveals unpredictable behavior."))
    S.append(P(
        "A third problem was found while checking the report's own figures: the overhead per vehicle had first "
        "been divided by the whole 300-second window instead of by the time each car was actually on the road, "
        "which understated every strategy's cost by about four times. All overhead figures in this report use "
        "bytes per second per car <i>while it is on the road</i>."))

    # ============================ 5 Experimental setup ============================
    S.append(P("5 Experimental Setup", "RH1"))
    S.append(P("5.1 Environment", "RH2"))
    S.append(P(
        "The recorded results were produced on Linux with Python 3.12. The full pipeline was also run on Windows "
        f"with Python 3.14, where every step completed. Table {tn('stack')} lists the software. The simulated "
        "cars and RSUs have no CPU, memory or radio limits: the study measures bytes, accuracy and freshness, not "
        "processing time."))
    hw_rows = [[k, v] for k, v in HARDWARE.items() if v]
    if hw_rows:
        S.append(Spacer(1, 4))
        S.append(bw_table(["Item", "Specification"], hw_rows, [2.0, 4.0]))
        S.append(P("Machine used to run the simulation.", "RCaption"))

    S.append(P("5.2 Vehicles and workload", "RH2"))
    S.append(P(
        "Each of the 4 scenarios (steady-speed, lane-change, accel-decel, turning) was run at 5 vehicle densities "
        "(5, 10, 20, 50, 100), for 20 configurations total. Cars enter during the first 270 seconds of each setup "
        "and every run continues until the last car has finished its trip, so a run lasts between 245 and 441 "
        "simulated seconds. Every configuration was run once through SUMO/TraCI, with the resulting vehicle-state "
        "stream fed to all 8 strategy variants (Raw, Delta, Quantization at 8/12/16/32 bits, Event-triggered, and "
        "Adaptive) in parallel. For every vehicle at every timestep, the following were logged: whether an update "
        "was transmitted, bytes sent, position error, speed error, heading error, and Age of Information. "
        f"Table {tn('params')} summarizes the setup."))
    S.append(table_block(
        "params", "Experiment parameters.",
        bw_table(
            ["Parameter", "Setting"],
            [
                ["Road networks", "straight two-lane road (1,000 m); crossroads with four arms of about 300 m and a traffic light"],
                ["Driving situations", "constant speed; acceleration / deceleration; junction / turning; lane changing"],
                ["Vehicle densities", "5, 10, 20, 50 and 100 vehicles per setup"],
                ["Setups", "20 (4 situations \u00d7 5 densities), 740 cars in total"],
                ["Simulated time", "cars enter during the first 270 s; each run lasts until the last car finishes "
                                   "(245 to 441 s); time step 1 s"],
                ["Traffic random seed", "42, one seed per setup"],
                ["RSUs", "straight road: 3 (at 0, 500 and 1,000 m); crossroads: 4 (150 m from the centre on each arm); "
                         "nearest RSU by distance"],
                ["Strategies compared", "8 variants: Raw, Delta, Quantization (8, 12, 16, 32 bits), Event-triggered, Adaptive"],
                ["Ground truth", "SUMO's state of each car once per second"],
                ["Twin between updates", "constant-velocity extrapolation from the last received update"],
                ["Logged measurements", f"{car_seconds:,} car-seconds \u00d7 8 variants = {rows_total:,} rows"],
            ],
            [1.7, 4.75], rules_after=tuple(range(10)))))

    S.append(P("5.3 Metrics", "RH2"))
    S.append(P(
        "Every metric listed in the project brief is computed from this dataset. One row of the dataset is one car "
        "on the road for one simulated second, so &ldquo;per vehicle&rdquo; always means per car <i>while it is on "
        "the road</i>."))
    S.append(bullets([
        "<b>Total data transmitted:</b> the sum of the bytes sent by all cars.",
        "<b>Communication overhead:</b> total bytes divided by vehicle-seconds (bytes per second per vehicle).",
        "<b>Packet transmission rate:</b> packets sent per vehicle-second (also shown as the share of timesteps with a transmission).",
        "<b>Compression ratio:</b> Raw's total bytes divided by the strategy's total bytes.",
        "<b>Digital twin position, speed and heading error:</b> the difference between the RSU's reconstructed state "
        "and SUMO's true state, averaged over all vehicle-seconds.",
        "<b>Average and peak Age of Information (AoI):</b> the seconds since the RSU last received an update from "
        "that car: the average over all vehicle-seconds, and the single worst value.",
        "<b>V2I channel utilization:</b> the bytes offered to an RSU in one second divided by that RSU's bandwidth "
        "budget (above 100% means the channel is overloaded).",
        "<b>Packet delivery ratio:</b> the share of packets that fit within the RSU's budget; in an overloaded "
        "second, packets are dropped evenly.",
        "<b>Maximum supported vehicles:</b> the number of cars one RSU can serve before its average load reaches "
        "the budget (the budget divided by bytes per second per vehicle).",
        f"<b>Freshness-accuracy-communication trade-off:</b> Figure {fn('tradeoff')} (accuracy against bytes used), "
        f"together with the AoI results in Table {tn('acc')} and Figure {fn('aoi')}.",
    ]))

    S.append(P("5.4 Bandwidth model", "RH2"))
    S.append(P(
        "The brief asks for results under &ldquo;a given bandwidth constraint&rdquo; without fixing a number, so "
        "each RSU is assumed to have a fixed budget of bytes per second reserved for digital twin "
        f"synchronization. Three budgets are used: {budgets[0]}, {budgets[1]} and {budgets[2]} bytes per second "
        "(2, 4 and 8 kbit/s). These are assumptions sized to this small simulation, not measurements of a real V2I "
        f"link: no more than {most_cars} cars were ever attached to one RSU at the same time, and {tight} bytes per "
        "second is the only budget tight enough to overload an RSU in our traffic. Utilization and the packet "
        "delivery ratio are computed from the logged traffic. Dropped packets are not fed back into the twin's "
        "error figures, so those figures assume every packet a strategy sends is received."))

    S.append(P("5.5 Choice of parameter values", "RH2"))
    S.append(P(
        "The quantization levels (8, 12, 16 and 32 bits) come from the project brief. The event-trigger thresholds "
        "(1 m, 0.5 m/s, 5 degrees, 0.5 m/s<super>2</super>), the maneuvering cut-offs (1.5 m/s<super>2</super> and "
        "5 degrees), the bit-depths of Adaptive's two modes (8 and 16) and its update gaps (2 s and 0.5 s) are "
        "demonstration values fixed in the design specification before the experiment. They were not tuned per "
        "scenario and we do not claim they are optimal. The bandwidth budgets are assumptions (Section 5.4)."))

    # ============================ 6 Results ============================
    S.append(P("6 Results", "RH1"))
    S.append(P("6.1 Communication cost and compression", "RH2"))
    S.append(P(
        f"Table {tn('comm')} shows what each strategy costs, averaged across all 20 configurations. Adaptive uses "
        f"{num(ad['pct_of_raw_bytes'], 1)}% of Raw's bytes (a compression ratio of {num(ad['compression_ratio'], 1)}:1), "
        f"or {num(ad['overhead_bytes_per_sec_per_vehicle'])} bytes per second per vehicle against Raw's "
        f"{num(rw['overhead_bytes_per_sec_per_vehicle'], 0)}, while sending a packet in only "
        f"{num(100 * float(ad['packets_per_sec_per_vehicle']), 1)}% of timesteps."))
    S.append(table_block(
        "comm", "Communication cost of each strategy (all 20 configurations combined).",
        bw_table(
            ["Strategy", "Total bytes", "% of raw\nbytes", "Compression\nratio", "Bytes/sec\nper vehicle", "Packets/sec\nper vehicle"],
            [[n, f"{int(float(summ[n]['total_bytes'])):,}", f"{num(summ[n]['pct_of_raw_bytes'], 1)}%",
              f"{num(summ[n]['compression_ratio'])}:1", num(summ[n]["overhead_bytes_per_sec_per_vehicle"]),
              num(summ[n]["packets_per_sec_per_vehicle"], 3)] for n in order],
            [1.6, 1.0, 0.8, 0.95, 1.05, 1.05], bold_rows=(7,))))
    S.append(figure_block(
        "tradeoff", "tradeoff.png", 5.0,
        "Freshness-accuracy-communication trade-off. Adaptive sits furthest to the left (least data used) while "
        "matching or beating Quantization at 8 bits on accuracy, despite using fewer bytes."))
    S.append(figure_block("bytes", "bytes_by_strategy.png", 5.2,
                          "Total data transmitted by each strategy, relative to Raw."))
    S.append(figure_block(
        "overhead", "overhead_vs_density.png", 5.6,
        "Communication overhead per vehicle on the road, as density increases. Raw and 32-bit Quantization overlap "
        "exactly (identical byte count per update), as do Delta and 16-bit Quantization &mdash; this is expected, "
        "not an error. The per-vehicle cost stays flat because each vehicle's strategy runs independently of how "
        "many other vehicles are around; what grows with density is the total load on each RSU (Section 6.3)."))

    S.append(P("6.2 Accuracy and freshness", "RH2"))
    S.append(P(
        f"Table {tn('acc')} shows how closely the RSU's digital twin tracks the real vehicles. Strategies that "
        f"transmit at every timestep have zero Age of Information. For the two strategies that skip transmissions, "
        f"the average staleness is {num(ev['avg_aoi'])} s for Event-triggered and {num(ad['avg_aoi'])} s for "
        f"Adaptive; the worst case is far apart: {num(ev['peak_aoi'], 0)} s for Event-triggered against "
        f"{num(ad['peak_aoi'], 0)} s for Adaptive."))
    S.append(table_block(
        "acc", "Digital twin accuracy and Age of Information (AoI) for each strategy.",
        bw_table(
            ["Strategy", "Position\nerror (m)", "Speed error\n(m/s)", "Heading\nerror (deg)", "Average\nAoI (s)", "Peak\nAoI (s)"],
            [[n, num(summ[n]["avg_position_error"], 3), num(summ[n]["avg_speed_error"], 3),
              num(summ[n]["avg_heading_error"], 3), num(summ[n]["avg_aoi"]), num(summ[n]["peak_aoi"], 0)]
             for n in order],
            [1.6, 1.0, 1.0, 1.0, 0.9, 0.9], bold_rows=(7,))))
    S.append(figure_block(
        "aoi", "aoi_vs_density.png", 6.2,
        "Age of Information under increasing traffic density, average (left) and worst case (right). Adaptive keeps "
        "staleness low and flat; plain Event-triggered is higher and, in the worst case, can go tens of seconds "
        "without an update from a vehicle."))

    S.append(P("6.3 Channel utilization, packet delivery and supported vehicles", "RH2"))
    S.append(P(
        f"Table {tn('bw')} applies the bandwidth model of Section 5.4. At the tightest budget ({tight} bytes per "
        f"second per RSU), Raw's busiest moment fills the channel to {num(rw_bw['peak_utilization_pct'], 0)}% and "
        f"{num(rw_bw['overloaded_pct_of_rsu_seconds'], 1)}% of RSU-seconds are overloaded, so only "
        f"{num(rw_bw['packet_delivery_ratio_pct'], 1)}% of its packets get through. Adaptive peaks at "
        f"{num(ad_bw['peak_utilization_pct'], 0)}%, is never overloaded and delivers "
        f"{num(ad_bw['packet_delivery_ratio_pct'], 1)}% of its packets. Under the same budget one RSU can support "
        f"{ad_bw['max_vehicles_per_rsu']} vehicles with Adaptive against {rw_bw['max_vehicles_per_rsu']} with Raw "
        f"({num(cap_gain, 1)} times as many)."))
    S.append(table_block(
        "bw",
        f"Bandwidth analysis. Utilization, overload and delivery are shown for the {tight} B/s budget; the last "
        "three columns give the maximum vehicles one RSU can support at each budget (B/s = bytes per second).",
        bw_table(
            ["Strategy", f"Avg util.\n@{budgets[0]} B/s", f"Peak util.\n@{budgets[0]} B/s",
             f"Overloaded\n@{budgets[0]} B/s", f"Packets\ndelivered\n@{budgets[0]} B/s",
             f"Max veh.\n@{budgets[0]}", f"Max veh.\n@{budgets[1]}", f"Max veh.\n@{budgets[2]}"],
            [[n, f"{num(bw[(n, tight)]['mean_utilization_pct'], 1)}%", f"{num(bw[(n, tight)]['peak_utilization_pct'], 0)}%",
              f"{num(bw[(n, tight)]['overloaded_pct_of_rsu_seconds'], 1)}%",
              f"{num(bw[(n, tight)]['packet_delivery_ratio_pct'], 1)}%"] +
             [bw[(n, b)]["max_vehicles_per_rsu"] for b in budgets] for n in order],
            [1.45, 0.7, 0.7, 0.8, 0.8, 0.65, 0.65, 0.65], bold_rows=(7,))))
    S.append(figure_block(
        "channel", "channel_utilization.png", 5.8,
        f"How full an RSU's channel gets at a budget of {tight} bytes per second. Bars past the dashed line mean "
        "the channel is overloaded and packets are dropped."))
    S.append(figure_block("maxveh", "max_vehicles.png", 5.6,
                          "Maximum number of vehicles one RSU can support under each bandwidth budget."))

    S.append(P("6.4 Results by driving situation", "RH2"))
    cheap_text = (
        f"Adaptive is the cheapest strategy in each of the four situations, using between "
        f"{num(ad_pcts[min_pct_k], 1)}% ({label[min_pct_k].lower()}) and {num(ad_pcts[max_pct_k], 1)}% "
        f"({label[max_pct_k].lower()}) of Raw's bytes. "
        if cheapest_everywhere else
        "Table {0} gives the results for each situation. ".format(tn('scen')))
    S.append(P(
        f"The brief asks for the strategies to be evaluated under different mobility conditions. Table {tn('scen')} "
        f"splits the results by driving situation. {cheap_text}"
        f"Its position error is largest in {label[max_err_k].lower()} ({num(ad_errs[max_err_k])} m), where it "
        f"mostly uses its coarsest 8-bit packets, and smallest in {label[min_err_k].lower()} "
        f"({num(ad_errs[min_err_k])} m), which fits it spending the most bytes there and using its finer 16-bit "
        f"packets more often. Plain Event-triggered shows long gaps without an update in every situation, with a "
        f"worst case of {num(ev_peaks[ev_lo_k], 0)} s ({label[ev_lo_k].lower()}) up to {num(ev_peaks[ev_hi_k], 0)} s "
        f"({label[ev_hi_k].lower()}), while Adaptive never exceeds {num(ad['peak_aoi'], 0)} s. The same breakdown "
        "by vehicle density is in analysis/results_by_density.csv."))
    scen_table_rows, scen_bold, scen_rules = [], [], []
    for k, name in situations:
        for s_key, s_label in (("event_triggered", "Event-triggered"), ("quantization_8bit", "Quantization 8-bit"),
                               ("adaptive", "Adaptive")):
            r = scen[(k, s_key)]
            first = s_key == "event_triggered"
            scen_table_rows.append([name if first else "", s_label, f"{num(r['pct_of_raw_bytes'], 1)}%",
                                    num(r["avg_position_error_m"], 3), num(r["avg_aoi_s"]), num(r["peak_aoi_s"], 0)])
            if s_key == "adaptive":
                scen_bold.append(len(scen_table_rows) - 1)
                scen_rules.append(len(scen_table_rows) - 1)
    S.append(table_block(
        "scen",
        "Results by driving situation for the strategies that save the most data (all densities combined). "
        "Raw is 100% of bytes with zero error in every situation.",
        bw_table(["Situation", "Strategy", "% of raw\nbytes", "Position\nerror (m)", "Average\nAoI (s)", "Peak\nAoI (s)"],
                 scen_table_rows, [1.7, 1.45, 0.8, 0.9, 0.8, 0.8], bold_rows=tuple(scen_bold),
                 rules_after=tuple(scen_rules[:-1]), left_cols=2)))

    S.append(P("6.5 A lane-change-aware variant of Adaptive", "RH2"))
    lane_all_a, lane_all_l = lane[("ALL", "adaptive")], lane[("ALL", "adaptive_lane_aware")]
    S.append(P(
        "The brief lists lane changes as one of the conditions that should trigger more frequent updates. The "
        "submitted Adaptive strategy reacts to strong acceleration or braking and to heading changes, which "
        "catches junction turns, but it does not look at lane changes directly. As an extra test we built a "
        "variant that also treats a lane change as maneuvering, and ran it on the same 20 setups "
        f"(Table {tn('lane')}). The difference is negligible: {num(lane_all_a['pct_of_raw_bytes'], 1)}% against "
        f"{num(lane_all_l['pct_of_raw_bytes'], 1)}% of raw bytes and {num(lane_all_a['avg_position_error_m'], 3)} m "
        f"against {num(lane_all_l['avg_position_error_m'], 3)} m of position error. The reason is that lane "
        f"changes are rare in our scenarios: only {lane_all_a['lane_changes_seen']} occurred in {car_seconds:,} "
        "car-seconds. This extra run reproduced the submitted Adaptive total of "
        f"{int(float(ad['total_bytes'])):,} bytes exactly, so the submitted results are unaffected."))
    lane_rows_out = []
    for k, name in (("ALL", "All situations"), ("lane_change", "Lane changing")):
        for s_key, s_label in (("adaptive", "Adaptive (submitted)"), ("adaptive_lane_aware", "Adaptive, lane-aware")):
            r = lane[(k, s_key)]
            lane_rows_out.append([name if s_key == "adaptive" else "", s_label, f"{num(r['pct_of_raw_bytes'], 1)}%",
                                  num(r["avg_position_error_m"], 3), num(r["avg_aoi_s"]), r["lane_changes_seen"]])
    S.append(table_block(
        "lane", "Adaptive with and without lane-change awareness.",
        bw_table(["Situation", "Strategy", "% of raw\nbytes", "Position\nerror (m)", "Average\nAoI (s)", "Lane changes\nseen"],
                 lane_rows_out, [1.4, 1.75, 0.8, 0.9, 0.8, 0.95], rules_after=(1,), left_cols=2)))

    S.append(P("6.6 Implementation validation and reproducibility", "RH2"))
    S.append(P(
        f"<b>Scenario checks.</b> Each driving situation was run with 20 vehicles and measured (Table {tn('valid')}). "
        "Only the turning scenario turns cars; the traffic light gives the accel-decel scenario nearly twice the "
        "acceleration variability of steady driving; and the slow cars in the lane-change scenario cause more lane "
        "changes and a lower average speed than steady driving. These are the differences the scenarios were "
        "designed to produce."))
    S.append(table_block(
        "valid", "Scenario validation at 20 vehicles (recorded run of network/validate_scenarios.py).",
        bw_table(["Situation", "Cars that\nturned", "Acceleration\nvariability", "Average\nspeed (m/s)", "Lane\nchanges"],
                 [["Constant speed", "0%", "0.53", "15.3", "11"],
                  ["Lane changing", "0%", "0.56", "11.5", "28"],
                  ["Acceleration / deceleration", "0%", "0.98", "10.1", "45"],
                  ["Junction / turning", "100%", "1.10", "10.0", "50"]],
                 [2.0, 1.0, 1.15, 1.15, 0.9])))
    S.append(P(
        "<b>RSU hand-off.</b> Tracing single cars confirmed the nearest-RSU assignment. On the straight road a car "
        "moved from RSU_0 to RSU_1 after 19 s and to RSU_2 after 50 s; at the crossroads a car entering from the "
        "west arm and leaving by the south arm switched from RSU_W to RSU_S as it passed the junction."))
    S.append(P(
        "<b>Checks on the results.</b> The script <font face='Courier'>analysis/verify_results.py</font> runs 21 "
        "sanity checks that need no reference numbers:"))
    S.append(bullets([
        "Raw sends 24 bytes every second with zero error and zero Age of Information, and every fixed-size strategy "
        "sends exactly the packet size its format implies.",
        "Every strategy has the same number of rows, and time advances exactly one second per row, so the "
        "per-second metrics are valid.",
        "A quantizer is never wrong by more than half a step. For 8-bit quantization the worst position error is "
        "2.70 m against a limit of 2.77 m, and Delta's errors stay below half of one 16-bit step.",
        "For Event-triggered and Adaptive, bytes are counted exactly when a packet is sent, the Age of Information "
        "is 0 exactly when a packet is sent, and Adaptive never goes two seconds without an update.",
    ]))
    S.append(P(
        "All 21 checks pass, and all 11 headline numbers match the reference results. To test the checks "
        "themselves, the results file was corrupted in five different ways (a wrong packet size, an impossible "
        "error, a stale Age of Information, a missing row, and bytes counted for a packet never sent); the script "
        "failed on every one. Deleting every generated file and re-running the whole pipeline in a fresh "
        f"environment reproduced the stored results file ({rows_total:,} rows), the summary table and the "
        "bandwidth table exactly."))
    S.append(P(
        "These checks show that the numbers are internally consistent and obey the arithmetic they must obey. They "
        "do not show that the simulation matches real traffic, that the thresholds are the best possible, or how a "
        "real radio network would behave."))

    # ============================ 7 Discussion ============================
    S.append(P("7 Discussion", "RH1"))
    S.append(P(
        "The central finding is that Adaptive achieves the best overall result not by skipping more transmissions "
        "than plain Event-triggered (its transmission rate is actually similar), but by sending a smaller, "
        "quantized packet on the occasions when it does transmit. This confirms that the two compression "
        "mechanisms &mdash; deciding <i>whether</i> to send and deciding <i>how much</i> to send &mdash; are "
        "complementary rather than redundant, and that combining them outperforms either technique used alone."))
    S.append(P(
        f"Freshness is where the two event-based strategies differ most. A car that behaves exactly as the RSU "
        f"predicts never triggers an update, so plain Event-triggered can leave the RSU without news of a car for up "
        f"to {num(ev['peak_aoi'], 0)} seconds. Adaptive adds a maximum-staleness rule, which holds its worst case to "
        f"{num(ad['peak_aoi'], 0)} second at a cost of only a few extra packets."))
    S.append(P(
        f"Quantization alone shows a clear, expected trade-off: 8-bit quantization uses "
        f"{num(summ['quantization_8bit']['pct_of_raw_bytes'], 1)}% of Raw's bytes but has an average position error "
        f"of {num(summ['quantization_8bit']['avg_position_error'])} m, while 16-bit and 32-bit quantization are "
        "effectively lossless at correspondingly higher byte cost. The choice of bit-depth is a direct, tunable "
        "trade-off between communication cost and accuracy."))
    S.append(P(
        f"The bandwidth analysis turns these byte savings into capacity. Because every car decides independently, "
        f"the per-vehicle cost does not change with density (Figure {fn('overhead')}), so the load on an RSU grows "
        f"with the number of cars attached to it. Under a tight budget this separates the strategies: Raw overloads "
        f"the channel and loses packets, while Adaptive stays below the limit and supports about {num(cap_gain, 1)} "
        "times as many vehicles per RSU."))

    # ============================ 8 Limitations ============================
    S.append(P("8 Limitations and Future Work", "RH1"))
    S.append(bullets([
        f"The bandwidth budgets ({budgets[0]}, {budgets[1]} and {budgets[2]} bytes per second per RSU) are "
        "assumptions chosen to suit this small simulation, not measurements of a real V2I link. The utilization and "
        "packet delivery results depend on them.",
        "Packet delivery is analyzed on top of the logged traffic: dropped packets are not fed back into the twin, "
        "so the position, speed, heading and AoI figures assume every packet a strategy sends is received. There is "
        "no radio model, and &ldquo;nearest RSU&rdquo; means smallest distance only.",
        f"Maximum supported vehicles is calculated from the average per-vehicle rate. The busiest RSU in our tests "
        f"held {most_cars} cars at once, so any value above {most_cars} is an extrapolation rather than something "
        "the simulation directly tested.",
        "The Raw packet is 24 bytes: x, y, speed, heading and acceleration plus a 4-byte header that stands in for "
        "the vehicle id and timestamp. The timestamp is not modeled as a separate field.",
        "The submitted Adaptive strategy reacts to lane changes and junction movements only through acceleration "
        "and heading change. A variant with direct lane-change detection made almost no difference (Section 6.5).",
        "Quantization field ranges (speed, heading, acceleration, position relative to RSU) are fixed design "
        "assumptions; a deployment would need to calibrate these to its actual road and speed limits.",
        "The Adaptive strategy's mode-switching thresholds were chosen from the design specification and not "
        "separately tuned per scenario; a sensitivity analysis over these thresholds would be a natural extension.",
        "Only one random seed was used per configuration, and the simulation is small (at most 100 vehicles on two "
        "small road layouts); averaging over multiple seeds and larger networks would give more robust estimates "
        "of each strategy's performance.",
    ]))
    S.append(P(
        "Future work includes a wireless channel model with packet loss that feeds back into the twin, tuning the "
        "thresholds for each driving situation, several seeds and larger road networks, and several RSUs "
        "sharing coverage of the same road."))

    # ============================ 9 Conclusion ============================
    S.append(P("9 Conclusion", "RH1"))
    S.append(P(
        f"Adaptive state compression, combining event-triggered transmission with mode-dependent quantization, "
        f"reduced V2I communication overhead to {num(ad['pct_of_raw_bytes'], 1)}% of the uncompressed baseline "
        f"(a {num(ad['compression_ratio'], 1)}:1 compression ratio) while keeping average Digital Twin position "
        f"error near {num(ad['avg_position_error'], 1)} metres and worst-case staleness to {num(ad['peak_aoi'], 0)} "
        f"second. Under a tight bandwidth budget it also let one RSU support about {num(cap_gain, 1)} times as many "
        "vehicles as sending everything. This supports the hypothesis that recognizing when a vehicle's behavior is "
        "predictable, and compressing accordingly, is more effective than applying uniform compression regardless "
        "of driving context."))
    S.append(P(
        "The experiment runner, the exported CSV files, the verification script and the report generator let "
        "anyone reproduce the numbers and figures from the repository. The report keeps a clear line between "
        "simulated state updates and a real radio network."))

    # ============================ References ============================
    S.append(P("References", "RH1"))
    S.append(P(
        "[1] P. Alvarez Lopez, M. Behrisch, L. Bieker-Walz, J. Erdmann, Y.-P. Fl&ouml;tter&ouml;d, R. Hilbrich, "
        "L. L&uuml;cken, J. Rummel, P. Wagner and E. Wie&szlig;ner. Microscopic traffic simulation using SUMO. In "
        "<i>21st IEEE International Conference on Intelligent Transportation Systems (ITSC)</i>, pp. 2575&ndash;2582, "
        "2018. https://doi.org/10.1109/ITSC.2018.8569938", "RRef"))
    S.append(P(
        "[2] A. Wegener, M. Pi&oacute;rkowski, M. Raya, H. Hellbr&uuml;ck, S. Fischer and J.-P. Hubaux. TraCI: An "
        "interface for coupling road traffic and network simulators. In <i>Proceedings of the 11th Communications "
        "and Networking Simulation Symposium (CNS '08)</i>, pp. 155&ndash;163, 2008. "
        "https://doi.org/10.1145/1400713.1400740", "RRef"))
    S.append(P(
        "[3] S. Kaul, R. Yates and M. Gruteser. Real-time status: How often should one update? In <i>Proceedings of "
        "IEEE INFOCOM</i>, pp. 2731&ndash;2735, 2012. https://doi.org/10.1109/INFCOM.2012.6195689", "RRef"))

    doc = SimpleDocTemplate(
        os.path.join(REPORT_DIR, "report.pdf"), pagesize=A4,
        topMargin=0.9 * inch, bottomMargin=0.9 * inch, leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        title=" ".join(TITLE_LINES), author=", ".join(n for n, _ in TEAM))
    doc.build(S, onFirstPage=footer, onLaterPages=footer)
    print("Wrote", os.path.join(REPORT_DIR, "report.pdf"))


if __name__ == "__main__":
    build()
