import streamlit as st
import pandas as pd
from io import BytesIO
from collections import defaultdict

st.set_page_config(page_title="CSV/Excel Merger", page_icon="📊", layout="wide")

st.title("📊 CSV & Excel File Merger")
st.markdown("Upload multiple CSV or Excel files to merge them into one.")

# Initialize session state
if 'uploaded_files_data' not in st.session_state:
    st.session_state.uploaded_files_data = {}
if 'column_groups' not in st.session_state:
    st.session_state.column_groups = {}
if 'selected_group' not in st.session_state:
    st.session_state.selected_group = None
if 'files_to_delete' not in st.session_state:
    st.session_state.files_to_delete = set()
if 'merge_ready' not in st.session_state:
    st.session_state.merge_ready = False


def read_file(uploaded_file):
    """Read CSV or Excel file and return DataFrame"""
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file)
        else:
            return None, f"Unsupported file format: {uploaded_file.name}"
        return df, None
    except Exception as e:
        return None, f"Error reading {uploaded_file.name}: {str(e)}"


def get_column_signature(columns):
    """Get a hashable signature for column names"""
    return tuple(sorted(columns))


def group_files_by_columns(files_data):
    """Group files by their column structure"""
    groups = defaultdict(list)
    for filename, df in files_data.items():
        signature = get_column_signature(df.columns.tolist())
        groups[signature].append(filename)
    return dict(groups)


def convert_df_to_csv(df):
    """Convert DataFrame to CSV bytes"""
    return df.to_csv(index=False).encode('utf-8')


def convert_df_to_excel(df):
    """Convert DataFrame to Excel bytes"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Merged Data')
    return output.getvalue()


# File Upload Section
st.header("1️⃣ Upload Files")
uploaded_files = st.file_uploader(
    "Choose CSV or Excel files",
    type=['csv', 'xlsx', 'xls'],
    accept_multiple_files=True,
    help="Upload multiple CSV or Excel files to merge"
)

if uploaded_files:
    # Process uploaded files
    st.session_state.uploaded_files_data = {}
    errors = []
    
    with st.spinner("Reading files..."):
        for file in uploaded_files:
            # Reset file pointer
            file.seek(0)
            df, error = read_file(file)
            if error:
                errors.append(error)
            else:
                st.session_state.uploaded_files_data[file.name] = df
    
    # Show errors if any
    if errors:
        st.error("⚠️ Some files could not be read:")
        for err in errors:
            st.warning(err)
    
    # Show successfully loaded files
    if st.session_state.uploaded_files_data:
        st.success(f"✅ Successfully loaded {len(st.session_state.uploaded_files_data)} file(s)")
        
        # Display file info
        st.header("2️⃣ File Analysis")
        
        # Group files by columns
        column_groups = group_files_by_columns(st.session_state.uploaded_files_data)
        st.session_state.column_groups = column_groups
        
        num_groups = len(column_groups)
        
        if num_groups == 1:
            # All files have same columns
            st.success("🎉 All files have the same column structure!")
            st.session_state.merge_ready = True
            st.session_state.selected_group = list(column_groups.keys())[0]
            
            # Show columns
            cols = list(list(column_groups.keys())[0])
            st.write("**Common Columns:**")
            st.write(", ".join(cols))
            
        else:
            # Multiple column structures found
            st.warning(f"⚠️ Found {num_groups} different column structures!")
            st.session_state.merge_ready = False
            
            st.header("3️⃣ Column Structure Groups")
            st.markdown("Files are grouped by their column structure. Please select which group to keep for merging.")
            
            # Display each group
            group_options = {}
            for idx, (signature, files) in enumerate(column_groups.items(), 1):
                cols = list(signature)
                group_name = f"Group {idx} ({len(files)} file(s))"
                group_options[group_name] = signature
                
                with st.expander(f"📁 {group_name}", expanded=True):
                    st.write("**Files in this group:**")
                    for f in files:
                        st.write(f"  - {f}")
                    st.write("**Columns:**")
                    st.code(", ".join(cols))
                    
                    # Show preview of first file in group
                    first_file = files[0]
                    st.write(f"**Preview of {first_file}:**")
                    st.dataframe(st.session_state.uploaded_files_data[first_file].head(3), use_container_width=True)
            
            # Let user select which group to keep
            st.header("4️⃣ Select Column Structure to Keep")
            selected_group_name = st.radio(
                "Choose which group of files to merge:",
                options=list(group_options.keys()),
                help="Files from other groups will be excluded from the merge"
            )
            
            if selected_group_name:
                st.session_state.selected_group = group_options[selected_group_name]
                
                # Show which files will be kept and which will be excluded
                selected_signature = st.session_state.selected_group
                kept_files = column_groups[selected_signature]
                excluded_files = []
                
                for sig, files in column_groups.items():
                    if sig != selected_signature:
                        excluded_files.extend(files)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.success(f"✅ Files to be merged ({len(kept_files)}):")
                    for f in kept_files:
                        st.write(f"  ✓ {f}")
                
                with col2:
                    if excluded_files:
                        st.error(f"❌ Files to be excluded ({len(excluded_files)}):")
                        for f in excluded_files:
                            st.write(f"  ✗ {f}")
                
                # Confirm button
                if st.button("✅ Confirm Selection & Proceed to Merge", type="primary"):
                    # Remove excluded files from data
                    for f in excluded_files:
                        if f in st.session_state.uploaded_files_data:
                            del st.session_state.uploaded_files_data[f]
                    
                    st.session_state.merge_ready = True
                    st.rerun()

# Merge Section
if st.session_state.merge_ready and st.session_state.uploaded_files_data:
    st.header("5️⃣ Merge Files")
    
    # Show files to be merged
    files_to_merge = list(st.session_state.uploaded_files_data.keys())
    st.write(f"**Files to merge:** {len(files_to_merge)}")
    
    with st.expander("View files to be merged"):
        for f in files_to_merge:
            df = st.session_state.uploaded_files_data[f]
            st.write(f"- {f} ({len(df)} rows)")
    
    # Merge all DataFrames
    all_dfs = list(st.session_state.uploaded_files_data.values())
    merged_df = pd.concat(all_dfs, ignore_index=True)
    
    st.success(f"✅ Merged {len(files_to_merge)} files into {len(merged_df)} total rows")
    
    # Show preview of merged data
    st.subheader("Preview of Merged Data")
    st.dataframe(merged_df.head(20), use_container_width=True)
    
    # Show statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Rows", len(merged_df))
    with col2:
        st.metric("Total Columns", len(merged_df.columns))
    with col3:
        st.metric("Files Merged", len(files_to_merge))
    
    # Download Section
    st.header("6️⃣ Download Merged File")
    
    output_format = st.radio(
        "Select output format:",
        options=["CSV", "Excel (.xlsx)"],
        horizontal=True
    )
    
    # File name input
    output_filename = st.text_input("Output filename (without extension):", value="merged_data")
    
    if output_format == "CSV":
        csv_data = convert_df_to_csv(merged_df)
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"{output_filename}.csv",
            mime="text/csv",
            type="primary"
        )
    else:
        excel_data = convert_df_to_excel(merged_df)
        st.download_button(
            label="📥 Download Excel",
            data=excel_data,
            file_name=f"{output_filename}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )

# Reset button
if st.session_state.uploaded_files_data:
    st.divider()
    if st.button("🔄 Reset & Start Over"):
        st.session_state.uploaded_files_data = {}
        st.session_state.column_groups = {}
        st.session_state.selected_group = None
        st.session_state.files_to_delete = set()
        st.session_state.merge_ready = False
        st.rerun()

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>CSV & Excel Merger Tool | Built with Streamlit</p>
</div>
""", unsafe_allow_html=True)
