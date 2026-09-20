"""
Rule-Based Early Intervention Engine for Engineering Students.
File: services/intervention_engine.py

Generates transparent, personalized recommendations tailored strictly to
the student's actual behavioral and academic metrics.
"""

def generate_interventions(student_data, predicted_category="Average", risk_level="LOW RISK"):
    """
    Evaluates individual student attributes against educational thresholds
    and prescribes targeted early academic interventions.
    
    Parameters:
    - student_data: dict-like object containing student metrics
    - predicted_category: 'High' | 'Average' | 'Low'
    - risk_level: 'HIGH RISK' | 'MEDIUM RISK' | 'LOW RISK'
    
    Returns:
    - list of dicts: [
        {
          "type": "Attendance" | "Study Habits" | "Backlog Remediation" | "Coursework" | "Technical" | "General",
          "priority": "High" | "Medium" | "Low",
          "trigger": str (the actual metric value triggering the rule),
          "recommendation": str,
          "action_plan": str
        }
      ]
    """
    interventions = []
    
    attendance = float(student_data.get("attendance_percentage", 80))
    study_hours = float(student_data.get("study_hours_per_day", 3))
    backlogs = int(student_data.get("backlogs", 0))
    assignment_avg = float(student_data.get("assignment_average", 70))
    dept = str(student_data.get("department", "")).strip()
    coding_score = float(student_data.get("coding_skill_score", 60))
    tech_score = float(student_data.get("technical_skill_score", 60))
    comm_score = float(student_data.get("communication_skill_score", 60))
    int1 = float(student_data.get("internal_exam_1", 60))
    int2 = float(student_data.get("internal_exam_2", 60))
    internal_avg = (int1 + int2) / 2.0
    
    is_tech_dept = any(t in dept for t in [
        "Computer Science", "Information Technology", "Artificial Intelligence", "Data Science"
    ])
    
    # 1. Attendance Intervention Rule
    if attendance < 75.0:
        priority = "High" if attendance < 65.0 else "Medium"
        interventions.append({
            "type": "Attendance Alert",
            "priority": priority,
            "trigger": f"Current Attendance: {attendance:.1f}% (< 75% regulatory requirement)",
            "recommendation": "Monitor attendance and encourage regular class participation.",
            "action_plan": "Notify mentor; issue official attendance deficit warning; schedule weekly attendance check-in."
        })
        
    # 2. Daily Study Hours Rule
    if study_hours < 2.0:
        interventions.append({
            "type": "Study Habits",
            "priority": "Medium",
            "trigger": f"Dedicated Study Time: {study_hours:.1f} hrs/day (< 2.0 hrs)",
            "recommendation": "Create a structured daily study schedule.",
            "action_plan": "Faculty mentor to assist in establishing a 2-3 hour daily revision timetable with time-blocking."
        })
        
    # 3. Active Backlogs Rule
    if backlogs > 0:
        priority = "High" if backlogs >= 2 else "Medium"
        interventions.append({
            "type": "Backlog Remediation",
            "priority": priority,
            "trigger": f"Uncleared Subjects: {backlogs} active backlog(s)",
            "recommendation": "Create a backlog-clearing study plan and provide additional academic support.",
            "action_plan": "Assign peer tutor; organize weekend remedial doubt-clearing sessions; monitor previous question paper solving."
        })
        
    # 4. Assignment Performance Rule
    if assignment_avg < 60.0:
        interventions.append({
            "type": "Continuous Assessment",
            "priority": "Medium",
            "trigger": f"Assignment Average: {assignment_avg:.1f}/100 (< 60)",
            "recommendation": "Provide additional assignments and monitor submission quality.",
            "action_plan": "Review homework feedback; provide formative sample solutions; offer re-submission opportunity."
        })
        
    # 5. Coding Skill Rule for CS/IT/AI Departments
    if is_tech_dept and coding_score < 50.0:
        interventions.append({
            "type": "Coding Competency",
            "priority": "High",
            "trigger": f"Coding Assessment: {coding_score:.1f}/100 in {dept}",
            "recommendation": "Provide additional programming practice.",
            "action_plan": "Enroll in departmental competitive programming lab; assign 3 algorithmic exercises weekly on coding portal."
        })
        
    # 6. Technical Skill Rule
    if tech_score < 50.0:
        interventions.append({
            "type": "Technical & Practical Skills",
            "priority": "Medium",
            "trigger": f"Technical Score: {tech_score:.1f}/100 (< 50)",
            "recommendation": "Provide additional laboratory and technical practice.",
            "action_plan": "Mandate additional hands-on lab sessions with teaching assistant supervision."
        })
        
    # 7. Communication Skill Rule
    if comm_score < 50.0:
        interventions.append({
            "type": "Soft Skills & Communication",
            "priority": "Low",
            "trigger": f"Communication Score: {comm_score:.1f}/100 (< 50)",
            "recommendation": "Encourage communication and presentation practice.",
            "action_plan": "Incorporate mini-seminar presentations and group discussions into regular tutorial hours."
        })
        
    # 8. Internal Exam Deficit
    if internal_avg < 50.0:
        interventions.append({
            "type": "Internal Examination",
            "priority": "High",
            "trigger": f"Internal Assessment Average: {internal_avg:.1f}/100 (< 50)",
            "recommendation": "Conduct remedial exam coaching and intensive conceptual review.",
            "action_plan": "Target specific unit weaknesses identified in Test 1 & 2 before university examinations."
        })
        
    # If no interventions triggered, provide commendation / enrichment advice
    if not interventions:
        interventions.append({
            "type": "Academic Enrichment",
            "priority": "Low",
            "trigger": f"Predicted '{predicted_category}' with strong attendance ({attendance:.1f}%) and no backlogs.",
            "recommendation": "Maintain current high-performing routine and explore competitive certifications or research projects.",
            "action_plan": "Recommend participation in technical symposiums, hackathons, and IEEE/ACM paper writing."
        })
        
    return interventions
