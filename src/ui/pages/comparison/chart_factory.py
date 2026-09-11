from src.ui.shared.locale_tr import L10N
import plotly.graph_objects as go
import pandas as pd
import numpy as np


DATE_AXIS_TICKFORMAT = "%d.%m.%Y"
MONTH_AXIS_TICKFORMAT = "%m.%Y"


class ComparisonChartFactory:
    @staticmethod
    def _date_value_hover_template(value_label: str = L10N.DEGER) -> str:
        return (
            f"{L10N.TARIH}: %{{x|{DATE_AXIS_TICKFORMAT}}}<br>"
            f"{value_label}: %{{y:.2f}}<extra>%{{fullData.name}}</extra>"
        )

    @staticmethod
    def _period_value_hover_template(value_label: str = L10N.GETIRI) -> str:
        return (
            f"{L10N.DONEM}: %{{x|{MONTH_AXIS_TICKFORMAT}}}<br>"
            f"{value_label}: %{{y:.2f}}<extra>%{{fullData.name}}</extra>"
        )

    @staticmethod
    def _apply_date_axis_format(fig: go.Figure, tickformat: str = DATE_AXIS_TICKFORMAT) -> go.Figure:
        fig.update_xaxes(tickformat=tickformat)
        return fig

    @staticmethod
    def _apply_theme_layout(fig: go.Figure, title: str, theme_colors: dict = None) -> go.Figure:
        """Tüm grafiklere aktif temaya uygun layout standartlarını uygular."""
        if theme_colors is None:
            # Koyu tema varsayılan renkleri
            theme_colors = {
                "paper_bg": "#0f172a",  # COLOR_CARD_SURFACE / BG
                "plot_bg": "#0b1120",   # Koyu grafik arka planı
                "text": "#f1f5f9",      # COLOR_TEXT_PRIMARY
                "grid": "#1e293b",      # COLOR_BORDER_SUBTLE
                "zeroline": "#334155"   # COLOR_BORDER
            }
            
        fig.update_layout(
            title={"text": title, "font": {"size": 15, "color": theme_colors.get("text", L10N.F1F5F9)}},
            paper_bgcolor=theme_colors.get("paper_bg", "#0f172a"),
            plot_bgcolor=theme_colors.get("plot_bg", "#0b1120"),
            font={"family": "Segoe UI, Arial", "color": theme_colors.get("text", L10N.F1F5F9)},
            autosize=True,
            margin={"l": 55, "r": 30, "t": 50, "b": 40},
            xaxis={
                "gridcolor": theme_colors.get("grid", "#1e293b"),
                "zerolinecolor": theme_colors.get("zeroline", "#334155"),
                "tickfont": {"color": theme_colors.get("text", L10N.F1F5F9), "size": 11}
            },
            yaxis={
                "gridcolor": theme_colors.get("grid", "#1e293b"),
                "zerolinecolor": theme_colors.get("zeroline", "#334155"),
                "tickfont": {"color": theme_colors.get("text", L10N.F1F5F9), "size": 11}
            },
            legend={
                "font": {"color": theme_colors.get("text", L10N.F1F5F9), "size": 11},
                "bgcolor": "rgba(15, 23, 42, 0.7)",
                "bordercolor": "#1e293b"
            }
        )
        return fig

    @staticmethod
    def build_summary_table(df_summary: pd.DataFrame, theme_colors: dict = None) -> go.Figure:
        if df_summary.empty:
            return go.Figure()
        
        # Toplam Getiri % kolonuna göre büyükten küçüğe sırala
        df = df_summary.sort_values(by=L10N.TOPLAM_GETIRI, ascending=False)
        
        if theme_colors is None:
            text_color = L10N.F1F5F9
            header_bg = "#1e293b"
            cell_bg = "#111827"
        else:
            text_color = theme_colors.get("text", L10N.F1F5F9)
            header_bg = theme_colors.get("grid", "#1e293b")
            cell_bg = theme_colors.get("paper_bg", "#111827")
            
        # Koşullu renklendirme
        colors = []
        for val in df[L10N.TOPLAM_GETIRI]:
            if val >= 0:
                colors.append(L10N.RGBA16_185_129_02)  # Kâr için şeffaf yeşil
            else:
                colors.append(L10N.RGBA239_68_68_02)   # Zarar için şeffaf kırmızı
                
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
        
        return ComparisonChartFactory._apply_theme_layout(fig, L10N.DONEM_SONU_GETIRI_OZETI, theme_colors)

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
                fillcolor=L10N.RGBA239_68_68_008 if i == 0 else None,
                line=dict(width=2, color=color),
                hovertemplate=ComparisonChartFactory._date_value_hover_template()
            ))
            
        fig = ComparisonChartFactory._apply_theme_layout(fig, L10N.MAKSIMUM_DRAWDOWN_ANALIZI, theme_colors)
        return ComparisonChartFactory._apply_date_axis_format(fig)

    @staticmethod
    def build_period_bar_chart(df_periodic: pd.DataFrame, theme_colors: dict = None) -> go.Figure:
        fig = go.Figure()
        colors_palette = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4"]
        
        for i, col in enumerate(df_periodic.columns):
            color = colors_palette[i % len(colors_palette)]
            fig.add_trace(go.Bar(
                x=df_periodic.index,
                y=df_periodic[col],
                name=col,
                marker_color=color,
                hovertemplate=ComparisonChartFactory._period_value_hover_template()
            ))
            
        fig.update_layout(barmode='group')
        fig = ComparisonChartFactory._apply_theme_layout(fig, L10N.DONEMSEL_GETIRI_KARSILASTIRMASI, theme_colors)
        return ComparisonChartFactory._apply_date_axis_format(fig, MONTH_AXIS_TICKFORMAT)

    @staticmethod
    def build_risk_return_scatter(df_risk_return: pd.DataFrame, theme_colors: dict = None) -> go.Figure:
        fig = go.Figure()
        colors_palette = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4"]
        
        for i, (name, row) in enumerate(df_risk_return.iterrows()):
            color = colors_palette[i % len(colors_palette)]
            fig.add_trace(go.Scatter(
                x=[row[L10N.VOLATILITE]],
                y=[row[L10N.GETIRI]],
                mode=L10N.MARKERSTEXT,
                name=name,
                text=[name],
                textposition=L10N.TOP_CENTER,
                marker=dict(size=14, color=color),
                hovertemplate=(
                    f"{L10N.VOLATILITE}: %{{x:.2f}}<br>"
                    f"{L10N.GETIRI}: %{{y:.2f}}<extra>%{{fullData.name}}</extra>"
                )
            ))
            
        fig = ComparisonChartFactory._apply_theme_layout(fig, L10N.RISKGETIRI_DAGILIMI, theme_colors)
        fig.update_layout(
            xaxis_title=L10N.YILLIK_VOLATILITE,
            yaxis_title=L10N.TOPLAM_GETIRI_1
        )
        return fig

    @staticmethod
    def build_treemap(df_portfolio_weights: pd.DataFrame, theme_colors: dict = None) -> go.Figure:
        if df_portfolio_weights.empty:
            return go.Figure()
            
        fig = go.Figure(go.Treemap(
            labels=df_portfolio_weights.index.tolist(),
            parents=[""] * len(df_portfolio_weights),
            values=df_portfolio_weights[L10N.VARLIK_AGIRLIGI].tolist(),
            customdata=df_portfolio_weights[L10N.GETIRI].tolist(),
            marker=dict(
                colors=df_portfolio_weights[L10N.GETIRI].tolist(),
                colorscale='RdYlGn',
                showscale=True
            ),
            hovertemplate=(
                "<b>%{label}</b><br>"
                f"{L10N.VARLIK_AGIRLIGI}: %{{value:.2f}}<br>"
                f"{L10N.GETIRI}: %{{customdata:.2f}}<extra></extra>"
            )
        ))
        
        return ComparisonChartFactory._apply_theme_layout(fig, L10N.PORTFOY_GETIRI_KATKI_HARITASI_TREEMAP, theme_colors)
