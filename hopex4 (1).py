import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import datetime
import matplotlib.pyplot as plt
import seaborn as sns
# ────────────────────────────────────────────────
#  Page config & basic styling
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="Data Wrangling and Visualization",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Немного кастомизации (опционально)
st.markdown("""
    <style>
    .stButton>button {width: 100%;}
    .reportview-container {background: #f8f9fa;}
    </style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
#  Session state initialization
# ────────────────────────────────────────────────
if "df_original" not in st.session_state:
    st.session_state.df_original = None
    st.session_state.df_working = None
    st.session_state.transform_log = []
    st.session_state.file_name = None

# ────────────────────────────────────────────────
#  Sidebar navigation
# ────────────────────────────────────────────────
st.sidebar.title("Data Wrangler")
page = st.sidebar.radio("Go to", [
    "A. Overview",
    "B. Cleaning tool",
    "C. Dashboards",
    "D. Export & Report"
])

if st.sidebar.button("🔄 Reset everything", type="primary"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ────────────────────────────────────────────────
#  Page A — Upload & Overview
# ────────────────────────────────────────────────
if page == "A. Overview":

    st.title("A. Overview")

    st.markdown(
        "Upload your file in one of the following formats: **CSV**, **Excel (.xlsx)** or **JSON**.\n"
        "For coursework requirements, datasets should ideally have ≥ 1000 rows and ≥ 8 columns."
    )

    # Выбор разделителя для CSV (показываем всегда)
    separator = st.selectbox(
        "CSV delimiter (separator)",
        options=[", (comma)", "; (semicolon)", "\\t (tab)", "| (pipe)", "space"],
        index=1,  # по умолчанию semicolon
        help="Choose the character that separates columns in your CSV file"
    )

    sep_map = {
        ", (comma)": ",",
        "; (semicolon)": ";",
        "\\t (tab)": "\t",
        "| (pipe)": "|",
        "space": " "
    }

    selected_sep = sep_map[separator]

    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["csv", "xlsx", "json"],
        accept_multiple_files=False,
        help="Supported formats: .csv, .xlsx, .json"
    )

    if uploaded_file is not None:
        ext = uploaded_file.name.split('.')[-1].lower()
        original_name = uploaded_file.name

        try:
            with st.spinner(f"Reading file {original_name} ..."):

                if ext == "csv":
                    encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
                    df = None
                    for enc in encodings:
                        try:
                            uploaded_file.seek(0)
                            df = pd.read_csv(
                                uploaded_file,
                                encoding=enc,
                                sep=selected_sep,
                                on_bad_lines='skip',
                                decimal=','
                            )
                            st.info(f"Successfully read with encoding: {enc}, separator: '{selected_sep}'")
                            break
                        except Exception:
                            continue

                    if df is None:
                        st.error("Failed to read CSV with any encoding and selected separator.")
                        st.stop()

                elif ext in ["xlsx", "xls"]:
                    df = pd.read_excel(uploaded_file, engine="openpyxl")

                elif ext == "json":
                    df = pd.read_json(uploaded_file)

                st.session_state.df_original = df.copy()
                st.session_state.df_working = df.copy()
                st.session_state.transform_log = []
                st.session_state.file_name = original_name

                st.success(f"File loaded: **{original_name}**  •  {df.shape[0]:,} rows × {df.shape[1]} columns")

        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

    if st.session_state.df_working is not None:
        df = st.session_state.df_working

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Rows", f"{df.shape[0]:,}")
        col2.metric("Columns", df.shape[1])
        col3.metric("Missing cells", df.isna().sum().sum())
        col4.metric("Full duplicates", df.duplicated().sum())

        tab1, tab2, tab3, tab4 = st.tabs(["Columns & Types", "Numeric Stats", "Missing Values", "Duplicates"])

        with tab1:
            st.subheader("Columns and types")
            overview = pd.DataFrame({
                "Column": df.columns,
                "Type": df.dtypes.astype(str),
                "Non-null": df.notna().sum(),
                "% Filled": (df.notna().mean() * 100).round(1)
            })
            st.dataframe(overview, use_container_width=True)

        with tab2:
            st.subheader("Numeric statistics")
            st.dataframe(df.describe().round(2), use_container_width=True)

        with tab3:
            st.subheader("Missing values")
            miss = pd.DataFrame({
                "Column": df.columns,
                "Missing": df.isna().sum(),
                "%": (df.isna().mean() * 100).round(2)
            }).sort_values("Missing", ascending=False)
            st.dataframe(miss[miss["Missing"] > 0], use_container_width=True)

        with tab4:
            st.subheader("Duplicates")
            st.metric("Full duplicates", df.duplicated().sum())

        if st.button("Show first 500 rows"):
            st.dataframe(df.head(500), use_container_width=True)

# ────────────────────────────────────────────────
#  Page B — Cleaning & Preparation
# ────────────────────────────────────────────────
elif page == "B. Cleaning tool":
    st.title("B. Cleaning & Preparation Studio")

    if st.session_state.get("df_working") is None:
        st.warning("Please upload a dataset first on the Upload & Overview page.")
    else:
        df = st.session_state.df_working
       
        def show_preview(before_df, after_df, action_name, highlight_col=None):
                st.markdown(f"### 📊 Preview: {action_name}")
                c1, c2 = st.columns(2)
                
                with c1:
                    st.markdown("**Before**")
                    st.metric("Rows", before_df.shape[0])
                    if highlight_col and highlight_col in before_df.columns:
                        st.dataframe(before_df[[highlight_col]].head(10), use_container_width=True)
                    else:
                        st.dataframe(before_df.head(10), use_container_width=True)
                
                with c2:
                    st.markdown("**After**")
                    st.metric("Rows", after_df.shape[0])
                    if highlight_col and highlight_col in after_df.columns:
                        st.dataframe(after_df[[highlight_col]].head(10), use_container_width=True)
                    else:
                        st.dataframe(after_df.head(10), use_container_width=True)
                
                st.divider()
        
        
        # Preview before/after helper
        def show_preview(before_df, after_df, action_name):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Before**")
                st.metric("Rows", before_df.shape[0])
                st.dataframe(before_df.head(3))
            with col2:
                st.markdown("**After**")
                st.metric("Rows", after_df.shape[0])
                st.dataframe(after_df.head(3))

        # Transformation log display
        with st.expander("Transformation Log (last 5 steps)", expanded=False):
            if st.session_state.transform_log:
                log_df = pd.DataFrame(st.session_state.transform_log[-5:])
                st.dataframe(log_df, use_container_width=True)
            else:
                st.info("No transformations yet.")
        st.subheader("Current dataset shape")
        st.metric("Rows × Columns", f"{df.shape[0]:,} × {df.shape[1]}")

        
                
                # 4.1 Missing Values (Null Handling)
                # 4.1 Missing Values (Null Handling)
        with st.expander("4.1 Missing Values (Null Handling)", expanded=True):
            st.subheader("Missing Values Handling")

            # Summary
            miss = pd.DataFrame({
                "Column": df.columns,
                "Missing Count": df.isna().sum(),
                "% Missing": (df.isna().mean() * 100).round(2)
            }).sort_values("Missing Count", ascending=False)

            st.dataframe(miss.style.bar(subset="% Missing", color="#ff9800"), use_container_width=True)

            action = st.radio(
                "Choose missing values action",
                ["Do nothing",
                 "Drop rows with missing in selected columns",
                 "Drop columns with > X% missing",
                 "Fill with constant value",
                 "Fill with statistic (mean / median / mode)",
                 "Forward fill / Backward fill"],
                index=0
            )

            if action != "Do nothing":
                numeric_cols = df.select_dtypes(include="number").columns.tolist()

                # Динамический выбор колонок
                if action == "Fill with statistic (mean / median / mode)":
                    stat_method = st.selectbox("Statistic", ["mean", "median", "mode"])
                    available_cols = numeric_cols if stat_method in ["mean", "median"] else df.columns.tolist()
                else:
                    available_cols = df.columns.tolist()

                selected_cols = st.multiselect("Select columns to apply action to", available_cols)

                # Threshold только для Drop columns
                threshold = None
                if action == "Drop columns with > X% missing":
                    threshold = st.slider("Threshold (%) - drop columns with missing above this value", 
                                        min_value=0, 
                                        max_value=100, 
                                        value=50, 
                                        step=1)

                if selected_cols and st.button("Apply action", type="primary"):
                    before_df = df.copy()
                    rows_before = before_df.shape[0]

                    if action == "Drop rows with missing in selected columns":
                        df = df.dropna(subset=selected_cols)
                        affected = rows_before - df.shape[0]
                        msg = f"Dropped {affected} rows with missing values"

                    elif action == "Drop columns with > X% missing":
                        cols_to_drop = [col for col in selected_cols if (df[col].isna().mean() * 100) > threshold]
                        df = df.drop(columns=cols_to_drop)
                        msg = f"Dropped {len(cols_to_drop)} columns with > {threshold}% missing"

                    elif action == "Fill with constant value":
                        const_value = st.text_input("Constant value", value="0")
                        try:
                            const_value = float(const_value) if const_value.replace('.','').replace('-','').isdigit() else const_value
                        except:
                            pass
                        df[selected_cols] = df[selected_cols].fillna(const_value)
                        msg = f"Filled missing values with constant '{const_value}'"

                    elif action == "Fill with statistic (mean / median / mode)":
                        filled_count = 0
                        for col in selected_cols:
                            if stat_method == "mean":
                                val = df[col].mean()
                            elif stat_method == "median":
                                val = df[col].median()
                            else:
                                val = df[col].mode()[0] if not df[col].mode().empty else 0
                            before_missing = df[col].isna().sum()
                            df[col] = df[col].fillna(val)
                            filled_count += before_missing
                        msg = f"Filled {filled_count} missing values using {stat_method}"

                    elif action == "Forward fill / Backward fill":
                        direction = st.radio("Direction", ["ffill (forward)", "bfill (backward)"])
                        method = direction.split()[0]
                        df[selected_cols] = df[selected_cols].fillna(method=method)
                        msg = f"Applied {method} fill"

                    st.session_state.df_working = df

                    st.session_state.transform_log.append({
                        "step": action.lower().replace(" ", "_").replace(">", "above"),
                        "columns": selected_cols,
                        "rows_before": rows_before,
                        "rows_after": df.shape[0],
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    })

                    # Простой Before/After preview
                    st.markdown(f"### 📊 Preview: {action}")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**Before**")
                        st.metric("Rows", before_df.shape[0])
                        st.dataframe(before_df.head(25), use_container_width=True)
                    with c2:
                        st.markdown("**After**")
                        st.metric("Rows", df.shape[0])
                        st.dataframe(df.head(25), use_container_width=True)

                    st.success(msg)


                



               # 4.2 Duplicates
        with st.expander("4.2 Duplicates", expanded=False):
            st.subheader("Duplicate Detection & Removal")

            # Full row duplicates
            full_dups = df.duplicated().sum()
            st.metric("Full row duplicates (completely identical rows)", full_dups)

            # Subset duplicates
            st.markdown("**Detect and remove duplicates by selected columns**")

            subset_cols = st.multiselect(
                "Select columns to check for duplicates",
                options=df.columns.tolist(),
                default=[],
                help="The more columns you select, the fewer duplicates will be found."
            )

            if subset_cols:
                subset_dups = df.duplicated(subset=subset_cols).sum()
                st.metric("Duplicates found using selected columns", subset_dups)

                if subset_dups > 0:
                    before_df = df.copy()

                    keep = st.radio("Which duplicate to keep?", ["first", "last"], index=0)

                    if len(subset_cols) == 1:
                        st.warning("⚠️ You selected only 1 column. This may remove a large number of rows.")

                    if st.button(f"Remove duplicates (keep {keep})", type="primary"):
                        df = df.drop_duplicates(subset=subset_cols, keep=keep)
                        removed = before_df.shape[0] - df.shape[0]

                        st.session_state.df_working = df

                        st.session_state.transform_log.append({
                            "step": "remove_duplicates",
                            "subset": subset_cols,
                            "keep": keep,
                            "rows_before": before_df.shape[0],
                            "rows_after": df.shape[0],
                            "duplicates_removed": removed,
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        })

                        # Показываем Before / After
                        st.markdown(f"### 📊 Preview: Remove duplicates")
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("**Before**")
                            st.metric("Rows", before_df.shape[0])
                            st.dataframe(before_df.head(10), use_container_width=True)
                        with c2:
                            st.markdown("**After**")
                            st.metric("Rows", df.shape[0])
                            st.dataframe(df.head(10), use_container_width=True)

                        st.success(f"Removed {removed} duplicate rows")
                        # st.rerun()  ← Убрали, чтобы превью осталось видимым

            # Show duplicate groups
            if st.button("Show duplicate groups (first 10 rows)"):
                if subset_cols:
                    dups_df = df[df.duplicated(subset=subset_cols, keep=False)].head(10)
                else:
                    dups_df = df[df.duplicated(keep=False)].head(10)
                
                if not dups_df.empty:
                    st.dataframe(dups_df, use_container_width=True)
                else:
                    st.info("No duplicates found with current selection.")

            st.caption("💡 Tip: Selecting more columns = fewer duplicates will be removed.")

       
        
        # 4.3 Data Types & Parsing
        with st.expander("4.3 Data Types & Parsing", expanded=False):
            st.subheader("Change column type")

            # Сначала выбираем желаемый тип
            desired_type = st.selectbox(
                "Desired type",
                ["numeric", "categorical", "datetime"],
                index=0
            )

            # Динамически фильтруем доступные колонки в зависимости от типа
            if desired_type == "numeric":
                available_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
                help_text = "Только текстовые столбцы (object/category) — будут очищены от $, запятых и пробелов"
            elif desired_type == "categorical":
                available_cols = df.columns.tolist()
                help_text = "Любой столбец → преобразуется в category (экономит память)"
            elif desired_type == "datetime":
                available_cols = df.columns.tolist()
                help_text = "Любой столбец → пытаемся распарсить как дату"

            col_to_change = st.selectbox(
                "Select column to convert",
                options=available_cols,
                index=0 if available_cols else None,
                help=help_text
            )

            # Если колонка выбрана — показываем действия
            if col_to_change:
                if desired_type == "numeric":
                    if st.button("Convert to numeric (clean dirty strings)", type="primary"):
                        try:
                            # Очистка типичных "грязных" символов
                            cleaned = df[col_to_change].astype(str).replace(
                                r'[\$,€£¥ ]', '', regex=True  # $, €, £, ¥, пробелы
                            ).str.replace(',', '.', regex=False)  # запятая → точка для десятичных

                            df[col_to_change] = pd.to_numeric(cleaned, errors='coerce')
                            invalid_count = df[col_to_change].isna().sum()

                            st.session_state.df_working = df
                            st.session_state.transform_log.append({
                                "step": "convert_to_numeric",
                                "column": col_to_change,
                                "invalid_values": invalid_count,
                                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                            })

                            st.success(f"Converted to numeric. Invalid values → NaN: {invalid_count}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Conversion failed: {str(e)}")

                elif desired_type == "categorical":
                    if st.button("Convert to categorical", type="primary"):
                        try:
                            df[col_to_change] = df[col_to_change].astype("category")
                            st.session_state.df_working = df
                            st.session_state.transform_log.append({
                                "step": "convert_to_categorical",
                                "column": col_to_change,
                                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                            })
                            st.success(f"Converted '{col_to_change}' to categorical")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Conversion failed: {str(e)}")

                elif desired_type == "datetime":
                    date_format = st.text_input(
                        "Datetime format (optional, e.g. %Y-%m-%d or %d/%m/%Y)",
                        value="",
                        help="Оставьте пустым для автоматического распознавания"
                    )
                    if st.button("Convert to datetime", type="primary"):
                        try:
                            df[col_to_change] = pd.to_datetime(
                                df[col_to_change],
                                format=date_format if date_format else None,
                                errors='coerce'
                            )
                            invalid_count = df[col_to_change].isna().sum()
                            st.session_state.df_working = df
                            st.session_state.transform_log.append({
                                "step": "convert_to_datetime",
                                "column": col_to_change,
                                "format_used": date_format or "auto",
                                "invalid_dates": invalid_count,
                                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                            })
                            st.success(f"Converted to datetime. Invalid dates → NaN: {invalid_count}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Conversion failed: {str(e)}")




               # 4.4 Categorical Data Tools
                # 4.4 Categorical Data Tools
        with st.expander("4.4 Categorical Data Tools", expanded=False):
            st.subheader("Categorical Data Tools")

            # Общий выбор колонки для большинства операций
            cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
            if not cat_cols:
                st.warning("No categorical columns found in the dataset.")
                st.stop()

            selected_cat_col = st.selectbox(
                "Select categorical column (for Standardization, Rare grouping, One-hot)",
                options=cat_cols,
                key="main_cat_col"
            )

            st.markdown(f"**Current selected column:** `{selected_cat_col}`")

            # 1. Standardization
            st.markdown("**1. Standardization** (trim, lower, title case)")
            std_action = st.radio("Choose action", ["Trim whitespace", "Lower case", "Title case"], horizontal=True)

            if st.button("Apply standardization", type="primary"):
                before_df = df.copy()
                if std_action == "Trim whitespace":
                    df[selected_cat_col] = df[selected_cat_col].str.strip()
                elif std_action == "Lower case":
                    df[selected_cat_col] = df[selected_cat_col].str.lower()
                elif std_action == "Title case":
                    df[selected_cat_col] = df[selected_cat_col].str.title()

                st.session_state.df_working = df
                st.session_state.transform_log.append({
                    "step": "standardize_categorical",
                    "column": selected_cat_col,
                    "action": std_action,
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                show_preview(before_df, df, "Standardization")
                st.success(f"Applied {std_action} to '{selected_cat_col}'")
                st.rerun()

            # 2. Rare category grouping
            st.markdown("**2. Group rare categories into 'Other'**")
            min_freq = st.slider("Minimum frequency (below this → 'Other')", 1, 100, 10)
            if st.button("Group rare categories into 'Other'", type="primary"):
                before_df = df.copy()
                counts = df[selected_cat_col].value_counts()
                rare = counts[counts < min_freq].index
                df[selected_cat_col] = df[selected_cat_col].replace(rare, "Other")

                st.session_state.df_working = df
                st.session_state.transform_log.append({
                    "step": "group_rare_categories",
                    "column": selected_cat_col,
                    "min_freq": min_freq,
                    "rare_categories": len(rare),
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                show_preview(before_df, df, "Rare grouping")
                st.success(f"Grouped {len(rare)} rare categories into 'Other'")
                st.rerun()

            # 3. Value Mapping — отдельный выбор колонки
            st.markdown("**3. Value mapping / replacement**")
            mapping_col = st.selectbox(
                "Select column for mapping",
                options=cat_cols,
                key="mapping_col_select"
            )

            mapping_input = st.text_area(
                "Enter mapping (old_value:new_value, one per line)",
                value="old_value1:new_value1\nold_value2:new_value2",
                height=100
            )

            if mapping_input and st.button("Apply mapping", type="primary"):
                before_df = df.copy()
                mapping_dict = {}
                for line in mapping_input.strip().split("\n"):
                    if ":" in line:
                        old, new = line.split(":", 1)
                        mapping_dict[old.strip()] = new.strip()

                df[mapping_col] = df[mapping_col].replace(mapping_dict)
                changed = (before_df[mapping_col] != df[mapping_col]).sum()

                st.session_state.df_working = df
                st.session_state.transform_log.append({
                    "step": "value_mapping",
                    "column": mapping_col,
                    "mapping": mapping_dict,
                    "changed_values": changed,
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                show_preview(before_df, df, "Value mapping")
                st.success(f"Applied mapping to '{mapping_col}'. Changed {changed} values.")
                st.rerun()

           
           # 4. One-hot encoding
                            
            st.markdown("**4. One-hot encoding (optional)**")
            st.warning("⚠️ This will permanently delete the original column and add multiple new columns.")

            if st.button("One-hot encode selected column", type="primary"):
                before_df = df.copy()
                one_hot = pd.get_dummies(df[selected_cat_col], prefix=selected_cat_col, prefix_sep="_")
                df = pd.concat([df.drop(columns=[selected_cat_col]), one_hot], axis=1)

                st.session_state.df_working = df
                st.session_state.transform_log.append({
                    "step": "one_hot_encoding",
                    "column": selected_cat_col,
                    "new_columns": list(one_hot.columns),
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                show_preview(before_df, df, "One-hot encoding")
                st.success(f"One-hot encoded '{selected_cat_col}'. Original column deleted. Added {len(one_hot.columns)} new columns.")
                st.rerun()




                        # 4.5 Numeric Cleaning (Outliers)
                        
        with st.expander("4.5 Numeric Cleaning (Outliers)", expanded=False):
            st.subheader("Outlier Detection & Handling")

            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

            if not numeric_cols:
                st.warning("No numeric columns found in the dataset.")
            else:
                col_for_outliers = st.selectbox("Select numeric column for outlier handling", numeric_cols)

                method = st.radio("Outlier detection method", ["IQR Method (recommended)", "Z-Score"], horizontal=True)

                if method == "IQR Method (recommended)":
                    q1 = df[col_for_outliers].quantile(0.25)
                    q3 = df[col_for_outliers].quantile(0.75)
                    iqr = q3 - q1
                    lower = q1 - 1.5 * iqr
                    upper = q3 + 1.5 * iqr
                    outliers_count = ((df[col_for_outliers] < lower) | (df[col_for_outliers] > upper)).sum()
                    st.metric("Outliers detected (IQR)", outliers_count)
                    st.info(f"Lower bound: {lower:.2f} | Upper bound: {upper:.2f}")
                else:
                    mean = df[col_for_outliers].mean()
                    std = df[col_for_outliers].std()
                    z = np.abs((df[col_for_outliers] - mean) / std)
                    outliers_count = (z > 3).sum()
                    st.metric("Outliers detected (Z-Score > 3)", outliers_count)

                action = st.radio("Action for outliers", 
                                ["Do nothing", 
                                 "Cap (Winsorize) at bounds", 
                                 "Remove outlier rows"], 
                                horizontal=True)

                if action != "Do nothing" and st.button("Apply outlier handling", type="primary"):
                    before_df = df.copy()
                    rows_before = before_df.shape[0]

                    if action == "Cap (Winsorize) at bounds":
                        if method == "IQR Method (recommended)":
                            df[col_for_outliers] = df[col_for_outliers].clip(lower=lower, upper=upper)
                        else:
                            df[col_for_outliers] = df[col_for_outliers].clip(lower=mean-3*std, upper=mean+3*std)
                        st.success(f"Outliers capped in column '{col_for_outliers}'. {outliers_count} values adjusted.")
                    else:  # Remove outlier rows
                        if method == "IQR Method (recommended)":
                            df = df[(df[col_for_outliers] >= lower) & (df[col_for_outliers] <= upper)]
                        else:
                            df = df[z <= 3]
                        removed = rows_before - df.shape[0]
                        st.success(f"Removed {removed} outlier rows from column '{col_for_outliers}'.")

                    st.session_state.df_working = df

                    st.session_state.transform_log.append({
                        "step": "outlier_handling",
                        "column": col_for_outliers,
                        "method": method,
                        "action": action,
                        "outliers_affected": outliers_count,
                        "rows_before": rows_before,
                        "rows_after": df.shape[0],
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    })

                    st.metric("Rows before", rows_before)
                    st.metric("Rows after", df.shape[0])
                    st.rerun()

        
                
                # 4.6 Normalization / Scaling
                # 4.6 Normalization / Scaling
        with st.expander("4.6 Normalization / Scaling", expanded=False):
            st.subheader("Normalization and Scaling")

            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

            if not numeric_cols:
                st.warning("No numeric columns available for scaling.")
            else:
                scaling_method = st.radio("Scaling method", 
                                        ["Min-Max Scaling (0 to 1)", 
                                         "Z-Score Standardization"], 
                                        horizontal=True)

                cols_to_scale = st.multiselect(
                    "Select numeric columns to scale",
                    options=numeric_cols,
                    default=numeric_cols[:min(3, len(numeric_cols))]
                )

                if cols_to_scale:
                    if st.button("Apply scaling", type="primary"):
                        before_df = df.copy()

                        if scaling_method == "Min-Max Scaling (0 to 1)":
                            for col in cols_to_scale:
                                min_val = df[col].min()
                                max_val = df[col].max()
                                if max_val > min_val:
                                    df[col] = (df[col] - min_val) / (max_val - min_val)
                            success_msg = f"Min-Max scaling applied to {len(cols_to_scale)} columns"
                        else:
                            for col in cols_to_scale:
                                mean = df[col].mean()
                                std = df[col].std()
                                if std > 0:
                                    df[col] = (df[col] - mean) / std
                            success_msg = f"Z-Score standardization applied to {len(cols_to_scale)} columns"

                        st.session_state.df_working = df

                        st.session_state.transform_log.append({
                            "step": "scaling",
                            "method": scaling_method,
                            "columns": cols_to_scale,
                            "rows_before": before_df.shape[0],
                            "rows_after": df.shape[0],
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        })

                        # Показываем Before / After Statistics БЕЗ rerun
                        st.markdown("### 📊 Before / After Statistics")

                        stats_before = before_df[cols_to_scale].describe().round(4)
                        stats_after = df[cols_to_scale].describe().round(4)

                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Before Scaling**")
                            st.dataframe(stats_before, use_container_width=True)
                        with col2:
                            st.markdown("**After Scaling**")
                            st.dataframe(stats_after, use_container_width=True)

                        st.success(success_msg)

                    # Если scaling уже был применён ранее — показываем статистику
                    elif st.session_state.get("last_scaling_cols") == cols_to_scale:
                        st.markdown("### 📊 Before / After Statistics (last scaling)")
                        # Здесь можно добавить сохранение before_df, но для простоты показываем текущую статистику

       
        # 4.7 Column Operations
               
        with st.expander("4.7 Column Operations", expanded=False):
            st.subheader("Column Operations")

            operation = st.radio("Choose operation", 
                               ["Rename columns", 
                                "Drop columns", 
                                "Create new column (formula)", 
                                "Binning numeric column"],
                               horizontal=True)

            # 1. Rename columns
            if operation == "Rename columns":
                st.markdown("**Rename columns**")
                rename_dict = {}
                for col in df.columns:
                    new_name = st.text_input(f"Rename '{col}' to:", value=col, key=f"rename_{col}")
                    if new_name != col and new_name.strip() != "":
                        rename_dict[col] = new_name.strip()
                
                if rename_dict and st.button("Apply renaming", type="primary"):
                    before_df = df.copy()
                    df = df.rename(columns=rename_dict)
                    st.session_state.df_working = df
                    st.session_state.transform_log.append({
                        "step": "rename_columns",
                        "mapping": rename_dict,
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    st.success(f"Renamed {len(rename_dict)} columns")
                    st.rerun()

            # 2. Drop columns
            elif operation == "Drop columns":
                st.markdown("**Drop columns**")
                cols_to_drop = st.multiselect("Select columns to drop", options=df.columns.tolist())
                
                if cols_to_drop and st.button("Drop selected columns", type="primary"):
                    before_df = df.copy()
                    df = df.drop(columns=cols_to_drop)
                    st.session_state.df_working = df
                    st.session_state.transform_log.append({
                        "step": "drop_columns",
                        "columns": cols_to_drop,
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    st.success(f"Dropped {len(cols_to_drop)} columns")
                    st.rerun()

            # 3. Create new column with formula
            elif operation == "Create new column (formula)":
                st.markdown("**Create new column using formula**")
                
                new_col_name = st.text_input("New column name", value="new_column")

                formula = st.text_input(
                    "Formula (use column names)",
                    value="colA / colB",
                    help="Examples:\ncolA + colB\ncolA * 2\nlog(colA)\ncolA - colB.mean()"
                )
                
                if st.button("Create new column", type="primary"):
                    try:
                        before_df = df.copy()
                        df[new_col_name] = df.eval(formula)
                        
                        st.session_state.df_working = df
                        st.session_state.transform_log.append({
                            "step": "create_new_column",
                            "column": new_col_name,
                            "formula": formula,
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
                        st.success(f"Created new column '{new_col_name}'")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Formula error: {str(e)}")
                        st.info("Tip: Use column names exactly as they appear. For columns with spaces use backticks ` `.")

            # 4. Binning numeric column
            elif operation == "Binning numeric column":
                st.markdown("**Binning numeric column**")
                
                num_col = st.selectbox("Select numeric column to bin", 
                                     options=df.select_dtypes(include=["number"]).columns.tolist())
                
                bin_method = st.radio("Binning method", ["Equal width bins", "Quantile bins"])
                
                if bin_method == "Equal width bins":
                    n_bins = st.slider("Number of bins", 2, 20, 5)
                else:
                    n_bins = st.slider("Number of quantiles", 2, 10, 4)
                
                new_bin_col = st.text_input("Name for binned column", value=f"{num_col}_binned")
                
                if st.button("Apply binning", type="primary"):
                    before_df = df.copy()
                    
                    if bin_method == "Equal width bins":
                        df[new_bin_col] = pd.cut(df[num_col], bins=n_bins, labels=[f"Bin_{i}" for i in range(n_bins)])
                    else:
                        df[new_bin_col] = pd.qcut(df[num_col], q=n_bins, labels=[f"Q{i+1}" for i in range(n_bins)])
                    
                    st.session_state.df_working = df
                    st.session_state.transform_log.append({
                        "step": "binning",
                        "column": num_col,
                        "new_column": new_bin_col,
                        "method": bin_method,
                        "bins": n_bins,
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    st.success(f"Created binned column '{new_bin_col}' with {n_bins} bins")
                    st.rerun()

                 # 4.8 Data Validation Rules
        with st.expander("4.8 Data Validation Rules", expanded=False):
            st.subheader("Data Validation Rules")

            # Инициализация хранилища нарушений (если ещё нет)
            if "validation_results" not in st.session_state:
                st.session_state.validation_results = pd.DataFrame()

            validation_type = st.radio("Choose validation rule type", 
                                     ["Numeric range check", 
                                      "Allowed categories", 
                                      "Non-null constraint"],
                                     horizontal=True)

            # 1. Numeric range check
            if validation_type == "Numeric range check":
                numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
                col = st.selectbox("Select numeric column", numeric_cols)
                min_val = st.number_input("Minimum allowed value", value=float(df[col].min()))
                max_val = st.number_input("Maximum allowed value", value=float(df[col].max()))

                if st.button("Apply numeric range check", type="primary"):
                    violations = df[(df[col] < min_val) | (df[col] > max_val)].copy()
                    violations["Violation Type"] = f"{col} out of range ({min_val} - {max_val})"
                    st.session_state.validation_results = violations
                    st.success(f"Found {len(violations)} violations in '{col}'")

            # 2. Allowed categories
            elif validation_type == "Allowed categories":
                cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
                col = st.selectbox("Select categorical column", cat_cols)
                allowed = st.text_area("Allowed categories (one per line)", height=120)

                if st.button("Apply allowed categories check", type="primary"):
                    allowed_list = [x.strip() for x in allowed.strip().split("\n") if x.strip()]
                    violations = df[~df[col].isin(allowed_list)].copy()
                    violations["Violation Type"] = f"{col} not in allowed list"
                    st.session_state.validation_results = violations
                    st.success(f"Found {len(violations)} violations in '{col}'")

            # 3. Non-null constraint
            elif validation_type == "Non-null constraint":
                cols = st.multiselect("Select columns that must not be null", options=df.columns.tolist())

                if st.button("Apply non-null check", type="primary"):
                    violations = df[df[cols].isnull().any(axis=1)].copy()
                    violations["Violation Type"] = "Missing values in required columns"
                    st.session_state.validation_results = violations
                    st.success(f"Found {len(violations)} rows with missing values")

            # ====================== VIOLATIONS TABLE ======================
            st.divider()
            st.subheader("Violations Table")

            if st.session_state.validation_results.empty:
                st.info("No violations detected yet. Run a validation rule above.")
            else:
                st.dataframe(st.session_state.validation_results, use_container_width=True)
                # Кнопка скачивания нарушений
                csv_violations = st.session_state.validation_results.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Violations Table (CSV)",
                    data=csv_violations,
                    file_name="data_violations.csv",
                    mime="text/csv"
                )

            st.caption("This table shows all rows that violate the defined rules.")
elif page == "C. Dashboards":
    st.title("C. Dashboards Studio")
    
    if st.button("🔄 Upload Different File"):
        st.session_state.df_working = None
        st.session_state.file_name = None
        st.rerun()
    
    df_source = st.session_state.df_working.copy()
    filename = st.session_state.file_name
    
    # Dataset info
    st.write(f"**File:** {filename}")
    st.write(f"**Shape:** {df_source.shape[0]:,} rows × {df_source.shape[1]} columns")
    
    st.divider()
    
    st.subheader("🔽 Filter Data (Optional)")
    
    with st.expander("Apply Filters", expanded=False):
        filtered_df = df_source.copy()
        
        all_columns = df_source.columns.tolist()
        selected_filter_cols = st.multiselect(
            "Select columns to filter on",
            options=all_columns,
            default=[],
            help="Choose one or more columns to add filters for."
        )
        
        # Filtering
        for col in selected_filter_cols:
            st.markdown(f"**Filter: {col}**")
            col_dtype = df_source[col].dtype
            
            # Numeric column - range slider
            if pd.api.types.is_numeric_dtype(col_dtype):
                min_val = float(df_source[col].min())
                max_val = float(df_source[col].max())
                
                if min_val == max_val:
                    st.caption(f"Only one unique value: {min_val}")
                    continue
                
                filter_range = st.slider(
                    f"Range for {col}",
                    min_value=min_val,
                    max_value=max_val,
                    value=(min_val, max_val),
                    key=f"filter_{col}"
                )
                filtered_df = filtered_df[
                    filtered_df[col].between(filter_range[0], filter_range[1])
                ]
            
            # Categorical/Text column - multi-select
            else:
                unique_vals = df_source[col].dropna().unique().tolist()
                
                # Limiting for too many variables
                if len(unique_vals) > 100:
                    st.caption(f"⚠️ {col} has {len(unique_vals)} unique values. Showing top 100.")
                    unique_vals = unique_vals[:100]
                
                selected_vals = st.multiselect(
                    f"Values for {col}",
                    options=unique_vals,
                    default=unique_vals,
                    key=f"filter_values_{col}"
                )
                
                if selected_vals:
                    filtered_df = filtered_df[filtered_df[col].isin(selected_vals)]
                else:
                    st.warning(f"No values selected for {col} - no rows will match.")
                    filtered_df = filtered_df.iloc[0:0]  # Empty DataFrame
        
        # Metrics after filtering
        total_rows = len(df_source)
        remaining_rows = len(filtered_df)
        removed_rows = total_rows - remaining_rows
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Rows", f"{total_rows:,}")
        col2.metric("Rows After Filter", f"{remaining_rows:,}")
        col3.metric("Rows Removed", f"{removed_rows:,}", 
                    delta=f"-{removed_rows:,}" if removed_rows > 0 else "0",
                    delta_color="inverse")
        
        if remaining_rows == 0:
            st.error("⚠️ No rows match your filters. Please adjust.")
            st.stop()
    
    st.divider()
    
    # Charts
    st.subheader("📈 Choose Your Chart")
    
    chart_type = st.selectbox(
        "Chart Type",
        ["Histogram", "Box Plot", "Scatter Plot", "Line Chart (Time Series)", 
         "Grouped Bar Chart", "Correlation Heatmap"]
    )
    
    st.divider()
    
    # Chart rendering
    
    # 1. HISTOGRAM
    if chart_type == "Histogram":
        st.subheader("Histogram")
        
        numeric_cols = filtered_df.select_dtypes(include=[np.number]).columns.tolist()
        
        if not numeric_cols:
            st.error("No numeric columns available for histogram.")
        else:
            col = st.selectbox("Select Column", numeric_cols)
            bins = st.slider("Number of Bins", 5, 100, 30)
            color = st.color_picker("Bar Color", "#4C72B0")
            
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.hist(filtered_df[col].dropna(), bins=bins, color=color, 
                   edgecolor='black', alpha=0.7)
            ax.set_xlabel(col)
            ax.set_ylabel("Frequency")
            ax.set_title(f"Distribution of {col}")
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
            plt.close(fig)
    
    # 2. BOX PLOT
    elif chart_type == "Box Plot":
        st.subheader("Box Plot")
        
        numeric_cols = filtered_df.select_dtypes(include=[np.number]).columns.tolist()
        
        if not numeric_cols:
            st.error("No numeric columns available for box plot.")
        else:
            col = st.selectbox("Select Column", numeric_cols)
            color = st.color_picker("Box Color", "#55A868")
            
            fig, ax = plt.subplots(figsize=(10, 6))
            bp = ax.boxplot(filtered_df[col].dropna(), patch_artist=True)
            for patch in bp['boxes']:
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
            ax.set_ylabel(col)
            ax.set_title(f"Box Plot of {col}")
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
            plt.close(fig)
    
    # 3. SCATTER PLOT
    elif chart_type == "Scatter Plot":
        st.subheader("Scatter Plot")
        
        numeric_cols = filtered_df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = filtered_df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        if len(numeric_cols) < 2:
            st.error("Need at least 2 numeric columns for scatter plot.")
        else:
            x_col = st.selectbox("X Axis", numeric_cols)
            y_col = st.selectbox("Y Axis", numeric_cols, index=min(1, len(numeric_cols)-1))
            
            # Color by category option
            color_mode = st.radio(
                "Color Mode",
                ["Single Color", "Color by Category"],
                horizontal=True
            )
            
            if color_mode == "Single Color":
                color = st.color_picker("Point Color", "#C44E52")
                color_col = None
            else:
                if not cat_cols:
                    st.warning("No categorical columns found. Using single color.")
                    color = st.color_picker("Point Color", "#C44E52")
                    color_col = None
                else:
                    color_col = st.selectbox("Color by Category", cat_cols)
                    color = None
            
            alpha = st.slider("Opacity", 0.1, 1.0, 0.6)
            
            # Prepare data
            cols_needed = [x_col, y_col] + ([color_col] if color_col else [])
            plot_df = filtered_df[cols_needed].dropna()
            
            # Row limit for performance
            if len(plot_df) > 3000:
                plot_df = plot_df.sample(3000, random_state=42)
                st.info(f"Showing sample of 3000 rows (total: {len(filtered_df):,})")
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            if color_col is None:
                # Single color
                ax.scatter(plot_df[x_col], plot_df[y_col], color=color, 
                          alpha=alpha, s=20)
            else:
                # Color by category
                categories = plot_df[color_col].unique()
                # Use matplotlib's default color cycle
                colors = plt.cm.tab10(np.linspace(0, 1, len(categories)))
                
                for i, cat in enumerate(categories):
                    mask = plot_df[color_col] == cat
                    ax.scatter(
                        plot_df.loc[mask, x_col],
                        plot_df.loc[mask, y_col],
                        label=str(cat),
                        color=colors[i],
                        alpha=alpha,
                        s=20
                    )
                ax.legend(title=color_col, bbox_to_anchor=(1.05, 1), 
                         loc='upper left', fontsize=8)
            
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            ax.set_title(f"{x_col} vs {y_col}")
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
    
    # 4. LINE CHART
    elif chart_type == "Line Chart (Time Series)":
        st.subheader("Line Chart (Time Series)")
        
        # Find datetime columns
        datetime_cols = filtered_df.select_dtypes(include=['datetime64']).columns.tolist()
        numeric_cols = filtered_df.select_dtypes(include=[np.number]).columns.tolist()
        
        if not numeric_cols:
            st.error("No numeric columns available for line chart.")
        else:
            # Choose x-axis (prefer datetime columns)
            x_options = datetime_cols + filtered_df.columns.tolist()
            x_col = st.selectbox("X Axis (Time)", x_options)
            y_col = st.selectbox("Y Axis (Numeric)", numeric_cols)
            
            # Aggregation options
            agg_func = st.selectbox(
                "Aggregate Duplicate X Values",
                ["sum", "mean", "median", "count", "max", "min"],
                help="If multiple rows share the same X value, combine them using this method."
            )
            
            # Prepare data with aggregation
            plot_df = filtered_df[[x_col, y_col]].dropna()
            
            # Group by x_col and aggregate
            if plot_df[x_col].duplicated().any():
                plot_df = plot_df.groupby(x_col)[y_col].agg(agg_func).reset_index()
                st.caption(f"Data aggregated using {agg_func} for duplicate X values.")
            
            # Sort by x axis
            plot_df = plot_df.sort_values(x_col)
            
            # Row limit for performance
            if len(plot_df) > 3000:
                plot_df = plot_df.sample(3000, random_state=42).sort_values(x_col)
                st.info(f"Showing sample of 3000 points (total: {len(plot_df):,})")
            
            color = st.color_picker("Line Color", "#8172B2")
            show_markers = st.checkbox("Show Point Markers", value=False)
            
            fig, ax = plt.subplots(figsize=(10, 6))
            marker = 'o' if show_markers else None
            ax.plot(plot_df[x_col], plot_df[y_col], color=color, 
                   linewidth=1.5, marker=marker, markersize=3)
            ax.set_xlabel(x_col)
            ax.set_ylabel(f"{agg_func.capitalize()} of {y_col}")
            ax.set_title(f"{agg_func.capitalize()} of {y_col} over {x_col}")
            plt.xticks(rotation=45, ha='right')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
    
    # 5. GROUPED BAR CHART
    elif chart_type == "Grouped Bar Chart":
        st.subheader("Grouped Bar Chart")
        
        cat_cols = filtered_df.select_dtypes(include=['object', 'category']).columns.tolist()
        numeric_cols = filtered_df.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(cat_cols) < 2:
            st.error("Need at least 2 categorical columns for grouped bar chart.")
        elif not numeric_cols:
            st.error("No numeric columns available for bar values.")
        else:
            x_col = st.selectbox("X Axis (Main Category)", cat_cols)
            group_col = st.selectbox(
                "Group By (Color Groups)",
                [c for c in cat_cols if c != x_col]
            )
            y_col = st.selectbox("Value (Numeric)", numeric_cols)
            agg_func = st.selectbox("Aggregation", ["mean", "sum", "median", "count"])
            top_n = st.slider("Show Top N Categories", 3, 20, 6)
            
            # Aggregate data
            agg_df = filtered_df.groupby([x_col, group_col])[y_col].agg(agg_func).reset_index()
            
            # Get top categories
            top_cats = filtered_df[x_col].value_counts().nlargest(top_n).index.tolist()
            agg_df = agg_df[agg_df[x_col].isin(top_cats)]
            
            # Prepare for plotting
            groups = agg_df[group_col].unique()
            x_cats = agg_df[x_col].unique()
            x_positions = np.arange(len(x_cats))
            bar_width = 0.8 / max(len(groups), 1)
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            for i, grp in enumerate(groups):
                subset = agg_df[agg_df[group_col] == grp]
                values = [
                    subset[subset[x_col] == cat][y_col].values[0] 
                    if cat in subset[x_col].values else 0
                    for cat in x_cats
                ]
                ax.bar(
                    x_positions + i * bar_width,
                    values,
                    width=bar_width,
                    label=str(grp),
                    edgecolor='white',
                    linewidth=0.5
                )
            
            ax.set_xticks(x_positions + bar_width * (len(groups) - 1) / 2)
            ax.set_xticklabels([str(c) for c in x_cats], rotation=45, ha='right')
            ax.set_xlabel(x_col)
            ax.set_ylabel(f"{agg_func.capitalize()} of {y_col}")
            ax.set_title(f"{y_col} by {x_col} grouped by {group_col}")
            ax.legend(title=group_col)
            ax.grid(True, alpha=0.3, axis='y')
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
    
    # 6. CORRELATION HEATMAP
    elif chart_type == "Correlation Heatmap":
        st.subheader("Correlation Heatmap")
        
        numeric_df = filtered_df.select_dtypes(include=[np.number])
        
        if numeric_df.shape[1] < 2:
            st.error("Need at least 2 numeric columns for correlation heatmap.")
        else:
            # Let user select columns if too many
            if len(numeric_df.columns) > 15:
                selected_cols = st.multiselect(
                    "Select columns to include",
                    options=numeric_df.columns.tolist(),
                    default=numeric_df.columns.tolist()[:10]
                )
                if len(selected_cols) < 2:
                    st.warning("Select at least 2 columns.")
                    st.stop()
                numeric_df = numeric_df[selected_cols]
            
            # Calculate correlation
            corr = numeric_df.corr()
            
            # Color map selection
            cmap = st.selectbox(
                "Color Map",
                ["coolwarm", "viridis", "RdYlGn", "Blues", "YlOrRd"]
            )
            show_values = st.checkbox("Show Correlation Values", value=True)
            
            fig, ax = plt.subplots(figsize=(10, 8))
            mask = np.triu(np.ones_like(corr, dtype=bool))
            
            sns.heatmap(
                corr,
                mask=mask,
                annot=show_values,
                fmt='.2f',
                cmap=cmap,
                center=0,
                square=True,
                linewidths=0.5,
                cbar_kws={"shrink": 0.8},
                ax=ax
            )
            ax.set_title("Correlation Matrix")
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
    
    st.divider()
    
    # DATA PREVIEW (Filtered Data)
    with st.expander("📋 View Filtered Data"):
        st.dataframe(filtered_df.head(100), use_container_width=True)
        st.caption(f"Showing first 100 rows of {len(filtered_df):,} filtered rows")
        
elif page == "D. Export & Report":
    st.title("Export & Report")
    df = st.session_state.df_working
    filename = st.session_state.file_name or "data"  # ← Define filename FIRST
    
    # Check if data exists
    if df is None:
        st.warning("⚠️ No data loaded. Please upload data first (Upload page).")
    else:        # Reset button
        if st.button("🔄 Upload Different File", key="upload_reset_button"):
            st.session_state.df_working = None
            st.session_state.df_original = None
            st.session_state.file_name = None
            st.session_state.transform_log = []
            st.rerun()
        
        # Show basic info
        st.write(f"**File:** {filename}")
        st.write(f"**Shape:** {df.shape[0]:,} rows × {df.shape[1]} columns")
        
        # Preview
        with st.expander("🔍 Preview Data"):
            st.dataframe(df.head(100))
        
        st.divider()
        
        # Download section
        st.subheader("📥 Download Cleaned Data")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # CSV download
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download as CSV",
                data=csv_data,
                file_name=f"cleaned_{filename}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Excel download
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            buffer.seek(0)
            
            st.download_button(
                label="Download as Excel",
                data=buffer,
                file_name=f"cleaned_{filename}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with col3:
            json_data = df.to_json(orient="records", indent=2).encode('utf-8')
            st.download_button(
                label="Download JSON",
                data=json_data,
                file_name=f"cleaned_{filename}.json",
                mime="application/json",
    )
        st.divider()
        
        # Basic statistics
        st.subheader("📊 Summary Statistics")
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if numeric_cols:
            st.dataframe(df[numeric_cols].describe())
        else:
            st.info("No numeric columns found")
        
        # Show column info
        with st.expander("📋 Column Information"):
            col_info = pd.DataFrame({
                'Column': df.columns,
                'Type': df.dtypes.astype(str),
                'Missing': df.isnull().sum(),
                'Missing %': (df.isnull().sum() / len(df) * 100).round(1)
            })
            st.dataframe(col_info)