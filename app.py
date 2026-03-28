import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
from fuzzywuzzy import process
import time
import io

# --- 1. DESIGN E TELA DE CARREGAMENTO (SHOPITO) ---
st.set_page_config(page_title="Shopee Avarias Hub", layout="wide")

if 'carregado' not in st.session_state:
    p = st.empty()
    with p.container():
        st.markdown("<h2 style='text-align: center; color: #ee4d2d;'>Shopito está organizando o armazém...</h2>", unsafe_allow_html=True)
        st.image("https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM2Z4ZzB6Z3R4bmV3bm56bmZ4bmZ4bmZ4bmZ4bmZ4bmZ4bmZ4bmZ4JmVwPXYxX2ludGVybmFsX2dpZl9ieV9pZCZjdD1n/3o7TKMGpxV1mNI7AHe/giphy.gif")
        bar = st.progress(0)
        for i in range(100):
            time.sleep(0.01)
            bar.progress(i + 1)
    p.empty()
    st.session_state.carregado = True

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #161B22; border-right: 2px solid #ee4d2d; }
    .stButton>button {
        background: linear-gradient(90deg, #ee4d2d 0%, #ff7337 100%);
        color: white; border-radius: 8px; font-weight: bold; width: 100%; transition: 0.3s;
    }
    .stButton>button:hover { background: white; color: #ee4d2d; transform: scale(1.02); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
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
    
    c.execute("INSERT OR IGNORE INTO usuarios VALUES ('123', 'Shopee123', 'Admin', 'admin@shopee.com', 'SPX', 'admin.tech', '001', 'T1', 'TI', 'ADM', 1, 1, 1, 1, 1)")
    conn.commit()
    return conn

conn = init_db()

# --- 3. LOGIN E REDEFINIÇÃO DE SENHA ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    st.title("🟠 Shopee Avarias | Login")
    with st.container(border=True):
        w_in = st.text_input("Número WMS")
        s_in = st.text_input("Senha", type="password")
        if st.button("ENTRAR"):
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM usuarios WHERE wms=? AND senha=?", (w_in, s_in))
            u = cursor.fetchone()
            if u:
                st.session_state.user_data = {
                    'wms': u[0], 'senha': u[1], 'nome': u[2], 'login_nome': u[5], 'nivel': u[9],
                    'perm': [u[10], u[11], u[12], u[13]], 'p_acesso': u[14]
                }
                st.session_state.logado = True
                st.rerun()
            else: st.error("Acesso negado.")
    st.stop()

# TELA DE REDEFINIÇÃO OBRIGATÓRIA
if st.session_state.user_data['senha'] == "Shopee123" or st.session_state.user_data['p_acesso'] == 1:
    st.header("🔒 Redefinir Senha Obrigatória")
    st.info("Por segurança, altere sua senha de primeiro acesso.")
    n1 = st.text_input("Nova Senha", type="password")
    n2 = st.text_input("Confirme a Senha", type="password")
    if st.button("SALVAR E INICIAR"):
        if n1 == n2 and n1 != "Shopee123" and len(n1) >= 4:
            conn.execute("UPDATE usuarios SET senha=?, primeiro_acesso=0 WHERE wms=?", (n1, st.session_state.user_data['wms']))
            conn.commit()
            st.success("Senha alterada! Reiniciando...")
            st.session_state.logado = False
            st.rerun()
        else: st.error("Senhas inválidas ou não coincidem.")
    st.stop()

# --- 4. INTERFACE ---
u = st.session_state.user_data
st.sidebar.markdown(f"### 🟠 Olá, {u['login_nome']}")

menu_items = []
if u['perm'][0]: menu_items.append("📦 Registro de Avarias")
if u['perm'][1]: menu_items.append("⚙️ Tratativa de Avarias")
if u['perm'][3] or u['nivel'] == 'ADM': menu_items.append("📊 Dashboard & Relatórios")
if u['nivel'] == 'ADM': 
    menu_items.append("🤖 Cruzamento IA")
    menu_items.append("👥 Gestão de Usuários")

sel = st.sidebar.radio("Navegação", menu_items)

# --- MÓDULO: REGISTRO ---
if sel == "📦 Registro de Avarias":
    st.header("📦 Registro de Avarias")
    with st.container(border=True):
        device = st.text_input("Bipe a Device/Caixa")
        if device:
            sku = st.text_input("Bipe SKU (ou '0' para descrição)")
            desc = st.text_input("Descrição do Produto") if sku == "0" else ""
            tipo = st.selectbox("Tipo de Avaria", ["CONTAMINADO", "DANIFICADO", "VAZAMENTO", "VIOLADO"])
            if st.button("CONCLUIR ITEM"):
                conn.execute("INSERT INTO registros (device, sku, descricao, tipo_avaria, status, usuario, wms_executor, data) VALUES (?,?,?,?,?,?,?,?)",
                             (device, sku, desc, tipo, "Stage", u['login_nome'], u['wms'], datetime.now().strftime("%d/%m/%Y %H:%M")))
                conn.commit()
                st.success("Item registrado na device!")

# --- MÓDULO: TRATATIVA (BIPAR E INICIAR) ---
elif sel == "⚙️ Tratativa de Avarias":
    st.header("⚙️ Tratativa de Avarias")
    dev_t = st.text_input("Bipe a Device para INICIAR TRABALHO")
    if dev_t:
        df_t = pd.read_sql_query("SELECT * FROM registros WHERE device=? AND status='Stage'", conn, params=(dev_t,))
        if not df_t.empty:
            st.write(f"🛒 Itens na Device: {len(df_t)}")
            st.dataframe(df_t[['sku', 'tipo_avaria', 'data']], use_container_width=True)
            trat = st.radio("Selecione o Destino Final:", ["Salvado", "Descarte", "Retorno ao Estoque"])
            if st.button("FINALIZAR E FECHAR DEVICE"):
                conn.execute("UPDATE registros SET tratativa=?, status='Finalizado' WHERE device=?", (trat, dev_t))
                conn.commit()
                st.success(f"Device {dev_t} processada com sucesso!")
        else: st.warning("Esta device não possui registros em Stage ou não existe.")

# --- MÓDULO: GESTÃO DE USUÁRIOS (LOTE + MANUAL + BUSCA) ---
elif sel == "👥 Gestão de Usuários":
    st.header("👥 Gestão de Equipe")
    t1, t2, t3 = st.tabs(["🔍 Busca/Reset", "➕ Cadastro Manual", "📂 Importar Lote CSV"])
    
    with t1:
        busca = st.text_input("Buscar WMS ou WFM")
        if busca:
            res = pd.read_sql(f"SELECT * FROM usuarios WHERE wms LIKE '%{busca}%' OR wfm LIKE '%{busca}%'", conn)
            for i, r in res.iterrows():
                with st.expander(f"{r['nome']} ({r['wms']})"):
                    if st.button(f"Resetar Senha para {r['wms']}"):
                        conn.execute("UPDATE usuarios SET senha='Shopee123', primeiro_acesso=1 WHERE wms=?", (r['wms'],))
                        conn.commit()
                        st.warning("Senha resetada.")

    with t2:
        with st.form("manual"):
            col_a, col_b = st.columns(2)
            f_wms = col_a.text_input("WMS")
            f_nome = col_b.text_input("Nome")
            f_login = col_a.text_input("Username")
            f_nivel = col_b.selectbox("Nível", ["OPERADOR", "ADM"])
            st.write("Permissões:")
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

    with t3:
        st.write("Suba o arquivo CSV conforme o modelo padrão (WMS, LOGIN, TURNO, ÁREA, Nome Do Rep, AGÊNCIA, WFM)")
        file = st.file_uploader("Selecionar CSV", type="csv")
        if file:
            df_up = pd.read_csv(file)
            df_up.columns = df_up.columns.str.strip()
            if st.button("PROCESSAR LOTE"):
                for _, r in df_up.iterrows():
                    conn.execute("INSERT OR IGNORE INTO usuarios (wms, senha, nome, login_nome, nivel, p_reg, p_trat, p_col, p_dash, primeiro_acesso) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                 (str(r['WMS']), "Shopee123", str(r.get('Nome Do
