"""
Plotly chart builders for the GEM Media Optimiser.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Colour palette
COLOUR_MAP = {
    "essential": "#e74c3c",
    "enhancing": "#f39c12",
    "dispensable": "#2ecc71",
}


def essentiality_chart(df: pd.DataFrame) -> go.Figure:
    """
    Horizontal bar chart showing growth ratio for each nutrient,
    coloured by essentiality classification.
    """
    if df.empty:
        return _empty_fig("No essentiality data available.")

    df_plot = df.copy()
    df_plot["colour"] = df_plot["classification"].map(COLOUR_MAP)
    df_plot = df_plot.sort_values("growth_ratio", ascending=True)

    fig = px.bar(
        df_plot,
        x="growth_ratio",
        y="metabolite_name",
        color="classification",
        color_discrete_map=COLOUR_MAP,
        orientation="h",
        labels={
            "growth_ratio": "Growth ratio (without nutrient / baseline)",
            "metabolite_name": "Nutrient",
            "classification": "Classification",
        },
        title="Nutrient Essentiality Screen",
        hover_data=["reaction_id", "uptake_rate"],
    )
    fig.update_layout(
        xaxis_range=[0, 1.05],
        yaxis_title="",
        legend_title="Classification",
        height=max(350, len(df_plot) * 22),
        margin=dict(l=10, r=20, t=50, b=40),
    )
    fig.add_vline(x=0.90, line_dash="dash", line_color="gray",
                  annotation_text="90% threshold", annotation_position="top right")
    fig.add_vline(x=0.01, line_dash="dot", line_color="darkgray",
                  annotation_text="1% threshold", annotation_position="bottom right")
    return fig


def shadow_price_chart(df: pd.DataFrame, top_n: int = 20) -> go.Figure:
    """
    Horizontal bar chart of absolute shadow prices (nutrient sensitivity).
    """
    if df.empty:
        return _empty_fig("No shadow price data available.")

    df_plot = df.head(top_n).copy()
    df_plot = df_plot.sort_values("abs_shadow_price", ascending=True)

    fig = px.bar(
        df_plot,
        x="abs_shadow_price",
        y="metabolite_name",
        orientation="h",
        color="abs_shadow_price",
        color_continuous_scale="Blues",
        labels={
            "abs_shadow_price": "|Shadow Price| (growth sensitivity)",
            "metabolite_name": "Metabolite",
        },
        title=f"Nutrient Sensitivity (Top {min(top_n, len(df_plot))} by Shadow Price)",
        hover_data=["reaction_id", "shadow_price"],
    )
    fig.update_layout(
        coloraxis_showscale=False,
        yaxis_title="",
        height=max(350, len(df_plot) * 22),
        margin=dict(l=10, r=20, t=50, b=40),
    )
    return fig


def growth_waterfall_chart(df: pd.DataFrame, baseline: float) -> go.Figure:
    """
    Waterfall chart showing cumulative growth as nutrients are added.
    """
    if df.empty:
        return _empty_fig("No waterfall data available.")

    measures = []
    values = []
    prev = 0.0
    for _, row in df.iterrows():
        delta = row["cumulative_growth"] - prev
        measures.append("relative")
        values.append(round(delta, 4))
        prev = row["cumulative_growth"]

    fig = go.Figure(go.Waterfall(
        name="Growth rate",
        orientation="v",
        measure=measures,
        x=df["nutrient"].tolist(),
        y=values,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#2ecc71"}},
        decreasing={"marker": {"color": "#e74c3c"}},
        totals={"marker": {"color": "#3498db"}},
    ))
    fig.add_hline(y=baseline, line_dash="dash", line_color="gray",
                  annotation_text="Baseline", annotation_position="right")
    fig.update_layout(
        title="Growth Rate Build-Up by Nutrient",
        xaxis_title="Nutrient added",
        yaxis_title="Growth rate contribution (h⁻¹)",
        height=400,
        margin=dict(l=10, r=20, t=50, b=80),
        xaxis_tickangle=-45,
    )
    return fig


def fva_range_chart(
    fva_df: pd.DataFrame,
    key_reaction_ids: list[str] | None = None,
) -> go.Figure:
    """
    Horizontal range bar chart (min/max) for exchange reaction fluxes from FVA.
    Shows feasible uptake ranges at 95% optimal growth.
    """
    if fva_df.empty:
        return _empty_fig("No FVA data available.")

    df = fva_df.copy()
    if key_reaction_ids:
        df = df[df["reaction_id"].isin(key_reaction_ids)]

    if df.empty:
        return _empty_fig("No FVA data for selected nutrients.")

    fig = go.Figure()
    for _, row in df.iterrows():
        name = row.get("metabolite_name", row["reaction_id"])
        fig.add_trace(go.Scatter(
            x=[row["minimum"], row["maximum"]],
            y=[name, name],
            mode="lines+markers",
            line=dict(color="#3498db", width=3),
            marker=dict(size=8),
            name=name,
            showlegend=False,
            hovertemplate=f"{name}<br>Min: {row['minimum']:.3f}<br>Max: {row['maximum']:.3f}<extra></extra>",
        ))

    fig.update_layout(
        title="Feasible Flux Ranges (FVA @ 95% optimal growth)",
        xaxis_title="Flux (mmol / gDW / h)",
        yaxis_title="",
        height=max(350, len(df) * 25),
        margin=dict(l=10, r=20, t=50, b=40),
    )
    return fig


def doe_parallel_coordinates(doe_df: pd.DataFrame) -> go.Figure:
    """
    Parallel coordinates plot of the DoE matrix to show experimental space coverage.
    """
    if doe_df.empty:
        return _empty_fig("No DoE matrix available.")

    dims = [
        dict(label=col, values=doe_df[col])
        for col in doe_df.columns
    ]
    fig = go.Figure(go.Parcoords(
        line=dict(
            color=list(range(len(doe_df))),
            colorscale="Viridis",
        ),
        dimensions=dims,
    ))
    fig.update_layout(
        title="DoE Matrix — Parallel Coordinates View",
        height=450,
        margin=dict(l=80, r=80, t=60, b=40),
    )
    return fig


def _empty_fig(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=14, color="gray"),
    )
    fig.update_layout(
        xaxis_visible=False,
        yaxis_visible=False,
        height=300,
    )
    return fig
