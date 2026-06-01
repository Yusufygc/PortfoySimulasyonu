import plotly.graph_objects as go
import pandas as pd
import numpy as np

class ComparisonChartFactory:
    @staticmethod
    def _apply_theme_layout(fig: go.Figure, title: str, theme_colors: dict = None) -> go.Figure:
        """Tüm grafiklere aktif temaya uygun layout standartlarını uygular."""
        if theme_colors is None:
            # Koyu tema varsayılan renkleri
            theme_colors = {
                "paper_bg": "#111827",  # COLOR_CARD_SURFACE
                "plot_bg": "#0f172a",   # COLOR_BG_BASE
                "text": "#f1f5f9",      # COLOR_TEXT_PRIMARY
                "grid": "#1e293b",      # COLOR_BORDER_SUBTLE
                "zeroline": "#334155"   # COLOR_BORDER
            }
            
        fig.update_layout(
            title={"text": title, "font": {"size": 16, "color": theme_colors.get("text", "#f1f5f9")}},
            paper_bgcolor=theme_colors.get("paper_bg", "#111827"),
            plot_bgcolor=theme_colors.get("plot_bg", "#0f172a"),
            font={"family": "Segoe UI, Arial", "color": theme_colors.get("text", "#f1f5f9")},
            margin={"l": 40, "r": 40, "t": 60, "b": 40},
            xaxis={
                "gridcolor": theme_colors.get("grid", "#1e293b"),
                "zerolinecolor": theme_colors.get("zeroline", "#334155"),
                "tickfont": {"color": theme_colors.get("text", "#f1f5f9")}
            },
            yaxis={
                "gridcolor": theme_colors.get("grid", "#1e293b"),
                "zerolinecolor": theme_colors.get("zeroline", "#334155"),
                "tickfont": {"color": theme_colors.get("text", "#f1f5f9")}
            },
            legend={
                "font": {"color": theme_colors.get("text", "#f1f5f9")}
            }
        )
        return fig

    @staticmethod
    def build_summary_table(df_summary: pd.DataFrame, theme_colors: dict = None) -> go.Figure:
        if df_summary.empty:
            return go.Figure()
        
        # Toplam Getiri % kolonuna göre büyükten küçüğe sırala
        df = df_summary.sort_values(by="Toplam Getiri %", ascending=False)
        
        if theme_colors is None:
            text_color = "#f1f5f9"
            header_bg = "#1e293b"
            cell_bg = "#111827"
        else:
            text_color = theme_colors.get("text", "#f1f5f9")
            header_bg = theme_colors.get("grid", "#1e293b")
            cell_bg = theme_colors.get("paper_bg", "#111827")
            
        # Koşullu renklendirme
        colors = []
        for val in df["Toplam Getiri %"]:
            if val >= 0:
                colors.append("rgba(16, 185, 129, 0.2)")  # Kâr için şeffaf yeşil
            else:
                colors.append("rgba(239, 68, 68, 0.2)")   # Zarar için şeffaf kırmızı
                
        fill_colors = [
            [cell_bg] * len(df),
            [cell_bg] * len(df),
            [cell_bg] * len(df),
            colors
        ]
        
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=list(df.columns),
                fill_color=header_bg,
                align='left',
                font=dict(color=text_color, size=12)
            ),
            cells=dict(
                values=[df[col] for col in df.columns],
                fill_color=fill_colors,
                align='left',
                font=dict(color=text_color, size=11)
            )
        )])
        
        return ComparisonChartFactory._apply_theme_layout(fig, "Dönem Sonu Getiri Özeti", theme_colors)

    @staticmethod
    def build_drawdown_chart(df_drawdowns: pd.DataFrame, theme_colors: dict = None) -> go.Figure:
        fig = go.Figure()
        colors_palette = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4"]
        
        for i, col in enumerate(df_drawdowns.columns):
            color = colors_palette[i % len(colors_palette)]
            fig.add_trace(go.Scatter(
                x=df_drawdowns.index,
                y=df_drawdowns[col],
                mode='lines',
                name=col,
                fill='tozeroy' if i == 0 else None,
                fillcolor='rgba(239, 68, 68, 0.08)' if i == 0 else None,
                line=dict(width=2, color=color)
            ))
            
        return ComparisonChartFactory._apply_theme_layout(fig, "Maksimum Drawdown Analizi (%)", theme_colors)

    @staticmethod
    def build_period_bar_chart(df_periodic: pd.DataFrame, theme_colors: dict = None) -> go.Figure:
        fig = go.Figure()
        colors_palette = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4"]
        
        x_labels = df_periodic.index
        if isinstance(df_periodic.index, pd.DatetimeIndex):
            x_labels = df_periodic.index.strftime("%Y-%m")
            
        for i, col in enumerate(df_periodic.columns):
            color = colors_palette[i % len(colors_palette)]
            fig.add_trace(go.Bar(
                x=x_labels,
                y=df_periodic[col],
                name=col,
                marker_color=color
            ))
            
        fig.update_layout(barmode='group')
        return ComparisonChartFactory._apply_theme_layout(fig, "Dönemsel Getiri Karşılaştırması (%)", theme_colors)

    @staticmethod
    def build_risk_return_scatter(df_risk_return: pd.DataFrame, theme_colors: dict = None) -> go.Figure:
        fig = go.Figure()
        colors_palette = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4"]
        
        for i, (name, row) in enumerate(df_risk_return.iterrows()):
            color = colors_palette[i % len(colors_palette)]
            fig.add_trace(go.Scatter(
                x=[row["Volatilite %"]],
                y=[row["Getiri %"]],
                mode='markers+text',
                name=name,
                text=[name],
                textposition="top center",
                marker=dict(size=14, color=color)
            ))
            
        fig = ComparisonChartFactory._apply_theme_layout(fig, "Risk-Getiri Dağılımı", theme_colors)
        fig.update_layout(
            xaxis_title="Yıllık Volatilite (%)",
            yaxis_title="Toplam Getiri (%)"
        )
        return fig

    @staticmethod
    def build_treemap(df_portfolio_weights: pd.DataFrame, theme_colors: dict = None) -> go.Figure:
        if df_portfolio_weights.empty:
            return go.Figure()
            
        fig = go.Figure(go.Treemap(
            labels=df_portfolio_weights.index.tolist(),
            parents=[""] * len(df_portfolio_weights),
            values=df_portfolio_weights["Varlık Ağırlığı %"].tolist(),
            marker=dict(
                colors=df_portfolio_weights["Getiri %"].tolist(),
                colorscale='RdYlGn',
                showscale=True
            )
        ))
        
        return ComparisonChartFactory._apply_theme_layout(fig, "Portföy Getiri Katkı Haritası (Treemap)", theme_colors)
