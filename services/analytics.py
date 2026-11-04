"""
Analytics and Plotly Visualization Engine.
File: services/analytics.py
"""

import json
import plotly
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from database.models import Student

# Premium AI Dashboard Theme Palette
THEME_COLORS = {
    "primary": "#3978F6",    # Electric Blue
    "secondary": "#22D3EE",  # Cyan (Highlights / AI accents)
    "success": "#10b981",    # Emerald
    "warning": "#f59e0b",    # Amber Gold
    "danger": "#f43f5e",     # Rose
    "neutral": "#94A3B8",    # Soft Gray
    "dark": "#F8FAFC",       # Cloud White
    "card_bg": "rgba(0,0,0,0)",
    "grid": "rgba(148, 163, 184, 0.12)", # Soft subtle grid
    "text": "#F8FAFC"        # Cloud White
}

def get_dashboard_kpis():
    """Calculates KPI card values directly from the database."""
    total_students = Student.query.count()
    if total_students == 0:
        return {
            "total_students": 0,
            "high_performers": 0,
            "avg_performers": 0,
            "at_risk_students": 0,
            "avg_attendance": 0.0,
            "avg_marks": 0.0,
            "avg_cgpa": 0.0
        }
        
    high_count = Student.query.filter_by(latest_prediction="High").count()
    avg_count = Student.query.filter_by(latest_prediction="Average").count()
    low_count = Student.query.filter_by(latest_prediction="Low").count()
    
    # At-risk students are defined as High Risk level
    at_risk_count = Student.query.filter(Student.latest_risk_level == "HIGH RISK").count()
    
    students = Student.query.all()
    avg_attendance = sum(s.attendance_percentage for s in students) / total_students
    avg_marks = sum(s.previous_semester_percentage for s in students) / total_students
    avg_cgpa = avg_marks / 9.5
    
    return {
        "total_students": total_students,
        "high_performers": high_count,
        "avg_performers": avg_count,
        "low_performers": low_count,
        "at_risk_students": at_risk_count,
        "avg_attendance": round(avg_attendance, 1),
        "avg_marks": round(avg_marks, 1),
        "avg_cgpa": round(avg_cgpa, 2)
    }

def get_dashboard_charts():
    """Generates JSON-serialized Plotly charts for the executive dashboard."""
    students = Student.query.all()
    if not students:
        return {}
        
    data = [s.to_dict() for s in students]
    df = pd.DataFrame(data)
    
    charts = {}
    
    # 1. Performance Category Distribution (Donut Chart)
    perf_counts = df["latest_prediction"].value_counts()
    order_perf = ["High", "Average", "Low"]
    perf_y = [int(perf_counts.get(k, 0)) for k in order_perf]
    perf_colors = ["#10b981", "#3b82f6", "#ef4444"]
    
    fig_perf = go.Figure(data=[go.Pie(
        labels=order_perf,
        values=perf_y,
        hole=0.55,
        marker=dict(colors=perf_colors),
        textinfo="label+percent",
        hoverinfo="label+value+percent"
    )])
    fig_perf.update_layout(
        margin=dict(t=25, b=25, l=20, r=20),
        showlegend=True,
        paper_bgcolor=THEME_COLORS["card_bg"],
        plot_bgcolor=THEME_COLORS["card_bg"],
        font=dict(family="Inter, sans-serif", size=12, color=THEME_COLORS["text"]),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
    )
    charts["performance_dist"] = json.dumps(fig_perf, cls=plotly.utils.PlotlyJSONEncoder)
    
    # 2. Risk Level Distribution (Bar Chart)
    risk_counts = df["latest_risk_level"].value_counts()
    order_risk = ["LOW RISK", "MEDIUM RISK", "HIGH RISK"]
    y_vals_risk = [int(risk_counts.get(r, 0)) for r in order_risk]
    colors_risk = ["#10b981", "#f59e0b", "#ef4444"]
    
    fig_risk = go.Figure(data=[go.Bar(
        x=order_risk,
        y=y_vals_risk,
        marker_color=colors_risk,
        text=y_vals_risk,
        textposition="auto",
        width=0.45
    )])
    fig_risk.update_layout(
        margin=dict(t=25, b=25, l=35, r=20),
        xaxis=dict(gridcolor=THEME_COLORS["grid"], title=dict(text="Risk Classification", font=dict(color="#94a3b8"))),
        yaxis=dict(gridcolor=THEME_COLORS["grid"], title=dict(text="Student Count", font=dict(color="#94a3b8"))),
        paper_bgcolor=THEME_COLORS["card_bg"],
        plot_bgcolor=THEME_COLORS["card_bg"],
        font=dict(family="Inter, sans-serif", size=12, color=THEME_COLORS["text"])
    )
    charts["risk_dist"] = json.dumps(fig_risk, cls=plotly.utils.PlotlyJSONEncoder)
    
    # 3. Department Performance Breakdown (Grouped Bar)
    dept_perf = pd.crosstab(df["department"], df["latest_prediction"])
    dept_short = {
        "Computer Science and Engineering": "CSE",
        "Information Technology": "IT",
        "Electronics and Communication Engineering": "ECE",
        "Electrical and Electronics Engineering": "EEE",
        "Mechanical Engineering": "MECH",
        "Civil Engineering": "CIVIL",
        "Artificial Intelligence and Data Science": "AI & DS",
        "Artificial Intelligence and Machine Learning": "AI & ML"
    }
    short_depts = [dept_short.get(d, d) for d in dept_perf.index]
    
    fig_dept = go.Figure()
    for category, color in [("High", "#10b981"), ("Average", "#3b82f6"), ("Low", "#ef4444")]:
        if category in dept_perf.columns:
            fig_dept.add_trace(go.Bar(
                name=category,
                x=short_depts,
                y=dept_perf[category],
                marker_color=color
            ))
    fig_dept.update_layout(
        barmode="group",
        margin=dict(t=25, b=25, l=35, r=20),
        xaxis=dict(gridcolor=THEME_COLORS["grid"], title=dict(text="Department", font=dict(color="#94a3b8"))),
        yaxis=dict(gridcolor=THEME_COLORS["grid"], title=dict(text="Students", font=dict(color="#94a3b8"))),
        paper_bgcolor=THEME_COLORS["card_bg"],
        plot_bgcolor=THEME_COLORS["card_bg"],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(family="Inter, sans-serif", size=12, color=THEME_COLORS["text"])
    )
    charts["dept_perf"] = json.dumps(fig_dept, cls=plotly.utils.PlotlyJSONEncoder)
    
    # 4. Attendance vs Predicted Outcome (Box Plot)
    fig_att = px.box(
        df,
        x="latest_prediction",
        y="attendance_percentage",
        color="latest_prediction",
        category_orders={"latest_prediction": ["High", "Average", "Low"]},
        color_discrete_map={"High": "#10b981", "Average": "#3b82f6", "Low": "#ef4444"},
        labels={"latest_prediction": "Predicted Category", "attendance_percentage": "Attendance (%)"}
    )
    fig_att.update_layout(
        margin=dict(t=25, b=25, l=35, r=20),
        showlegend=False,
        xaxis=dict(gridcolor=THEME_COLORS["grid"]),
        yaxis=dict(gridcolor=THEME_COLORS["grid"]),
        paper_bgcolor=THEME_COLORS["card_bg"],
        plot_bgcolor=THEME_COLORS["card_bg"],
        font=dict(family="Inter, sans-serif", size=12, color=THEME_COLORS["text"])
    )
    charts["attendance_vs_perf"] = json.dumps(fig_att, cls=plotly.utils.PlotlyJSONEncoder)
    
    # 5. Internal Assessment Marks 1 & 2 Correlation with Outcome (Replaces Study Hours)
    # Calculate average IA score
    df["ia_avg"] = (df["internal_exam_1"] + df["internal_exam_2"]) / 2.0
    fig_ia = px.histogram(
        df,
        x="ia_avg",
        color="latest_prediction",
        nbins=20,
        opacity=0.8,
        barmode="overlay",
        color_discrete_map={"High": "#10b981", "Average": "#3b82f6", "Low": "#ef4444"},
        labels={"ia_avg": "Internal Assessment Marks (Avg of 1 & 2)", "latest_prediction": "Category"}
    )
    fig_ia.update_layout(
        margin=dict(t=25, b=25, l=35, r=20),
        xaxis=dict(gridcolor=THEME_COLORS["grid"]),
        yaxis=dict(gridcolor=THEME_COLORS["grid"]),
        paper_bgcolor=THEME_COLORS["card_bg"],
        plot_bgcolor=THEME_COLORS["card_bg"],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(family="Inter, sans-serif", size=12, color=THEME_COLORS["text"])
    )
    charts["internal_assessment_dist"] = json.dumps(fig_ia, cls=plotly.utils.PlotlyJSONEncoder)
    
    # 6. Standing Arrears vs Performance Distribution
    backlog_summary = pd.crosstab(df["backlogs"], df["latest_prediction"])
    fig_backlog = go.Figure()
    for category, color in [("High", "#059669"), ("Average", "#2563eb"), ("Low", "#dc2626")]:
        if category in backlog_summary.columns:
            fig_backlog.add_trace(go.Bar(
                name=category,
                x=[f"{b} Arrear(s)" for b in backlog_summary.index],
                y=backlog_summary[category],
                marker_color=color
            ))
    fig_backlog.update_layout(
        barmode="stack",
        margin=dict(t=25, b=25, l=35, r=20),
        xaxis=dict(gridcolor=THEME_COLORS["grid"], title=dict(text="Standing Arrears Count", font=dict(color="#64748b"))),
        yaxis=dict(gridcolor=THEME_COLORS["grid"], title=dict(text="Student Count", font=dict(color="#64748b"))),
        paper_bgcolor=THEME_COLORS["card_bg"],
        plot_bgcolor=THEME_COLORS["card_bg"],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(family="Inter, sans-serif", size=12, color=THEME_COLORS["text"])
    )
    charts["backlogs_dist"] = json.dumps(fig_backlog, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Provide raw structured data for interactive client-side switching (Bar <-> Pie <-> Donut)
    charts["raw_data"] = {
        "performance": {
            "labels": order_perf,
            "values": perf_y,
            "colors": perf_colors
        },
        "risk": {
            "labels": order_risk,
            "values": y_vals_risk,
            "colors": colors_risk
        },
        "dept": {
            "departments": short_depts,
            "categories": ["High", "Average", "Low"],
            "series": {
                c: [int(x) for x in dept_perf[c].tolist()] if c in dept_perf.columns else [0] * len(short_depts)
                for c in ["High", "Average", "Low"]
            },
            "colors": {"High": "#059669", "Average": "#2563eb", "Low": "#dc2626"}
        }
    }
    
    return charts

def get_student_profile_charts(student):
    """Generates a spider/radar skill profile chart and academic trajectory for a single student."""
    skills = ["Technical", "Coding", "Communication", "Aptitude", "Lab Work", "Projects"]
    values = [
        student.technical_skill_score,
        student.coding_skill_score,
        student.communication_skill_score,
        student.aptitude_score,
        student.lab_score,
        student.project_score
    ]
    # Close polygon
    skills_closed = skills + [skills[0]]
    values_closed = values + [values[0]]
    
    fig_radar = go.Figure(data=go.Scatterpolar(
        r=values_closed,
        theta=skills_closed,
        fill="toself",
        fillcolor="rgba(57, 120, 246, 0.2)",
        line=dict(color="#3978F6", width=2.5),
        name="Skill Score"
    ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor=THEME_COLORS["grid"], linecolor=THEME_COLORS["grid"]),
            angularaxis=dict(gridcolor=THEME_COLORS["grid"], linecolor=THEME_COLORS["grid"]),
            bgcolor="rgba(0,0,0,0)"
        ),
        showlegend=False,
        margin=dict(t=25, b=25, l=25, r=25),
        paper_bgcolor=THEME_COLORS["card_bg"],
        font=dict(family="Inter, sans-serif", size=11, color=THEME_COLORS["text"])
    )
    
    # Internal Assessments Trajectory (IA1, IA2, IA Avg, Prev Sem CGPA Equivalent)
    ia_labels = ["Internal Exam 1", "Internal Exam 2", "Continuous Assessment Avg", "Prev Sem CGPA Equiv"]
    prev_cgpa_equiv = (student.previous_semester_percentage / 9.5) * 10
    ia_avg_val = round((student.internal_exam_1 + student.internal_exam_2) / 2.0, 1)
    ia_values = [
        student.internal_exam_1,
        student.internal_exam_2,
        ia_avg_val,
        prev_cgpa_equiv
    ]
    fig_trajectory = go.Figure(data=[go.Scatter(
        x=ia_labels,
        y=ia_values,
        mode="lines+markers+text",
        text=[f"{v:.1f}" for v in ia_values],
        textposition="top center",
        line=dict(color="#3978F6", width=3),
        marker=dict(size=9, color="#22D3EE", line=dict(color="#ffffff", width=1.5))
    )])
    fig_trajectory.update_layout(
        margin=dict(t=25, b=25, l=35, r=25),
        yaxis=dict(range=[0, 105], gridcolor=THEME_COLORS["grid"]),
        xaxis=dict(gridcolor=THEME_COLORS["grid"]),
        paper_bgcolor=THEME_COLORS["card_bg"],
        plot_bgcolor=THEME_COLORS["card_bg"],
        font=dict(family="Inter, sans-serif", size=11, color=THEME_COLORS["text"])
    )
    
    return {
        "radar": json.dumps(fig_radar, cls=plotly.utils.PlotlyJSONEncoder),
        "trajectory": json.dumps(fig_trajectory, cls=plotly.utils.PlotlyJSONEncoder)
    }

def get_model_performance_charts(metrics_data):
    """Generates comparison bar chart, confusion matrix heatmap, and feature importance bar chart."""
    charts = {}
    if not metrics_data:
        return charts
        
    # 1. Multi-Model Benchmark Comparison Chart
    comparison_table = metrics_data.get("comparison_table", [])
    if not comparison_table and "models_evaluation" in metrics_data:
        comparison_table = []
        for m_name, m_eval in metrics_data["models_evaluation"].items():
            comparison_table.append({
                "model": m_name,
                "accuracy": m_eval.get("accuracy", 0),
                "precision": m_eval.get("precision_weighted", 0),
                "recall": m_eval.get("recall_weighted", 0),
                "f1_score": m_eval.get("f1_weighted", 0),
                "is_selected": (m_name == metrics_data.get("selected_model"))
            })
            
    if comparison_table:
        model_names = [m["model"] for m in comparison_table]
        accuracies = [round(m.get("accuracy", 0) * 100, 1) for m in comparison_table]
        precisions = [round(m.get("precision", 0) * 100, 1) for m in comparison_table]
        recalls = [round(m.get("recall", 0) * 100, 1) for m in comparison_table]
        f1_scores = [round(m.get("f1_score", 0) * 100, 1) for m in comparison_table]
        
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(
            name="Accuracy (%)",
            x=model_names,
            y=accuracies,
            marker_color="#3978F6",
            text=[f"{v}%" for v in accuracies],
            textposition="auto"
        ))
        fig_comp.add_trace(go.Bar(
            name="Precision (%)",
            x=model_names,
            y=precisions,
            marker_color="#22D3EE",
            text=[f"{v}%" for v in precisions],
            textposition="auto"
        ))
        fig_comp.add_trace(go.Bar(
            name="Recall (%)",
            x=model_names,
            y=recalls,
            marker_color="#10b981",
            text=[f"{v}%" for v in recalls],
            textposition="auto"
        ))
        fig_comp.add_trace(go.Bar(
            name="F1-Score (%)",
            x=model_names,
            y=f1_scores,
            marker_color="#f59e0b",
            text=[f"{v}%" for v in f1_scores],
            textposition="auto"
        ))
        fig_comp.update_layout(
            barmode="group",
            margin=dict(t=25, b=25, l=45, r=20),
            yaxis=dict(range=[50, 105], title="Score (%)", gridcolor=THEME_COLORS["grid"]),
            xaxis=dict(gridcolor=THEME_COLORS["grid"]),
            paper_bgcolor=THEME_COLORS["card_bg"],
            plot_bgcolor=THEME_COLORS["card_bg"],
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            font=dict(family="Inter, sans-serif", size=12, color=THEME_COLORS["text"])
        )
        comp_json = json.dumps(fig_comp, cls=plotly.utils.PlotlyJSONEncoder)
        charts["model_comparison_chart"] = comp_json
        charts["comparison"] = comp_json

    # 2. Confusion Matrix Heatmap for Selected Model
    selected_model = metrics_data.get("selected_model", "Random Forest")
    models_eval = metrics_data.get("models_evaluation", {})
    model_eval = models_eval.get(selected_model) or (list(models_eval.values())[0] if models_eval else None)

    if model_eval and "confusion_matrix" in model_eval:
        cm = model_eval["confusion_matrix"]
        classes = model_eval.get("classes", ["High", "Average", "Low"])
        z_text = [[str(val) for val in row] for row in cm]

        fig_cm = go.Figure(data=go.Heatmap(
            z=cm,
            x=classes,
            y=classes,
            text=z_text,
            texttemplate="%{text}",
            textfont=dict(size=16, color="#ffffff", family="Inter, sans-serif"),
            colorscale=[[0, "#101828"], [0.35, "#18263D"], [0.75, "#3978F6"], [1.0, "#22D3EE"]],
            showscale=True,
            hoverongaps=False
        ))
        fig_cm.update_layout(
            margin=dict(t=30, b=45, l=65, r=20),
            xaxis=dict(title="Predicted Category", side="bottom", gridcolor=THEME_COLORS["grid"]),
            yaxis=dict(title="Actual Class", autorange="reversed", gridcolor=THEME_COLORS["grid"]),
            paper_bgcolor=THEME_COLORS["card_bg"],
            plot_bgcolor=THEME_COLORS["card_bg"],
            font=dict(family="Inter, sans-serif", size=12, color=THEME_COLORS["text"])
        )
        charts["confusion_matrix"] = json.dumps(fig_cm, cls=plotly.utils.PlotlyJSONEncoder)

    # 3. Feature Importance Bar Chart
    feat_imps = metrics_data.get("feature_importances", [])
    if feat_imps:
        top_feats = feat_imps[:10][::-1]
        feat_labels = [f["feature"].replace("_", " ").title() for f in top_feats]
        feat_values = [round(f["importance"] * 100, 2) for f in top_feats]

        fig_fi = go.Figure(go.Bar(
            x=feat_values,
            y=feat_labels,
            orientation="h",
            marker=dict(
                color=feat_values,
                colorscale=[[0, "#3978F6"], [1.0, "#22D3EE"]],
                line=dict(color="#22D3EE", width=1)
            ),
            text=[f"{v}%" for v in feat_values],
            textposition="outside"
        ))
        fig_fi.update_layout(
            margin=dict(t=25, b=25, l=150, r=40),
            xaxis=dict(title="Contribution to Prediction (%)", gridcolor=THEME_COLORS["grid"]),
            yaxis=dict(gridcolor=THEME_COLORS["grid"]),
            paper_bgcolor=THEME_COLORS["card_bg"],
            plot_bgcolor=THEME_COLORS["card_bg"],
            font=dict(family="Inter, sans-serif", size=12, color=THEME_COLORS["text"])
        )
        charts["feature_importance"] = json.dumps(fig_fi, cls=plotly.utils.PlotlyJSONEncoder)

    return charts
