import urllib.parse
import json

def generate_revenue_growth_chart(daily_data, width=800, height=400):
    """
    Generate a QuickChart.io URL for revenue growth over time
    daily_data: list of tuples (date_string, revenue_amount)
    """
    if not daily_data:
        return None
    
    labels = [row[0] for row in daily_data]
    values = [row[1] for row in daily_data]
    
    chart_config = {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Revenue (₮)",
                "data": values,
                "borderColor": "rgb(46, 204, 113)",
                "backgroundColor": "rgba(46, 204, 113, 0.2)",
                "fill": True,
                "tension": 0.4
            }]
        },
        "options": {
            "title": {
                "display": True,
                "text": "Revenue Growth (Last 30 Days)",
                "fontSize": 18,
                "fontColor": "#ffffff"
            },
            "scales": {
                "yAxes": [{
                    "ticks": {
                        "beginAtZero": True,
                        "fontColor": "#ffffff"
                    },
                    "gridLines": {
                        "color": "rgba(255, 255, 255, 0.1)"
                    }
                }],
                "xAxes": [{
                    "ticks": {
                        "fontColor": "#ffffff"
                    },
                    "gridLines": {
                        "color": "rgba(255, 255, 255, 0.1)"
                    }
                }]
            },
            "legend": {
                "labels": {
                    "fontColor": "#ffffff"
                }
            }
        }
    }
    
    chart_json = json.dumps(chart_config)
    encoded = urllib.parse.quote(chart_json)
    
    return f"https://quickchart.io/chart?c={encoded}&backgroundColor=rgb(44,47,51)&width={width}&height={height}"

def generate_role_breakdown_chart(role_data, width=600, height=400):
    """
    Generate a QuickChart.io URL for role revenue pie chart
    role_data: list of tuples (role_name, revenue, payment_count)
    """
    if not role_data:
        return None
    
    labels = [row[0] for row in role_data]
    values = [row[1] for row in role_data]
    
    colors = [
        "rgb(46, 204, 113)",
        "rgb(52, 152, 219)",
        "rgb(155, 89, 182)",
        "rgb(241, 196, 15)",
        "rgb(230, 126, 34)",
        "rgb(231, 76, 60)",
        "rgb(149, 165, 166)",
        "rgb(26, 188, 156)"
    ]
    
    chart_config = {
        "type": "pie",
        "data": {
            "labels": labels,
            "datasets": [{
                "data": values,
                "backgroundColor": colors[:len(labels)]
            }]
        },
        "options": {
            "title": {
                "display": True,
                "text": "Revenue by Role Plan",
                "fontSize": 18,
                "fontColor": "#ffffff"
            },
            "legend": {
                "position": "right",
                "labels": {
                    "fontColor": "#ffffff",
                    "fontSize": 12
                }
            },
            "plugins": {
                "datalabels": {
                    "color": "#ffffff",
                    "font": {
                        "weight": "bold",
                        "size": 14
                    },
                    "formatter": "(value, ctx) => { const sum = ctx.dataset.data.reduce((a, b) => a + b, 0); const percentage = (value * 100 / sum).toFixed(1) + '%'; return percentage; }"
                }
            }
        }
    }
    
    chart_json = json.dumps(chart_config)
    encoded = urllib.parse.quote(chart_json)
    
    return f"https://quickchart.io/chart?c={encoded}&backgroundColor=rgb(44,47,51)&width={width}&height={height}"
