# Festa IFC Blumenau

Aplicacao web para organizar a festa do IFC Campus Blumenau. A equipe pode cadastrar os alimentos que serao vendidos e seus precos, os insumos necessarios, os doadores, as doacoes recebidas e as pessoas que trabalharao no evento. Os insumos sao tratados como doacoes, sem controle de compra.

## Requisitos

- Python 3.10 ou superior
- [uv](https://docs.astral.sh/uv/)

## Executar localmente

Por padrao, o sistema usa SQLite e cria o banco `data/festa_ifc.db` automaticamente.

```powershell
uv sync
uv run streamlit run src/app.py
```

Abra o endereco local apresentado pelo Streamlit (normalmente `http://localhost:8501`).

## TiDB Cloud

O SQLite continua como padrao para desenvolvimento e testes locais. Para conectar ao TiDB Cloud, obtenha no painel do cluster o endpoint, a porta, o usuario, o nome do banco e a senha. O usuario do banco deve ter permissao para as operacoes usadas pela aplicacao.

Copie o modelo e substitua os valores em `.streamlit/secrets.toml` (o arquivo real e ignorado pelo Git):

```powershell
Copy-Item .streamlit/secrets.toml.example .streamlit/secrets.toml
```

No arquivo local, substitua `DATABASE_URL` pela string fornecida pelo TiDB Cloud e preencha a senha. O certificado CA anexado fica em `certificadoCA/isrgrootx1.pem`; ajuste `ca_path` caso mova o certificado.

O conteudo segue este formato:

```toml
DATABASE_BACKEND = "tidb"
DATABASE_URL = "mysql://usuario@host:4000/sys"

[tidb]
password = "sua-senha"
# Opcional: use o arquivo CA fornecido pelo TiDB Cloud.
ca_path = "certificadoCA/isrgrootx1.pem"
```

Substitua `usuario` e `host` pela connection string real e informe a senha em `[tidb].password`. A senha tambem pode estar embutida na URL, desde que caracteres especiais estejam codificados para URL. O modulo converte o esquema `mysql://` para `mysql+pymysql://` automaticamente. A connection string completa deve ficar somente no `secrets.toml` local ou nos Secrets de producao.

O TLS e sempre habilitado para MySQL/TiDB, com validacao do certificado e do hostname. `ca_path` aceita caminho absoluto ou relativo a raiz do projeto; sem CA especifico, e usado o armazenamento de autoridades confiaveis do sistema. Se o provedor fornecer o certificado CA como texto, configure `ssl_ca_cert` com o PEM em vez de `ca_path`.

Tambem e possivel definir `TIDB_HOST`, `TIDB_PORT`, `TIDB_USER`, `TIDB_PASSWORD`, `TIDB_DATABASE`, `TIDB_SSL_CA_FILE` e `TIDB_SSL_CA_CERT` no ambiente. Para manter compatibilidade, `DATABASE_URL` continua aceito; URLs MySQL tambem recebem TLS validado automaticamente.

## Executar e testar

```powershell
uv sync
uv run streamlit run src/app.py
```

Com `DATABASE_BACKEND = "tidb"` configurado, use o botao **Testar conexao com o banco** na barra lateral. Ele executa `SELECT 1`. Tambem e possivel testar pelo Python:

```powershell
uv run python -c "import sys; sys.path.insert(0, 'src'); from database import test_connection; print(test_connection())"
```

Para voltar ao SQLite, remova `DATABASE_BACKEND` e os valores `TIDB_*` ou defina `DATABASE_BACKEND = "sqlite"`.

## Producao e Streamlit Cloud

No painel do Streamlit Cloud, abra **App settings > Secrets** e cadastre a mesma estrutura TOML usada localmente, mas com a connection string e senha de producao. O valor dos Secrets tem precedencia sobre valores locais quando nao ha variavel de ambiente `DATABASE_URL`. Configure tambem o CA de producao quando fornecido pelo TiDB Cloud. O codigo seleciona o backend por Secrets, sem alteracoes entre ambientes. Nunca adicione o arquivo local `secrets.toml`, arquivos `.env` ou certificados privados ao GitHub.

No deploy, aponte o arquivo principal para `src/app.py`. O `requirements.txt` e o `pyproject.toml` declaram Streamlit, SQLAlchemy e PyMySQL.

## Funcionalidades

- CRUD de alimentos, com preco de venda e selecao dos insumos da receita.
- CRUD de insumos, doadores, doacoes e trabalhadores.
- Registro de perfil de trabalhador (estudante, pai/mae ou responsavel, servidor ou outro), funcao e disponibilidade.
- Persistencia via SQLAlchemy, com chaves e relacionamentos entre entidades.
- Banco selecionado por Secrets ou variaveis de ambiente; sem configuracao TiDB, usa SQLite local.

## Estrutura

```text
src/
	app.py       # Interface Streamlit e paginas CRUD
	database.py  # Configuracao de conexao e inicializacao
	models.py    # Modelos SQLAlchemy
```
