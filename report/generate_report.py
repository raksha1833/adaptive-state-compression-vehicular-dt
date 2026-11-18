"""
Generates report.pdf: understanding, workflow, and results, per the assignment.
Needs the output of analysis/plots.py: analysis/plots/*.png, summary_by_strategy.csv and bandwidth_analysis.csv.
"""
import csv
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle, ListFlowable, ListItem
)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="Justify", parent=styles["Normal"], alignment=4, spaceAfter=10, leading=15))
styles.add(ParagraphStyle(name="H1", parent=styles["Heading1"], spaceBefore=18, spaceAfter=8))
styles.add(ParagraphStyle(name="H2", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6))
styles.add(ParagraphStyle(name="Caption", parent=styles["Normal"], fontSize=9, textColor=colors.grey,
                          alignment=1, spaceAfter=14))
styles.add(ParagraphStyle(name="TitleMain", parent=styles["Title"], fontSize=20, spaceAfter=6))
styles.add(ParagraphStyle(name="Subtitle", parent=styles["Normal"], fontSize=13, alignment=1,
                          textColor=colors.grey, spaceAfter=40))

P = lambda text, style="Justify": Paragraph(text, styles[style])


def read_summary(path):
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def make_table(header, body, col_widths, font_size=9):
    """A styled table; the last row (Adaptive) is highlighted."""
    table = Table([header] + body, colWidths=[w * inch for w in col_widths])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#378ADD")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1EFE8")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E1F5EE")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def num(x, digits=2):
    return f"{float(x):.{digits}f}"


def fig(path, width=6.3 * inch):
    img = Image(path)
    aspect = img.imageHeight / float(img.imageWidth)
    img.drawWidth = width
    img.drawHeight = width * aspect
    return img


# ---- FILL THESE IN, then run:  python report/generate_report.py ----
# Anything left as "" is printed as a blank line you can write on by hand.
STUDENT_NAMES = "Shreeraksha R J"
ROLL_NUMBERS = "241CS155"
GROUP_SECTION = "S1"
MENTOR_NAME = "ANSHUL"
SUBMISSION_DATE = "20/11/2026"
# ---------------------------------------------------------------------

BLANK = "_______________________________"

REPORT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(REPORT_DIR)


def build():
    doc = SimpleDocTemplate(os.path.join(REPORT_DIR, "report.pdf"), pagesize=letter,
                             topMargin=0.9 * inch, bottomMargin=0.9 * inch,
                             leftMargin=0.9 * inch, rightMargin=0.9 * inch)
    S = []

    # ---- Title page ----
    S.append(Spacer(1, 1.5 * inch))
    S.append(P("Adaptive State Compression for<br/>Communication-Efficient Vehicular Digital Twins", "TitleMain"))
    S.append(P("Cloud Computing Course Project Report", "Subtitle"))
    meta = Table([
        ["Name(s):", STUDENT_NAMES or BLANK],
        ["Roll Number(s):", ROLL_NUMBERS or BLANK],
        ["Group/Section:", GROUP_SECTION or BLANK],
        ["Mentor:", MENTOR_NAME or BLANK],
        ["Date:", SUBMISSION_DATE or BLANK],
    ], colWidths=[1.6 * inch, 3.6 * inch])
    meta.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    S.append(meta)
    S.append(PageBreak())

    # ---- 1. Introduction ----
    S.append(P("1. Introduction", "H1"))
    S.append(P(
        "Digital Twin-assisted Vehicular Edge Computing systems maintain a live virtual replica of each "
        "vehicle at a nearby Roadside Unit (RSU), so the roadside infrastructure can support applications "
        "such as collision prediction and traffic coordination without waiting on a distant cloud server. "
        "Keeping that replica accurate requires vehicles to continuously report their state &mdash; position, "
        "speed, heading, and acceleration &mdash; to their RSU. Doing this naively, by transmitting the "
        "complete state at every timestep, produces V2I communication overhead that scales directly with "
        "the number of vehicles and the update frequency, which becomes a bottleneck as vehicle density grows."
    ))
    S.append(P(
        "This project investigates whether <b>adaptive state compression</b> &mdash; combining reduced-precision "
        "encoding with transmitting only when a vehicle's behavior actually changes &mdash; can substantially cut "
        "this communication overhead while keeping the Digital Twin's accuracy within an acceptable range. Five "
        "strategies are implemented and compared: Raw transmission, Delta encoding, State Quantization (at four "
        "bit-depths), Event-triggered transmission, and an Adaptive strategy that combines the previous "
        "techniques and switches behavior based on whether a vehicle is driving predictably or maneuvering."
    ))

    # ---- 2. Understanding ----
    S.append(P("2. Understanding of the Problem", "H1"))
    S.append(P(
        "The core tension in this problem is between three competing goals that cannot all be maximized "
        "simultaneously: <b>communication cost</b> (how much data is sent), <b>freshness</b> (how quickly the "
        "RSU learns about a change, measured as Age of Information), and <b>accuracy</b> (how closely the "
        "RSU's Digital Twin matches the vehicle's real state). Sending the complete state every timestep "
        "maximizes freshness and accuracy but wastes bandwidth on redundant information &mdash; a vehicle "
        "cruising at constant speed on a straight road is, from a communication standpoint, not doing anything "
        "worth reporting every second."
    ))
    S.append(P(
        "The insight this project tests is that vehicle behavior is not uniformly unpredictable: steady "
        "cruising is easy to predict from a vehicle's last known speed and heading, while braking, accelerating, "
        "or turning is not. A compression scheme that recognizes this distinction can spend its communication "
        "budget where it is actually needed &mdash; coarse and infrequent updates during predictable driving, "
        "fine and frequent updates during maneuvers &mdash; rather than treating every moment as equally important."
    ))

    # ---- 3. System Design ----
    S.append(P("3. System Design", "H1"))

    S.append(P("3.1 Simulation Environment", "H2"))
    S.append(P(
        "Vehicle mobility is simulated in SUMO (Simulation of Urban MObility) and controlled at runtime via "
        "TraCI (Traffic Control Interface), which allows querying and stepping the simulation from Python. "
        "Two road networks are used and reused across four driving scenarios: a straight two-lane road "
        "(for the steady-speed and lane-change scenarios) and a signalized four-arm intersection (for the "
        "accel-decel and turning scenarios). Reusing two networks across four scenarios, rather than building "
        "four separate networks, keeps the setup simpler while still producing four behaviorally distinct "
        "traffic patterns."
    ))

    S.append(P("3.2 RSU Placement", "H2"))
    S.append(P(
        "Roadside Units are placed at fixed coordinates: three along the straight road (start, midpoint, end) "
        "so no point on the road is far from an RSU, and one on each arm of the intersection. Each vehicle is "
        "assigned to its nearest RSU by Euclidean distance at every timestep, so a vehicle traveling the length "
        "of the road or through the intersection is handed off between RSUs exactly as it would be in a real "
        "deployment."
    ))

    S.append(P("3.3 Vehicle State Model", "H2"))
    S.append(P(
        "Each vehicle's state is defined by five fields extracted directly from TraCI at every simulation "
        "step: position (x, y in metres), speed (m/s), heading (degrees, compass convention), and acceleration "
        "(m/s<super>2</super>). These five fields are what every strategy encodes, compresses, or withholds."
    ))

    S.append(P("3.4 The Five Strategies", "H2"))
    strategy_list = [
        ("Raw", "Transmits the complete state, in full precision, every timestep. Serves as the "
                 "uncompressed baseline (~24 bytes per update)."),
        ("Delta encoding", "Transmits the change since the last update instead of absolute values, "
                            "fixed-point encoded at 16 bits per field (~14 bytes per update)."),
        ("Quantization", "Transmits the absolute state every timestep, but with each field reduced to a "
                          "fixed bit-depth (8, 12, 16, or 32 bits), trading precision for size."),
        ("Event-triggered", "Transmits only when the vehicle's actual state deviates from where the RSU "
                             "would predict it to be (assuming constant velocity) by more than a threshold."),
        ("Adaptive", "Combines event-triggering, quantization, and a maximum staleness bound, all tuned "
                      "by whether the vehicle is currently classified as 'stable' or 'maneuvering'."),
    ]
    S.append(ListFlowable(
        [ListItem(P(f"<b>{name}:</b> {desc}"), leftIndent=12) for name, desc in strategy_list],
        bulletType="bullet", start="circle",
    ))

    S.append(P("3.5 RSU-Side Reconstruction", "H2"))
    S.append(P(
        "When a vehicle's update is not received (Event-triggered and Adaptive strategies), the RSU does not "
        "simply freeze the last known position. Instead it extrapolates using a constant-velocity model based "
        "on the vehicle's last reported speed and heading, which is a meaningfully better estimate than holding "
        "position fixed and costs almost no extra computation."
    ))

    # ---- 4. Implementation Workflow ----
    S.append(P("4. Implementation Workflow", "H1"))
    S.append(P("The project was built in the following order:"))
    workflow_steps = [
        "Defined field ranges, quantization bit-depths, event-trigger thresholds, and the adaptive "
        "mode-switching rule in a design specification before writing any code.",
        "Verified the SUMO + TraCI toolchain end-to-end on a minimal network before building the real one.",
        "Built two reusable road networks and generated traffic for all 5 densities (5/10/20/50/100 vehicles) "
        "across all 4 scenarios (20 configurations total), validating that each scenario actually produces "
        "its intended driving behavior (e.g. confirming that only the turning scenario's vehicles change "
        "heading, and that lane-change and accel-decel scenarios show measurably different lane-switching "
        "and acceleration variance than the steady-speed baseline).",
        "Placed RSUs and implemented nearest-RSU assignment.",
        "Implemented all five strategies against the design spec's parameters, with a shared vehicle-state "
        "data structure and RSU-reconstruction logic reused across all of them.",
        "Built an experiment runner that simulates each of the 20 configurations once and feeds the same "
        "vehicle-state stream to all strategy variants in parallel, rather than re-running the simulation "
        "once per strategy.",
        "Computed every metric listed in the project brief from the full result set, and produced the plots and tables discussed in Section 6.",
    ]
    S.append(ListFlowable(
        [ListItem(P(s), leftIndent=12) for s in workflow_steps],
        bulletType="bullet",
    ))

    S.append(P("4.1 Two Issues Found During Testing", "H2"))
    S.append(P(
        "Two design errors were caught by testing against real simulation output rather than trusting the "
        "code by inspection, and both are informative about the problem domain itself:"
    ))
    S.append(P(
        "<b>Coordinate offset.</b> SUMO's <font face='Courier'>netconvert</font> tool shifts a network's "
        "internal coordinates so that none are negative, which does not match the coordinates originally used "
        "to design the network's layout. RSU positions were initially placed using the original design "
        "coordinates directly, which silently misplaced every RSU on the intersection network (the straight "
        "road was unaffected, since its coordinates were already non-negative). The fix reads the actual "
        "coordinate offset from the network file at runtime and applies it, rather than hardcoding "
        "post-shift values that would break again if the network geometry changed."
    ))
    S.append(P(
        "<b>Event-trigger threshold reference point.</b> The Event-triggered strategy initially compared a "
        "vehicle's new position to its last <i>transmitted</i> position. Since a vehicle cruising at a typical "
        "15 m/s covers about 15 metres every second from ordinary motion alone, this comparison exceeded the "
        "1-metre threshold on essentially every timestep regardless of whether the vehicle's behavior had "
        "changed at all &mdash; producing zero communication savings on the steady-speed scenario. The fix "
        "compares the vehicle's actual position against where the RSU would <i>predict</i> it to be (constant-"
        "velocity extrapolation from the last transmitted state), which is both the conceptually correct "
        "comparison and the one that actually reveals unpredictable behaviour."
    ))

    # ---- numbers used in the text below come straight from the CSV files ----
    summ = {r["strategy"]: r for r in read_summary(os.path.join(REPO_ROOT, "analysis", "summary_by_strategy.csv"))}
    bw_rows = read_summary(os.path.join(REPO_ROOT, "analysis", "bandwidth_analysis.csv"))
    budgets = sorted({int(r["budget_bytes_per_sec"]) for r in bw_rows})
    tight = budgets[0]
    bw = {(r["strategy"], int(r["budget_bytes_per_sec"])): r for r in bw_rows}
    most_cars = int(bw_rows[0]["most_cars_seen_on_one_rsu_in_tests"])
    order = ["raw", "quantization_32bit", "delta", "quantization_16bit",
             "quantization_12bit", "event_triggered", "quantization_8bit", "adaptive"]
    ad, ev, rw = summ["adaptive"], summ["event_triggered"], summ["raw"]
    ad_bw, rw_bw = bw[("adaptive", tight)], bw[("raw", tight)]
    cap_gain = float(ad_bw["max_vehicles_per_rsu"]) / float(rw_bw["max_vehicles_per_rsu"])

    # ---- 5. Experimental Setup ----
    S.append(P("5. Experimental Setup", "H1"))
    S.append(P(
        "Each of the 4 scenarios (steady-speed, lane-change, accel-decel, turning) was run at 5 vehicle "
        "densities (5, 10, 20, 50, 100), for 20 configurations total, each simulated for 300 seconds. Every "
        "configuration was run once through SUMO/TraCI, with the resulting vehicle-state stream fed to all "
        "8 strategy variants (Raw, Delta, Quantization at 8/12/16/32 bits, Event-triggered, and Adaptive) in "
        "parallel. For every vehicle at every timestep, the following were logged: whether an update was "
        "transmitted, bytes sent, position error, speed error, heading error, and Age of Information &mdash; "
        "producing a combined dataset of 410,136 rows."
    ))

    S.append(P("5.1 Metrics", "H2"))
    S.append(P(
        "Every metric listed in the project brief is computed from this dataset. One row of the dataset is one "
        "car on the road for one simulated second, so &ldquo;per vehicle&rdquo; always means per car "
        "<i>while it is on the road</i>."
    ))
    metric_defs = [
        ("Total data transmitted", "the sum of the bytes sent by all cars."),
        ("Communication overhead", "total bytes divided by vehicle-seconds (bytes per second per vehicle)."),
        ("Packet transmission rate", "packets sent per vehicle-second (also shown as the share of timesteps with a transmission)."),
        ("Compression ratio", "Raw's total bytes divided by the strategy's total bytes."),
        ("Digital twin position, speed and heading error", "the difference between the RSU's reconstructed "
         "state and SUMO's true state, averaged over all vehicle-seconds."),
        ("Average and peak Age of Information (AoI)", "the seconds since the RSU last received an update from "
         "that car: the average over all vehicle-seconds, and the single worst value."),
        ("V2I channel utilization", "the bytes offered to an RSU in one second divided by that RSU's bandwidth "
         "budget (above 100% means the channel is overloaded)."),
        ("Packet delivery ratio", "the share of packets that fit within the RSU's budget; in an overloaded "
         "second, packets are dropped evenly."),
        ("Maximum supported vehicles", "the number of cars one RSU can serve before its average load reaches "
         "the budget (the budget divided by bytes per second per vehicle)."),
        ("Freshness-accuracy-communication trade-off", "Figure 1 (accuracy against bytes used), together with "
         "the AoI results in Table 2 and Figure 4."),
    ]
    S.append(ListFlowable(
        [ListItem(P(f"<b>{n}:</b> {d}"), leftIndent=12) for n, d in metric_defs], bulletType="bullet"))

    S.append(P("5.2 Bandwidth model", "H2"))
    S.append(P(
        "The brief asks for results under &ldquo;a given bandwidth constraint&rdquo; without fixing a number, "
        "so each RSU is assumed to have a fixed budget of bytes per second reserved for digital twin "
        f"synchronisation. Three budgets are used: {budgets[0]}, {budgets[1]} and {budgets[2]} bytes per second "
        "(2, 4 and 8 kbit/s). These are assumptions sized to this small simulation, not measurements of a real "
        f"V2I link: no more than {most_cars} cars were ever attached to one RSU at the same time, and "
        f"{tight} bytes per second is the only budget tight enough to overload an RSU in our traffic. "
        "Utilization and the packet delivery ratio are computed from the logged traffic. Dropped packets are not "
        "fed back into the twin's error figures, so those figures assume every packet a strategy sends is received."
    ))

    # ---- 6. Results ----
    S.append(P("6. Results", "H1"))
    S.append(P("6.1 Communication cost and compression", "H2"))
    S.append(P(
        f"Table 1 shows what each strategy costs, averaged across all 20 configurations. Adaptive uses "
        f"{num(ad['pct_of_raw_bytes'], 1)}% of Raw's bytes (a compression ratio of {num(ad['compression_ratio'], 1)}:1), "
        f"or {num(ad['overhead_bytes_per_sec_per_vehicle'])} bytes per second per vehicle against Raw's "
        f"{num(rw['overhead_bytes_per_sec_per_vehicle'], 0)}, while sending a packet in only "
        f"{num(100 * float(ad['packets_per_sec_per_vehicle']), 1)}% of timesteps."
    ))
    S.append(Spacer(1, 6))
    S.append(make_table(
        ["Strategy", "Total bytes", "% of raw\nbytes", "Compression\nratio", "Bytes/sec\nper vehicle", "Packets/sec\nper vehicle"],
        [[n, f"{int(float(summ[n]['total_bytes'])):,}", f"{num(summ[n]['pct_of_raw_bytes'], 1)}%",
          f"{num(summ[n]['compression_ratio'])}:1", num(summ[n]["overhead_bytes_per_sec_per_vehicle"]),
          num(summ[n]["packets_per_sec_per_vehicle"], 3)] for n in order],
        [1.6, 1.0, 0.8, 0.95, 1.05, 1.05]))
    S.append(P("Table 1: Communication cost of each strategy (all 20 configurations combined).", "Caption"))

    S.append(fig(os.path.join(REPO_ROOT, "analysis", "plots", "tradeoff.png")))
    S.append(P(
        "Figure 1: Freshness-accuracy-communication trade-off. Adaptive sits furthest to the left "
        "(least data used) while matching or beating Quantization at 8 bits on accuracy, despite using fewer "
        "bytes.", "Caption"
    ))

    S.append(fig(os.path.join(REPO_ROOT, "analysis", "plots", "bytes_by_strategy.png")))
    S.append(P("Figure 2: Total data transmitted by each strategy, relative to Raw.", "Caption"))

    S.append(fig(os.path.join(REPO_ROOT, "analysis", "plots", "overhead_vs_density.png")))
    S.append(P(
        "Figure 3: Communication overhead per vehicle on the road, as density increases. Raw and 32-bit "
        "Quantization overlap exactly (identical byte count per update), as do Delta and 16-bit Quantization "
        "&mdash; this is expected, not an error. The per-vehicle cost stays flat because each vehicle's strategy "
        "runs independently of how many other vehicles are around; what grows with density is the total load "
        "on each RSU (Section 6.3).", "Caption"
    ))

    S.append(P("6.2 Accuracy and freshness", "H2"))
    S.append(P(
        f"Table 2 shows how closely the RSU's digital twin tracks the real vehicles. Strategies that transmit at "
        f"every timestep have zero Age of Information. For the two strategies that skip transmissions, the "
        f"average staleness is {num(ev['avg_aoi'])} s for Event-triggered and {num(ad['avg_aoi'])} s for Adaptive; "
        f"the worst case is far apart: {num(ev['peak_aoi'], 0)} s for Event-triggered against "
        f"{num(ad['peak_aoi'], 0)} s for Adaptive."
    ))
    S.append(Spacer(1, 6))
    S.append(make_table(
        ["Strategy", "Position\nerror (m)", "Speed error\n(m/s)", "Heading\nerror (deg)", "Average\nAoI (s)", "Peak\nAoI (s)"],
        [[n, num(summ[n]["avg_position_error"], 3), num(summ[n]["avg_speed_error"], 3),
          num(summ[n]["avg_heading_error"], 3), num(summ[n]["avg_aoi"]), num(summ[n]["peak_aoi"], 0)]
         for n in order],
        [1.6, 1.0, 1.0, 1.0, 0.9, 0.9]))
    S.append(P("Table 2: Digital twin accuracy and Age of Information (AoI) for each strategy.", "Caption"))

    S.append(fig(os.path.join(REPO_ROOT, "analysis", "plots", "aoi_vs_density.png")))
    S.append(P(
        "Figure 4: Age of Information under increasing traffic density, average (left) and worst case (right). "
        "Adaptive keeps staleness low and flat; plain Event-triggered is higher and, in the worst case, can go "
        "tens of seconds without an update from a vehicle.", "Caption"
    ))

    S.append(P("6.3 Channel utilization, packet delivery and supported vehicles", "H2"))
    S.append(P(
        f"Table 3 applies the bandwidth model of Section 5.2. At the tightest budget ({tight} bytes per second per "
        f"RSU), Raw's busiest moment fills the channel to {num(rw_bw['peak_utilization_pct'], 0)}% and "
        f"{num(rw_bw['overloaded_pct_of_rsu_seconds'], 1)}% of RSU-seconds are overloaded, so only "
        f"{num(rw_bw['packet_delivery_ratio_pct'], 1)}% of its packets get through. Adaptive peaks at "
        f"{num(ad_bw['peak_utilization_pct'], 0)}%, is never overloaded and delivers "
        f"{num(ad_bw['packet_delivery_ratio_pct'], 1)}% of its packets. Under the same budget one RSU can support "
        f"{ad_bw['max_vehicles_per_rsu']} vehicles with Adaptive against {rw_bw['max_vehicles_per_rsu']} with Raw "
        f"({num(cap_gain, 1)} times as many)."
    ))
    S.append(Spacer(1, 6))
    S.append(make_table(
        ["Strategy", f"Avg util.\n@{budgets[0]} B/s", f"Peak util.\n@{budgets[0]} B/s",
         f"Overloaded\n@{budgets[0]} B/s", f"Packets\ndelivered\n@{budgets[0]} B/s",
         f"Max veh.\n@{budgets[0]}", f"Max veh.\n@{budgets[1]}", f"Max veh.\n@{budgets[2]}"],
        [[n, f"{num(bw[(n, tight)]['mean_utilization_pct'], 1)}%", f"{num(bw[(n, tight)]['peak_utilization_pct'], 0)}%",
          f"{num(bw[(n, tight)]['overloaded_pct_of_rsu_seconds'], 1)}%",
          f"{num(bw[(n, tight)]['packet_delivery_ratio_pct'], 1)}%"] +
         [bw[(n, b)]["max_vehicles_per_rsu"] for b in budgets] for n in order],
        [1.45, 0.7, 0.7, 0.8, 0.8, 0.65, 0.65, 0.65], font_size=8))
    S.append(P(
        f"Table 3: Bandwidth analysis. Utilization, overload and delivery are shown for the {tight} B/s budget; "
        "the last three columns give the maximum vehicles one RSU can support at each budget (B/s = bytes per second).",
        "Caption"))

    S.append(fig(os.path.join(REPO_ROOT, "analysis", "plots", "channel_utilization.png")))
    S.append(P(
        f"Figure 5: How full an RSU's channel gets at a budget of {tight} bytes per second. Bars past the dashed "
        "line mean the channel is overloaded and packets are dropped.", "Caption"
    ))

    S.append(fig(os.path.join(REPO_ROOT, "analysis", "plots", "max_vehicles.png")))
    S.append(P("Figure 6: Maximum number of vehicles one RSU can support under each bandwidth budget.", "Caption"))

    # ---- 7. Discussion ----
    S.append(P("7. Discussion", "H1"))
    S.append(P(
        "The central finding is that Adaptive achieves the best overall result not by skipping more "
        "transmissions than plain Event-triggered (its transmission rate is actually similar), but by sending "
        "a smaller, quantized packet on the occasions when it does transmit. This confirms that the two "
        "compression mechanisms &mdash; deciding <i>whether</i> to send and deciding <i>how much</i> to send "
        "&mdash; are complementary rather than redundant, and that combining them outperforms either technique "
        "used alone."
    ))
    S.append(P(
        f"Freshness is where the two event-based strategies differ most. A car that behaves exactly as the RSU "
        f"predicts never triggers an update, so plain Event-triggered can leave the RSU without news of a car for "
        f"up to {num(ev['peak_aoi'], 0)} seconds. Adaptive adds a maximum-staleness rule, which holds its worst case "
        f"to {num(ad['peak_aoi'], 0)} second at a cost of only a few extra packets."
    ))
    S.append(P(
        f"Quantization alone shows a clear, expected trade-off: 8-bit quantization uses "
        f"{num(summ['quantization_8bit']['pct_of_raw_bytes'], 1)}% of Raw's bytes but has an average position error of "
        f"{num(summ['quantization_8bit']['avg_position_error'])} m, while 16-bit and 32-bit quantization are "
        "effectively lossless at correspondingly higher byte cost. The choice of bit-depth is a direct, tunable "
        "trade-off between communication cost and accuracy."
    ))
    S.append(P(
        f"The bandwidth analysis turns these byte savings into capacity. Because every car decides independently, the "
        f"per-vehicle cost does not change with density (Figure 3), so the load on an RSU grows with the number of "
        f"cars attached to it. Under a tight budget this separates the strategies: Raw overloads the channel and "
        f"loses packets, while Adaptive stays below the limit and supports about {num(cap_gain, 1)} times as many "
        f"vehicles per RSU."
    ))

    # ---- 8. Limitations and Future Work ----
    S.append(P("8. Limitations and Future Work", "H1"))
    limitations = [
        f"The bandwidth budgets ({budgets[0]}, {budgets[1]} and {budgets[2]} bytes per second per RSU) are "
        "assumptions chosen to suit this small simulation, not measurements of a real V2I link. The utilization "
        "and packet delivery results depend on them.",
        "Packet delivery is analysed on top of the logged traffic: dropped packets are not fed back into the "
        "twin, so the position, speed, heading and AoI figures assume every packet a strategy sends is received. "
        "A full channel simulation, with loss changing what each strategy does next, would be a natural extension.",
        f"Maximum supported vehicles is calculated from the average per-vehicle rate. The busiest RSU in our tests "
        f"held {most_cars} cars at once, so any value above {most_cars} is an extrapolation rather than something "
        "the simulation directly tested.",
        "Quantization field ranges (speed, heading, acceleration, position relative to RSU) are fixed "
        "design assumptions; a deployment would need to calibrate these to its actual road and speed limits.",
        "The Adaptive strategy's mode-switching thresholds (acceleration and heading-change cutoffs) were "
        "chosen from the design specification and not separately tuned per scenario; a sensitivity analysis "
        "over these thresholds would be a natural extension.",
        "Only one random seed was used per configuration, and the simulation is small (at most 100 vehicles on "
        "two small road layouts); averaging over multiple seeds and larger networks would give more robust "
        "estimates of each strategy's performance.",
    ]
    S.append(ListFlowable([ListItem(P(s_), leftIndent=12) for s_ in limitations], bulletType="bullet"))

    # ---- 9. Conclusion ----
    S.append(P("9. Conclusion", "H1"))
    S.append(P(
        f"Adaptive state compression, combining event-triggered transmission with mode-dependent quantization, "
        f"reduced V2I communication overhead to {num(ad['pct_of_raw_bytes'], 1)}% of the uncompressed baseline "
        f"(a {num(ad['compression_ratio'], 1)}:1 compression ratio) while keeping average Digital Twin position "
        f"error near {num(ad['avg_position_error'], 1)} metres and worst-case staleness to {num(ad['peak_aoi'], 0)} "
        f"second. Under a tight bandwidth budget it also let one RSU support about {num(cap_gain, 1)} times as many "
        "vehicles as sending everything. This supports the hypothesis that recognizing when a vehicle's behavior "
        "is predictable, and compressing accordingly, is more effective than applying uniform compression "
        "regardless of driving context."
    ))

    doc.build(S)
    print("Wrote report.pdf")


if __name__ == "__main__":
    build()
