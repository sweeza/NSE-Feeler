"""
Nifty 500 Market Breadth & Sector Rotation Dashboard.
Interactive Dash application implementing 5 comprehensive tabs:
1. Executive Regime Cockpit
2. Advance-Decline & McClellan Momentum
3. DMA Participation & High-Low Extremes
4. Volume Conviction & Breadth Thrusts
5. Sector Rotation & Participation (Sector Indices & Quadrant Scatter Plot)
"""

import dash
import pandas as pd
import plotly.graph_objs as go
from dash import dash_table, dcc, html
from dash.dependencies import Input, Output
from plotly.subplots import make_subplots

from market_breadth import MarketBreadthEngine
from market_breadth.sectors import (
    OFFICIAL_SECTORS,
    compute_all_sectors_summary,
    compute_sector_timeseries,
)

# Initialize Dash App
app = dash.Dash(__name__, title="Nifty 500 Market Breadth Engine", suppress_callback_exceptions=True)
server = app.server

# Load Engine Data (Nifty 500)
print("Initializing Market Breadth Engine for Nifty 500 dashboard...")
engine = MarketBreadthEngine(universe="nifty500")
try:
    engine.load_data(start="2023-01-01", adjusted=True)
    breadth_df = engine.compute_breadth_report()
except Exception as e:  # noqa: BLE001
    print(f"Warning: Could not load live/cached nseuniverse data: {e}. Generating fallback synthetic data.")
    dates = pd.date_range("2023-01-01", periods=250, freq="B")
    breadth_df = pd.DataFrame(index=dates)
    breadth_df["advancers"] = 250
    breadth_df["decliners"] = 200
    breadth_df["net_advances"] = 50
    breadth_df["ad_line"] = breadth_df["net_advances"].cumsum()
    breadth_df["ad_ratio"] = 0.1
    breadth_df["cumulative_ad_ratio"] = breadth_df["ad_ratio"].cumsum()
    breadth_df["mcclellan_oscillator"] = 45.0
    breadth_df["mcclellan_summation"] = 1200.0
    breadth_df["mcclellan_oscillator_ratio"] = 0.05
    breadth_df["mcclellan_summation_ratio"] = 1.2
    breadth_df["pct_above_sma_20"] = 65.0
    breadth_df["pct_above_sma_50"] = 58.0
    breadth_df["pct_above_sma_200"] = 52.0
    breadth_df["new_highs"] = 15
    breadth_df["new_lows"] = 5
    breadth_df["net_new_highs"] = 10
    breadth_df["high_low_logic_index"] = 0.02
    breadth_df["hindenburg_omen"] = 0
    breadth_df["up_down_volume_ratio"] = 1.25
    breadth_df["trin"] = 0.85
    breadth_df["up_volume_9_1"] = 0
    breadth_df["down_volume_9_1"] = 0
    breadth_df["zweig_thrust_ema10"] = 0.55
    breadth_df["zweig_thrust_signal"] = 0
    breadth_df["whaley_issues_thrust"] = 0
    breadth_df["equal_weighted_close"] = 100.0 * (1 + 0.0005).cumprod()
    breadth_df["cap_weighted_close"] = 100.0 * (1 + 0.0004).cumprod()
    breadth_df["eq_cap_ratio"] = breadth_df["equal_weighted_close"] / breadth_df["cap_weighted_close"]
    breadth_df["eq_cap_roc20_spread"] = 1.5

# App Layout styling
app.layout = html.Div(
    style={"backgroundColor": "#0f172a", "color": "#f8fafc", "fontFamily": "Inter, sans-serif", "minHeight": "100vh", "padding": "20px"},
    children=[
        html.Div(
            style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "20px", "borderBottom": "1px solid #334155", "paddingBottom": "15px"},
            children=[
                html.H1("Nifty 500 Market Breadth & Sector Rotation Engine", style={"fontSize": "24px", "fontWeight": "bold", "color": "#38bdf8", "margin": "0"}),
                html.Div(
                    style={"fontSize": "14px", "color": "#94a3b8"},
                    children=[f"Universe: Nifty 500 | Latest Date: {breadth_df.index[-1].strftime('%Y-%m-%d') if len(breadth_df) > 0 else 'N/A'}"]
                )
            ]
        ),
        dcc.Tabs(
            id="dashboard-tabs",
            value="tab-cockpit",
            colors={"border": "#334155", "primary": "#38bdf8", "background": "#1e293b"},
            children=[
                dcc.Tab(label="1. Executive Regime Cockpit", value="tab-cockpit", style={"backgroundColor": "#1e293b", "color": "#cbd5e1"}, selected_style={"backgroundColor": "#0f172a", "color": "#38bdf8", "fontWeight": "bold"}),
                dcc.Tab(label="2. Advance-Decline & McClellan", value="tab-ad", style={"backgroundColor": "#1e293b", "color": "#cbd5e1"}, selected_style={"backgroundColor": "#0f172a", "color": "#38bdf8", "fontWeight": "bold"}),
                dcc.Tab(label="3. DMA & High-Low Extremes", value="tab-dma", style={"backgroundColor": "#1e293b", "color": "#cbd5e1"}, selected_style={"backgroundColor": "#0f172a", "color": "#38bdf8", "fontWeight": "bold"}),
                dcc.Tab(label="4. Volume & Breadth Thrusts", value="tab-volume", style={"backgroundColor": "#1e293b", "color": "#cbd5e1"}, selected_style={"backgroundColor": "#0f172a", "color": "#38bdf8", "fontWeight": "bold"}),
                dcc.Tab(label="5. Sector Rotation & Participation", value="tab-sectors", style={"backgroundColor": "#1e293b", "color": "#cbd5e1"}, selected_style={"backgroundColor": "#0f172a", "color": "#38bdf8", "fontWeight": "bold"}),
            ]
        ),
        html.Div(id="tab-content", style={"marginTop": "20px"})
    ]
)


@app.callback(
    Output("tab-content", "children"),
    Input("dashboard-tabs", "value")
)
def render_tab_content(tab_value):
    if tab_value == "tab-cockpit":
        last = breadth_df.iloc[-1] if len(breadth_df) > 0 else {}
        regime = "BULLISH (Army Leading)" if last.get("eq_cap_ratio", 1.0) >= 1.0 else "DEFENSIVE (Generals Only)"
        
        return html.Div([
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(180px, 1fr))", "gap": "15px", "marginBottom": "20px"},
                children=[
                    kpi_card("Market Regime", regime, "#38bdf8"),
                    kpi_card("% > 50 DMA", f"{last.get('pct_above_sma_50', 0):.1f}%", "#4ade80"),
                    kpi_card("% > 200 DMA", f"{last.get('pct_above_sma_200', 0):.1f}%", "#4ade80"),
                    kpi_card("TRIN (Arms Index)", f"{last.get('trin', 1.0):.2f}", "#f43f5e" if last.get('trin', 1.0) > 1.5 else "#38bdf8"),
                    kpi_card("McClellan Oscillator", f"{last.get('mcclellan_oscillator', 0):.1f}", "#fbbf24"),
                    kpi_card("Zweig EMA10", f"{last.get('zweig_thrust_ema10', 0):.3f}", "#a855f7"),
                    kpi_card("Hindenburg Omen", "ACTIVE" if last.get('hindenburg_omen', 0) == 1 else "Clear", "#f43f5e" if last.get('hindenburg_omen', 0) == 1 else "#4ade80"),
                ]
            ),
            html.Div(
                style={"backgroundColor": "#1e293b", "padding": "15px", "borderRadius": "8px", "boxShadow": "0 4px 6px rgba(0,0,0,0.3)"},
                children=[
                    dcc.Graph(figure=create_cockpit_figure(breadth_df))
                ]
            )
        ])

    elif tab_value == "tab-ad":
        return html.Div([
            html.Div(
                style={"backgroundColor": "#1e293b", "padding": "15px", "borderRadius": "8px"},
                children=[
                    dcc.Graph(figure=create_ad_figure(breadth_df))
                ]
            )
        ])

    elif tab_value == "tab-dma":
        return html.Div([
            html.Div(
                style={"backgroundColor": "#1e293b", "padding": "15px", "borderRadius": "8px"},
                children=[
                    dcc.Graph(figure=create_dma_figure(breadth_df))
                ]
            )
        ])

    elif tab_value == "tab-volume":
        return html.Div([
            html.Div(
                style={"backgroundColor": "#1e293b", "padding": "15px", "borderRadius": "8px"},
                children=[
                    dcc.Graph(figure=create_volume_figure(breadth_df))
                ]
            )
        ])

    elif tab_value == "tab-sectors":
        summary_df = compute_all_sectors_summary(start="2023-01-01")
        sector_options = [{"label": s["name"], "value": s["key"]} for s in OFFICIAL_SECTORS]
        
        return html.Div([
            html.H3("Sector Rotation & Participation Matrix (Equal-Weight vs Cap-Weight Spread)", style={"color": "#38bdf8", "fontSize": "18px", "marginBottom": "15px"}),
            html.Div(
                style={"backgroundColor": "#1e293b", "padding": "15px", "borderRadius": "8px", "marginBottom": "20px"},
                children=[
                    dash_table.DataTable(
                        data=summary_df.to_dict("records"),
                        columns=[{"name": i, "id": i} for i in summary_df.columns],
                        style_header={"backgroundColor": "#0f172a", "color": "#38bdf8", "fontWeight": "bold"},
                        style_cell={"backgroundColor": "#1e293b", "color": "#f8fafc", "border": "1px solid #334155", "textAlign": "center", "fontSize": "12px", "padding": "6px"},
                        style_data_conditional=[
                            {
                                "if": {"column_id": [c for c in summary_df.columns if "Spread" in c], "filter_query": f"{{{c}}} > 0"},
                                "backgroundColor": "#064e3b",
                                "color": "#6ee7b7",
                            } for c in summary_df.columns if "Spread" in c
                        ],
                        page_size=15,
                        sort_action="native"
                    )
                ]
            ),
            # Sector Quadrant Scatter Plot
            html.Div(
                style={"backgroundColor": "#1e293b", "padding": "15px", "borderRadius": "8px", "marginBottom": "20px"},
                children=[
                    dcc.Graph(figure=create_sector_quadrant_figure(summary_df))
                ]
            ),
            html.Div(
                style={"display": "flex", "gap": "15px", "marginBottom": "15px", "alignItems": "center"},
                children=[
                    html.Label("Select Sector for Drill-Down:", style={"color": "#cbd5e1", "fontWeight": "bold"}),
                    dcc.Dropdown(
                        id="sector-dropdown",
                        options=sector_options,
                        value="niftybank",
                        style={"width": "300px", "backgroundColor": "#1e293b", "color": "#000"}
                    )
                ]
            ),
            html.Div(
                style={"backgroundColor": "#1e293b", "padding": "15px", "borderRadius": "8px"},
                children=[
                    dcc.Graph(id="sector-drilldown-graph")
                ]
            )
        ])


def kpi_card(title, value, color):
    return html.Div(
        style={"backgroundColor": "#1e293b", "padding": "15px", "borderRadius": "8px", "borderLeft": f"4px solid {color}", "boxShadow": "0 2px 4px rgba(0,0,0,0.2)"},
        children=[
            html.Div(title, style={"fontSize": "12px", "color": "#94a3b8", "marginBottom": "5px", "textTransform": "uppercase"}),
            html.Div(value, style={"fontSize": "20px", "fontWeight": "bold", "color": color})
        ]
    )


def create_cockpit_figure(df):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3],
                        subplot_titles=("Cap-Weighted vs Equal-Weighted Index Trajectory & Ratio", "20-Day Army vs Generals ROC Spread Histogram"))
    
    if "cap_weighted_close" in df.columns and "equal_weighted_close" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["cap_weighted_close"], name="Cap-Weighted Index", line={"color": "#38bdf8", "width": 2}), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df["equal_weighted_close"], name="Equal-Weighted Index", line={"color": "#4ade80", "width": 2}), row=1, col=1)
    
    if "eq_cap_roc20_spread" in df.columns:
        colors = ["#4ade80" if val >= 0 else "#f43f5e" for val in df["eq_cap_roc20_spread"]]
        fig.add_trace(go.Bar(x=df.index, y=df["eq_cap_roc20_spread"], name="20D ROC Spread (EW - MCAP)", marker_color=colors), row=2, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#1e293b", plot_bgcolor="#1e293b", height=600, margin={"l": 40, "r": 40, "t": 40, "b": 40})
    return fig


def create_ad_figure(df):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.4, 0.3, 0.3],
                        subplot_titles=("Cumulative Normalized A/D Line", "Ratio-Adjusted McClellan Oscillator", "McClellan Summation Index"))
    
    if "cumulative_ad_ratio" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["cumulative_ad_ratio"], name="Cumulative A/D Ratio", line={"color": "#38bdf8", "width": 2}), row=1, col=1)
    
    if "mcclellan_oscillator_ratio" in df.columns:
        colors = ["#4ade80" if val >= 0 else "#f43f5e" for val in df["mcclellan_oscillator_ratio"]]
        fig.add_trace(go.Bar(x=df.index, y=df["mcclellan_oscillator_ratio"], name="McClellan Oscillator (Ratio)", marker_color=colors), row=2, col=1)
    
    if "mcclellan_summation_ratio" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["mcclellan_summation_ratio"], name="McClellan Summation (Ratio)", line={"color": "#fbbf24", "width": 2}), row=3, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#1e293b", plot_bgcolor="#1e293b", height=700, margin={"l": 40, "r": 40, "t": 40, "b": 40})
    return fig


def create_dma_figure(df):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.4, 0.3, 0.3],
                        subplot_titles=("Tri-horizon DMA Participation Ribbon (% > 20/50/200 SMA)", "Net New 52-Week Highs / Lows", "High-Low Logic Index & Hindenburg Omen"))
    
    if "pct_above_sma_20" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["pct_above_sma_20"], name="% > 20 SMA", line={"color": "#38bdf8", "width": 1.5}), row=1, col=1)
    if "pct_above_sma_50" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["pct_above_sma_50"], name="% > 50 SMA", line={"color": "#4ade80", "width": 1.5}), row=1, col=1)
    if "pct_above_sma_200" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["pct_above_sma_200"], name="% > 200 SMA", line={"color": "#a855f7", "width": 1.5}), row=1, col=1)
    
    fig.add_hline(y=80, line_dash="dash", line_color="#f43f5e", row=1, col=1, annotation_text="Overbought (80%)")
    fig.add_hline(y=15, line_dash="dash", line_color="#fbbf24", row=1, col=1, annotation_text="Washout (15%)")

    if "net_new_highs" in df.columns:
        fig.add_trace(go.Bar(x=df.index, y=df["net_new_highs"], name="Net New Highs (NH - NL)", marker_color="#38bdf8"), row=2, col=1)

    if "high_low_logic_index" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["high_low_logic_index"], name="High-Low Logic Index", line={"color": "#fbbf24", "width": 2}), row=3, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#1e293b", plot_bgcolor="#1e293b", height=700, margin={"l": 40, "r": 40, "t": 40, "b": 40})
    return fig


def create_volume_figure(df):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.34, 0.33, 0.33],
                        subplot_titles=("Up/Down Volume Ratio & 9:1 Impulse Days", "Arms Index (TRIN)", "Zweig Breadth Thrust (EMA10)"))
    
    if "up_down_volume_ratio" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["up_down_volume_ratio"], name="Up/Down Volume Ratio", line={"color": "#38bdf8", "width": 1.5}), row=1, col=1)
    fig.add_hline(y=1.0, line_dash="dot", line_color="#94a3b8", row=1, col=1)

    if "trin" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["trin"], name="TRIN", line={"color": "#fbbf24", "width": 1.5}), row=2, col=1)
    fig.add_hline(y=1.0, line_dash="dash", line_color="#4ade80", row=2, col=1, annotation_text="Neutral (1.0)")
    fig.add_hline(y=2.0, line_dash="dash", line_color="#f43f5e", row=2, col=1, annotation_text="Washout (2.0)")

    if "zweig_thrust_ema10" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["zweig_thrust_ema10"], name="Zweig Thrust EMA10", line={"color": "#a855f7", "width": 2}), row=3, col=1)
    fig.add_hline(y=0.615, line_dash="dash", line_color="#4ade80", row=3, col=1, annotation_text="Thrust Trigger (0.615)")
    fig.add_hline(y=0.40, line_dash="dash", line_color="#f43f5e", row=3, col=1, annotation_text="Oversold Zone (0.40)")

    fig.update_layout(template="plotly_dark", paper_bgcolor="#1e293b", plot_bgcolor="#1e293b", height=700, margin={"l": 40, "r": 40, "t": 40, "b": 40})
    return fig


def create_sector_quadrant_figure(summary_df: pd.DataFrame):
    if summary_df.empty or "1M Cap (%)" not in summary_df.columns or "1M Spread (%)" not in summary_df.columns:
        fig = go.Figure()
        fig.update_layout(template="plotly_dark", paper_bgcolor="#1e293b", plot_bgcolor="#1e293b", height=500)
        return fig

    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=summary_df["1M Cap (%)"],
        y=summary_df["1M Spread (%)"],
        mode="text+markers",
        text=summary_df["Sector"],
        marker={
            "size": summary_df["Breadth (% > 50 DMA)"].clip(lower=10) * 0.4,
            "color": summary_df["1M Spread (%)"],
            "colorscale": "Viridis",
            "showscale": True,
            "colorbar": {"title": "1M Spread (%)"}
        },
        hovertemplate="<b>%{text}</b><br>1M Cap Return: %{x:.2f}%<br>1M Spread (EW-MCAP): %{y:.2f}%<extra></extra>"
    ))

    fig.add_vline(x=0, line_dash="dash", line_color="#94a3b8")
    fig.add_hline(y=0, line_dash="dash", line_color="#94a3b8")

    max_x = max(abs(summary_df["1M Cap (%)"].max()), abs(summary_df["1M Cap (%)"].min()), 5)
    max_y = max(abs(summary_df["1M Spread (%)"].max()), abs(summary_df["1M Spread (%)"].min()), 2)

    fig.add_annotation(x=max_x*0.6, y=max_y*0.6, text="<b>Broad Leadership</b><br>(Army + Generals)", showarrow=False, font={"color": "#4ade80", "size": 11})
    fig.add_annotation(x=max_x*0.6, y=-max_y*0.6, text="<b>Narrow Rally</b><br>(Generals Only)", showarrow=False, font={"color": "#f43f5e", "size": 11})
    fig.add_annotation(x=-max_x*0.6, y=max_y*0.6, text="<b>Broadening Base</b><br>(Early Rotation)", showarrow=False, font={"color": "#38bdf8", "size": 11})
    fig.add_annotation(x=-max_x*0.6, y=-max_y*0.6, text="<b>Broad Laggard</b><br>(Distribution)", showarrow=False, font={"color": "#fbbf24", "size": 11})

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        height=500,
        title="Sector Rotation Quadrant (1M Cap Return vs EW-MCAP Spread)",
        xaxis_title="1M Cap-Weighted Return (%)",
        yaxis_title="1M Participation Spread (EW - MCAP %)",
        margin={"l": 40, "r": 40, "t": 50, "b": 40}
    )
    return fig


@app.callback(
    Output("sector-drilldown-graph", "figure"),
    Input("sector-dropdown", "value")
)
def update_sector_drilldown(sector_key):
    res = compute_sector_timeseries(sector_key, start="2023-01-01")
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08,
        row_heights=[0.4, 0.3, 0.3],
        subplot_titles=(
            f"{res.get('sector_name', sector_key)}: Cap-Weighted vs Equal-Weighted Trajectory",
            "EW / MCAP Ratio & Relative Performance",
            "Internal Sector DMA Breadth (% > 20/50/200 DMA)"
        )
    )
    
    if "cap_close" in res and "eq_close" in res:
        cap_norm = res["cap_close"] / (res["cap_close"].iloc[0] + 1e-6) * 100.0
        eq_norm = res["eq_close"] / (res["eq_close"].iloc[0] + 1e-6) * 100.0
        fig.add_trace(go.Scatter(x=res["dates"], y=cap_norm, name="Cap-Weighted (Norm 100)", line={"color": "#38bdf8", "width": 2}), row=1, col=1)
        fig.add_trace(go.Scatter(x=res["dates"], y=eq_norm, name="Equal-Weighted (Norm 100)", line={"color": "#4ade80", "width": 2}), row=1, col=1)

    if "eq_cap_ratio" in res:
        fig.add_trace(go.Scatter(x=res["dates"], y=res["eq_cap_ratio"], name="EW / MCAP Ratio", line={"color": "#fbbf24", "width": 2}), row=2, col=1)
        fig.add_hline(y=1.0, line_dash="dash", line_color="#94a3b8", row=2, col=1)

    if "pct_above_20" in res:
        fig.add_trace(go.Scatter(x=res["dates"], y=res["pct_above_20"], name="% > 20 DMA", line={"color": "#38bdf8", "width": 1.2}), row=3, col=1)
    if "pct_above_50" in res:
        fig.add_trace(go.Scatter(x=res["dates"], y=res["pct_above_50"], name="% > 50 DMA", line={"color": "#4ade80", "width": 1.2}), row=3, col=1)
    if "pct_above_200" in res:
        fig.add_trace(go.Scatter(x=res["dates"], y=res["pct_above_200"], name="% > 200 DMA", line={"color": "#a855f7", "width": 1.2}), row=3, col=1)
    
    fig.add_hline(y=50, line_dash="dash", line_color="#94a3b8", row=3, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#1e293b", plot_bgcolor="#1e293b", height=750, margin={"l": 40, "r": 40, "t": 40, "b": 40})
    return fig


if __name__ == "__main__":
    print("Starting Nifty 500 Market Breadth Dash Dashboard on http://127.0.0.1:8050 ...")
    app.run(debug=False, port=8050)
