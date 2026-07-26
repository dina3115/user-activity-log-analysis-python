"""Analyse application activity logs and generate portfolio-ready outputs."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "app_logs.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
IMAGE_DIR = PROJECT_ROOT / "images"

ACTION_CATEGORIES = {
    "login": "Access",
    "logout": "Access",
    "view_page": "Navigation",
    "view_dashboard": "Navigation",
    "view_profile": "Navigation",
    "create_post": "Content",
}


def load_and_prepare_data(path: Path) -> pd.DataFrame:
    """Load the activity log, validate it and create analysis fields."""
    logs = pd.read_csv(path, parse_dates=["log_time"])

    required_columns = {
        "log_id",
        "log_time",
        "user_id",
        "action",
        "duration_seconds",
        "source",
    }
    missing_columns = required_columns.difference(logs.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    logs = logs.drop_duplicates().copy()
    logs["action_type"] = logs["action"].map(ACTION_CATEGORIES)
    logs["hour"] = logs["log_time"].dt.hour
    logs["day_name"] = logs["log_time"].dt.day_name()
    logs["date"] = logs["log_time"].dt.date

    if logs["action_type"].isna().any():
        unknown = sorted(logs.loc[logs["action_type"].isna(), "action"].unique())
        raise ValueError(f"Unmapped actions found: {unknown}")

    return logs


def create_summaries(logs: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Create reusable summary tables for the analysis."""
    action_summary = (
        logs.groupby(["action_type", "action"], as_index=False)
        .agg(
            events=("log_id", "count"),
            total_duration_seconds=("duration_seconds", "sum"),
            average_duration_seconds=("duration_seconds", "mean"),
        )
        .sort_values(["events", "total_duration_seconds"], ascending=False)
    )

    source_summary = (
        logs.groupby("source", as_index=False)
        .agg(
            events=("log_id", "count"),
            total_duration_seconds=("duration_seconds", "sum"),
            average_duration_seconds=("duration_seconds", "mean"),
        )
        .sort_values("events", ascending=False)
    )

    hourly_summary = (
        logs.groupby("hour", as_index=False)
        .agg(
            events=("log_id", "count"),
            total_duration_seconds=("duration_seconds", "sum"),
            average_duration_seconds=("duration_seconds", "mean"),
        )
        .sort_values("hour")
    )

    user_summary = (
        logs.groupby("user_id", as_index=False)
        .agg(
            events=("log_id", "count"),
            total_duration_seconds=("duration_seconds", "sum"),
            average_duration_seconds=("duration_seconds", "mean"),
        )
        .sort_values("events", ascending=False)
    )

    return {
        "action_summary": action_summary,
        "source_summary": source_summary,
        "hourly_summary": hourly_summary,
        "user_summary": user_summary,
    }


def save_outputs(summaries: dict[str, pd.DataFrame]) -> None:
    """Save the summary tables as CSV files."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, table in summaries.items():
        table.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)


def create_dashboard(logs: pd.DataFrame, summaries: dict[str, pd.DataFrame]) -> None:
    """Create a concise visual summary of the activity data."""
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    fig.suptitle("Application User Activity Overview", fontsize=16, fontweight="bold")

    action_counts = logs["action"].value_counts().sort_values()
    action_counts.plot(kind="barh", ax=axes[0], color="#2A495E")
    axes[0].set_title("Events by Action")
    axes[0].set_xlabel("Number of events")
    axes[0].set_ylabel("")

    hourly = summaries["hourly_summary"]
    axes[1].plot(
        hourly["hour"],
        hourly["events"],
        marker="o",
        linewidth=2.2,
        color="#D17A22",
    )
    axes[1].set_title("Activity by Hour")
    axes[1].set_xlabel("Hour of day")
    axes[1].set_ylabel("Number of events")
    axes[1].set_xticks(hourly["hour"])

    source = summaries["source_summary"].set_index("source")
    source["events"].plot(
        kind="bar",
        ax=axes[2],
        color=["#4F81BD", "#70AD47"],
        rot=0,
    )
    axes[2].set_title("Events by Source")
    axes[2].set_xlabel("")
    axes[2].set_ylabel("Number of events")

    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(IMAGE_DIR / "user_activity_dashboard.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def print_key_findings(logs: pd.DataFrame, summaries: dict[str, pd.DataFrame]) -> None:
    """Print the headline metrics and findings."""
    hourly = summaries["hourly_summary"]
    peak_hour = hourly.loc[hourly["events"].idxmax()]
    action_duration = (
        logs.groupby("action", as_index=False)["duration_seconds"]
        .sum()
        .sort_values("duration_seconds", ascending=False)
        .iloc[0]
    )

    print("APPLICATION ACTIVITY SUMMARY")
    print(f"Observation period: {logs['log_time'].min()} to {logs['log_time'].max()}")
    print(f"Total events: {len(logs)}")
    print(f"Unique users: {logs['user_id'].nunique()}")
    print(f"Total recorded duration: {logs['duration_seconds'].sum()} seconds")
    print(f"Peak activity hour: {int(peak_hour['hour']):02d}:00")
    print(
        "Highest-duration action: "
        f"{action_duration['action']} "
        f"({int(action_duration['duration_seconds'])} seconds)"
    )


def main() -> None:
    logs = load_and_prepare_data(DATA_PATH)
    summaries = create_summaries(logs)
    save_outputs(summaries)
    create_dashboard(logs, summaries)
    print_key_findings(logs, summaries)


if __name__ == "__main__":
    main()
