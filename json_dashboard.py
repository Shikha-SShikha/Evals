import os
import streamlit as st
import pandas as pd
import plotly.express as px
import json
from datetime import datetime

@st.cache_data
def load_json_data(uploaded_file=None, default_path="merged_results.json"):
    if uploaded_file:
        data = json.load(uploaded_file)
    else:
        # Try to load shipped file for demos
        if os.path.exists(default_path):
            with open(default_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []

    records = []
    for item in data:
        record = {
            'timestamp': item['metadata']['timestamp'],
            'evaluations_run': ', '.join(item['metadata']['evaluations_run']),
            'jid': str(item['input_data']['jid']).upper(),
            'aid': item['input_data']['aid'],
            'aligned': item['input_data']['aligned'],
            'gold_aligned': item['input_data']['gold_aligned'],
            'title': item['input_data']['title'],
            'rationale': item['input_data'].get('rationale', 'N/A'),
            'source_file': item['source_file']
        }
        eval_results = item['evaluation_results']
        def convert_bool_to_pass_fail(value):
            if isinstance(value, bool):
                return "Pass" if value else "Fail"
            if isinstance(value, str):
                lv = value.lower()
                if lv in ("true", "pass"): return "Pass"
                if lv in ("false", "fail"): return "Fail"
            return value

        for eval_type, result in eval_results.items():
            if eval_type == 'decision_accuracy':
                record[f'eval_{eval_type}'] = convert_bool_to_pass_fail(result)
            elif isinstance(result, dict):
                if 'grounded' in result:
                    record[f'eval_{eval_type}'] = convert_bool_to_pass_fail(result['grounded'])
                    if 'reason' in result:
                        record[f'eval_{eval_type}_reason'] = result['reason']
                elif 'Eval_Status' in result:
                    record[f'eval_{eval_type}'] = convert_bool_to_pass_fail(result['Eval_Status'])
                    if 'which_one_executed' in result:
                        record[f'eval_{eval_type}_which_one_executed'] = result['which_one_executed']
                    if 'reason' in result:
                        record[f'eval_{eval_type}_reason'] = result['reason']
                elif 'negation_pass' in result:
                    record[f'eval_{eval_type}'] = convert_bool_to_pass_fail(result['negation_pass'])
                    if 'which_one_executed' in result:
                        record[f'eval_{eval_type}_which_one_executed'] = result['which_one_executed']
                    if 'reason' in result:
                        record[f'eval_{eval_type}_reason'] = result['reason']
                else:
                    for key, value in result.items():
                        record[f'eval_{eval_type}_{key}'] = convert_bool_to_pass_fail(value)
            else:
                record[f'eval_{eval_type}'] = convert_bool_to_pass_fail(result)

        records.append(record)

    return pd.DataFrame(records)


def convert_bool_to_pass_fail(value):
    """Convert boolean values to Pass/Fail"""
    if isinstance(value, bool):
        return "Pass" if value else "Fail"
    elif isinstance(value, str):
        lower_value = value.lower()
        if lower_value == 'true':
            return "Pass"
        elif lower_value == 'false':
            return "Fail"
        elif lower_value == 'pass' or lower_value == 'fail':
            return value.title() # Ensure "Pass" or "Fail" capitalization
    return value

st.set_page_config(page_title="JSON Evaluation Dashboard", layout="wide")

# --- Header ---
st.title("Evals Dashboard")
st.markdown("Comprehensive visualization of manuscript evaluation results")

# --- Sidebar filters ---
st.sidebar.header("Data Upload & Filters")
uploaded_file = st.sidebar.file_uploader("Upload JSON File", type=["json"])

try:
    df = load_json_data(uploaded_file)
    
    if df.empty:
        st.warning("No data loaded. Please upload a JSON file with evaluation results.")
        st.stop()
    
    # Filters
    journal_filter = st.sidebar.selectbox("Journal ID", ["All"] + sorted(df["jid"].unique().tolist()))
    if journal_filter != "All":
        df = df[df["jid"] == journal_filter]
    
    alignment_filter = st.sidebar.selectbox("Alignment Status", ["All", "Aligned", "Not Aligned"])
    if alignment_filter == "Aligned":
        df = df[df["aligned"] == True]
    elif alignment_filter == "Not Aligned":
        df = df[df["aligned"] == False]
    
    
    # --- Main Data Table ---
    st.subheader("Evaluation Results Overview")
    
    # Prepare display DataFrame
    display_df = df.copy()
    
    # Identify all columns that should be styled as Pass/Fail
    # These are the 'eval_' columns (excluding specific ones) and 'aligned', 'gold_aligned'
    columns_to_style_pass_fail_original = [
        col for col in display_df.columns 
        if col.startswith('eval_') and 
           not any(exclude_word in col for exclude_word in ['reason', 'which_one_executed'])
    ]
    # Add 'aligned' and 'gold_aligned' if they are present in the DataFrame
    if 'aligned' in display_df.columns:
        columns_to_style_pass_fail_original.append('aligned')
    if 'gold_aligned' in display_df.columns:
        columns_to_style_pass_fail_original.append('gold_aligned')

    # Select columns for display
    columns_to_remove = ['aligned', 'gold_aligned']
    
    # Filter out eval_ columns that contain 'reason' or 'which_one_is_executed'
    eval_cols_to_keep = [
        col for col in display_df.columns 
        if col.startswith('eval_') and 
           not any(exclude_word in col for exclude_word in ['reason', 'which_one_executed'])
    ]
    
    # Combine base columns with filtered eval columns, excluding specified columns
    display_columns = ['jid', 'aid'] + eval_cols_to_keep
    display_columns = [col for col in display_columns if col not in columns_to_remove]
    display_columns = [col for col in display_columns if col in display_df.columns]

    # Rename columns for display in Title Case
    display_df_renamed = display_df[display_columns].rename(columns={
        col: col.replace('eval_', '').replace('_', ' ').title() if col.startswith('eval_') else col.title()
        for col in display_columns
    })

    # Create a set of renamed column names that should be styled for the highlight function
    renamed_columns_to_style = {
        col.replace('eval_', '').replace('_', ' ').title() if col.startswith('eval_') else col.title()
        for col in columns_to_style_pass_fail_original
    }

    # Define highlight function
    def highlight_pass_fail(row):
        styles = [''] * len(row)
        for i, col_name in enumerate(row.index):
            if col_name in renamed_columns_to_style:
                if row[col_name] == "Pass":
                    styles[i] = 'background-color: #255C32; color: white' # Darker green
                elif row[col_name] == "Fail":
                    styles[i] = 'background-color: #893A42; color: white' # Darker red
        return styles

    # Rename columns for display in Title Case
    display_df_renamed = display_df[display_columns].rename(columns={
        col: col.replace('eval_', '').replace('_', ' ').title() if col.startswith('eval_') else col.title()
        for col in display_columns
    })
    
    st.dataframe(
        display_df_renamed.style.apply(highlight_pass_fail, axis=1),
        use_container_width=True,
        height=500
    )
    
    # --- Detailed Individual Records ---
    st.subheader("Individual Evaluation Details")
    
    # Record selector
    record_options = [f"{row['jid']} - {row['aid']} - {row['title'][:50]}..." 
                     for idx, row in df.iterrows()]
    
    if record_options:
        selected_record = st.selectbox("Select a record to view details:", record_options)
        selected_idx = record_options.index(selected_record)
        selected_row = df.iloc[selected_idx]
        
        # Display detailed information
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Basic Information:**")
            st.write(f"- **Journal ID:** {selected_row['jid']}")
            st.write(f"- **Article ID:** {selected_row['aid']}")
            st.write(f"- **Title:** {selected_row['title']}")
            st.write(f"- **Timestamp:** {selected_row['timestamp']}")
            st.write(f"- **Evaluations Run:** {selected_row['evaluations_run']}")
            st.write(f"- **Source File:** {selected_row['source_file']}")
                
        with col2:
            st.write("**Alignment Status:**")
            aligned_status = "Pass" if selected_row['aligned'] else "Fail"
            gold_aligned_status = "Pass" if selected_row['gold_aligned'] else "Fail"
            
            if aligned_status == "Pass":
                st.success(f"Aligned: {aligned_status}")
            else:
                st.error(f"Aligned: {aligned_status}")
                
            if gold_aligned_status == "Pass":
                st.success(f"Gold Aligned: {gold_aligned_status}")
            else:
                st.error(f"Gold Aligned: {gold_aligned_status}")
        
            # Rationale from Input Data
            st.write("**Rationale:**")
            st.write(selected_row['rationale'])

        # Evaluation Results
        st.write("**Evaluation Results:**")
        eval_cols = [
            col for col in selected_row.index 
            if col.startswith('eval_') and 'which_one_executed' not in col
        ]
        if eval_cols:
            eval_data = []
            for col in eval_cols:
                eval_name = col.replace('eval_', '').replace('_', ' ').title()
                value = selected_row[col]
                # Apply convert_bool_to_pass_fail to all eval_ columns to ensure consistent Pass/Fail display
                status = convert_bool_to_pass_fail(value)
                eval_data.append({'Evaluation': eval_name, 'Result': status})
            
            eval_df = pd.DataFrame(eval_data)
            
            def highlight_eval_results(row):
                styles = [''] * len(row)
                if row['Result'] == "Pass":
                    styles[1] = 'background-color: #255C32; color: white' # Darker green
                elif row['Result'] == "Fail":
                    styles[1] = 'background-color: #893A42; color: white' # Darker red
                return styles
            
            st.dataframe(
                eval_df.style.apply(highlight_eval_results, axis=1),
                use_container_width=True,
                hide_index=True
            )
    
    # --- Charts ---
    st.subheader("Visualization Charts")
    
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        # Alignment distribution
        if 'aligned' in df.columns:
            alignment_counts = df['aligned'].value_counts()
            alignment_labels = ['Aligned' if x else 'Not Aligned' for x in alignment_counts.index]
            
            fig1 = px.pie(
                values=alignment_counts.values,
                names=alignment_labels,
                title="Alignment Distribution",
                color_discrete_map={'Aligned': '#255C32', 'Not Aligned': '#893A42'} # Darker colors
            )
            st.plotly_chart(fig1, use_container_width=True)
    
    with chart_col2:
        # Journal distribution
        journal_counts = df['jid'].value_counts()
        fig2 = px.bar(
            x=journal_counts.index,
            y=journal_counts.values,
            title="Manuscripts per Journal",
            labels={'x': 'Journal ID', 'y': 'Count'}
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # Evaluation success rates
    st.subheader("Evaluation Success Rates")
    eval_columns = [col for col in df.columns if col.startswith('eval_') and df[col].dtype == 'bool']
    
    if eval_columns:
        success_rates = []
        for col in eval_columns:
            eval_name = col.replace('eval_', '').replace('_', ' ').title()
            success_rate = (df[col].sum() / len(df)) * 100
            success_rates.append({'Evaluation': eval_name, 'Success Rate (%)': success_rate})
        
        if success_rates:
            success_df = pd.DataFrame(success_rates)
            fig3 = px.bar(
                success_df,
                x='Evaluation',
                y='Success Rate (%)',
                title="Evaluation Pass Rates",
                text='Success Rate (%)',
                color='Success Rate (%)',
                color_continuous_scale='RdYlGn'
            )
            fig3.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig3.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig3, use_container_width=True)
    
    # --- Summary Statistics ---
    st.subheader("Summary Statistics")
    
    summary_col1, summary_col2, summary_col3 = st.columns(3)
    
    with summary_col1:
        st.write("**Dataset Overview:**")
        st.write(f"- Total Records: {len(df)}")
        st.write(f"- Unique Journals: {df['jid'].nunique()}")
        st.write(f"- Date Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    with summary_col2:
        st.write("**Alignment Statistics:**")
        if 'aligned' in df.columns:
            aligned_pct = (df['aligned'].sum() / len(df)) * 100
            st.write(f"- Aligned: {aligned_pct:.1f}%")
            st.write(f"- Not Aligned: {100-aligned_pct:.1f}%")
        
        if 'gold_aligned' in df.columns:
            gold_aligned_pct = (df['gold_aligned'].sum() / len(df)) * 100
            st.write(f"- Gold Standard Aligned: {gold_aligned_pct:.1f}%")
    
    with summary_col3:
        st.write("**Evaluation Coverage:**")
        total_evals = len([col for col in df.columns if col.startswith('eval_')])
        st.write(f"- Total Evaluation Types: {total_evals}")
        if eval_columns:
            avg_success = sum((df[col].sum() / len(df)) * 100 for col in eval_columns) / len(eval_columns)
            st.write(f"- Average Success Rate: {avg_success:.1f}%")

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.write("Please ensure your JSON file matches the expected format.")
