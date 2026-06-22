import streamlit as st
import math
import pandas as pd

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Portal de Projetos Fotovoltaicos",
    page_icon="⚡",
    layout="wide"
)

# Cabeçalho do Sistema
col_logo, col_title = st.columns([1, 8])
with col_logo:
    st.markdown("<h1>⚡</h1>", unsafe_allow_html=True)
with col_title:
    st.title("Dimensionamento e Propostas Fotovoltaicas")
    st.caption("Engenharia e Projetos - MS & RS")

st.markdown("---")

# ==========================================
# BARRA LATERAL (CONFIGURAÇÕES TÉCNICAS)
# ==========================================
st.sidebar.header("⚙️ Parâmetros de Engenharia")
st.sidebar.caption("Ajuste de acordo com a NDU 013 e dados locais.")

# O HSP padrão já está ajustado para a irradiação média de Campo Grande
hsp = st.sidebar.number_input("Irradiação Local (HSP)", min_value=3.0, max_value=7.0, value=5.2, step=0.1)
pr = st.sidebar.number_input("Performance Ratio (PR)", min_value=0.50, max_value=1.00, value=0.75, step=0.01)

st.sidebar.markdown("---")
st.sidebar.subheader("Especificações do Kit")
potencia_painel = st.sidebar.number_input("Potência do Módulo (W)", min_value=300, max_value=800, value=550, step=10)
tipo_inversor = st.sidebar.selectbox("Tecnologia", ["Inversor String", "Microinversor"])

# ==========================================
# ÁREA PRINCIPAL (DADOS DO CLIENTE E CONSUMO)
# ==========================================
st.subheader("👤 CADASTRO DO CLIENTE")

col1, col2 = st.columns(2)

with col1:
    nome_cliente = st.text_input("Nome do Cliente", placeholder="Ex: Fulano de Tal")
    endereço_cliente = st.text_input("Endereço do Cliente", placeholder="Ex: Rua das Flores, 123 - Campo Grande/MS")
    tipo_ligacao = st.selectbox("Padrão de Entrada (Energisa)", ["Monofásico", "Bifásico", "Trifásico"])
    custo_disponibilidade = {
        "Monofásico": 30,
        "Bifásico": 50,
        "Trifásico": 100
    }

    if tipo_ligacao:
        st.caption(f"Custo de Disponibilidade para clientes {tipo_ligacao}: {custo_disponibilidade[tipo_ligacao]} KWh por mês (conforme tabela Energisa MS), gerando um custo fixo mensal de aproxidamente {custo_disponibilidade[tipo_ligacao] * 0.88:.2f}. (considerando tarifa média de R$ 0,88 por kWh).")
    codigo_UC = st.text_input("Código da Unidade Consumidora (UC)", placeholder="Ex: 1234567890")

    




with col2:
    consumo_atual = st.number_input("Média Histórica Atual (kWh/mês)", min_value=0, value=0, step=50)
    consumo_alvo = consumo_atual  # Inicialmente, o consumo alvo é igual ao consumo atual 
    tipo_telhado = st.selectbox("Tipo de Telhado", ["Fibrocimento", "Cerâmico", "Metálico/Zinco", "Laje"])
    tensao_fornecimento = st.selectbox("Tensão de Fornecimento (V)", ["127V", "220V"])

# Variáveis base para os aumentos de carga, usadas mesmo quando a seção de análise não aparece.
consumo_arcond = 0
consumo_iluminacao = 0
consumo_eletrodomesticos = 0
consumo_climatizacao = 0
consumo_outro = 0
  
if consumo_atual > 0:
    st.markdown("---")
    st.subheader("📈 ANÁLISE DE CARGAS E PREVISÃO DE AUMENTOS")
    st.caption("Modifique ou adicione cargas somente se o cliente desejar incluir novos equipamentos, cada equipamento adicionado aumentará o consumo estimado e, consequentemente, a potência necessária do sistema fotovoltaico.")

# ==========================================
# ANÁLISE DE CARGAS E PREVISÃO DE AUMENTOS
# ==========================================

    with st.expander("💡 Previsão de Aumento de Carga", expanded=False):
        df_cargas = pd.DataFrame({
            # Potências médias típicas (W) baseadas em faixas usuais de INMETRO/PROCEL e fabricantes.
            "Descrição": [
                'Ar Condicionado 12k BTUs inverter',
                'Ar Condicionado 9k BTUs inverter',
                "Ar Condicionado 12k BTUs convencional",
                'Geladeira frost free',
                'Chuveiro elétrico',
                'Máquina de lavar roupa',
                'Micro-ondas',
                'Forno elétrico',
                'Air Fryer',
                'Televisão LED 50"',
                'Computador desktop',
                'Ventilador',
                'Iluminação LED (conjunto)',
                'Bomba de piscina',
                'Freezer horizontal'
            ],
            "Quantidade": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            "Consumo (Potência Média em kW)": [
                1.2, 0.9, 1.2, 0.5, 5.5, 0.5, 1.4, 2.0, 1.5, 0.1, 0.2, 0.08, 0.12, 0.75, 0.4
            ],
            "Horas de Uso por Dia": [8, 8, 8, 24, 0.3, 1, 0.3, 0.5, 0.5, 5, 6, 8, 5, 4, 24],
            "Dias de Uso por Mês": [22, 22, 22, 30, 30, 20, 25, 20, 20, 30, 26, 30, 30, 20, 30],
        })
        df_editado = st.data_editor(df_cargas, num_rows="dynamic", use_container_width=True, key="cargas_editor")

        # Garantir cálculo do consumo estimado mensal a partir dos campos editáveis
        if not df_editado.empty:
            df_editado["Descrição"] = df_editado["Descrição"].fillna("").astype(str)
            for col in ["Quantidade", "Consumo (Potência Média em kW)", "Horas de Uso por Dia", "Dias de Uso por Mês"]:
                df_editado[col] = pd.to_numeric(df_editado[col], errors="coerce").fillna(0)
            df_editado["Consumo Estimado (kWh/mês)"] = (
                df_editado["Quantidade"]
                * df_editado["Consumo (Potência Média em kW)"]
                * df_editado["Horas de Uso por Dia"]
                * df_editado["Dias de Uso por Mês"]
            )

            # Cálculo de consumo por tipo de carga a partir da tabela interativa
            for idx, row in df_editado.iterrows():
                descricao = str(row.get("Descrição", "")).strip().lower()
                if not descricao:
                    continue
                consumo_item = row["Consumo Estimado (kWh/mês)"]

                # Categorizar por tipo de carga
                if "ar condicionado" in descricao or "ar cond" in descricao:
                    if "inverter" in descricao:
                        consumo_arcond += consumo_item * 0.6  # Considera eficiência de 40% para inverter
                    else:
                        consumo_arcond += consumo_item
                elif "iluminação" in descricao or "luz" in descricao:
                    consumo_iluminacao += consumo_item
                elif "bomba" in descricao or "ventilador" in descricao:
                    consumo_climatizacao += consumo_item
                elif any(x in descricao for x in ["geladeira", "freezer", "micro-ondas", "forno", "máquina", "chuveiro", "air fryer", "televisão", "computador"]):
                    consumo_eletrodomesticos += consumo_item
                else:
                    consumo_outro += consumo_item

        # insira as métricas por tipo de carga
        total_aumentos_preview = (
            consumo_arcond
            + consumo_iluminacao
            + consumo_climatizacao
            + consumo_eletrodomesticos
            + consumo_outro
        )

        if total_aumentos_preview > 0:
            st.markdown("#### 📌 Aumento de Carga por Tipo")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Ar Condicionado", f"{consumo_arcond:.1f} kWh/mês")
            c2.metric("Iluminação", f"{consumo_iluminacao:.1f} kWh/mês")
            c3.metric("Climatização", f"{consumo_climatizacao:.1f} kWh/mês")
            c4.metric("Eletrodomésticos", f"{consumo_eletrodomesticos:.1f} kWh/mês")
            c5.metric("Outros", f"{consumo_outro:.1f} kWh/mês")
            st.metric("Total de Aumento Previsto", f"{total_aumentos_preview:.1f} kWh/mês")


# ==========================================
# MOTOR DE CÁLCULO
# ==========================================

# Soma total de aumentos
total_aumentos_cargas = consumo_arcond + consumo_iluminacao + consumo_climatizacao + consumo_eletrodomesticos + consumo_outro

# Consumo alvo final
consumo_alvo = consumo_atual + total_aumentos_cargas

if consumo_alvo > 0:
    # Engenharia base
    potencia_gerador = consumo_alvo / (30 * hsp * pr)
    potencia_painel_kw = potencia_painel / 1000
    qtd_paineis = math.ceil(potencia_gerador / potencia_painel_kw)
    potencia_real = qtd_paineis * potencia_painel_kw
    geracao_estimada = potencia_real * 30 * hsp * pr

    # ==========================================
    # EXIBIÇÃO DE RESULTADOS
    # ==========================================
    st.markdown("---")
    st.subheader("📊 Resultados do Dimensionamento")
    st.caption("Esses resultados são baseados no consumo atual e nas previsões de aumento de carga. Para modificações, ajuste os parâmetros ou as cargas previstas para recalcular automaticamente o dimensionamento do sistema fotovoltaico.")
    # Métricas de destaque
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Consumo Alvo", f"{consumo_alvo:.2f} kWh/mês", f"+{total_aumentos_cargas:.1f} kWh extra" if total_aumentos_cargas > 0 else None)
    m2.metric("Potência Necessária", f"{potencia_gerador:.2f} kWp")
    m3.metric("Potência Real Instalada", f"{potencia_real:.2f} kWp")
    m4.metric("Qtd. de Módulos", f"{qtd_paineis} un.")

    st.success(f"**Geração Estimada do Sistema:** {geracao_estimada:.0f} kWh/mês (Cobre 100% da necessidade calculada).")

    # ==========================================
    # RESUMO PARA A PROPOSTA COMERCIAL
    # ==========================================
    st.markdown("### 📝 Resumo Executivo para a Proposta")
    st.caption("Copie e cole este texto no contrato ou apresentação em PDF do cliente.")
    
    texto_proposta = f"""
    **Proposta Técnica - Sistema Fotovoltaico**
    * **Cliente:** {nome_cliente if nome_cliente else 'Não informado'}
    * **Local de Instalação:**
        - **Endereço:** {endereço_cliente if endereço_cliente else 'Não informado'}
        - **Código UC:** {codigo_UC if codigo_UC else 'Não informado'}
        - **Padrão de Entrada:** {tipo_ligacao}
        - **Tensão de Fornecimento:** {tensao_fornecimento}
        - **Taxa de Custo de Disponibilidade:** {custo_disponibilidade[tipo_ligacao]} KWh/mês (conforme tabela Energisa MS), gerando um custo fixo mensal de aproxidamente {custo_disponibilidade[tipo_ligacao] * 0.88:.2f} (considerando tarifa média de R$ 0,88 por kWh).

    
    **Memorial descritivo de cálculo:**
        - **Irradiação Local (HSP):** {hsp} (horas de sol pleno por dia, fator para Campo Grande/MS)
        - **Performance Ratio (PR):** {pr} (considerando perdas do sistema)   
        - **Média deConsumo Atual:** {consumo_atual} kWh/mês
        - **Aumentos de Carga Previstos:** {total_aumentos_cargas  if total_aumentos_cargas > 0 else '0'} kWh/mês (Detalhado na tabela de cargas)
        - **Base de Cálculo:** 
            1. Consumo Alvo (kWh/mês) = Consumo Médio Atual + Aumentos de Carga Previstos -> {consumo_atual} + {total_aumentos_cargas:.1f} = {consumo_alvo:.2f} kWh/mês
            2. Pkwp = Consumo Alvo(KWh) / (30 dias * HSP * PR) -> Pkwp = {consumo_alvo:.2f} / (30 * {hsp} * {pr}) = {potencia_gerador:.2f} kWp
            3. Quantidade de Módulos = Potência do Gerador / Potência do Módulo -> {potencia_gerador:.2f} / {potencia_painel_kw:.2f} = {qtd_paineis} módulos

    **Composição do Gerador:**
       - **Potência Total Instalada:** {potencia_real:.2f} kWp
       - **Módulos Fotovoltaicos:** {qtd_paineis} painéis de {potencia_painel}W
       - **Tecnologia de Conversão:** {tipo_inversor}
       - **Geração Média Mensal Estimada:** {geracao_estimada:.0f} kWh
    """
    
    st.code(texto_proposta, language="markdown")

else:
    st.warning("Insira a média de consumo do cliente para gerar o dimensionamento.")