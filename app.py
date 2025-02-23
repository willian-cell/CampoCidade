import streamlit as st
import sqlite3
import time
import pandas as pd
import matplotlib.pyplot as plt
import os
from PIL import Image
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

# ========================== CONFIGURAÇÃO DE DIRETÓRIOS ==========================
UPLOAD_FOLDER = "uploads"
IMAGENS_FOLDER = "imagens"
DEFAULT_USER_IMG = os.path.join(IMAGENS_FOLDER, "default-user.jpg")

# Criar diretórios caso não existam
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGENS_FOLDER, exist_ok=True)

# Criar um placeholder para a imagem padrão se ela não existir
if not os.path.exists(DEFAULT_USER_IMG):
    with open(DEFAULT_USER_IMG, "wb") as f:
        f.write(b"")  # Cria um arquivo vazio para evitar erro

# ========================== FUNÇÕES DO BANCO DE DADOS ==========================

DATABASE = "database.db"
UPLOAD_FOLDER = "uploads"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def coluna_existe(nome_tabela, nome_coluna):
    if not nome_tabela.isidentifier():
        raise ValueError("Nome de tabela inválido.")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"PRAGMA table_info({nome_tabela})")  # PRAGMA não aceita `?`
    colunas = [row["name"] for row in cursor.fetchall()]
    conn.close()
    return nome_coluna in colunas

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            idade INTEGER,
            telefone TEXT NOT NULL,
            endereco TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0
        );
    ''')

    if not coluna_existe("users", "foto_perfil"):
        cursor.execute("ALTER TABLE users ADD COLUMN foto_perfil TEXT DEFAULT '';")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hortas (
            horta_id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_horta TEXT NOT NULL,
            usuario_id INTEGER NOT NULL,
            foto TEXT NOT NULL,
            especie TEXT NOT NULL,
            dias_colheita INTEGER NOT NULL,
            contato TEXT NOT NULL,
            endereco TEXT NOT NULL,
            email TEXT NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES users(user_id)
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feed_hortas (
            feed_id INTEGER PRIMARY KEY AUTOINCREMENT,
            horta_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            foto TEXT NOT NULL,
            descricao TEXT,
            data_postagem DATETIME NOT NULL,
            FOREIGN KEY (horta_id) REFERENCES hortas(horta_id),
            FOREIGN KEY (usuario_id) REFERENCES users(user_id)
        );
    ''')

    conn.commit()
    conn.close()

def criar_usuario_admin():
    email_admin = "ADM@123"
    senha_admin = "123456"

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT user_id FROM users WHERE email = ?", (email_admin,))
    admin_exists = cursor.fetchone()

    if admin_exists:
        conn.close()
        return

    senha_hash = generate_password_hash(senha_admin)
    cursor.execute('''
        INSERT INTO users (email, senha, nome, is_admin, telefone, endereco, idade) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (email_admin, senha_hash, "Administrador", 1, "61986221356", "SAD", 32))

    conn.commit()
    conn.close()

init_db()
criar_usuario_admin()

# ========================== GERENCIAMENTO DE LOGIN ==========================

if "user" not in st.session_state:
    st.session_state["user"] = None

if "pagina" not in st.session_state:
    st.session_state["pagina"] = "login"



def login():
    st.subheader("🔐 Login")
    email = st.text_input("Email", key="login_email")
    senha = st.text_input("Senha", type="password", key="login_senha")

    if st.button("Entrar"):
        conn = get_db_connection()
        cursor = conn.cursor()
        user = cursor.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["senha"], senha):
            st.session_state["user"] = user
            st.success(f"Bem-vindo, {user['nome']}!")
            st.rerun()
        else:
            st.error("Email ou senha incorretos.")

    if st.button("Cadastre-se"):
        st.session_state["pagina"] = "cadastro"  # ✅ Correção aqui
        st.rerun()


def logout():
    st.session_state["user"] = None
    st.rerun()  # ✅ Alterado para evitar erro


# ========================== TELA PESSOAL DO USUÁRIO ==========================

def salvar_foto(uploaded_file, nome_arquivo):
    """Salva a foto no diretório correto e retorna o caminho do arquivo."""
    try:
        if uploaded_file is not None:
            file_path = os.path.join(UPLOAD_FOLDER, nome_arquivo)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            return file_path
    except Exception as e:
        st.error(f"Erro ao salvar a imagem: {e}")
    return DEFAULT_USER_IMG  # Retorna a imagem padrão caso ocorra erro


def tela_usuario():
    st.subheader(f"👤 Bem-vindo, {st.session_state['user']['nome']}!")

    # Converter para dicionário para permitir modificações
    st.session_state["user"] = dict(st.session_state["user"])

    # Verifica se há uma foto de perfil cadastrada e se o arquivo existe
    foto_perfil = st.session_state["user"].get("foto_perfil", None)

    if not foto_perfil or not os.path.exists(foto_perfil) or os.path.getsize(foto_perfil) == 0:
        foto_perfil = DEFAULT_USER_IMG  # Usa a imagem padrão caso a imagem esteja ausente ou vazia

    # Exibir imagem da foto de perfil responsivamente
    try:
        st.image(foto_perfil, caption="Foto de Perfil", use_container_width=True)
    except Exception as e:
        st.warning(f"Erro ao carregar imagem, tente salvar alguma imagem: {e}")
        st.image("https://via.placeholder.com/150", caption="Imagem temporária")

    # Opção para alterar a foto de perfil
    if st.button("🔄 Alterar foto de perfil"):
        st.session_state["alterar_foto"] = True
        st.rerun()

    # Upload de nova foto, se solicitado
    if st.session_state.get("alterar_foto", False):
        uploaded_file = st.file_uploader("Envie sua foto de perfil", type=["jpg", "png", "jpeg"])

        if uploaded_file:
            file_path = salvar_foto(uploaded_file, f"user_{st.session_state['user']['user_id']}.jpg")

            # Atualizar o caminho da foto no banco de dados
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET foto_perfil = ? WHERE user_id = ?", (file_path, st.session_state["user"]["user_id"]))
            conn.commit()
            conn.close()

            # Atualizar o estado da sessão com a nova foto
            st.session_state["user"]["foto_perfil"] = file_path
            st.success("Foto de perfil atualizada com sucesso! Recarregando a página...")
            
            # Reseta a variável de controle e recarrega a página
            st.session_state["alterar_foto"] = False
            st.rerun()

    # Exibir informações do usuário
    st.write(f"📧 **Email:** {st.session_state['user']['email']}")
    st.write(f"📍 **Endereço:** {st.session_state['user']['endereco']}")
    st.write(f"📞 **Telefone:** {st.session_state['user']['telefone']}")

    # Buscar as hortas do usuário
    conn = get_db_connection()
    hortas = conn.execute("SELECT * FROM hortas WHERE usuario_id = ?", (st.session_state["user"]["user_id"],)).fetchall()
    conn.close()

    if not hortas:
        st.warning(" 🌱  Ainda não cadastrou sua horta? ")
        st.warning(" 🌱 VÁ ATÉ A BARRA DE NAVEGAÇAO AO LADO!")
        st.warning(" 🌱 CADASTRE AGORA!")

    else:
        st.subheader("🌾 Minhas Hortas")
        for horta in hortas:
            nome_horta = horta["nome_horta"]
            especie = horta["especie"]
            dias_colheita = horta["dias_colheita"]
            foto = horta["foto"]

            # Verifica se a imagem existe e se tem conteúdo
            if not foto or not os.path.exists(foto) or os.path.getsize(foto) == 0:
                foto = "imagens/default-horta.jpg"

            try:
                st.image(foto, use_container_width=True)
            except Exception as e:
                st.warning(f"Erro ao carregar imagem da horta: {e}")
                st.image("https://via.placeholder.com/300", use_container_width=True)

            st.write(f"**Horta:** {nome_horta}")
            st.write(f"**Espécie:** {especie}")
            st.write(f"**Dias para Colheita:** {dias_colheita}")

            # Botão para atualizar e postar no feed
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"✏️ Atualizar {nome_horta}", key=f"update_{horta['horta_id']}"):
                    st.session_state["horta_em_edicao"] = horta["horta_id"]
                    st.rerun()

            with col2:
                if st.button("📢 Postar no Feed", key=f"post_{horta['horta_id']}"):
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO feed_hortas (horta_id, usuario_id, foto, descricao, data_postagem) VALUES (?, ?, ?, ?, ?)",
                        (horta["horta_id"], st.session_state["user"]["user_id"], horta["foto"], f"Horta de {st.session_state['user']['nome']}", datetime.now())
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"Horta '{nome_horta}' postada no feed!")

    # Se uma horta estiver sendo editada, mostrar o formulário de edição
    if "horta_em_edicao" in st.session_state:
        editar_horta(st.session_state["horta_em_edicao"])

            
def editar_horta(horta_id):
    conn = get_db_connection()
    horta = conn.execute("SELECT * FROM hortas WHERE horta_id = ?", (horta_id,)).fetchone()
    conn.close()

    if not horta:
        st.error("Horta não encontrada!")
        return

    st.subheader(f"✏️ Editar Horta: {horta['nome_horta']}")

    nome_horta = st.text_input("Nome da Horta", value=horta["nome_horta"])
    especie = st.text_input("Espécie Plantada", value=horta["especie"])
    dias_colheita = st.number_input("Dias para Colheita", min_value=1, step=1, value=horta["dias_colheita"])
    endereco = st.text_input("Endereço da Horta", value=horta["endereco"])

    foto = st.file_uploader("Atualize a foto da horta", type=["jpg", "png", "jpeg"])
    file_path = horta["foto"]

    if foto:
        file_path = salvar_foto(foto, f"horta_{horta_id}.jpg")

    if st.button("💾 Salvar Alterações"):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE hortas 
            SET nome_horta = ?, especie = ?, dias_colheita = ?, endereco = ?, foto = ?
            WHERE horta_id = ?;
        ''', (nome_horta, especie, dias_colheita, endereco, file_path, horta_id))
        conn.commit()
        conn.close()

        st.success("Horta atualizada com sucesso!")

        # Limpar estado após salvar
        del st.session_state["horta_em_edicao"]
        st.rerun()

    if st.button("❌ Cancelar"):
        del st.session_state["horta_em_edicao"]
        st.rerun()


    if st.button("Postar no Feed"):
        conn = get_db_connection()
        cursor = conn.cursor()
        for horta in hortas:
            cursor.execute("INSERT INTO feed_hortas (horta_id, usuario_id, foto, descricao, data_postagem) VALUES (?, ?, ?, ?, ?)",
                           (horta["horta_id"], st.session_state["user"]["user_id"], horta["foto"], f"Horta de {st.session_state['user']['nome']}", datetime.now()))
        conn.commit()
        conn.close()
        st.success("Horta postada no feed!")



def painel_administrador():
    st.subheader("🛠️ Painel do Administrador")


    # ================== LISTAGEM DE HORTAS CADASTRADAS ==================
    st.subheader("📋 Hortas Cadastradas")

    conn = get_db_connection()
    hortas = conn.execute("SELECT * FROM hortas").fetchall()
    conn.close()

    if not hortas:
        st.info("📢 Nenhuma horta cadastrada ainda.")
        return

    for horta in hortas:
        with st.container():
            st.write(f"**🌿 Horta:** {horta['nome_horta']}")
            st.write(f"📌 **Espécie:** {horta['especie']}")
            st.write(f"⏳ **Dias para Colheita:** {horta['dias_colheita']} dias")
            st.write(f"👨‍🌾 **Produtor:** {horta['contato']} - 📧 {horta['email']}")

            foto_horta = horta["foto"]
            if not foto_horta or not os.path.exists(foto_horta):
                foto_horta = "imagens/default-horta.jpg"

            try:
                st.image(foto_horta, width=300)
            except Exception as e:
                st.warning(f"Erro ao carregar imagem: {e}")
                st.image("https://via.placeholder.com/300", width=300)

            # Criar colunas para botões
            col1, col2 = st.columns(2)

            with col1:
                if st.button("🗑️ Excluir", key=f"del_{horta['horta_id']}"):
                    st.session_state["confirmar_exclusao"] = horta["horta_id"]
                    st.rerun()

            with col2:
                if st.button("✏️ Editar", key=f"edit_{horta['horta_id']}"):
                    st.session_state["horta_em_edicao"] = horta["horta_id"]
                    st.rerun()

            st.write("---")  # Separador entre hortas


# ========================== EXCLUIR HORTA ==========================

def excluir_horta(horta_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM hortas WHERE horta_id = ?", (horta_id,))
    conn.commit()
    conn.close()
    st.success("✅ Horta excluída com sucesso!")
    st.rerun()

# ========================== ATUALIZAR HORTA ==========================

def atualizar_horta(horta_id):
    st.subheader("✏️ Atualizar Horta")

    conn = get_db_connection()
    horta = conn.execute("SELECT * FROM hortas WHERE horta_id = ?", (horta_id,)).fetchone()
    conn.close()

    if not horta:
        st.error("❌ Horta não encontrada!")
        return

    nome_horta = st.text_input("🌿 Nome da Horta", value=horta["nome_horta"])
    especie = st.text_input("📌 Espécie Plantada", value=horta["especie"])
    dias_colheita = st.number_input("⏳ Dias para Colheita", min_value=1, step=1, value=horta["dias_colheita"])
    endereco = st.text_input("📍 Endereço da Horta", value=horta["endereco"])

    foto = st.file_uploader("📸 Atualize a foto da horta", type=["jpg", "png", "jpeg"])
    file_path = horta["foto"]

    if foto:
        file_path = os.path.join("uploads", f"horta_{horta_id}.jpg")
        try:
            with open(file_path, "wb") as f:
                f.write(foto.getbuffer())
            st.success("✅ Nova imagem carregada com sucesso!")
        except Exception as e:
            st.error(f"⚠️ Erro ao salvar a nova imagem: {e}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Salvar Alterações", key=f"save_{horta_id}"):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE hortas 
                SET nome_horta = ?, especie = ?, dias_colheita = ?, endereco = ?, foto = ?
                WHERE horta_id = ?;
            ''', (nome_horta, especie, dias_colheita, endereco, file_path, horta_id))
            conn.commit()
            conn.close()

            st.success("✅ Horta atualizada com sucesso!")
            del st.session_state["horta_em_edicao"]
            st.rerun()

    with col2:
        if st.button("❌ Cancelar", key=f"cancel_{horta_id}"):
            del st.session_state["horta_em_edicao"]
            st.rerun()



# ========================== SISTEMA DE NAVEGAÇÃO ==========================

def main():
    st.title("🌱 Campo Cidade 🏠")


    if "pagina" not in st.session_state:
        st.session_state["pagina"] = "login"

    if st.session_state["user"]:
        menu = ["Página Inicial", "Feed de Hortas", "Cadastrar Horta", "Painel do Administrador", "Sair"]
        escolha = st.sidebar.selectbox("📌 Navegação", menu)

        if escolha == "Página Inicial":
            tela_usuario()
        elif escolha == "Feed de Hortas":
            feed_hortas()
        elif escolha == "Cadastrar Horta":
            cadastrar_horta()
        elif escolha == "Painel do Administrador":
            if st.session_state["user"]["is_admin"]:
                painel_administrador()
            else:
                st.warning("Acesso negado! Apenas administradores podem acessar esta página.")
        elif escolha == "Sair":
            # Remove o usuário da sessão e retorna para a página de login
            del st.session_state["user"]
            st.session_state["pagina"] = "login"
            st.rerun() 



    else:
        if st.session_state["pagina"] == "login":
            login()
        elif st.session_state["pagina"] == "cadastro":
            form_cadastro()
            if st.button("Voltar ao Login"):
                st.session_state["pagina"] = "login"
                st.rerun()




def form_cadastro():
    st.subheader("📋 Cadastro de Usuário")
    nome = st.text_input("Nome", key="cadastro_nome")
    idade = st.number_input("Idade", min_value=1, step=1, key="cadastro_idade")
    telefone = st.text_input("Telefone", key="cadastro_telefone")
    endereco = st.text_input("Endereço", key="cadastro_endereco")
    email = st.text_input("Email", key="cadastro_email")
    senha = st.text_input("Senha", type="password", key="cadastro_senha")
    confirmaSenha = st.text_input("Confirme a Senha", type="password", key="cadastro_confirma_senha")

    if st.button("Cadastrar"):
        if senha != confirmaSenha:
            st.error("As senhas não coincidem!")
            return

        senha_hash = generate_password_hash(senha)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            INSERT INTO users (nome, idade, telefone, endereco, email, senha)
            VALUES (?, ?, ?, ?, ?, ?);
            ''',
            (nome, idade, telefone, endereco, email, senha_hash)
        )
        conn.commit()
        conn.close()
        st.success("Cadastro realizado com sucesso! Faça login para continuar.")


# ========================== TELA DE CADASTRO DE HORTA ==========================

def cadastrar_horta():
    st.subheader("🌱 Cadastrar Nova Horta")

    if "user" not in st.session_state or not st.session_state["user"]:
        st.warning("Você precisa estar logado para cadastrar uma horta.")
        return

    # Campos do formulário
    nome_horta = st.text_input("Nome da Horta")
    especie = st.text_input("Espécie Plantada")
    dias_colheita = st.number_input("Dias para Colheita", min_value=1, step=1)
    endereco = st.text_input("Endereço da Horta")
    contato = st.text_input("Nome do Produtor", value=st.session_state["user"]["nome"])
    email = st.text_input("Email do Produtor", value=st.session_state["user"]["email"])

    # Upload da imagem da horta
    foto = st.file_uploader("Envie uma foto da sua horta", type=["jpg", "png", "jpeg"])

    # ✅ Corrigido: Adicionando um identificador `key` exclusivo ao botão
    if st.button("Cadastrar Horta", key="btn_cadastrar_horta"):
        if not nome_horta or not especie or not endereco or not contato or not email:
            st.error("Preencha todos os campos obrigatórios!")
            return

        # Caminho para salvar a imagem da horta
        file_path = ""
        if foto:
            file_path = os.path.join("uploads", f"horta_{st.session_state['user']['user_id']}.jpg")
            with open(file_path, "wb") as f:
                f.write(foto.getbuffer())

        # Inserir no banco de dados
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO hortas (nome_horta, usuario_id, foto, especie, dias_colheita, contato, endereco, email)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        ''', (nome_horta, st.session_state["user"]["user_id"], file_path, especie, dias_colheita, contato, endereco, email))
        conn.commit()
        conn.close()

        st.success("Horta cadastrada com sucesso!")

        # ✅ Redireciona para a Página Inicial
        st.session_state["pagina"] = "home"
        st.rerun()


def feed_hortas():
    st.subheader("🌱 Feed das Hortas")

    # Conectar ao banco de dados
    conn = get_db_connection()
    cursor = conn.cursor()

    # Buscar todas as postagens do feed
    postagens = cursor.execute("""
        SELECT feed_hortas.foto, feed_hortas.descricao, feed_hortas.data_postagem, 
               users.nome, hortas.nome_horta, hortas.especie 
        FROM feed_hortas
        JOIN users ON feed_hortas.usuario_id = users.user_id
        JOIN hortas ON feed_hortas.horta_id = hortas.horta_id
        ORDER BY feed_hortas.data_postagem DESC
    """).fetchall()

    conn.close()

    if not postagens:
        st.info("Nenhuma postagem no feed ainda. Poste sua primeira horta! 🌿")
        return

    # Exibir as postagens do feed
    for postagem in postagens:
        with st.container():
            st.markdown(f"### 🌿 {postagem['nome_horta']} ({postagem['especie']})")
            st.markdown(f"👤 **Produtor:** {postagem['nome']}")
            st.markdown(f"📅 **Data da Postagem:** {postagem['data_postagem']}")

            # Exibir imagem da postagem, se houver
            if postagem["foto"] and os.path.exists(postagem["foto"]):
                st.image(postagem["foto"], width=300)
            else:
                st.image("imagens/default-horta.jpg", width=300)  # Imagem padrão

            # Exibir descrição, se houver
            if postagem["descricao"]:
                st.write(f"📖 **Descrição:** {postagem['descricao']}")
            
            st.write("---")  # Linha separadora entre postagens


if __name__ == "__main__":
    main()
