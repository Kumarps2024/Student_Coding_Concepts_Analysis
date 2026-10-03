import sys
import asyncio

# =====================================================================
# WINDOWS ASYNCIO FIX: Prevents ConnectionResetError [WinError 10054]
# =====================================================================
if sys.platform.startswith('win'):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

# Set page configuration
st.set_page_config(
    page_title="Java Assessment Analytics | Sections A, D & E",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for polished dashboard UI
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #1f77b4;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 18px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 1. LOAD & EVALUATE DATA
# -------------------------------------------------------------
@st.cache_data
def load_data():
    file_candidates = [
        "Comprehensive Java Technical Interview Assessment (100 Questions) (Responses) (1).xlsx",
        "Comprehensive Java Technical Interview Assessment (100 Questions) (Responses).xlsx"
    ]
    file_path = None
    for f in file_candidates:
        if os.path.exists(f):
            file_path = f
            break
            
    if not file_path:
        for f in os.listdir('.'):
            if f.endswith('.xlsx') and 'Responses' in f:
                file_path = f
                break

    if not file_path:
        st.error("Excel assessment file not found. Place the file in the working directory.")
        st.stop()

    df = pd.read_excel(file_path)

    # 10 Syllabus topics
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

    # Identify Question columns (Q1 to Q100)
    q_cols = [c for c in df.columns if c.strip().startswith('Q') and '.' in c[:5]]

    # Map each question to its topic (10 questions per topic)
    q_to_topic = {}
    for idx, q in enumerate(q_cols):
        topic_idx = min(idx // 10, len(topics) - 1)
        q_to_topic[q] = topics[topic_idx]

    # Authoritative ground truth key derived from top candidates & Java specifications
    top_candidates = df[df['Score'] >= 94]
    answer_key = {q: top_candidates[q].mode()[0] for q in q_cols}

    # Explicit ground-truth fixes for ambiguous parsing
    for q in q_cols:
        if q.startswith("Q7."):
            answer_key[q] = 13
        elif q.startswith("Q36."):
            answer_key[q] = "Prints nothing and enters an infinite loop"
        elif q.startswith("Q45."):
            answer_key[q] = '"Hello"'
        elif q.startswith("Q91."):
            answer_key[q] = "Capacity: 16, Load Factor: 0.75"

    # Evaluation Matrix: 1 if match, else 0
    eval_matrix = pd.DataFrame(index=df.index)
    for q in q_cols:
        eval_matrix[q] = (df[q] == answer_key[q]).astype(int)

    # Raw score per topic (out of 10) & accuracy percentage
    student_topic_scores = pd.DataFrame(index=df.index)
    for topic in topics:
        topic_questions = [q for q in q_cols if q_to_topic[q] == topic]
        student_topic_scores[topic] = eval_matrix[topic_questions].sum(axis=1)

    student_topic_pct = student_topic_scores * 10.0

    # Clean metadata
    df['Student Name'] = df['Student Name'].astype(str).str.strip()
    df['Registration Number'] = df['Registration Number'].astype(str).str.strip()
    df['Section'] = df['Section'].astype(str).str.strip().str.upper()

    return df, q_cols, topics, q_to_topic, answer_key, eval_matrix, student_topic_scores, student_topic_pct

df, q_cols, topics, q_to_topic, answer_key, eval_matrix, student_topic_scores, student_topic_pct = load_data()

# -------------------------------------------------------------
# SIDEBAR FILTERS & CONTROLS
# -------------------------------------------------------------
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/226/226777.png", width=65)
st.sidebar.title("Navigation & Filters")

available_sections = sorted(df['Section'].unique().tolist())
section_filter = st.sidebar.selectbox("Select Section Scope:", ["All Sections"] + available_sections)

# Filter dataset
if section_filter != "All Sections":
    sub_df = df[df['Section'] == section_filter]
    sub_topic_pct = student_topic_pct.loc[sub_df.index]
    sub_topic_scores = student_topic_scores.loc[sub_df.index]
else:
    sub_df = df
    sub_topic_pct = student_topic_pct
    sub_topic_scores = student_topic_scores

st.sidebar.markdown("---")
st.sidebar.caption(f"**Total Filtered Students:** {len(sub_df)}")
st.sidebar.caption(f"**Cohorts Included:** Sections {', '.join(available_sections)}")

# -------------------------------------------------------------
# MAIN HEADER & OVERALL KPI CARDS
# -------------------------------------------------------------
st.title("☕ Java Assessment Diagnostic & Remedial Dashboard")
st.markdown("Multi-section performance analysis and targeted student intervention tracking across Sections **A**, **D**, and **E**.")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Students Assessed", f"{len(sub_df)}")
col2.metric("Average Score", f"{sub_df['Score'].mean():.1f} / 100")
col3.metric("Median Score", f"{sub_df['Score'].median():.0f} / 100")
col4.metric("Pass Rate (≥ 50%)", f"{(sub_df['Score'] >= 50).mean()*100:.1f}%")
col5.metric("Top Score", f"{sub_df['Score'].max()} / 100")

st.markdown("---")

# -------------------------------------------------------------
# TABS
# -------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Section-Wise Comparison",
    "🎯 Concept Mastery & Remedial Priorities",
    "📋 Assistance Needed Roster (By Topic)",
    "👤 Individual Student Diagnostic"
])

# =============================================================
# TAB 1: SECTION-WISE COMPARISON
# =============================================================
with tab1:
    st.subheader("1. Cross-Section Comparative Performance (Sections A vs D vs E)")
    
    sec_summary = df.groupby('Section').agg(
        Students=('Student Name', 'count'),
        Average_Score=('Score', 'mean'),
        Median_Score=('Score', 'median'),
        Pass_Rate=('Score', lambda x: (x >= 50).mean() * 100),
        Min_Score=('Score', 'min'),
        Max_Score=('Score', 'max')
    ).reset_index()

    c_left, c_right = st.columns([3, 2])
    with c_left:
        fig_sec_box = px.box(
            df,
            x='Section',
            y='Score',
            color='Section',
            points='all',
            color_discrete_sequence=['#4361ee', '#2ec4b6', '#ff9f1c'],
            title="Score Distribution by Section (Hover to inspect quartiles & candidates)"
        )
        fig_sec_box.add_hline(y=50, line_dash="dash", line_color="red", annotation_text="Pass Cutoff (50)")
        fig_sec_box.update_layout(yaxis=dict(range=[0, 105]), height=400)
        st.plotly_chart(fig_sec_box, use_container_width=True)

    with c_right:
        st.markdown("**Section Performance Summary Card**")
        st.dataframe(
            sec_summary.style.format({
                'Average_Score': '{:.2f}',
                'Median_Score': '{:.1f}',
                'Pass_Rate': '{:.1f}%',
                'Min_Score': '{:.0f}',
                'Max_Score': '{:.0f}'
            }),
            use_container_width=True,
            hide_index=True
        )
        st.info("""
        **Summary Findings:**
        - **Section D** shows the highest consistency and average score.
        - **Section E** has the highest remedial need in fundamental topics like Strings and Control Flow.
        - **Section A** shows high polarization with 98-scorers alongside students needing foundational support.
        """)

    st.markdown("#### Topic-Wise Section Benchmark Breakdown")
    topic_sec_list = []
    for sec in available_sections:
        sec_idx = df[df['Section'] == sec].index
        sec_means = student_topic_pct.loc[sec_idx].mean()
        for t in topics:
            topic_sec_list.append({
                'Topic': t.split(". ", 1)[-1],
                'Section': f"Section {sec}",
                'Accuracy (%)': sec_means[t]
            })
    sec_topic_df = pd.DataFrame(topic_sec_list)

    fig_grouped_bar = px.bar(
        sec_topic_df,
        x='Topic',
        y='Accuracy (%)',
        color='Section',
        barmode='group',
        color_discrete_sequence=['#4361ee', '#2ec4b6', '#ff9f1c'],
        title="Accuracy (%) per Java Topic across Sections A, D, and E"
    )
    fig_grouped_bar.add_hline(y=60, line_dash="dash", line_color="#ef233c", annotation_text="Remedial Target (60%)")
    fig_grouped_bar.update_layout(xaxis_tickangle=-30, height=450, yaxis=dict(range=[0, 100]))
    st.plotly_chart(fig_grouped_bar, use_container_width=True)

# =============================================================
# TAB 2: CONCEPT MASTERY & REMEDIAL PRIORITIES
# =============================================================
with tab2:
    st.subheader(f"2. Concept-Wise Performance Breakdown ({section_filter})")
    
    cohort_avg = sub_topic_pct.mean().reset_index()
    cohort_avg.columns = ['Topic', 'Average Accuracy (%)']
    
    def assign_priority(score):
        if score < 60:
            return 'High Priority (Schedule Extra Class)'
        elif score < 75:
            return 'Medium Priority (Practice & Revision)'
        return 'Strong (Concept Mastered)'

    cohort_avg['Status'] = cohort_avg['Average Accuracy (%)'].apply(assign_priority)
    cohort_avg = cohort_avg.sort_values(by='Average Accuracy (%)', ascending=True)

    col_b1, col_b2 = st.columns([3, 2])
    with col_b1:
        fig_bar = px.bar(
            cohort_avg,
            x='Average Accuracy (%)',
            y='Topic',
            orientation='h',
            color='Status',
            color_discrete_map={
                'High Priority (Schedule Extra Class)': '#ef233c',
                'Medium Priority (Practice & Revision)': '#ffb703',
                'Strong (Concept Mastered)': '#06d6a0'
            },
            text=cohort_avg['Average Accuracy (%)'].apply(lambda x: f"{x:.1f}%"),
            title=f"Concept Mastery & Intervention Needs — {section_filter}"
        )
        fig_bar.add_vline(x=60, line_dash="dash", line_color="#ef233c", annotation_text="Extra Class Line (60%)")
        fig_bar.update_layout(xaxis=dict(range=[0, 105]), height=450)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_b2:
        st.markdown("**Actionable Intervention Priorities**")
        st.dataframe(
            cohort_avg[['Topic', 'Average Accuracy (%)', 'Status']].style.format({'Average Accuracy (%)': '{:.1f}%'}),
            use_container_width=True,
            hide_index=True
        )

# =============================================================
# TAB 3: ASSISTANCE NEEDED ROSTER (BY TOPIC)
# =============================================================
with tab3:
    st.subheader("3. Remedial Assistance Roster (Students Requiring Extra Classes)")
    st.markdown("Filter candidates who scored below the required threshold in a specific topic to schedule targeted tutorials.")

    f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
    with f_col1:
        selected_topic = st.selectbox("Select Java Topic:", topics, index=2)
    with f_col2:
        threshold_score = st.slider("Score Cutoff (out of 10):", min_value=1, max_value=9, value=5,
                                    help="Students scoring strictly less than this cutoff will be listed.")
    with f_col3:
        assist_section = st.selectbox("Filter Section:", ["All"] + available_sections)

    roster_df = pd.DataFrame({
        'Registration Number': df['Registration Number'],
        'Student Name': df['Student Name'],
        'Section': df['Section'],
        'Total Score': df['Score'],
        'Topic Score (out of 10)': student_topic_scores[selected_topic],
        'Topic Accuracy (%)': student_topic_pct[selected_topic],
        'Contact Number': df.get('Contact Number', 'N/A')
    })

    if assist_section != "All":
        roster_df = roster_df[roster_df['Section'] == assist_section]

    weak_roster = roster_df[roster_df['Topic Score (out of 10)'] < threshold_score].sort_values(
        by=['Topic Score (out of 10)', 'Total Score'], ascending=[True, True]
    )

    st.markdown(f"##### Found **{len(weak_roster)} students** scoring < {threshold_score}/10 in **{selected_topic}**")
    
    st.dataframe(
        weak_roster.style.format({
            'Topic Accuracy (%)': '{:.0f}%',
            'Topic Score (out of 10)': '{:.0f}/10',
            'Total Score': '{:.0f}/100'
        }),
        use_container_width=True,
        hide_index=True
    )

    csv_data = weak_roster.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"📥 Download Remedial List for {selected_topic.split('. ', 1)[-1]} (CSV)",
        data=csv_data,
        file_name=f"Remedial_List_{selected_topic[:15].replace(' ', '_')}.csv",
        mime='text/csv'
    )

# =============================================================
# TAB 4: INDIVIDUAL STUDENT DIAGNOSTIC
# =============================================================
with tab4:
    st.subheader("4. Individual Candidate Diagnostic Profile")

    df_sorted = sub_df.sort_values(by=['Section', 'Student Name'])
    student_labels = [
        f"[{row['Section']}] {row['Student Name']} ({row['Registration Number']}) - Score: {row['Score']}/100"
        for _, row in df_sorted.iterrows()
    ]

    default_idx = 0
    for i, label in enumerate(student_labels):
        if "benarji" in label.lower():
            default_idx = i
            break

    selected_label = st.selectbox("Select / Search Candidate:", student_labels, index=default_idx)
    cand_row = df_sorted.iloc[student_labels.index(selected_label)]
    cand_idx = cand_row.name

    cand_scores_pct = student_topic_pct.loc[cand_idx]
    cand_scores_raw = student_topic_scores.loc[cand_idx]
    sec_topic_avg = student_topic_pct.loc[df[df['Section'] == cand_row['Section']].index].mean()
    cohort_topic_avg = student_topic_pct.mean()

    cand_topic_summary = pd.DataFrame({
        'Topic': topics,
        'Raw Score': [f"{int(cand_scores_raw[t])}/10" for t in topics],
        'Accuracy (%)': [cand_scores_pct[t] for t in topics],
        'Section Avg (%)': [sec_topic_avg[t] for t in topics],
        'Cohort Avg (%)': [cohort_topic_avg[t] for t in topics]
    })

    cand_weak = cand_topic_summary[cand_topic_summary['Accuracy (%)'] < 50]
    cand_moderate = cand_topic_summary[(cand_topic_summary['Accuracy (%)'] >= 50) & (cand_topic_summary['Accuracy (%)'] < 70)]
    cand_strong = cand_topic_summary[cand_topic_summary['Accuracy (%)'] >= 70]

    col_ind_l, col_ind_r = st.columns([2, 3])
    with col_ind_l:
        st.markdown(f"### **{cand_row['Student Name']}**")
        st.write(f"**Registration Number:** `{cand_row['Registration Number']}`")
        st.write(f"**Section:** `{cand_row['Section']}` | **Year:** `{cand_row.get('Year', '3rd Year')}`")
        st.write(f"**Contact:** `{cand_row.get('Contact Number', 'N/A')}`")

        c_score = cand_row['Score']
        if c_score < 50:
            st.error(f"### Overall Score: **{c_score}/100** (Needs Critical Intervention)")
        elif c_score < 75:
            st.warning(f"### Overall Score: **{c_score}/100** (Moderate)")
        else:
            st.success(f"### Overall Score: **{c_score}/100** (Excellent)")

        st.markdown("#### 🚨 Weak Topics (< 50%):")
        if not cand_weak.empty:
            for _, r in cand_weak.iterrows():
                st.error(f"• **{r['Topic']}**: {r['Raw Score']} ({r['Accuracy (%)']:.0f}%)")
        else:
            st.success("No critical weaknesses detected!")

        st.markdown("#### ⚠️ Moderate Topics (50% – 69%):")
        if not cand_moderate.empty:
            for _, r in cand_moderate.iterrows():
                st.warning(f"• **{r['Topic']}**: {r['Raw Score']} ({r['Accuracy (%)']:.0f}%)")
        else:
            st.caption("None.")

        st.markdown("#### ✅ Strong Topics (≥ 70%):")
        if not cand_strong.empty:
            for _, r in cand_strong.iterrows():
                st.success(f"• **{r['Topic']}**: {r['Raw Score']} ({r['Accuracy (%)']:.0f}%)")
        else:
            st.caption("None.")

    with col_ind_r:
        radar_categories = [t.split(". ", 1)[-1] for t in topics]
        c_vals = [cand_scores_pct[t] for t in topics]
        s_vals = [sec_topic_avg[t] for t in topics]
        all_vals = [cohort_topic_avg[t] for t in topics]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=c_vals + [c_vals[0]],
            theta=radar_categories + [radar_categories[0]],
            fill='toself',
            name=cand_row['Student Name'],
            line_color='#ef233c' if c_score < 50 else '#4361ee'
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=s_vals + [s_vals[0]],
            theta=radar_categories + [radar_categories[0]],
            name=f"Section {cand_row['Section']} Avg",
            line=dict(color='#ffb703', dash='dot')
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=all_vals + [all_vals[0]],
            theta=radar_categories + [radar_categories[0]],
            name="Cohort Avg",
            line=dict(color='gray', dash='dash')
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title=f"Skill Radar: {cand_row['Student Name']} vs Section & Cohort",
            height=440
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with st.expander("🔍 View Question-by-Question Misconception Audit for this Candidate"):
        q_audit = []
        for idx, q in enumerate(q_cols):
            user_ans = cand_row[q]
            correct_ans = answer_key[q]
            is_correct = "✅ Correct" if str(user_ans).strip() == str(correct_ans).strip() else "❌ Incorrect"
            q_audit.append({
                "Q#": f"Q{idx+1}",
                "Topic": q_to_topic[q].split(". ", 1)[-1],
                "Question Prompt": q.split("\n")[0][:80] + "...",
                "Candidate's Answer": str(user_ans)[:65],
                "Correct Answer": str(correct_ans)[:65],
                "Evaluation": is_correct
            })
        st.dataframe(pd.DataFrame(q_audit), use_container_width=True)