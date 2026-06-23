import streamlit as st
import math
import pandas as pd
import textwrap
from geopy.geocoders import Nominatim
import requests

# =========================================
# FUNÇÕES DO APP
# ==========================================

# OBTER COORDENADAS GEOGRÁFICAS A PARTIR DO ENDEREÇO
def obter_coordenadas(endereco):
    if not endereco:
        return None, None
    
    geolocator = Nominatim(user_agent="solar_app")
    location = geolocator.geocode(endereco, timeout=10)

    if location:
        return location.latitude, location.longitude
    
    return None, None

# OBTER HSP (Horas de Sol Pleno) A PARTIR DAS COORDENADAS GEOGRÁFICAS
def obter_hsp(lat, lon):
    url = "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc"
    params = {
        "lat": lat,
        "lon": lon,
        "peakpower": 1,
        "loss": 14,
        "outputformat": "json"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        st.error(f"Erro ao obter dados de irradiancia: {e}")
        return None

    monthly = data.get("outputs", {}).get("monthly", {}).get("fixed", [])
    hsp_mensal = {}
    valores = []

    for item in monthly:
        mes = item.get("month")
        hsp_diario = item.get("H(i)_d")
        hsp_mensal[mes] = hsp_diario
        if hsp_diario is not None:
            valores.append(hsp_diario)

    hsp_medio_anual = sum(valores) / len(valores) if valores else None

    return {
        "hsp_medio_anual": hsp_medio_anual,
        "hsp_medio_mensal": hsp_mensal,
    }


def gerar_assinatura_inputs(*valores):
    partes = []
    for valor in valores:
        if hasattr(valor, "to_json"):
            partes.append(valor.to_json())
        else:
            partes.append(str(valor))
    return "||".join(partes)

    
# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Portal de Projetos Fotovoltaicos",
    page_icon="⚡",
    layout="wide"
)


# =========================================
# CONFIGURAÇÃO DOS STATES
# =========================================
st.session_state.setdefault("dados_hsp", None)
st.session_state.setdefault("coordenadas", None)
st.session_state.setdefault("endereco_busca", None)
st.session_state.setdefault("cache_endereco_geo", {})
st.session_state.setdefault("gerar_dimensionamento", False)
st.session_state.setdefault("ultima_assinatura_inputs", None)

hsp_auto = st.session_state.get("dados_hsp")
hsp_padrao = 5.2
if hsp_auto and hsp_auto.get("hsp_medio_anual") is not None:
    hsp_padrao = float(hsp_auto["hsp_medio_anual"])


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
hsp = st.sidebar.number_input(
    "Irradiação Local (HSP)",
    min_value=3.0,
    max_value=7.0,
    value=float(hsp_padrao),
    step=0.1
)
if hsp_auto and hsp_auto.get("hsp_medio_anual") is not None:
    st.sidebar.caption(f"Valor obtido automaticamente para a localização: {hsp_auto.get('hsp_medio_anual'):.2f} HSP médio anual.")
else:
    st.sidebar.caption("Valor padrão para Campo Grande/MS. Insira o endereço do cliente para obter o valor exato.")
pr = st.sidebar.number_input("Performance Ratio (PR)", min_value=0.50, max_value=1.00, value=0.8, step=0.01)

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
    endereco_normalizado = (endereço_cliente or "").strip()

    if (
        st.session_state.get("endereco_busca")
        and endereco_normalizado
        and endereco_normalizado != st.session_state.get("endereco_busca")
    ):
        st.session_state["coordenadas"] = None
        st.session_state["dados_hsp"] = None
        st.session_state["gerar_dimensionamento"] = False

    if st.button("Buscar coordenadas e HSP"):
        cache_geo = st.session_state["cache_endereco_geo"]

        if not endereco_normalizado:
            st.warning("Informe um endereço válido para obter as coordenadas.")
        else:
            dados_cache = cache_geo.get(endereco_normalizado)
            if dados_cache:
                st.session_state["coordenadas"] = dados_cache.get("coordenadas")
                st.session_state["dados_hsp"] = dados_cache.get("dados_hsp")
                st.session_state["endereco_busca"] = endereco_normalizado
            else:
                lat, lon = obter_coordenadas(endereco_normalizado)

                if lat is not None and lon is not None:
                    dados_hsp = obter_hsp(lat, lon)
                    if dados_hsp:
                        st.session_state["coordenadas"] = (lat, lon)
                        st.session_state["dados_hsp"] = dados_hsp
                        st.session_state["endereco_busca"] = endereco_normalizado
                        st.session_state["cache_endereco_geo"][endereco_normalizado] = {
                            "coordenadas": (lat, lon),
                            "dados_hsp": dados_hsp,
                        }
                    else:
                        st.warning("Não foi possível obter o HSP para esse endereço.")
                else:
                    st.warning("Informe um endereço válido para obter as coordenadas.")

    if (
        endereco_normalizado
        and st.session_state.get("endereco_busca") == endereco_normalizado
        and st.session_state.get("coordenadas")
        and st.session_state.get("dados_hsp")
    ):
        lat, lon = st.session_state["coordenadas"]
        dados_hsp = st.session_state["dados_hsp"]
        st.success(f"Coordenadas carregadas: latitude {lat:.6f}, longitude {lon:.6f}")
        st.caption(f"HSP médio anual estimado: {dados_hsp['hsp_medio_anual']:.2f} h/dia")
    elif endereco_normalizado:
        st.info("Altere o endereço e clique em Buscar coordenadas e HSP para carregar novamente as coordenadas e o HSP antes de gerar o dimensionamento.")

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

assinatura_atual = gerar_assinatura_inputs(
    nome_cliente,
    endereço_cliente,
    codigo_UC,
    tipo_ligacao,
    consumo_atual,
    tipo_telhado,
    tensao_fornecimento,
    hsp,
    pr,
    potencia_painel,
    tipo_inversor,
    st.session_state.get("cargas_editor"),
)

if st.session_state.get("gerar_dimensionamento") and st.session_state.get("ultima_assinatura_inputs") != assinatura_atual:
    st.session_state["gerar_dimensionamento"] = False

# botão para gerar o dimensionamento e renderizar o restante da página
if st.button("Gerar Dimensionamento", type="secondary", use_container_width=True):
    if consumo_atual <= 0:
        st.warning("Informe um valor de consumo atual maior que zero para gerar o dimensionamento.")
        st.session_state["gerar_dimensionamento"] = False
    else:
        st.session_state["gerar_dimensionamento"] = True
        st.session_state["ultima_assinatura_inputs"] = assinatura_atual

# Variáveis base para os aumentos de carga, usadas mesmo quando a seção de análise não aparece.
consumo_arcond = 0
consumo_iluminacao = 0
consumo_eletrodomesticos = 0
consumo_climatizacao = 0
consumo_outro = 0
  
if consumo_atual > 0 and st.session_state.get("gerar_dimensionamento"):
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

if consumo_alvo > 0 and st.session_state.get("gerar_dimensionamento"):
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

    dados_hsp = st.session_state.get("dados_hsp") or {}
    coordenadas_salvas = st.session_state.get("coordenadas")
    hsp_medio_anual = dados_hsp.get("hsp_medio_anual", "Não informado")
    hsp_medio_mensal = dados_hsp.get("hsp_medio_mensal", {}) or {}
    aumentos_cargas_txt = f"{total_aumentos_cargas:.2f}" if total_aumentos_cargas > 0 else "0.00"

    
    texto_proposta = textwrap.dedent(f"""
        **Proposta Técnica - Sistema Fotovoltaico**

        **Cliente**: {nome_cliente if nome_cliente else 'Não informado'}

        **Local de Instalação**
        - **Endereço:** {endereço_cliente if endereço_cliente else 'Não informado'}
        - **Código UC:** {codigo_UC if codigo_UC else 'Não informado'}
        - **Padrão de Entrada:** {tipo_ligacao}
        - **Tensão de Fornecimento:** {tensao_fornecimento}
        - **Custo de Disponibilidade:** R$ {custo_disponibilidade[tipo_ligacao] * 0.88:.2f}/mês

        **Dados de HSP obtidos automaticamente**
        - **Latitude:** {coordenadas_salvas[0] if coordenadas_salvas else 'Não informado'}
        - **Longitude:** {coordenadas_salvas[1] if coordenadas_salvas else 'Não informado'}
        - **HSP Médio Anual:** {hsp_medio_anual}
        - **TABELA DE HSP MÉDIO MENSAL OBTIDOS PELAS COORDENADAS**
            * - Med. Geral: {hsp_medio_anual} h/dia
            * - Jan: {hsp_medio_mensal.get(1, "Não informado")} h/dia
            * - Fev: {hsp_medio_mensal.get(2, "Não informado")} h/dia
            * - Mar: {hsp_medio_mensal.get(3, "Não informado")} h/dia
            * - Abr: {hsp_medio_mensal.get(4, "Não informado")} h/dia
            * - Mai: {hsp_medio_mensal.get(5, "Não informado")} h/dia
            * - Jun: {hsp_medio_mensal.get(6, "Não informado")} h/dia
            * - Jul: {hsp_medio_mensal.get(7, "Não informado")} h/dia
            * - Ago: {hsp_medio_mensal.get(8, "Não informado")} h/dia
            * - Set: {hsp_medio_mensal.get(9, "Não informado")} h/dia
            * - Out: {hsp_medio_mensal.get(10, "Não informado")} h/dia
            * - Nov: {hsp_medio_mensal.get(11, "Não informado")} h/dia
            * - Dez: {hsp_medio_mensal.get(12, "Não informado")} h/dia

        **Memorial descritivo de cálculo**
        - **Irradiação Local (HSP):** {hsp} h/dia
        - **Performance Ratio (PR):** {pr}
        - **Média de Consumo Atual:** {consumo_atual:.2f} kWh/mês
        - **Aumentos de Carga Previstos:** {aumentos_cargas_txt} kWh/mês
        - **Consumo Alvo:** {consumo_alvo:.2f} kWh/mês
        - **Potência Necessária:** {potencia_gerador:.2f} kWp
        - **Potência Real Instalada:** {potencia_real:.2f} kWp
        - **Quantidade de Módulos:** {qtd_paineis} módulos

        **Composição do Gerador**
        - **Módulos Fotovoltaicos:** {qtd_paineis} painéis de {potencia_painel}W
        - **Tecnologia de Conversão:** {tipo_inversor}
        - **Geração Média Mensal Estimada:** {geracao_estimada:.0f} kWh
    """).strip()

    st.code(texto_proposta, language="markdown")
