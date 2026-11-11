from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Column, Date, ForeignKey, Numeric, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


alimento_insumo = Table(
    "alimento_insumo",
    Base.metadata,
    Column("alimento_id", ForeignKey("alimentos.id", ondelete="CASCADE"), primary_key=True),
    Column("insumo_id", ForeignKey("insumos.id", ondelete="RESTRICT"), primary_key=True),
)


class Alimento(Base):
    __tablename__ = "alimentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    preco_venda: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    insumos: Mapped[list["Insumo"]] = relationship(secondary=alimento_insumo, back_populates="alimentos")


class Insumo(Base):
    __tablename__ = "insumos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    unidade: Mapped[str] = mapped_column(String(30), nullable=False)
    observacoes: Mapped[str | None] = mapped_column(Text)
    alimentos: Mapped[list[Alimento]] = relationship(secondary=alimento_insumo, back_populates="insumos")


class Doador(Base):
    __tablename__ = "doadores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    telefone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(160))
    observacoes: Mapped[str | None] = mapped_column(Text)
    doacoes: Mapped[list["Doacao"]] = relationship(back_populates="doador")


class Trabalhador(Base):
    __tablename__ = "trabalhadores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    perfil: Mapped[str] = mapped_column(String(30), nullable=False)
    funcao: Mapped[str] = mapped_column(String(100), nullable=False)
    telefone: Mapped[str | None] = mapped_column(String(30))
    disponibilidade: Mapped[str | None] = mapped_column(String(160))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Doacao(Base):
    __tablename__ = "doacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    insumo_id: Mapped[int] = mapped_column(ForeignKey("insumos.id", ondelete="RESTRICT"), nullable=False)
    doador_id: Mapped[int] = mapped_column(ForeignKey("doadores.id", ondelete="RESTRICT"), nullable=False)
    quantidade: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    data_doacao: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    observacoes: Mapped[str | None] = mapped_column(Text)
    insumo: Mapped[Insumo] = relationship()
    doador: Mapped[Doador] = relationship(back_populates="doacoes")