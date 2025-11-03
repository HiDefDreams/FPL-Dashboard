import plotly.express as px
import pandas as pd

def create_visualizations(df, weeks):
    """Create various charts and visualizations"""
    if df.empty:
        return None, None, None
    
    # Top players by rolling average
    fig1 = px.bar(
        df.head(15),
        x='Player',
        y=f'Rolling_{weeks}_Week_Avg',
        color='Position',
        title=f"Top 15 Players by {weeks}-Week Rolling Average",
        hover_data=['Team', 'Points_Per_90', 'Cost']
    )
    fig1.update_layout(height=400)
    
    # Points vs Cost scatter plot
    fig2 = px.scatter(
        df.head(50),
        x='Cost_Numeric',
        y=f'Rolling_{weeks}_Week_Avg',
        color='Position',
        size='Points_Per_90',
        hover_name='Player',
        title=f"Value Analysis: {weeks}-Week Average vs Cost",
        labels={'Cost_Numeric': 'Cost (£m)', f'Rolling_{weeks}_Week_Avg': 'Rolling Average'}
    )
    fig2.update_layout(height=400)
    
    # Points per 90 distribution by position
    fig3 = px.box(
        df,
        x='Position',
        y='Points_Per_90',
        color='Position',
        title=f"Points Per 90 Distribution by Position (Last {weeks} GWs)"
    )
    fig3.update_layout(height=400)
    
    return fig1, fig2, fig3