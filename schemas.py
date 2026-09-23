from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from decimal import Decimal

# --- USUARIOS & AUTH ---
class UsuarioRegistro(BaseModel):
    nombre: str
    telefono: str
    password: str
    rol: str = "cliente"  # "cliente" o "repartidor"

class UsuarioLogin(BaseModel):
    telefono: str
    password: str

class UsuarioResponse(BaseModel):
    id: str
    nombre: str
    telefono: str
    rol: str

    model_config = ConfigDict(from_attributes=True)

# --- PEDIDOS ---
class PedidoCreate(BaseModel):
    cliente_id: str
    cliente_nombre: str
    cliente_telefono: str
    descripcion: str
    origen_direccion: str
    origen_lat: Optional[float] = None
    origen_lng: Optional[float] = None
    destino_direccion: str
    destino_lat: Optional[float] = None
    destino_lng: Optional[float] = None
    costo_productos: Optional[Decimal] = Decimal("0.00")
    metodo_pago: Optional[str] = "efectivo"
    tipo: Optional[str] = "mandado_express"

class PedidoTomar(BaseModel):
    repartidor_id: str
    repartidor_nombre: str
    repartidor_telefono: str

class PedidoUpdateEstado(BaseModel):
    estado: str

class PedidoResponse(BaseModel):
    id: str
    cliente_id: Optional[str] = None
    cliente_nombre: Optional[str] = None
    cliente_telefono: Optional[str] = None
    repartidor_id: Optional[str] = None
    repartidor_nombre: Optional[str] = None
    repartidor_telefono: Optional[str] = None
    descripcion: str
    origen_direccion: str
    origen_lat: Optional[float] = None
    origen_lng: Optional[float] = None
    destino_direccion: str
    destino_lat: Optional[float] = None
    destino_lng: Optional[float] = None
    costo_envio: Decimal
    costo_productos: Decimal
    metodo_pago: str
    estado: str
    tipo: str
    created_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)