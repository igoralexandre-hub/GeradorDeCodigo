from datetime import date
from decimal import Decimal

import streamlit as st
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload


st.set_page_config(page_title="Festa IFC Blumenau", page_icon="F", layout="wide")

try:
    from database import (
        SessionLocal,
        initialize_database,
        test_connection,
    )
    from models import Alimento, Doacao, Doador, Insumo, Trabalhador

    initialize_database()
except (OSError, ValueError, RuntimeError) as error:
    st.error(f"Configuracao do banco invalida: {error}")
    st.stop()

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 3rem; }
    [data-testid="stSidebar"] { border-right: 1px solid rgba(120, 120, 120, .18); }
    div[data-testid="stMetric"] { background: #f3f6f1; padding: 1rem; border-radius: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

PAGES = ["Visao geral", "Alimentos", "Insumos", "Doadores", "Doacoes", "Equipe"]
st.sidebar.title("Festa IFC")
st.sidebar.caption("Campus Blumenau")
page = st.sidebar.radio("Navegacao", PAGES, label_visibility="collapsed")
if st.sidebar.button("Testar conexao com o banco"):
    connected, message = test_connection()
    if connected:
        st.sidebar.success(message)
    else:
        st.sidebar.error(message)


def records(model):
    relationships = {
        Alimento: [selectinload(Alimento.insumos)],
        Insumo: [selectinload(Insumo.alimentos)],
        Doador: [selectinload(Doador.doacoes)],
        Doacao: [selectinload(Doacao.insumo), selectinload(Doacao.doador)],
    }
    statement = select(model).order_by(model.id).options(*relationships.get(model, []))
    with SessionLocal() as session:
        return list(session.scalars(statement))


def save_record(record, record_id=None):
    try:
        with SessionLocal() as session:
            if record_id is not None:
                current = session.get(type(record), record_id)
                if current is None:
                    st.error("Este registro nao foi encontrado.")
                    return False
                for key, value in vars(record).items():
                    if not key.startswith("_") and key != "id":
                        setattr(current, key, value)
                record = current
            session.add(record)
            session.commit()
        st.success("Registro salvo.")
        return True
    except IntegrityError:
        st.error("Nao foi possivel salvar. Verifique nomes duplicados e relacionamentos existentes.")
        return False


def delete_record(model, record_id):
    try:
        with SessionLocal() as session:
            item = session.get(model, record_id)
            if item is not None:
                session.delete(item)
                session.commit()
        st.success("Registro excluido.")
        st.rerun()
    except IntegrityError:
        st.error("Este registro esta vinculado a outros dados e nao pode ser excluido.")


def crud_header(title, description):
    st.title(title)
    st.caption(description)
    return st.tabs(["Cadastrar", "Consultar / editar", "Excluir"])


def display_rows(items, columns):
    rows = [{label: getter(item) for label, getter in columns} for item in items]
    st.dataframe(rows, hide_index=True, use_container_width=True)


if page == "Visao geral":
    st.title("Festa do IFC Blumenau")
    st.caption("Organizacao dos alimentos, doacoes e equipe do evento.")
    with SessionLocal() as session:
        foods = len(session.scalars(select(Alimento.id)).all())
        inputs = len(session.scalars(select(Insumo.id)).all())
        donations = len(session.scalars(select(Doacao.id)).all())
        crew = len(session.scalars(select(Trabalhador.id).where(Trabalhador.ativo.is_(True))).all())
    columns = st.columns(4)
    columns[0].metric("Alimentos", foods)
    columns[1].metric("Insumos", inputs)
    columns[2].metric("Doacoes", donations)
    columns[3].metric("Pessoas na equipe", crew)
    st.subheader("Alimentos para venda")
    foods_list = records(Alimento)
    if foods_list:
        display_rows(foods_list, [("Alimento", lambda item: item.nome), ("Preco de venda", lambda item: f"R$ {item.preco_venda:.2f}"), ("Insumos", lambda item: ", ".join(i.nome for i in item.insumos) or "Nao informados"), ("Ativo", lambda item: "Sim" if item.ativo else "Nao")])
    else:
        st.info("Cadastre os alimentos que serao vendidos na festa.")

elif page == "Alimentos":
    create_tab, list_tab, delete_tab = crud_header("Alimentos", "Produtos para venda, precos e insumos utilizados.")
    ingredients = records(Insumo)
    with create_tab:
        with st.form("create_food"):
            name = st.text_input("Nome")
            description = st.text_area("Descricao")
            price = st.number_input("Preco de venda (R$)", min_value=0.0, step=0.5, format="%.2f")
            selected_ingredients = st.multiselect("Insumos da receita", ingredients, format_func=lambda item: f"{item.nome} ({item.unidade})")
            active = st.checkbox("Disponivel para venda", value=True)
            submitted = st.form_submit_button("Cadastrar alimento", type="primary")
            if submitted:
                if not name.strip() or price <= 0:
                    st.error("Informe o nome e um preco maior que zero.")
                else:
                    food = Alimento(nome=name.strip(), descricao=description.strip() or None, preco_venda=Decimal(str(price)), ativo=active, insumos=selected_ingredients)
                    if save_record(food):
                        st.rerun()
    with list_tab:
        items = records(Alimento)
        if items:
            display_rows(items, [("Alimento", lambda item: item.nome), ("Descricao", lambda item: item.descricao or ""), ("Preco (R$)", lambda item: f"{item.preco_venda:.2f}"), ("Insumos", lambda item: ", ".join(i.nome for i in item.insumos)), ("Ativo", lambda item: "Sim" if item.ativo else "Nao")])
            selected = st.selectbox("Editar alimento", items, format_func=lambda item: item.nome, key="food_edit")
            with st.form("edit_food"):
                name = st.text_input("Nome", value=selected.nome)
                description = st.text_area("Descricao", value=selected.descricao or "")
                price = st.number_input("Preco de venda (R$)", min_value=0.0, step=0.5, value=float(selected.preco_venda), format="%.2f")
                selected_ingredients = st.multiselect("Insumos da receita", ingredients, default=selected.insumos, format_func=lambda item: f"{item.nome} ({item.unidade})")
                active = st.checkbox("Disponivel para venda", value=selected.ativo)
                if st.form_submit_button("Salvar alteracoes", type="primary"):
                    if not name.strip() or price <= 0:
                        st.error("Informe o nome e um preco maior que zero.")
                    elif save_record(Alimento(nome=name.strip(), descricao=description.strip() or None, preco_venda=Decimal(str(price)), ativo=active, insumos=selected_ingredients), selected.id):
                        st.rerun()
        else:
            st.info("Nenhum alimento cadastrado.")
    with delete_tab:
        items = records(Alimento)
        if items:
            selected = st.selectbox("Alimento", items, format_func=lambda item: item.nome, key="food_delete")
            if st.button("Excluir alimento", type="secondary"):
                delete_record(Alimento, selected.id)
        else:
            st.info("Nenhum alimento para excluir.")

elif page == "Insumos":
    create_tab, list_tab, delete_tab = crud_header("Insumos", "Itens necessarios para preparar os alimentos. Os insumos sao doados.")
    with create_tab:
        with st.form("create_input"):
            name = st.text_input("Nome")
            unit = st.text_input("Unidade", placeholder="kg, unidade, litro...")
            notes = st.text_area("Observacoes")
            if st.form_submit_button("Cadastrar insumo", type="primary"):
                if not name.strip() or not unit.strip():
                    st.error("Informe o nome e a unidade.")
                elif save_record(Insumo(nome=name.strip(), unidade=unit.strip(), observacoes=notes.strip() or None)):
                    st.rerun()
    with list_tab:
        items = records(Insumo)
        if items:
            display_rows(items, [("Insumo", lambda item: item.nome), ("Unidade", lambda item: item.unidade), ("Observacoes", lambda item: item.observacoes or ""), ("Alimentos", lambda item: ", ".join(food.nome for food in item.alimentos))])
            selected = st.selectbox("Editar insumo", items, format_func=lambda item: item.nome, key="input_edit")
            with st.form("edit_input"):
                name = st.text_input("Nome", value=selected.nome)
                unit = st.text_input("Unidade", value=selected.unidade)
                notes = st.text_area("Observacoes", value=selected.observacoes or "")
                if st.form_submit_button("Salvar alteracoes", type="primary"):
                    if not name.strip() or not unit.strip():
                        st.error("Informe o nome e a unidade.")
                    elif save_record(Insumo(nome=name.strip(), unidade=unit.strip(), observacoes=notes.strip() or None), selected.id):
                        st.rerun()
        else:
            st.info("Nenhum insumo cadastrado.")
    with delete_tab:
        items = records(Insumo)
        if items:
            selected = st.selectbox("Insumo", items, format_func=lambda item: item.nome, key="input_delete")
            if st.button("Excluir insumo"):
                delete_record(Insumo, selected.id)
        else:
            st.info("Nenhum insumo para excluir.")

elif page == "Doadores":
    create_tab, list_tab, delete_tab = crud_header("Doadores", "Pessoas e organizacoes que contribuem com insumos para a festa.")
    donor_types = ["Pessoa", "Empresa", "Instituicao", "Outro"]
    with create_tab:
        with st.form("create_donor"):
            name = st.text_input("Nome")
            kind = st.selectbox("Tipo", donor_types)
            phone = st.text_input("Telefone")
            email = st.text_input("E-mail")
            notes = st.text_area("Observacoes")
            if st.form_submit_button("Cadastrar doador", type="primary"):
                if not name.strip():
                    st.error("Informe o nome do doador.")
                elif save_record(Doador(nome=name.strip(), tipo=kind, telefone=phone.strip() or None, email=email.strip() or None, observacoes=notes.strip() or None)):
                    st.rerun()
    with list_tab:
        items = records(Doador)
        if items:
            display_rows(items, [("Nome", lambda item: item.nome), ("Tipo", lambda item: item.tipo), ("Telefone", lambda item: item.telefone or ""), ("E-mail", lambda item: item.email or ""), ("Doacoes", lambda item: len(item.doacoes))])
            selected = st.selectbox("Editar doador", items, format_func=lambda item: item.nome, key="donor_edit")
            with st.form("edit_donor"):
                name = st.text_input("Nome", value=selected.nome)
                kind = st.selectbox("Tipo", donor_types, index=donor_types.index(selected.tipo))
                phone = st.text_input("Telefone", value=selected.telefone or "")
                email = st.text_input("E-mail", value=selected.email or "")
                notes = st.text_area("Observacoes", value=selected.observacoes or "")
                if st.form_submit_button("Salvar alteracoes", type="primary"):
                    if not name.strip():
                        st.error("Informe o nome do doador.")
                    elif save_record(Doador(nome=name.strip(), tipo=kind, telefone=phone.strip() or None, email=email.strip() or None, observacoes=notes.strip() or None), selected.id):
                        st.rerun()
        else:
            st.info("Nenhum doador cadastrado.")
    with delete_tab:
        items = records(Doador)
        if items:
            selected = st.selectbox("Doador", items, format_func=lambda item: item.nome, key="donor_delete")
            if st.button("Excluir doador"):
                delete_record(Doador, selected.id)
        else:
            st.info("Nenhum doador para excluir.")

elif page == "Doacoes":
    create_tab, list_tab, delete_tab = crud_header("Doacoes", "Registre os insumos doados e quem realizou cada doacao.")
    ingredients = records(Insumo)
    donors = records(Doador)
    with create_tab:
        if not ingredients or not donors:
            st.info("Cadastre pelo menos um insumo e um doador antes de registrar doacoes.")
        else:
            with st.form("create_donation"):
                ingredient = st.selectbox("Insumo", ingredients, format_func=lambda item: f"{item.nome} ({item.unidade})")
                donor = st.selectbox("Doador", donors, format_func=lambda item: item.nome)
                quantity = st.number_input("Quantidade", min_value=0.01, step=1.0, format="%.2f")
                donation_date = st.date_input("Data da doacao", value=date.today())
                notes = st.text_area("Observacoes")
                if st.form_submit_button("Registrar doacao", type="primary"):
                    donation = Doacao(insumo_id=ingredient.id, doador_id=donor.id, quantidade=Decimal(str(quantity)), data_doacao=donation_date, observacoes=notes.strip() or None)
                    if save_record(donation):
                        st.rerun()
    with list_tab:
        items = records(Doacao)
        if items:
            display_rows(items, [("Data", lambda item: item.data_doacao.strftime("%d/%m/%Y")), ("Insumo", lambda item: item.insumo.nome), ("Quantidade", lambda item: f"{item.quantidade} {item.insumo.unidade}"), ("Doador", lambda item: item.doador.nome), ("Observacoes", lambda item: item.observacoes or "")])
            selected = st.selectbox("Editar doacao", items, format_func=lambda item: f"{item.data_doacao:%d/%m/%Y} - {item.insumo.nome} - {item.doador.nome}", key="donation_edit")
            with st.form("edit_donation"):
                ingredient = st.selectbox("Insumo", ingredients, index=ingredients.index(selected.insumo), format_func=lambda item: f"{item.nome} ({item.unidade})")
                donor = st.selectbox("Doador", donors, index=donors.index(selected.doador), format_func=lambda item: item.nome)
                quantity = st.number_input("Quantidade", min_value=0.01, step=1.0, value=float(selected.quantidade), format="%.2f")
                donation_date = st.date_input("Data da doacao", value=selected.data_doacao)
                notes = st.text_area("Observacoes", value=selected.observacoes or "")
                if st.form_submit_button("Salvar alteracoes", type="primary"):
                    if save_record(Doacao(insumo_id=ingredient.id, doador_id=donor.id, quantidade=Decimal(str(quantity)), data_doacao=donation_date, observacoes=notes.strip() or None), selected.id):
                        st.rerun()
        else:
            st.info("Nenhuma doacao registrada.")
    with delete_tab:
        items = records(Doacao)
        if items:
            selected = st.selectbox("Doacao", items, format_func=lambda item: f"{item.data_doacao:%d/%m/%Y} - {item.insumo.nome} - {item.doador.nome}", key="donation_delete")
            if st.button("Excluir doacao"):
                delete_record(Doacao, selected.id)
        else:
            st.info("Nenhuma doacao para excluir.")

elif page == "Equipe":
    create_tab, list_tab, delete_tab = crud_header("Equipe", "Pessoas responsaveis pelo trabalho durante a festa.")
    profiles = ["Estudante", "Pai/mae ou responsavel", "Servidor", "Outro"]
    with create_tab:
        with st.form("create_worker"):
            name = st.text_input("Nome")
            profile = st.selectbox("Perfil", profiles)
            role = st.text_input("Funcao", placeholder="Caixa, cozinha, montagem...")
            phone = st.text_input("Telefone")
            availability = st.text_input("Disponibilidade", placeholder="Ex.: manha, tarde, durante todo o evento")
            active = st.checkbox("Participacao ativa", value=True)
            if st.form_submit_button("Cadastrar pessoa", type="primary"):
                if not name.strip() or not role.strip():
                    st.error("Informe o nome e a funcao.")
                elif save_record(Trabalhador(nome=name.strip(), perfil=profile, funcao=role.strip(), telefone=phone.strip() or None, disponibilidade=availability.strip() or None, ativo=active)):
                    st.rerun()
    with list_tab:
        items = records(Trabalhador)
        if items:
            display_rows(items, [("Nome", lambda item: item.nome), ("Perfil", lambda item: item.perfil), ("Funcao", lambda item: item.funcao), ("Telefone", lambda item: item.telefone or ""), ("Disponibilidade", lambda item: item.disponibilidade or ""), ("Ativo", lambda item: "Sim" if item.ativo else "Nao")])
            selected = st.selectbox("Editar pessoa", items, format_func=lambda item: item.nome, key="worker_edit")
            with st.form("edit_worker"):
                name = st.text_input("Nome", value=selected.nome)
                profile = st.selectbox("Perfil", profiles, index=profiles.index(selected.perfil))
                role = st.text_input("Funcao", value=selected.funcao)
                phone = st.text_input("Telefone", value=selected.telefone or "")
                availability = st.text_input("Disponibilidade", value=selected.disponibilidade or "")
                active = st.checkbox("Participacao ativa", value=selected.ativo)
                if st.form_submit_button("Salvar alteracoes", type="primary"):
                    if not name.strip() or not role.strip():
                        st.error("Informe o nome e a funcao.")
                    elif save_record(Trabalhador(nome=name.strip(), perfil=profile, funcao=role.strip(), telefone=phone.strip() or None, disponibilidade=availability.strip() or None, ativo=active), selected.id):
                        st.rerun()
        else:
            st.info("Nenhuma pessoa cadastrada na equipe.")
    with delete_tab:
        items = records(Trabalhador)
        if items:
            selected = st.selectbox("Pessoa", items, format_func=lambda item: f"{item.nome} - {item.funcao}", key="worker_delete")
            if st.button("Excluir pessoa"):
                delete_record(Trabalhador, selected.id)
        else:
            st.info("Nenhuma pessoa para excluir.")