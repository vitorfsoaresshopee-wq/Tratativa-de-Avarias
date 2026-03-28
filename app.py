import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
from fuzzywuzzy import process
import time
import io

# --- 1. DESIGN E TELA DE CARREGAMENTO (SHOPITO) ---
st.set_page_config(page_title="Shopee Avarias Pro", layout="wide")

def carregar_sistema():
    if 'auth' not in st.session_state:
        placeholder = st.empty()
        with placeholder.container():
            st.markdown("<h2 style='text-align: center; color: #ee4d2d;'>Shopito está preparando o hub...</h2>", unsafe_allow_html=True)
            st.image("https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM2Z4ZzB6Z3R4bmV3bm56bmZ4bmZ4bmZ4bmZ4bmZ4bmZ4bmZ4bmZ4JmVwPXYxX2ludGVybmFsX2dpZl9ieV9pZCZjdD1n/3o7TKMGpxV1mNI7AHe/giphy.gif")
            progress = st.progress(0)
            for i in range(100):
                time.sleep(0.01)
                progress.progress(i + 1)
        placeholder.empty()

carregar_sistema()

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #161B22; border-right: 2px solid #ee4d2d; }
    .stButton>button {
        background: linear-gradient(90deg, #ee4d2d 0%, #ff7337 100%);
        color: white; border-radius: 8px; font-weight: bold; width: 100%; transition: 0.3s;
    }
    .stButton>button:hover { background: white; color: #ee4d2d; transform: translateY(-2px); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS (SQLite para Local / Pronto para Migrar para Nuvem) ---
def init_db():
    conn = sqlite3.connect('sistema_avarias.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    wms TEXT PRIMARY KEY, senha TEXT, nome TEXT, email_wms TEXT, agencia TEXT, 
                    login_nome TEXT, wfm TEXT, turno TEXT, setor TEXT, nivel TEXT, 
                    p_reg INTEGER, p_trat INTEGER, p_col INTEGER, p_dash INTEGER, primeiro_acesso INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS registros (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, device TEXT, sku TEXT, descricao TEXT, 
                    tipo_avaria TEXT, status TEXT, tratativa TEXT, usuario TEXT, wms_executor TEXT, data TEXT)''')
    
    c.execute("INSERT OR IGNORE INTO usuarios VALUES ('123', 'Shopee123', 'Admin Technical', 'admin@shopee.com', 'SPX', 'admin.tech', 'WFM01', 'T1', 'TI', 'ADM', 1, 1, 1, 1, 1)")
    conn.commit()
    return conn

conn = init_db()

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    st.title("🟠 Shopee Avarias | Login Único")
    with st.container(border=True):
        w_in = st.text_input("Número WMS")
        s_in = st.text_input("Senha", type="password")
        if st.button("ENTRAR"):
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM usuarios WHERE wms=? AND senha=?", (w_in, s_in))
            u = cursor.fetchone()
            if u:
                st.session_state.user_data = {
                    'wms': u[0], 'nome': u[2], 'login_nome': u[5], 'nivel': u[9],
                    'perm': [u[10], u[11], u[12], u[13]], 'p_acesso': u[14]
                }
                st.session_state.logado = True
                st.session_state.auth = True
                st.rerun()
            else: st.error("Acesso negado.")
    st.stop()

# --- 4. INTERFACE ---
u = st.session_state.user_data
st.sidebar.image("https://logodownload.org/wp-content/uploads/2021/03/shopee-logo-0.png", width=120)
st.sidebar.markdown(f"### 🟠 Olá, {u['login_nome']}")

menu_items = ["Home"]
if u['perm'][0]: menu_items.append("📦 Registro de Avarias")
if u['perm'][1]: menu_items.append("⚙️ Tratativa de Avarias")
if u['perm'][3] or u['nivel'] == 'ADM': menu_items.append("📊 Dashboard & Relatórios")
if u['nivel'] == 'ADM': 
    menu_items.append("🤖 Cruzamento IA")
    menu_items.append("👥 Usuários")

sel = st.sidebar.radio("Navegação", menu_items)

# --- MÓDULO: CRUZAMENTO IA ---
if sel == "🤖 Cruzamento IA":
    st.header("🤖 Inteligência de Cruzamento de Dados")
    st.write("A IA irá sugerir SKUs para itens registrados apenas com descrição.")
    
    file_av = st.file_uploader("Subir Backlog AV do WMS (CSV/Excel)", type=['csv', 'xlsx'])
    if file_av:
        df_av = pd.read_excel(file_av) if file_av.name.endswith('.xlsx') else pd.read_csv(file_av)
        df_registros = pd.read_sql("SELECT descricao FROM registros WHERE sku = '0' OR sku = 'S/N'", conn)
        
        if not df_registros.empty:
            st.subheader("Sugestões da IA")
            matches = []
            for desc_reg in df_registros['descricao'].unique():
                match = process.extractOne(desc_reg, df_av['DESCRICAO_WMS'].tolist())
                if match[1] > 60:
                    sku_suggerido = df_av[df_av['DESCRICAO_WMS'] == match[0]]['SKU'].values[0]
                    matches.append({"Descrição Original": desc_reg, "Sugestão IA": match[0], "Possível SKU": sku_suggerido, "Confiança": f"{match[1]}%"})
            st.table(pd.DataFrame(matches))
        else: st.info("Nenhum item pendente de cruzamento.")

# --- MÓDULO: RELATÓRIOS (ADMIN E OPERADOR) ---
elif sel == "📊 Dashboard & Relatórios":
    st.header("📊 Inteligência de Processo")
    
    if u['nivel'] == 'ADM':
        # Filtros Admin: Dia, Semana, Mês
        periodo = st.selectbox("Intervalo de Tempo", ["Hoje", "Últimos 7 dias", "Últimos 30 dias", "Este Ano"])
        df_total = pd.read_sql("SELECT * FROM registros", conn)
    else:
        df_total = pd.read_sql(f"SELECT * FROM registros WHERE wms_executor = '{u['wms']}'", conn)
        st.info("Você está visualizando apenas os seus processamentos.")

    if not df_total.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Processado", len(df_total))
        c2.metric("Para Descarte", len(df_total[df_total['tratativa'] == 'Descarte']))
        c3.metric("Salvados", len(df_total[df_total['tratativa'] == 'Salvado']))
        
        st.plotly_chart(px.pie(df_total, names='tratativa', hole=0.5, title="Destino das Avarias", color_discrete_sequence=['#ee4d2d', '#26aa99', '#ffb100']))
        st.plotly_chart(px.bar(df_total, x='tipo_avaria', title="Incidência por Tipo de Avaria"))
        
        st.download_button("Baixar Relatório (CSV)", df_total.to_csv(), "relatorio_shopee.csv")
    else: st.warning("Sem dados para o período.")

# --- MÓDULO: GESTÃO DE USUÁRIOS ---
elif sel == "👥 Usuários":
    st.header("👥 Gestão de Usuários e Permissões")
    tab1, tab2 = st.tabs(["🔍 Busca e Edição", "➕ Novo Usuário"])
    
    with tab1:
        busca = st.text_input("Buscar WMS ou WFM")
        if busca:
            res = pd.read_sql(f"SELECT * FROM usuarios WHERE wms LIKE '%{busca}%' OR wfm LIKE '%{busca}%'", conn)
            for i, r in res.iterrows():
                with st.expander(f"{r['nome']} ({r['wms']})"):
                    st.write(f"Email: {r['email_wms']} | WFM: {r['wfm']}")
                    if st.button(f"Resetar Senha para {r['wms']}"):
                        conn.execute("UPDATE usuarios SET senha='Shopee123', primeiro_acesso=1 WHERE wms=?", (r['wms'],))
                        conn.commit()
                        st.warning("Senha resetada.")

    with tab2:
        with st.form("manual"):
            col_a, col_b = st.columns(2)
            f_wms = col_a.text_input("WMS")
            f_nome = col_b.text_input("Nome")
            f_login = col_a.text_input("Login (Username)")
            f_nivel = col_b.selectbox("Nível", ["OPERADOR", "ADM"])
            st.write("Permissões de Acesso:")
            p1, p2, p3, p4 = st.columns(4)
            r1 = p1.checkbox("Registro")
            r2 = p2.checkbox("Tratativa")
            r3 = p3.checkbox("Coleta")
            r4 = p4.checkbox("Dashboard")
            if st.form_submit_button("CADASTRAR"):
                conn.execute("INSERT INTO usuarios VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", 
                             (f_wms, 'Shopee123', f_nome, '', '', f_login, '', '', '', f_nivel, int(r1), int(r2), int(r3), int(r4), 1))
                conn.commit()
                st.success("Usuário criado!")

if st.sidebar.button("LOGOFF"):
    st.session_state.logado = False
    st.rerun()
