"""Areas de la organizacion (lista fija). El area es un dato de la ORGANIZACION (a que area
pertenece un buzon), no del correo: no se guarda nada nuevo de los mensajes."""

DEFAULT = "Sin área"
DEPARTMENTS = (
    "Gerencia/Dirección",
    "Finanzas",
    "Recursos Humanos",
    "Ventas y Compras",
    "Operaciones y Logística",
    "IT y Sistemas",
)
ALLOWED = DEPARTMENTS + (DEFAULT,)


def clean(value: str | None) -> str:
    """Devuelve el area si esta en la lista; si no, el valor por defecto."""
    return value if value in ALLOWED else DEFAULT


def is_valid(value: str | None) -> bool:
    return value in ALLOWED
