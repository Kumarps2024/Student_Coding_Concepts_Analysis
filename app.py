import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Java Assessment Concept Analytics Dashboard",
    page_icon="☕",
    layout="wide"
)

# -------------------------------------------------------------
# 1. LOAD DATA & DEFINE ASSESSMENT TOPICS & ANSWER KEY
# -------------------------------------------------------------
@st.cache_data
def load_and_evaluate_data():
    file_path = "Comprehensive Java Technical Interview Assessment (100 Questions) (Responses).xlsx"
    df = pd.read_excel(file_path)

    # 10 Topics corresponding to Q1-Q10, Q11-Q20, ..., Q91-Q100
    topics = [
        "1. Strings and Text Processing",
        "2. Basic Input operations",
        "3. Control Flow — if-else, switch-case",
        "4. Loops — for, while, do-while",
        "5. String operations",
        "6. Classes, Objects and Constructors",
        "7. Inheritance and Polymorphism",
        "8. Encapsulation and Abstraction",
        "9. File I/O basics",
        "10. Collections Framework"
    ]

    # Identify metadata and question columns
    q_cols = [c for c in df.columns if c.strip().startswith('Q') and '.' in c[:5]]
    
    # Map each question to its topic (10 questions per topic)
    q_to_topic = {}
    for idx, q in enumerate(q_cols):
        topic_idx = min(idx // 10, len(topics) - 1)
        q_to_topic[q] = topics[topic_idx]

    # Derive the authoritative Answer Key from top scorers
    top_candidates = df[df['Score'] >= 90]
    answer_key = {q: top_candidates[q].mode()[0] for q in q_cols}

    # Binary evaluation: 1 if answer matches answer key, else 0
    eval_matrix = pd.DataFrame(index=df.index)
    for q in q_cols:
        eval_matrix[q] = (df[q] == answer_key[q]).astype(int)

    # Aggregate student score per concept (out of 10)
    student_concept_scores = pd.DataFrame(index=df.index)
    for topic in topics:
        topic_questions = [q for q in q_cols if q_to_topic[q] == topic]
        student_concept_scores[topic] = eval_matrix[topic_questions].sum(axis=1)

    # Concept accuracy as percentage (out of 10 questions = * 10)
    student_concept_pct = student_concept_scores * 10.0

    return df, q_cols, topics, q_to_topic, answer_key, eval_matrix, student_concept_pct

df, q_cols, topics, q_to_topic, answer_key, eval_matrix, student_concept_pct = load_and_evaluate_data()

# -------------------------------------------------------------
# 2. OVERALL COHORT METRICS
# -------------------------------------------------------------
st.title("☕ Java Assessment Diagnostic & Remedial Class Dashboard")
st.markdown("Pinpoint weak areas cohort-wide and drill down into individual student profiles for targeted extra classes.")

total_students = len(df)
avg_score = df['Score'].mean()
median_score = df['Score'].median()
pass_rate = (df['Score'] >= 50).sum() / total_students * 100

m1, m2, m3, m4 = st.columns(4)
m1.metric("Students Assessed", f"{total_students}")
m2.metric("Cohort Average Score", f"{avg_score:.1f} / 100")
m3.metric("Cohort Median Score", f"{median_score:.0f} / 100")
m4.metric("Pass Rate (≥ 50%)", f"{pass_rate:.1f}%")

st.markdown("---")

# -------------------------------------------------------------
# 3. CONCEPT-WISE COHORT OVERVIEW (INTERVENTION PRIORITIES)
# -------------------------------------------------------------
st.subheader("1. Cohort Performance by Concept (Needs for Extra Classes)")

cohort_concept_avg = student_concept_pct.mean().reset_index()
cohort_concept_avg.columns = ['Concept', 'Average Accuracy (%)']

def get_class_priority(score):
    if score < 60:
        return 'High Priority (Schedule Extra Class)'
    elif score < 75:
        return 'Medium Priority (Revision / Practice)'
    return 'Good (Well Understood)'

cohort_concept_avg['Intervention Status'] = cohort_concept_avg['Average Accuracy (%)'].apply(get_class_priority)
cohort_concept_avg = cohort_concept_avg.sort_values(by='Average Accuracy (%)', ascending=True)

col_chart, col_table = st.columns([3, 2])

with col_chart:
    fig_bar = px.bar(
        cohort_concept_avg,
        x='Average Accuracy (%)',
        y='Concept',
        orientation='h',
        color='Intervention Status',
        color_discrete_map={
            'High Priority (Schedule Extra Class)': '#EF553B',
            'Medium Priority (Revision / Practice)': '#FFA15A',
            'Good (Well Understood)': '#00CC96'
        },
        text=cohort_concept_avg['Average Accuracy (%)'].apply(lambda x: f"{x:.1f}%"),
        title="Cohort Mastery per Topic"
    )
    fig_bar.add_vline(x=60, line_dash="dash", line_color="#EF553B", annotation_text="Remedial Cutoff (60%)")
    fig_bar.update_layout(xaxis=dict(range=[0, 100]), height=440)
    st.plotly_chart(fig_bar, use_container_width=True)

with col_table:
    st.markdown("**Remedial Class Prioritization**")
    st.dataframe(
        cohort_concept_avg[['Concept', 'Average Accuracy (%)', 'Intervention Status']].style.format({
            'Average Accuracy (%)': '{:.1f}%'
        }),
        hide_index=True,
        use_container_width=True
    )

st.markdown("---")

# -------------------------------------------------------------
# 4. INDIVIDUAL STUDENT DIAGNOSTIC
# -------------------------------------------------------------
st.subheader("2. Individual Student Concept Diagnostic")

# Build student search dropdown
df['Student_Display'] = df['Student Name'] + " (" + df['Registration Number'].astype(str) + ") - Score: " + df['Score'].astype(str) + "/100"
student_names = df['Student_Display'].tolist()

# Default to A.Benarji Naidu if present to demonstrate fix
default_index = 0
for idx, name in enumerate(student_names):
    if "benarji" in name.lower():
        default_index = idx
        break

selected_display = st.selectbox("Select Student:", student_names, index=default_index)
student_idx = student_names.index(selected_display)
student_data = df.iloc[student_idx]

# Concept scores for selected student
student_scores_pct = student_concept_pct.iloc[student_idx]
student_summary_df = pd.DataFrame({
    'Concept': topics,
    'Score (out of 10)': [int(student_scores_pct[t] / 10) for t in topics],
    'Accuracy (%)': [student_scores_pct[t] for t in topics]
})

weak_topics = student_summary_df[student_summary_df['Accuracy (%)'] < 50]
moderate_topics = student_summary_df[(student_summary_df['Accuracy (%)'] >= 50) & (student_summary_df['Accuracy (%)'] < 70)]
strong_topics = student_summary_df[student_summary_df['Accuracy (%)'] >= 70]

col_left, col_right = st.columns([2, 3])

with col_left:
    st.markdown(f"### **Diagnostic Card: {student_data['Student Name']}**")
    st.write(f"**Registration Number:** `{student_data['Registration Number']}`")
    st.write(f"**Section / Year:** `{student_data.get('Section', 'A')}` | `{student_data.get('Year', '3rd Year')}`")
    
    score_val = student_data['Score']
    if score_val < 50:
        st.error(f"### Assessment Score: **{score_val}/100** (Needs Intervention)")
    elif score_val < 75:
        st.warning(f"### Assessment Score: **{score_val}/100** (Moderate)")
    else:
        st.success(f"### Assessment Score: **{score_val}/100** (Strong)")

    st.markdown("#### 🚨 Weak Concepts (< 50%):")
    if not weak_topics.empty:
        for _, r in weak_topics.iterrows():
            st.error(f"• **{r['Concept']}**: {r['Score (out of 10)']}/10 ({r['Accuracy (%)']:.0f}%)")
    else:
        st.success("None! Student scored ≥ 50% across all topics.")

    st.markdown("#### ⚠️ Moderate Concepts (50% – 69%):")
    if not moderate_topics.empty:
        for _, r in moderate_topics.iterrows():
            st.warning(f"• **{r['Concept']}**: {r['Score (out of 10)']}/10 ({r['Accuracy (%)']:.0f}%)")
    else:
        st.write("None.")

    st.markdown("#### ✅ Strong Concepts (≥ 70%):")
    if not strong_topics.empty:
        for _, r in strong_topics.iterrows():
            st.success(f"• **{r['Concept']}**: {r['Score (out of 10)']}/10 ({r['Accuracy (%)']:.0f}%)")
    else:
        st.info("No concepts above 70%. Needs fundamental review.")

with col_right:
    # Radar chart comparing Student vs Cohort Average
    radar_concepts = [t.split(". ", 1)[-1] for t in topics]
    student_vals = [student_scores_pct[t] for t in topics]
    cohort_vals = [cohort_concept_avg.set_index('Concept').loc[t, 'Average Accuracy (%)'] for t in topics]

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=student_vals + [student_vals[0]],
        theta=radar_concepts + [radar_concepts[0]],
        fill='toself',
        name=student_data['Student Name'],
        line_color='#EF553B' if score_val < 50 else '#636EFA'
    ))
    fig_radar.add_trace(go.Scatterpolar(
        r=cohort_vals + [cohort_vals[0]],
        theta=radar_concepts + [radar_concepts[0]],
        name='Cohort Average',
        line=dict(color='gray', dash='dash')
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title=f"Topic Skill Radar vs Cohort Average",
        height=450
    )
    st.plotly_chart(fig_radar, use_container_width=True)

# -------------------------------------------------------------
# 5. DETAILED QUESTION MISCONCEPTION LOG
# -------------------------------------------------------------
with st.expander("🔍 View Detailed Question-by-Question Answers for this Student"):
    q_table = []
    for idx, q in enumerate(q_cols):
        user_ans = student_data[q]
        correct_ans = answer_key[q]
        is_correct = "✅ Correct" if user_ans == correct_ans else "❌ Incorrect"
        q_table.append({
            "No.": f"Q{idx+1}",
            "Topic": q_to_topic[q],
            "Question": q.split("\n")[0][:80] + "...",
            "Student's Answer": str(user_ans)[:60],
            "Correct Answer": str(correct_ans)[:60],
            "Result": is_correct
        })
    st.dataframe(pd.DataFrame(q_table), use_container_width=True)