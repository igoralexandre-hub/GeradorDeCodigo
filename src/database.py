import os
import ssl
from pathlib import Path
from typing import Any

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_DATABASE = PROJECT_ROOT / "data" / "festa_ifc.db"
CONNECTION_TIMEOUT_SECONDS = 10


class DatabaseConfigurationError(ValueError):
    pass


class DatabaseConnectionError(RuntimeError):
    pass


class Base(DeclarativeBase):
    pass


def _secrets() -> Any:
    try:
        return dict(st.secrets)
    except (FileNotFoundError, AttributeError, StreamlitSecretNotFoundError):
        return {}


def _tidb_settings() -> dict[str, Any]:
    secrets = _secrets()
    configured = secrets.get("tidb", {})
    return {
        "host": os.getenv("TIDB_HOST") or configured.get("host"),
        "port": os.getenv("TIDB_PORT") or configured.get("port", 4000),
        "user": os.getenv("TIDB_USER") or configured.get("user"),
        "password": os.getenv("TIDB_PASSWORD") or configured.get("password"),
        "database": os.getenv("TIDB_DATABASE") or configured.get("database"),
        "ssl_ca_file": (
            os.getenv("TIDB_SSL_CA_FILE")
            or configured.get("ssl_ca_file")
            or configured.get("ca_path")
        ),
        "ssl_ca_cert": os.getenv("TIDB_SSL_CA_CERT") or configured.get("ssl_ca_cert"),
    }


def get_database_url() -> URL:
    secrets = _secrets()
    configured_url = os.getenv("DATABASE_URL") or secrets.get("DATABASE_URL")
    if configured_url:
        url = make_url(configured_url)
        if url.drivername == "mysql":
            url = url.set(drivername="mysql+pymysql")
        if url.drivername.startswith("mysql") and url.password is None:
            password = _tidb_settings()["password"]
            if password is not None:
                url = url.set(password=password)
        return url

    backend = (
        os.getenv("DATABASE_BACKEND")
        or secrets.get("DATABASE_BACKEND")
        or ("tidb" if os.getenv("TIDB_HOST") or secrets.get("tidb") else "sqlite")
    ).lower()

    if backend in {"tidb", "mysql"}:
        config = _tidb_settings()
        required = ("host", "user", "password", "database")
        missing = [key for key in required if not config[key]]
        if missing:
            raise DatabaseConfigurationError(
                "Configuracao TiDB incompleta. Verifique os campos: " + ", ".join(missing)
            )
        try:
            port = int(config["port"])
        except (TypeError, ValueError) as error:
            raise DatabaseConfigurationError("TIDB_PORT deve ser um numero inteiro.") from error

        return URL.create(
            "mysql+pymysql",
            username=config["user"],
            password=config["password"],
            host=config["host"],
            port=port,
            database=config["database"],
        )

    if backend != "sqlite":
        raise DatabaseConfigurationError(
            "DATABASE_BACKEND deve ser 'sqlite' ou 'tidb'."
        )

    LOCAL_DATABASE.parent.mkdir(parents=True, exist_ok=True)
    return URL.create("sqlite", database=LOCAL_DATABASE.as_posix())


def _tls_context() -> ssl.SSLContext:
    config = _tidb_settings()
    if config["ssl_ca_file"] and config["ssl_ca_cert"]:
        raise DatabaseConfigurationError(
            "Configure somente um entre TIDB_SSL_CA_FILE e TIDB_SSL_CA_CERT."
        )

    ca_file = config["ssl_ca_file"]
    if ca_file:
        ca_path = Path(ca_file).expanduser()
        if not ca_path.is_absolute():
            ca_path = PROJECT_ROOT / ca_path
        if not ca_path.is_file():
            raise DatabaseConfigurationError(
                "O arquivo CA configurado para o TiDB Cloud nao foi encontrado."
            )
        ca_file = str(ca_path)

    context = ssl.create_default_context(
        cafile=ca_file,
        cadata=config["ssl_ca_cert"],
    )
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    return context


def create_database_engine() -> Engine:
    url = get_database_url()
    options: dict[str, Any] = {"pool_pre_ping": True}
    if url.drivername.startswith("mysql"):
        options.update(
            pool_size=5,
            max_overflow=10,
            pool_recycle=1800,
            pool_timeout=30,
            connect_args={"connect_timeout": CONNECTION_TIMEOUT_SECONDS, "ssl": _tls_context()},
        )
    elif url.drivername == "sqlite":
        options["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **options)


engine = create_database_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def initialize_database() -> None:
    import models

    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as error:
        raise DatabaseConnectionError(
            "Nao foi possivel inicializar o banco. Confira endpoint, porta, credenciais e acesso de rede."
        ) from error


def _connection_error_message(error: Exception) -> str:
    original = getattr(error, "orig", error)
    arguments = getattr(original, "args", ())
    error_code = arguments[0] if arguments and isinstance(arguments[0], int) else None
    details = " ".join(str(argument) for argument in arguments[1:]).lower()

    if isinstance(original, ssl.SSLError) or error_code == 2026 or any(
        marker in details for marker in ("ssl", "tls", "certificate", "handshake")
    ):
        return "Erro de TLS/certificado. Verifique o CA, o hostname e os requisitos TLS do cluster."

    if error_code in {1044, 1045, 1130, 1698} or any(
        marker in details for marker in ("access denied", "authentication", "password")
    ):
        return "Erro de autenticacao. Verifique usuario, senha e permissoes no TiDB Cloud."

    if error_code == 1049 or "unknown database" in details:
        return "Banco de dados nao encontrado. Verifique o schema configurado no TiDB Cloud."

    if error_code in {2002, 2003, 2005, 2013, 2026, 2055} or any(
        marker in details for marker in ("timed out", "connection refused", "name or service not known")
    ):
        return "Erro de rede. Verifique endpoint, porta, DNS e regras de acesso do cluster."

    return "Erro de conexao nao classificado. Verifique o estado e a configuracao do cluster."


def test_connection() -> tuple[bool, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "Conexao com o banco realizada com sucesso."
    except Exception as error:
        return False, _connection_error_message(error)