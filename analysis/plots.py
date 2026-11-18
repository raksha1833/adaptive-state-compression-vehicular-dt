"""
Phase 7: turns results/all_results.csv into every metric the project brief asks
for, plus the comparison plots.

Run from the repo root:
    python analysis/plots.py

Writes (in analysis/):
    summary_by_strategy.csv   one row per strategy: bytes, compression ratio, bytes/sec/vehicle,
                              packet rate, position/speed/heading error, average + peak Age of Information
    bandwidth_analysis.csv    one row per (strategy, bandwidth budget): channel utilization,
                              packet delivery ratio, maximum supported vehicles per RSU
Plots (in analysis/plots/):
    bytes_by_strategy.png     total data used, all strategies
    tradeoff.png              THE headline plot: accuracy vs. bytes used
    overhead_vs_density.png   per-vehicle communication cost vs. traffic density
    aoi_vs_density.png        average and peak Age of Information vs. density
    channel_utilization.png   how full an RSU's channel gets (tightest budget)
    max_vehicles.png          how many vehicles one RSU can support, per budget

How each metric is defined
  * One row of the results = one car on the road for one simulated second
    (SUMO's step is 1 s), so "per vehicle" always means per car *while it is on the road*.
  * Compression ratio    = Raw's total bytes / this strategy's total bytes.
  * Overhead             = total bytes / vehicle-seconds.   Packet rate = packets sent / vehicle-seconds.
  * Channel model (bandwidth analysis): every RSU gets a fixed budget of B bytes per second for
    twin-sync traffic. In each second, the bytes sent by all cars attached to that RSU are its offered load.
      - Utilization               = offered load / B   (above 100% = overloaded)
      - Packet delivery ratio     = packets that fit in the budget / packets sent
                                    (when overloaded, packets are dropped evenly)
      - Max supported vehicles    = floor(B / bytes-per-second-per-vehicle), i.e. how many cars one
                                    RSU can serve before its average load reaches the budget
    The budgets are ASSUMPTIONS (edit BANDWIDTH_BUDGETS below). Dropped packets are not fed back into
    the twin's error figures -- the delivery ratio is an analysis layered on the logged traffic.
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_CSV = os.path.join(os.path.dirname(HERE), "results", "all_results.csv")
OUT_DIR = os.path.join(HERE, "plots")

# Bytes per second each RSU can spend on digital-twin sync (assumed budgets; edit freely).
BANDWIDTH_BUDGETS = [250, 500, 1000]
TIGHT_BUDGET = BANDWIDTH_BUDGETS[0]  # the only one tight enough to overload an RSU in our traffic

STRATEGY_ORDER = [
    "raw", "quantization_32bit", "delta", "quantization_16bit",
    "quantization_12bit", "event_triggered", "quantization_8bit", "adaptive",
]


def load_and_summarize(df):
    g = df.groupby("strategy")
    vehicle_seconds = g.size()  # one row = one car on the road for one second
    summary = pd.DataFrame({
        "total_bytes": g.bytes_sent.sum(),
        "overhead_bytes_per_sec_per_vehicle": g.bytes_sent.sum() / vehicle_seconds,
        "packets_per_sec_per_vehicle": g.transmitted.sum() / vehicle_seconds,
        "pct_transmitted": (100 * g.transmitted.mean()).round(1),
        "avg_position_error": g.position_error.mean(),
        "avg_speed_error": g.speed_error.mean(),
        "avg_heading_error": g.heading_error.mean(),
        "avg_aoi": g.age_of_information.mean(),
        "peak_aoi": g.age_of_information.max(),
    }).reindex(STRATEGY_ORDER)

    raw_bytes = summary.loc["raw", "total_bytes"]
    summary["pct_of_raw_bytes"] = (100 * summary["total_bytes"] / raw_bytes).round(1)
    summary["compression_ratio"] = raw_bytes / summary["total_bytes"]
    return summary


def bandwidth_analysis(df, summary):
    # Offered load on each RSU in each simulated second (only seconds when >= 1 car is attached).
    load = (df.groupby(["scenario", "density", "strategy", "rsu_id", "t"])
              .agg(bytes=("bytes_sent", "sum"), packets=("transmitted", "sum"))
              .reset_index())

    # Most cars ever attached to one RSU at once in these tests (same for every strategy).
    raw = df[df.strategy == "raw"]
    peak_cars = int(raw.groupby(["scenario", "density", "rsu_id", "t"]).vehicle_id.nunique().max())

    rows = []
    for budget in BANDWIDTH_BUDGETS:
        load["delivered"] = load["packets"] * np.minimum(1.0, budget / load["bytes"].clip(lower=1))
        for strategy, d in load.groupby("strategy"):
            per_vehicle_rate = summary.loc[strategy, "overhead_bytes_per_sec_per_vehicle"]
            rows.append({
                "budget_bytes_per_sec": budget,
                "strategy": strategy,
                "mean_utilization_pct": 100 * d["bytes"].mean() / budget,
                "peak_utilization_pct": 100 * d["bytes"].max() / budget,
                "overloaded_pct_of_rsu_seconds": 100 * (d["bytes"] > budget).mean(),
                "packet_delivery_ratio_pct": 100 * d["delivered"].sum() / d["packets"].sum(),
                "max_vehicles_per_rsu": int(np.floor(budget / per_vehicle_rate)),
                "most_cars_seen_on_one_rsu_in_tests": peak_cars,
            })
    out = pd.DataFrame(rows)
    out["strategy"] = pd.Categorical(out["strategy"], STRATEGY_ORDER, ordered=True)
    return out.sort_values(["budget_bytes_per_sec", "strategy"]).reset_index(drop=True)


def plot_bytes_by_strategy(summary):
    fig, ax = plt.subplots(figsize=(8, 5))
    order = summary["pct_of_raw_bytes"].sort_values().index
    ax.barh(order, summary.loc[order, "pct_of_raw_bytes"], color="#378ADD")
    ax.set_xlabel("% of raw-strategy bytes used")
    ax.set_title("Total data transmitted, relative to sending everything (Raw)")
    ax.invert_yaxis()
    for i, v in enumerate(summary.loc[order, "pct_of_raw_bytes"]):
        ax.text(v + 1, i, f"{v}%", va="center")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "bytes_by_strategy.png"), dpi=150)
    plt.close(fig)


def plot_tradeoff(summary):
    fig, ax = plt.subplots(figsize=(7.5, 6))
    ax.scatter(summary["pct_of_raw_bytes"], summary["avg_position_error"], s=80, color="#D85A30", zorder=3)

    # Cluster points that are visually indistinguishable (raw/32-bit quantization
    # are both ~lossless at full size; delta/16-bit quantization are both
    # ~lossless at the same byte count) so their labels don't overlap.
    X_TOL, Y_TOL = 3, 0.02
    clusters = []
    for name, row in summary.iterrows():
        x, y = row["pct_of_raw_bytes"], row["avg_position_error"]
        for c in clusters:
            if abs(c["x"] - x) <= X_TOL and abs(c["y"] - y) <= Y_TOL:
                c["names"].append(name)
                break
        else:
            clusters.append({"names": [name], "x": x, "y": y})

    manual_offsets = {
        "adaptive": (8, 6),
        "quantization_8bit": (8, 6),
        "event_triggered": (8, 8),
        "quantization_12bit": (-10, 16),
        "raw": (8, -4),
    }
    default_cycle = [(8, -14), (8, 10)]
    for i, c in enumerate(clusters):
        label = " / ".join(c["names"])
        dx, dy = manual_offsets.get(c["names"][0], default_cycle[i % len(default_cycle)])
        ax.annotate(label, (c["x"], c["y"]), textcoords="offset points", xytext=(dx, dy), fontsize=9)

    ax.set_xlabel("% of raw bytes used  (lower = less communication)")
    ax.set_ylabel("Average digital twin position error, m  (lower = more accurate)")
    ax.set_title("Freshness-accuracy-communication trade-off")
    ax.set_xlim(15, 118)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "tradeoff.png"), dpi=150)
    plt.close(fig)


def plot_overhead_vs_density(df):
    # Bytes per second per car *while it is on the road*: total bytes / vehicle-seconds,
    # pooled over the four scenarios at each density.
    pooled = df.groupby(["strategy", "density"]).agg(
        bytes=("bytes_sent", "sum"), vehicle_seconds=("bytes_sent", "size")).reset_index()
    pooled["overhead"] = pooled["bytes"] / pooled["vehicle_seconds"]

    # raw & 32-bit quantization use the same byte count per update, as do delta
    # & 16-bit quantization -- their lines land exactly on top of each other.
    # Dashing one of each pair keeps both visible instead of one hiding the other.
    linestyles = {"quantization_32bit": "--", "quantization_16bit": "--"}

    fig, ax = plt.subplots(figsize=(8, 5))
    for strategy in STRATEGY_ORDER:
        sub = pooled[pooled.strategy == strategy].sort_values("density")
        ax.plot(sub["density"], sub["overhead"], marker="o",
                linestyle=linestyles.get(strategy, "-"), label=strategy)
    ax.set_xlabel("Vehicle density")
    ax.set_ylabel("Communication overhead (bytes/sec per vehicle on the road)")
    ax.set_title("Per-vehicle communication cost as traffic density increases")
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.02, 1))
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "overhead_vs_density.png"), dpi=150)
    plt.close(fig)


def plot_aoi_vs_density(df):
    sub = df[df.strategy.isin(["event_triggered", "adaptive"])]
    stats = sub.groupby(["strategy", "density"])["age_of_information"].agg(["mean", "max"]).reset_index()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.6))
    for strategy in ["event_triggered", "adaptive"]:
        s = stats[stats.strategy == strategy].sort_values("density")
        ax1.plot(s["density"], s["mean"], marker="o", label=strategy)
        ax2.plot(s["density"], s["max"], marker="o", label=strategy)
    ax1.set_ylabel("Average Age of Information (s)")
    ax1.set_title("Average staleness")
    ax2.set_ylabel("Peak Age of Information (s)")
    ax2.set_title("Worst-case staleness")
    for ax in (ax1, ax2):
        ax.set_xlabel("Vehicle density")
        ax.set_ylim(bottom=0)
        ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "aoi_vs_density.png"), dpi=150)
    plt.close(fig)


def plot_channel_utilization(bw):
    d = bw[bw.budget_bytes_per_sec == TIGHT_BUDGET].set_index("strategy").loc[STRATEGY_ORDER]
    y = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(9, 5.8))
    ax.barh(y - 0.2, d["mean_utilization_pct"], height=0.38, color="#378ADD", label="average")
    ax.barh(y + 0.2, d["peak_utilization_pct"], height=0.38, color="#D85A30", label="busiest moment")
    ax.axvline(100, color="black", linestyle="--", linewidth=1, label="channel full (100%)")
    ax.set_yticks(y)
    ax.set_yticklabels(d.index)
    ax.invert_yaxis()
    # one tidy column of labels to the right of the longest bar
    for i, (p, pdr) in enumerate(zip(d["peak_utilization_pct"], d["packet_delivery_ratio_pct"])):
        ax.text(222, i + 0.2, f"peak {p:.0f}%  |  delivered {pdr:.1f}%", va="center", fontsize=8)
    ax.set_xlim(0, 340)
    ax.set_xlabel(f"RSU channel utilization, %  (budget assumed: {TIGHT_BUDGET} bytes/sec per RSU)")
    ax.set_title("How full does an RSU's channel get?")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3, fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "channel_utilization.png"), dpi=150)
    plt.close(fig)


def plot_max_vehicles(bw):
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(STRATEGY_ORDER))
    width = 0.26
    colors = ["#B5D4F4", "#378ADD", "#0C447C"]
    for k, budget in enumerate(BANDWIDTH_BUDGETS):
        d = bw[bw.budget_bytes_per_sec == budget].set_index("strategy").loc[STRATEGY_ORDER]
        bars = ax.bar(x + (k - 1) * width, d["max_vehicles_per_rsu"], width,
                      color=colors[k % len(colors)], label=f"{budget} bytes/sec per RSU")
        for rect, v in zip(bars, d["max_vehicles_per_rsu"]):
            ax.text(rect.get_x() + rect.get_width() / 2, v + 2, str(v), ha="center", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(STRATEGY_ORDER, rotation=30, ha="right")
    ax.set_ylabel("Vehicles one RSU can support")
    ax.set_title("Maximum supported vehicles under a bandwidth budget")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "max_vehicles.png"), dpi=150)
    plt.close(fig)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    df = pd.read_csv(RESULTS_CSV)

    summary = load_and_summarize(df)
    cols = ["total_bytes", "pct_of_raw_bytes", "compression_ratio", "overhead_bytes_per_sec_per_vehicle",
            "packets_per_sec_per_vehicle", "pct_transmitted", "avg_position_error", "avg_speed_error",
            "avg_heading_error", "avg_aoi", "peak_aoi"]
    summary = summary[cols]
    summary.to_csv(os.path.join(HERE, "summary_by_strategy.csv"))

    bw = bandwidth_analysis(df, summary)
    bw.to_csv(os.path.join(HERE, "bandwidth_analysis.csv"), index=False)

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    print("=== Summary by strategy ===")
    print(summary.round(3).to_string())
    print(f"\n=== Bandwidth analysis at {TIGHT_BUDGET} bytes/sec per RSU (assumed budget) ===")
    print(bw[bw.budget_bytes_per_sec == TIGHT_BUDGET].drop(columns=["budget_bytes_per_sec"]).round(1).to_string(index=False))

    plot_bytes_by_strategy(summary)
    plot_tradeoff(summary)
    plot_overhead_vs_density(df)
    plot_aoi_vs_density(df)
    plot_channel_utilization(bw)
    plot_max_vehicles(bw)

    print(f"\nPlots written to {OUT_DIR}")
    print(f"Tables written to {HERE} (summary_by_strategy.csv, bandwidth_analysis.csv)")


if __name__ == "__main__":
    main()
