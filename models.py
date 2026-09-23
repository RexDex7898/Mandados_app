from sqlalchemy import Column, String, Numeric, DateTime, Enum
from sqlalchemy.sql import func
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(String(36), primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    telefono = Column(String(15), unique=True, index=True, nullable=False)
    password_hash = Column(String(64), nullable=False)
    rol = Column(String(20), default="cliente")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(String(36), primary_key=True, index=True)
    cliente_id = Column(String(36), nullable=True)
    cliente_nombre = Column(String(100), nullable=True)
    cliente_telefono = Column(String(15), nullable=True)
    
    repartidor_id = Column(String(36), nullable=True)
    repartidor_nombre = Column(String(100), nullable=True)
    repartidor_telefono = Column(String(15), nullable=True)

    descripcion = Column(String(255), nullable=False)
    origen_direccion = Column(String(255), nullable=False)
    origen_lat = Column(Numeric(10, 7), nullable=True)
    origen_lng = Column(Numeric(10, 7), nullable=True)
    destino_direccion = Column(String(255), nullable=False)
    destino_lat = Column(Numeric(10, 7), nullable=True)
    destino_lng = Column(Numeric(10, 7), nullable=True)
    costo_envio = Column(Numeric(10, 2), default=35.00)
    costo_productos = Column(Numeric(10, 2), default=0.00)
    metodo_pago = Column(String(30), default="efectivo")
    estado = Column(String(50), default="buscando_repartidor")
    tipo = Column(String(50), default="mandado_express")
    created_at = Column(DateTime(timezone=True), server_default=func.now())