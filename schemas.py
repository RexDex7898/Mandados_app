from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from decimal import Decimal
# --- USUARIOS ---
class UsuarioRegistro(BaseModel):
    nombre: str
    telefono: str
    password: str
    rol: str = "cliente"

class UsuarioLogin(BaseModel):
    telefono: str
    password: str

class UsuarioResponse(BaseModel):
    id: str
    nombre: str
    telefono: str
    rol: str

    class Config:
        from_attributes = True

# --- PEDIDOS ---
class PedidoCreate(BaseModel):
    cliente_id: Optional[str] = None
    cliente_nombre: str
    cliente_telefono: str
    cliente_fcm_token: Optional[str] = None  # <-- Recibe el token del celular
    descripcion: str
    origen_direccion: Optional[str] = None
    origen_lat: Optional[float] = None
    origen_lng: Optional[float] = None
    destino_direccion: str
    destino_lat: Optional[float] = None
    destino_lng: Optional[float] = None
    costo_productos: float = 0.0
    metodo_pago: str = "efectivo"
    tipo: str = "mandado"

class PedidoTomar(BaseModel):
    repartidor_id: str
    repartidor_nombre: str
    repartidor_telefono: str

class PedidoUpdateEstado(BaseModel):
    estado: str

class PedidoResponse(BaseModel):
    id: str
    cliente_id: Optional[str]
    cliente_nombre: str
    cliente_telefono: str
    cliente_fcm_token: Optional[str] = None
    repartidor_id: Optional[str] = None
    repartidor_nombre: Optional[str] = None
    repartidor_telefono: Optional[str] = None
    descripcion: str
    origen_direccion: Optional[str]
    origen_lat: Optional[float]
    origen_lng: Optional[float]
    destino_direccion: str
    destino_lat: Optional[float]
    destino_lng: Optional[float]
    costo_productos: float
    costo_envio: float
    metodo_pago: str
    tipo: str
    estado: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True