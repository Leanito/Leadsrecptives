import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# --- Page Configuration ---
st.set_page_config(
    page_title="Dashboard de Análise de Leads",
    page_icon="📊",
    layout="wide"
)

# --- Title and Description ---
st.title("📊 Coffe & Results")
st.markdown("""
Compilação da planilha dos leads com validação e dashboards (Feito pelo estagiario mais bonito desse brasil)
""")

# --- File Uploader ---
st.sidebar.header("Upload da Planilha Excel")
uploaded_file = st.sidebar.file_uploader(
    "Arraste e solte sua planilha Excel aqui", type=["xlsx", "xls"]
)

df = None
if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.sidebar.success("Planilha carregada com sucesso!")
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar a planilha: {e}")

if df is not None:
    # --- Data Preprocessing ---

    # Function to normalize column names for robust matching
    def normalize_col_name(col_name):
        return col_name.strip().lower().replace(' ', '_').replace('-', '_').replace('/', '_').replace(':', '')

    # Define the target standardized names
    TARGET_STATUS_COL = 'status'
    TARGET_DATE_COL = 'data_da_conversao'
    TARGET_SEGMENT_COL = 'segmento_categoria'

    # Potential variations of the column names (normalized) that we expect from user's input
    potential_status_names = [normalize_col_name('Status'), normalize_col_name('status')]
    potential_date_names = [normalize_col_name('Data da conversão:'), normalize_col_name('Data da conversão'), normalize_col_name('data_da_conversao')]
    potential_segment_names = [normalize_col_name('Segmento/Categoria'), normalize_col_name('segmento_categoria')]

    # Find the actual column names in the DataFrame based on their normalized form
    found_status_col = None
    found_date_col = None
    found_segment_col = None

    current_normalized_cols_map = {normalize_col_name(col): col for col in df.columns}

    for norm_name, original_name in current_normalized_cols_map.items():
        if norm_name in potential_status_names:
            found_status_col = original_name
        if norm_name in potential_date_names:
            found_date_col = original_name
        if norm_name in potential_segment_names:
            found_segment_col = original_name

    # Create a renaming dictionary for the found columns
    rename_dict = {}
    if found_status_col and found_status_col != TARGET_STATUS_COL:
        rename_dict[found_status_col] = TARGET_STATUS_COL
    if found_date_col and found_date_col != TARGET_DATE_COL:
        rename_dict[found_date_col] = TARGET_DATE_COL
    if found_segment_col and found_segment_col != TARGET_SEGMENT_COL:
        rename_dict[found_segment_col] = TARGET_SEGMENT_COL

    if rename_dict:
        df.rename(columns=rename_dict, inplace=True)
        st.sidebar.markdown("Colunas renomeadas para padronização:")
        for original, new in rename_dict.items():
            st.sidebar.markdown(f"- `{original}` -> `{new}`")
    else:
        st.sidebar.markdown("As colunas essenciais já estão nos nomes padronizados ou não foram encontradas para renomeação explícita.")


    # Check if required columns exist after renaming
    required_columns_standardized = [TARGET_STATUS_COL, TARGET_DATE_COL, TARGET_SEGMENT_COL]
    if not all(col in df.columns for col in required_columns_standardized):
        missing_cols = [col for col in required_columns_standardized if col not in df.columns]
        st.error(
            f"Erro: As seguintes colunas essenciais não foram encontradas na sua planilha "
            f"após a tentativa de padronização: `{', '.join(missing_cols)}`."
            f"Por favor, verifique se os nomes das colunas estão corretos na sua planilha "
            f"(`Status`, `Data da conversão:`, `Segmento/Categoria` ou variações próximas)."
            f"Colunas encontradas no arquivo: {', '.join(df.columns)}"
        )
        df = None # Invalidate df if required columns are missing

if df is not None:
    # Convert 'data_da_conversao' to datetime
    if TARGET_DATE_COL in df.columns:
        df[TARGET_DATE_COL] = pd.to_datetime(
            df[TARGET_DATE_COL], errors='coerce'
        )
        df.dropna(subset=[TARGET_DATE_COL], inplace=True) # Remove rows with invalid dates
    else:
        st.error(
            f"Coluna '{TARGET_DATE_COL}' (Data da Conversão) não encontrada após padronização. "
            "Verifique o nome da coluna na sua planilha."
        )
        df = None # Invalidate df if essential column is missing

if df is not None:
    # Classify leads based on 'status' column
    def classify_lead(status_value):
        if pd.isna(status_value) or str(status_value).strip() == "" or str(status_value).strip().lower() == "sem qualificação":
            return "⚠️ Sem qualificação"
        elif str(status_value).strip().lower() == "válido":
            return "✅ Válido"
        elif str(status_value).strip().lower() == "inválido":
            return "❌ Inválido"
        else:
            return "⚠️ Sem qualificação" # Default for unclassified but not explicitly invalid/valid

    df['categoria_lead'] = df[TARGET_STATUS_COL].apply(classify_lead)

    # --- Filtering out "duplicado" and "teste" from Segmento/Categoria ---
    if TARGET_SEGMENT_COL in df.columns:
        initial_rows = len(df)
        # Convert segment column to string to handle various data types and potential NaN
        df[TARGET_SEGMENT_COL] = df[TARGET_SEGMENT_COL].astype(str)

        df = df[
            ~df[TARGET_SEGMENT_COL].str.contains('duplicado', case=False, na=False) &
            ~df[TARGET_SEGMENT_COL].str.contains('teste', case=False, na=False)
        ].copy() # Use .copy() to avoid SettingWithCopyWarning

        rows_removed = initial_rows - len(df)
        if rows_removed > 0:
            st.sidebar.info(f"Removidas {rows_removed} linhas de 'duplicado' ou 'teste' da coluna '{TARGET_SEGMENT_COL}'.")
        else:
            st.sidebar.info(f"Nenhuma linha de 'duplicado' ou 'teste' encontrada na coluna '{TARGET_SEGMENT_COL}'.")
    # --- End of Filter for Segmento/Categoria ---

    # --- Sidebar Filters ---
    st.sidebar.header("Filtros")

    # Date Range Filter
    min_date = df[TARGET_DATE_COL].min().date()
    max_date = df[TARGET_DATE_COL].max().date()

    date_range = st.sidebar.date_input(
        "Selecione o período de conversão",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if len(date_range) == 2:
        start_date, end_date = date_range
        # Filter DataFrame by selected date range
        df_filtered = df[
            (df[TARGET_DATE_COL].dt.date >= start_date)
            & (df[TARGET_DATE_COL].dt.date <= end_date)
        ].copy()
    else:
        st.sidebar.warning("Por favor, selecione um período de data válido.")
        df_filtered = df.copy() # Use full data if date range is incomplete

    # --- Main Content - Tabs ---
    tab1, tab2 = st.tabs(["Visão Geral e Métricas", "Detalhamento por Segmento"])

    with tab1:
        st.header("Visão Geral e Métricas Principais")
        st.markdown("---")

        total_leads = len(df_filtered)
        st.metric(label="Total de Leads (Período Selecionado)", value=total_leads)

        if total_leads > 0:
            # Lead Classification Counts and Percentages
            lead_counts = df_filtered['categoria_lead'].value_counts()
            lead_percentages = df_filtered['categoria_lead'].value_counts(normalize=True) * 100

            st.subheader("Classificação de Leads")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Contagem de Leads por Categoria**")
                st.dataframe(lead_counts.reset_index().rename(columns={'index': 'Categoria', 'categoria_lead': 'Contagem'}), hide_index=True)
            with col2:
                st.markdown("**Percentual de Leads por Categoria**")
                st.dataframe(lead_percentages.reset_index().rename(columns={'index': 'Categoria', 'categoria_lead': 'Percentual (%)'}), hide_index=True, column_config={"Percentual (%)": st.column_config.ProgressColumn("Percentual (%)", format="%.2f %%", min_value=0, max_value=100)})

            st.markdown("---")

            # Highlight "Sem qualificação" leads
            st.subheader("⚠️ Leads Sem Qualificação (Ação Prioritária)")
            unqualified_leads = df_filtered[
                df_filtered['categoria_lead'] == "⚠️ Sem qualificação"
            ]
            st.info(
                f"Temos **{len(unqualified_leads)}** leads sem qualificação no período selecionado. "
                "Revise esses leads para priorizar ações."
            )
            if not unqualified_leads.empty:
                # Select only relevant columns for display of unqualified leads
                display_cols_candidates = ['nome', 'e-mail', 'telefone', TARGET_SEGMENT_COL, TARGET_STATUS_COL, TARGET_DATE_COL, 'categoria_lead']
                display_cols = [col for col in display_cols_candidates if col in df_filtered.columns]
                st.dataframe(unqualified_leads[display_cols])
            else:
                st.markdown("Nenhum lead 'Sem qualificação' encontrado no período selecionado.")

            st.markdown("---")

            # Pie Chart for Lead Classification
            st.subheader("Distribuição de Leads por Categoria")
            fig_pie = px.pie(
                names=lead_counts.index,
                values=lead_counts.values,
                title="Distribuição das Categorias de Leads",
                color=lead_counts.index,
                color_discrete_map={
                    '✅ Válido': 'green',
                    '❌ Inválido': 'red',
                    '⚠️ Sem qualificação': 'orange'
                }
            )
            fig_pie.update_traces(textinfo='percent+label', pull=[0.1 if cat == '⚠️ Sem qualificação' else 0 for cat in lead_counts.index])
            st.plotly_chart(fig_pie, use_container_width=True)

        else:
            st.warning("Nenhum lead encontrado para o período selecionado.")

    with tab2:
        st.header("Análise Detalhada por Segmento/Categoria")
        st.markdown("---")

        if total_leads > 0 and TARGET_SEGMENT_COL in df_filtered.columns:
            # Analysis by Segment
            segment_analysis = df_filtered.groupby(TARGET_SEGMENT_COL)[
                'categoria_lead'
            ].value_counts().unstack(fill_value=0)

            # Calculate total for sorting and display
            segment_analysis['Total'] = segment_analysis.sum(axis=1) # Calculate total
            segment_analysis = segment_analysis.sort_values(
                by='Total', ascending=False
            )

            st.subheader("Contagem de Leads por Segmento e Categoria")
            # Display the DataFrame including the 'Total' column
            st.dataframe(segment_analysis)

            st.markdown("---")

            st.subheader("Distribuição de Leads por Segmento")
            # Bar chart for segments (still using original columns for visualization)
            # You might want to plot the 'Total' column as a separate bar if desired,
            # but for stacked bar, we usually show counts per category.
            fig_bar_segment = px.bar(
                segment_analysis.drop(columns='Total'), # Drop 'Total' for stacked bar, as it's sum of others
                x=segment_analysis.index,
                y=segment_analysis.drop(columns='Total').columns,
                title="Contagem de Leads por Segmento e Categoria",
                labels={'value': 'Número de Leads', TARGET_SEGMENT_COL: 'Segmento/Categoria'},
                color_discrete_map={
                    '✅ Válido': 'green',
                    '❌ Inválido': 'red',
                    '⚠️ Sem qualificação': 'orange'
                }
            )
            fig_bar_segment.update_layout(barmode='stack')
            st.plotly_chart(fig_bar_segment, use_container_width=True)

        elif total_leads > 0 and TARGET_SEGMENT_COL not in df_filtered.columns:
            st.warning(f"Coluna '{TARGET_SEGMENT_COL}' (Segmento/Categoria) não encontrada para análise por segmento.")
        else:
            st.warning("Nenhum lead encontrado para o período selecionado para análise por segmento.")

    # --- Export Processed Data ---
    st.sidebar.markdown("---")
    st.sidebar.header("Exportar Dados Processados")

    @st.cache_data
    def convert_df_to_excel(df_to_export):
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df_to_export.to_excel(writer, index=False, sheet_name='Leads Processados')
        writer.close()
        processed_data = output.getvalue()
        return processed_data

    if df is not None and not df_filtered.empty:
        excel_data = convert_df_to_excel(df_filtered)
        st.sidebar.download_button(
            label="Download Dados Processados (Excel)",
            data=excel_data,
            file_name="leads_processados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    elif df is not None and df_filtered.empty:
        st.sidebar.warning("Nenhum dado processado para download no período selecionado.")
    else:
        st.sidebar.info("Carregue uma planilha para exportar os dados processados.")

else:
    st.info("Por favor, carregue sua planilha Excel na barra lateral para começar a análise.")

st.markdown("---")
st.markdown("Made by Lean")