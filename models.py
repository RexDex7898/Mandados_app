from sqlalchemy import Column, String, Float, DateTime, Text
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
    cliente_nombre = Column(String(100), nullable=False)
    cliente_telefono = Column(String(15), nullable=False)
    cliente_fcm_token = Column(String(255), nullable=True)  # <-- Token FCM del cliente
    
    repartidor_id = Column(String(36), nullable=True)
    repartidor_nombre = Column(String(100), nullable=True)
    repartidor_telefono = Column(String(15), nullable=True)

    descripcion = Column(Text, nullable=False)
    origen_direccion = Column(String(255), nullable=True)
    origen_lat = Column(Float, nullable=True)
    origen_lng = Column(Float, nullable=True)
    destino_direccion = Column(String(255), nullable=False)
    destino_lat = Column(Float, nullable=True)
    destino_lng = Column(Float, nullable=True)

    costo_productos = Column(Float, default=0.0)
    costo_envio = Column(Float, default=35.0)
    metodo_pago = Column(String(20), default="efectivo")
    tipo = Column(String(30), default="mandado")
    estado = Column(String(30), default="buscando_repartidor")
    created_at = Column(DateTime(timezone=True), server_default=func.now())