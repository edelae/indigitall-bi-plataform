"""
Chart Service
Generates Plotly charts based on query results with inDigital design system.
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Optional, Dict, Any, List


class ChartService:
    """Service for generating charts from data."""

    # inDigital Design System Colors
    COLORS = {
        'primary': '#1E88E5',
        'primary_dark': '#1565C0',
        'primary_light': '#42A5F5',
        'secondary': '#76C043',
        'secondary_dark': '#5EA832',
        'tertiary': '#A0A3BD',
        'text_primary': '#1A1A2E',
        'text_secondary': '#6E7191',
        'text_muted': '#A0A3BD',
        'background': '#FFFFFF',
        'background_accent': '#F5F7FA',
        'border': '#E4E4E7',
    }

    COLOR_SEQUENCE = [
        '#1E88E5',  # Primary Blue
        '#76C043',  # CTA Green
        '#42A5F5',  # Light Blue
        '#1565C0',  # Dark Blue
        '#A0A3BD',  # Muted Gray
        '#FFC107',  # Amber
        '#9C27B0',  # Purple
        '#FF5722',  # Deep Orange
    ]

    def __init__(self):
        """Initialize the chart service."""
        self.default_layout = {
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'plot_bgcolor': 'rgba(0,0,0,0)',
            'font': {
                'family': 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
                'size': 12,
                'color': '#6E7191'
            },
            'margin': {'l': 40, 'r': 40, 't': 40, 'b': 40},
            'xaxis': {
                'gridcolor': '#E4E4E7',
                'linecolor': '#E4E4E7',
                'tickfont': {'color': '#6E7191', 'size': 11}
            },
            'yaxis': {
                'gridcolor': '#E4E4E7',
                'linecolor': '#E4E4E7',
                'tickfont': {'color': '#6E7191', 'size': 11}
            },
            'hoverlabel': {
                'bgcolor': '#1A1A2E',
                'font_size': 13,
                'font_family': 'Inter, sans-serif'
            }
        }

    def create_chart(self, df: pd.DataFrame, chart_type: str, title: str = "",
                    x_col: Optional[str] = None, y_col: Optional[str] = None) -> go.Figure:
        """Create a chart based on the specified type."""
        if df.empty:
            return self._create_empty_chart(title)

        # Auto-detect columns if not specified
        if x_col is None and len(df.columns) > 0:
            x_col = df.columns[0]
        if y_col is None and len(df.columns) > 1:
            y_col = df.columns[1]

        if chart_type == 'bar':
            return self._create_bar_chart(df, title, x_col, y_col)
        elif chart_type == 'line':
            return self._create_line_chart(df, title, x_col, y_col)
        elif chart_type == 'pie':
            return self._create_pie_chart(df, title, x_col, y_col)
        elif chart_type == 'area':
            return self._create_area_chart(df, title, x_col, y_col)
        elif chart_type == 'horizontal_bar':
            return self._create_horizontal_bar_chart(df, title, x_col, y_col)
        else:
            return self._create_bar_chart(df, title, x_col, y_col)

    def _create_empty_chart(self, title: str) -> go.Figure:
        """Create an empty chart with a message."""
        fig = go.Figure()
        fig.add_annotation(
            text="No hay datos disponibles",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font={'size': 14, 'color': '#A0A3BD', 'family': 'Inter, sans-serif'}
        )
        fig.update_layout(title=title, **self.default_layout)
        return fig

    def _create_bar_chart(self, df: pd.DataFrame, title: str,
                         x_col: str, y_col: str) -> go.Figure:
        """Create a vertical bar chart."""
        fig = px.bar(
            df,
            x=x_col,
            y=y_col,
            title=title,
            color_discrete_sequence=[self.COLORS['primary']]
        )
        fig.update_layout(**self.default_layout)
        fig.update_traces(
            marker_color=self.COLORS['primary'],
            marker_line_width=0,
            hovertemplate='<b>%{x}</b><br>%{y:,}<extra></extra>'
        )
        return fig

    def _create_horizontal_bar_chart(self, df: pd.DataFrame, title: str,
                                    x_col: str, y_col: str) -> go.Figure:
        """Create a horizontal bar chart."""
        fig = px.bar(
            df,
            x=y_col,
            y=x_col,
            title=title,
            orientation='h',
            color_discrete_sequence=[self.COLORS['primary']]
        )
        fig.update_layout(**self.default_layout)
        fig.update_traces(
            marker_color=self.COLORS['primary'],
            marker_line_width=0,
            hovertemplate='<b>%{y}</b><br>%{x:,}<extra></extra>'
        )
        return fig

    def _create_line_chart(self, df: pd.DataFrame, title: str,
                          x_col: str, y_col: str) -> go.Figure:
        """Create a line chart."""
        fig = px.line(
            df,
            x=x_col,
            y=y_col,
            title=title,
            color_discrete_sequence=[self.COLORS['primary']]
        )
        fig.update_layout(**self.default_layout)
        fig.update_traces(
            line_color=self.COLORS['primary'],
            line_width=3,
            hovertemplate='<b>%{x}</b><br>%{y:,}<extra></extra>'
        )
        return fig

    def _create_area_chart(self, df: pd.DataFrame, title: str,
                          x_col: str, y_col: str) -> go.Figure:
        """Create an area chart."""
        fig = px.area(
            df,
            x=x_col,
            y=y_col,
            title=title,
            color_discrete_sequence=[self.COLORS['primary']]
        )
        fig.update_layout(**self.default_layout)
        fig.update_traces(
            line_color=self.COLORS['primary'],
            fillcolor='rgba(30, 136, 229, 0.1)'
        )
        return fig

    def _create_pie_chart(self, df: pd.DataFrame, title: str,
                         x_col: str, y_col: str) -> go.Figure:
        """Create a pie/donut chart."""
        fig = px.pie(
            df,
            names=x_col,
            values=y_col,
            title=title,
            color_discrete_sequence=self.COLOR_SEQUENCE,
            hole=0.45
        )
        fig.update_layout(**self.default_layout)
        fig.update_traces(
            textposition='outside',
            textinfo='percent+label',
            textfont_size=12,
            marker=dict(line=dict(color='#FFFFFF', width=2)),
            hovertemplate='<b>%{label}</b><br>%{value:,} (%{percent})<extra></extra>'
        )
        return fig

    def create_messages_by_direction_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create a specialized chart for messages by direction."""
        if df.empty:
            return self._create_empty_chart("Mensajes por Direccion")

        fig = px.pie(
            df,
            names='direction',
            values='count',
            title='',
            color_discrete_sequence=self.COLOR_SEQUENCE,
            hole=0.45
        )
        fig.update_layout(**self.default_layout)
        fig.update_traces(
            textposition='outside',
            textinfo='percent+label',
            textfont_size=12,
            marker=dict(line=dict(color='#FFFFFF', width=2))
        )
        return fig

    def create_messages_over_time_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create a specialized chart for messages over time."""
        if df.empty:
            return self._create_empty_chart("Mensajes en el Tiempo")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['count'],
            mode='lines',
            fill='tozeroy',
            line=dict(color=self.COLORS['primary'], width=3),
            fillcolor='rgba(30, 136, 229, 0.1)',
            hovertemplate='<b>%{x}</b><br>%{y:,} mensajes<extra></extra>'
        ))
        fig.update_layout(**self.default_layout)
        return fig

    def create_hourly_distribution_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create a chart for hourly message distribution."""
        if df.empty:
            return self._create_empty_chart("Mensajes por Hora")

        fig = px.bar(
            df,
            x='hour',
            y='count',
            title='',
            color_discrete_sequence=[self.COLORS['primary_light']]
        )
        fig.update_layout(**self.default_layout)
        fig.update_traces(
            marker_color=self.COLORS['primary_light'],
            marker_line_width=0,
            hovertemplate='<b>%{x}:00</b><br>%{y:,} mensajes<extra></extra>'
        )
        fig.update_xaxes(tickmode='linear', tick0=0, dtick=2)
        return fig

    def create_top_contacts_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create a chart for top contacts."""
        if df.empty:
            return self._create_empty_chart("Top Contactos")

        df_sorted = df.sort_values('message_count', ascending=True)

        fig = px.bar(
            df_sorted,
            x='message_count',
            y='contact_name',
            title='',
            orientation='h',
            color_discrete_sequence=[self.COLORS['primary']]
        )
        fig.update_layout(**self.default_layout)
        fig.update_traces(
            marker_color=self.COLORS['primary'],
            marker_line_width=0,
            hovertemplate='<b>%{y}</b><br>%{x:,} mensajes<extra></extra>'
        )
        return fig

    def create_intent_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create a chart for intent distribution."""
        if df.empty:
            return self._create_empty_chart("Distribucion de Intenciones")

        df_sorted = df.sort_values('count', ascending=True)

        fig = px.bar(
            df_sorted,
            x='count',
            y='intent',
            title='',
            orientation='h',
            color_discrete_sequence=[self.COLORS['secondary']]
        )
        fig.update_layout(**self.default_layout)
        fig.update_traces(
            marker_color=self.COLORS['secondary'],
            marker_line_width=0,
            hovertemplate='<b>%{y}</b><br>%{x:,}<extra></extra>'
        )
        return fig

    def create_agent_performance_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create a chart for agent performance."""
        if df.empty:
            return self._create_empty_chart("Rendimiento de Agentes")

        fig = px.bar(
            df,
            x='agent_id',
            y='messages',
            title='',
            color_discrete_sequence=[self.COLORS['primary_dark']]
        )
        fig.update_layout(**self.default_layout)
        fig.update_traces(
            marker_color=self.COLORS['primary_dark'],
            marker_line_width=0,
            hovertemplate='<b>Agente %{x}</b><br>%{y:,} mensajes<extra></extra>'
        )
        return fig

    def create_day_of_week_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create a chart for messages by day of week."""
        if df.empty:
            return self._create_empty_chart("Mensajes por Dia")

        fig = px.bar(
            df,
            x='day_of_week',
            y='count',
            title='',
            color_discrete_sequence=[self.COLORS['primary_light']]
        )
        fig.update_layout(**self.default_layout)
        fig.update_traces(
            marker_color=self.COLORS['primary_light'],
            marker_line_width=0,
            hovertemplate='<b>%{x}</b><br>%{y:,} mensajes<extra></extra>'
        )
        return fig

    # ==================== Control de Toques Charts ====================

    def create_multi_line_chart(self, df: pd.DataFrame, title: str,
                                x_col: str, y_cols: List[str],
                                labels: Optional[Dict[str, str]] = None) -> go.Figure:
        """Create a multi-series line chart for comparing metrics over time.

        Args:
            df: DataFrame with data
            title: Chart title
            x_col: Column for x-axis (typically date)
            y_cols: List of columns for y-axis series
            labels: Optional dict mapping column names to display labels
        """
        if df.empty:
            return self._create_empty_chart(title)

        fig = go.Figure()

        for i, y_col in enumerate(y_cols):
            label = labels.get(y_col, y_col) if labels else y_col
            fig.add_trace(go.Scatter(
                x=df[x_col],
                y=df[y_col],
                mode='lines+markers',
                name=label,
                line=dict(
                    color=self.COLOR_SEQUENCE[i % len(self.COLOR_SEQUENCE)],
                    width=2
                ),
                marker=dict(size=6),
                hovertemplate=f'<b>{label}</b><br>%{{x}}<br>%{{y:,.0f}}<extra></extra>'
            ))

        fig.update_layout(**self.default_layout, title=title)
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ))
        return fig

    def create_combo_chart(self, df: pd.DataFrame, title: str,
                           x_col: str,
                           y1_cols: List[str],
                           y2_cols: List[str],
                           y1_labels: Optional[Dict[str, str]] = None,
                           y2_labels: Optional[Dict[str, str]] = None,
                           y1_title: str = "Cantidad",
                           y2_title: str = "Porcentaje (%)") -> go.Figure:
        """Create combo chart with dual y-axes.

        Args:
            df: DataFrame with data
            title: Chart title
            x_col: Column for x-axis
            y1_cols: Columns for primary y-axis (left - counts)
            y2_cols: Columns for secondary y-axis (right - percentages)
            y1_labels: Optional labels for primary axis columns
            y2_labels: Optional labels for secondary axis columns
            y1_title: Title for primary y-axis
            y2_title: Title for secondary y-axis
        """
        if df.empty:
            return self._create_empty_chart(title)

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Primary y-axis traces (counts - bars or lines)
        for i, col in enumerate(y1_cols):
            label = y1_labels.get(col, col) if y1_labels else col
            fig.add_trace(
                go.Scatter(
                    x=df[x_col],
                    y=df[col],
                    name=label,
                    mode='lines+markers',
                    line=dict(color=self.COLOR_SEQUENCE[i], width=2),
                    marker=dict(size=6),
                    hovertemplate=f'<b>{label}</b><br>%{{x}}<br>%{{y:,.0f}}<extra></extra>'
                ),
                secondary_y=False
            )

        # Secondary y-axis traces (percentages - dashed lines)
        for i, col in enumerate(y2_cols):
            label = y2_labels.get(col, col) if y2_labels else col
            fig.add_trace(
                go.Scatter(
                    x=df[x_col],
                    y=df[col],
                    name=label,
                    mode='lines+markers',
                    line=dict(
                        color=self.COLOR_SEQUENCE[len(y1_cols) + i],
                        dash='dash',
                        width=2
                    ),
                    marker=dict(size=6, symbol='diamond'),
                    hovertemplate=f'<b>{label}</b><br>%{{x}}<br>%{{y:.2f}}%<extra></extra>'
                ),
                secondary_y=True
            )

        fig.update_layout(**self.default_layout, title=title)
        fig.update_yaxes(title_text=y1_title, secondary_y=False)
        fig.update_yaxes(title_text=y2_title, secondary_y=True)
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ))
        return fig

    def create_heatmap(self, df: pd.DataFrame, title: str,
                       x_col: str, y_col: str, z_col: str,
                       x_title: str = "", y_title: str = "",
                       colorscale: str = "Blues") -> go.Figure:
        """Create a heatmap for day x hour analysis.

        Args:
            df: DataFrame with columns for x, y, and z values
            title: Chart title
            x_col: Column for x-axis (e.g., hour)
            y_col: Column for y-axis (e.g., day of week)
            z_col: Column for values (e.g., count)
            x_title: X-axis title
            y_title: Y-axis title
            colorscale: Plotly colorscale name
        """
        if df.empty:
            return self._create_empty_chart(title)

        # Pivot data for heatmap format
        pivot_df = df.pivot(index=y_col, columns=x_col, values=z_col).fillna(0)

        # Order days properly (Spanish)
        day_order = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
        ordered_days = [d for d in day_order if d in pivot_df.index]
        if ordered_days:
            pivot_df = pivot_df.reindex(ordered_days)

        # Custom colorscale matching inDigital design
        custom_colorscale = [
            [0, '#F5F7FA'],       # Light gray for low values
            [0.25, '#E3F2FD'],    # Very light blue
            [0.5, '#42A5F5'],     # Primary light
            [0.75, '#1E88E5'],    # Primary
            [1, '#1565C0']        # Primary dark for high values
        ]

        fig = go.Figure(data=go.Heatmap(
            z=pivot_df.values,
            x=pivot_df.columns.tolist(),
            y=pivot_df.index.tolist(),
            colorscale=custom_colorscale,
            hovertemplate='<b>Hora: %{x}</b><br>%{y}<br>Valor: %{z:,.0f}<extra></extra>',
            colorbar=dict(
                title=dict(text=z_col.capitalize(), side='right'),
                tickfont=dict(size=10)
            )
        ))

        fig.update_layout(
            **self.default_layout,
            title=title,
            xaxis_title=x_title or x_col,
            yaxis_title=y_title or y_col
        )
        fig.update_xaxes(tickmode='linear', tick0=0, dtick=2)
        return fig

    def create_ranking_bar_chart(self, df: pd.DataFrame, title: str,
                                 name_col: str, value_col: str,
                                 secondary_col: Optional[str] = None,
                                 value_format: str = "{:,.0f}") -> go.Figure:
        """Create a horizontal bar chart for rankings with optional secondary info.

        Args:
            df: DataFrame with ranking data
            title: Chart title
            name_col: Column for item names
            value_col: Column for primary values
            secondary_col: Optional column for secondary values (shown in hover)
            value_format: Format string for values
        """
        if df.empty:
            return self._create_empty_chart(title)

        df_sorted = df.sort_values(value_col, ascending=True)

        fig = go.Figure()

        hover_template = f'<b>%{{y}}</b><br>{value_col}: %{{x:,.0f}}'
        if secondary_col:
            hover_template += f'<br>{secondary_col}: %{{customdata:.2f}}%'
        hover_template += '<extra></extra>'

        fig.add_trace(go.Bar(
            x=df_sorted[value_col],
            y=df_sorted[name_col],
            orientation='h',
            marker_color=self.COLORS['primary'],
            customdata=df_sorted[secondary_col] if secondary_col else None,
            hovertemplate=hover_template
        ))

        fig.update_layout(**self.default_layout, title=title)
        fig.update_traces(marker_line_width=0)
        return fig

    def create_bar_chart(self, df: pd.DataFrame, title: str,
                         x_col: str, y_col: str) -> go.Figure:
        """Create a vertical bar chart.

        Args:
            df: DataFrame with data
            title: Chart title
            x_col: Column for x-axis categories
            y_col: Column for y-axis values
        """
        return self._create_bar_chart(df, title, x_col, y_col)

    def create_pie_chart(self, df: pd.DataFrame, title: str,
                         x_col: str, y_col: str) -> go.Figure:
        """Create a pie/donut chart.

        Args:
            df: DataFrame with data
            title: Chart title
            x_col: Column for category labels
            y_col: Column for values
        """
        return self._create_pie_chart(df, title, x_col, y_col)
