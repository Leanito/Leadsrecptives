import streamlit as st
import pandas as pd
import io
import plotly.express as px # Importando Plotly Express

def analisar_conversao_por_etapa_web(df, coluna_conversao='Tipo', valor_conversao='Cancelado-Lead-Respondeu', coluna_etapa='Etapa'):
    """
    Função de análise principal, adaptada para ser usada na aplicação web.
    Recebe um DataFrame e retorna os resultados da análise e uma mensagem de status.
    """
    if df.empty:
        return pd.DataFrame(), "A planilha está vazia ou não contém dados válidos para análise."

    # Verifica se as colunas essenciais existem no DataFrame original
    if coluna_conversao not in df.columns:
        return pd.DataFrame(), f"Erro: Coluna '{coluna_conversao}' não encontrada na sua planilha. Por favor, verifique o nome da coluna."
    
    # Filtra as linhas onde a conversão (resposta do lead) aconteceu
    leads_convertidos = df[df[coluna_conversao] == valor_conversao].copy()

    if leads_convertidos.empty:
        return pd.DataFrame(), f"Nenhum lead com '{valor_conversao}' encontrado na coluna '{coluna_conversao}'."

    # Verifica se a coluna de etapa existe antes de tentar usá-la para a análise detalhada
    if coluna_etapa not in leads_convertidos.columns: # Verificar em leads_convertidos, não no df original
        st.warning(f"Atenção: Coluna '{coluna_etapa}' não encontrada nos leads convertidos. A análise de conversão por etapa não será detalhada por etapa, apenas a lista de convertidos.")
        cols_para_exibir_sem_etapa = ['Data-hora', 'Deal ID', 'Whatsapp', 'Mensagem', 'Deal name']
        cols_existentes_sem_etapa = [col for col in cols_para_exibir_sem_etapa if col in leads_convertidos.columns]
        
        return leads_convertidos[cols_existentes_sem_etapa], f"Análise concluída. Coluna '{coluna_etapa}' não encontrada para detalhar por etapa."

    # Seleciona as colunas relevantes para exibição
    cols_para_exibir = ['Data-hora', 'Deal ID', 'Whatsapp', 'Mensagem', 'Deal name', coluna_etapa]
    cols_existentes = [col for col in cols_para_exibir if col in leads_convertidos.columns]
    
    resultados = leads_convertidos[cols_existentes].copy()
    resultados.rename(columns={coluna_etapa: 'Etapa de Conversão'}, inplace=True)
    
    mensagem_sucesso = "Análise de conversões concluída com sucesso!"
    
    return resultados, mensagem_sucesso

# --- Configuração e Layout da Aplicação Streamlit ---
st.set_page_config(
    page_title="Leanito analisa planilha!",
    page_icon="📊",
    layout="wide", # Usa a largura total da tela
    initial_sidebar_state="auto"
)

st.title("📊 Leanzinho analisa planilha! ")

st.markdown("""
    Sim, seu estagiario agora faz automação de por onde seus leads converteram! Faça o upload da sua planilha (CSV ou Excel)
    para visualizar em qual estágio da automação seus leads responderam e converteram.
    
    **Como funciona?**
    1. Certifique-se de que sua planilha contenha as colunas:
       - **'Tipo'**: Com o valor `'Cancelado-Lead-Respondeu'` para indicar uma conversão.
       - **'Etapa'**: Para identificar o estágio da automação (ex: 'Primeiro contato', 'Segundo contato').
    2. Colunas como 'Data-hora', 'Deal ID', 'Whatsapp', 'Mensagem' e 'Deal name' serão usadas para detalhes.
""")

# Área para upload de arquivo
st.subheader("Upload da sua Planilha")
uploaded_file = st.file_uploader("Arraste e solte ou clique para selecionar seu arquivo (.csv ou .xlsx)", type=["csv", "xlsx"])

if uploaded_file is not None:
    # Lendo o arquivo carregado
    try:
        if uploaded_file.name.endswith('.csv'):
            df_input = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.xlsx'):
            df_input = pd.read_excel(uploaded_file)
        
        st.success("✅ Planilha carregada com sucesso!")
        st.info(f"Nome do arquivo: **{uploaded_file.name}**")
        
        st.subheader("Prévia das Primeiras Linhas da Planilha")
        st.dataframe(df_input.head(), use_container_width=True)

        # Parâmetros para a análise (mantidos fixos com base na sua descrição)
        coluna_conversao_padrao = 'Tipo'
        valor_conversao_padrao = 'Cancelado-Lead-Respondeu'
        coluna_etapa_padrao = 'Etapa'

        # Executando a análise
        with st.spinner("Analisando as conversões..."):
            df_conversoes, mensagem_status = analisar_conversao_por_etapa_web(
                df_input,
                coluna_conversao=coluna_conversao_padrao,
                valor_conversao=valor_conversao_padrao,
                coluna_etapa=coluna_etapa_padrao
            )
        
        st.markdown(f"**Status da Análise:** _{mensagem_status}_")

        if not df_conversoes.empty:
            # Dividir a tela em colunas para organizar o dashboard
            col1, col2 = st.columns([1, 2]) # Uma coluna menor para o resumo e uma maior para os detalhes

            with col1:
                # O erro da imagem estava aqui: df_conversoes['Etapa de Conversão'] é a Series para contagem
                if 'Etapa de Conversão' in df_conversoes.columns:
                    st.subheader("📊 Resumo por Etapa")
                    
                    contagem_por_etapa = df_conversoes['Etapa de Conversão'].value_counts().sort_index()
                    total_conversoes = contagem_por_etapa.sum()

                    if total_conversoes > 0:
                        porcentagem_por_etapa = (contagem_por_etapa / total_conversoes * 100).round(2)
                        
                        # Cria o DataFrame de resumo com os nomes de coluna explícitos
                        df_resumo = pd.DataFrame({
                            'Etapa': contagem_por_etapa.index, # Garante que 'Etapa' é o nome da coluna das categorias
                            'Conversões': contagem_por_etapa.values,
                            'Percentual (%)': porcentagem_por_etapa.values
                        })
                        
                        st.dataframe(df_resumo, use_container_width=True)

                        st.markdown("---")
                        st.subheader("Gráfico de Distribuição")
                        # Usando Plotly Express para um gráfico de pizza interativo
                        fig = px.pie(
                            df_resumo,             # Passa o DataFrame df_resumo
                            values='Conversões',   # Coluna para os valores
                            names='Etapa',         # Coluna para os nomes/rótulos das fatias (AQUI ESTAVA O PONTO CRÍTICO)
                            title='Distribuição de Conversões por Etapa',
                            hole=0.4, # Para fazer um gráfico de rosca
                            hover_data=['Percentual (%)'] # Mostra a porcentagem ao passar o mouse
                        )
                        fig.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig, use_container_width=True) # Exibe o gráfico do Plotly
                    else:
                        st.warning("Não há conversões para calcular porcentagens.")
                else:
                    st.warning("Não foi possível gerar o resumo por etapa, pois a coluna 'Etapa de Conversão' não foi encontrada nos resultados.")

            with col2:
                st.subheader("✅ Detalhes de Leads Convertidos")
                st.dataframe(df_conversoes, use_container_width=True) # Tabela de detalhes ocupa a coluna maior

            # Opção para baixar os resultados (abaixo das colunas para melhor organização)
            st.markdown("---")
            st.subheader("📥 Baixar Relatórios")
            col_dl1, col_dl2 = st.columns(2)

            with col_dl1:
                csv_detalhado = df_conversoes.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Baixar Leads Detalhados (CSV)",
                    data=csv_detalhado,
                    file_name="leads_convertidos_detalhados.csv",
                    mime="text/csv",
                    help="Baixa a tabela completa dos leads que converteram."
                )
            
            if 'Etapa de Conversão' in df_conversoes.columns and total_conversoes > 0:
                with col_dl2:
                    csv_resumo = df_resumo.to_csv(index=False).encode('utf-8') # Salva o DataFrame com as porcentagens
                    st.download_button(
                        label="Baixar Resumo por Etapa (CSV)",
                        data=csv_resumo,
                        file_name="resumo_conversoes_por_etapa.csv",
                        mime="text/csv",
                        help="Baixa a contagem e porcentagem de conversões por cada etapa da automação."
                    )

    except pd.errors.EmptyDataError:
        st.error("❌ Erro: O arquivo carregado está vazio ou mal formatado. Por favor, verifique o conteúdo.")
    except Exception as e:
        st.error(f"❌ Ocorreu um erro ao processar o arquivo: {e}")
        st.warning("Por favor, verifique se o arquivo está no formato correto e se as colunas esperadas (como 'Tipo', 'Etapa', 'Data-hora', 'Deal ID', etc.) estão presentes e com os nomes exatos.")

st.markdown("---")
st.markdown("Desenvolvido pelo seu melhor estagiario Leanito")