"""[ETIQUETA: MODULO-BACKEND-SQL]
Gestor SQLite de referencia, compatible con los contratos descritos en el handoff.
Integrar tras comparar con la implementación original de main.py.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from time import perf_counter
from typing import Any


def _solo_comentarios(texto: str) -> bool:
    """Ignora instrucciones compuestas únicamente por comentarios SQL."""
    texto = re.sub(r"/\*.*?\*/", "", texto, flags=re.DOTALL)
    texto = re.sub(r"--[^\n]*", "", texto)
    return not texto.strip()


def _separar_sentencias(texto: str) -> list[str]:
    """Divide cuando SQLite confirma un ; final válido (no en literales)."""
    sentencias: list[str] = []
    actual: list[str] = []
    for caracter in texto:
        actual.append(caracter)
        if caracter == ";":
            posible = "".join(actual)
            if sqlite3.complete_statement(posible):
                if not _solo_comentarios(posible):
                    sentencias.append(posible.strip())
                actual.clear()
    pendiente = "".join(actual).strip()
    if pendiente and not _solo_comentarios(pendiente):
        # SQLite permite enviar una sentencia sin ; final.
        sentencias.append(pendiente)
    return sentencias


def _primer_token(sql: str) -> str:
    """Determina la operación omitiendo comentarios iniciales."""
    restante = sql.lstrip()
    while True:
        if restante.startswith("--"):
            _, _, restante = restante.partition("\n")
            restante = restante.lstrip()
        elif restante.startswith("/*"):
            final = restante.find("*/")
            if final < 0:
                return ""
            restante = restante[final + 2:].lstrip()
        else:
            break
    encontrado = re.match(r"[A-Za-z]+", restante)
    return encontrado.group(0).upper() if encontrado else ""


class SQLDatabaseManager:
    """Conexión a archivo SQLite y ejecución de sentencias SQL con transacción."""

    def __init__(self) -> None:
        self.connection: sqlite3.Connection | None = None
        self.db_path: str | None = None

    def connect(self, db_path: str) -> dict[str, Any]:
        """Abre una BD persistente (salvo si el usuario elige :memory:)."""
        self.disconnect()
        ruta = str(db_path).strip()
        if not ruta:
            return {"success": False, "message": "Indica la ruta del archivo SQLite."}
        try:
            if ruta != ":memory:":
                ruta = str(Path(ruta).expanduser().resolve())
            # Modo de diario de SQLite predeterminado; no forzar MEMORY.
            conexion = sqlite3.connect(ruta, timeout=10, isolation_level=None)
            conexion.execute("PRAGMA foreign_keys = ON")
            conexion.execute("PRAGMA busy_timeout = 3000")
            version = conexion.execute("SELECT sqlite_version()").fetchone()[0]
            self.connection = conexion
            self.db_path = ruta
            return {
                "success": True,
                "message": f"[SQL CONECTADO] SQLite v{version} | Archivo: '{ruta}'",
                "version": version,
            }
        except (sqlite3.Error, OSError, ValueError) as error:
            self.connection = None
            self.db_path = None
            return {"success": False, "message": f"[ERROR SQL] No se pudo conectar: {error}"}

    def disconnect(self) -> None:
        """Cierra la conexión actual y limpia su estado."""
        if self.connection is not None:
            try:
                self.connection.close()
            finally:
                self.connection = None
                self.db_path = None

    def execute_query(self, raw_query: str) -> dict[str, Any]:
        """Ejecuta una o varias sentencias de forma atómica, muestra última tabla."""
        inicio = perf_counter()
        base = {"success": False, "category": "SQL", "columns": [], "rows": []}
        if self.connection is None:
            return {**base, "message": "[ERROR SQL] Conecta una base de datos primero.", "elapsed_ms": 0.0}
        if not isinstance(raw_query, str):
            return {**base, "message": "[ERROR SQL] La consulta debe ser texto.", "elapsed_ms": 0.0}
        comandos = _separar_sentencias(raw_query)
        if not comandos:
            return {**base, "message": "[ERROR SQL] No hay sentencias que ejecutar.", "elapsed_ms": 0.0}
        token = _primer_token(comandos[0])
        if token in {"CREATE", "ALTER", "DROP"}:
            categoria = f"DDL ({token})"
        elif token in {"INSERT", "UPDATE", "DELETE", "REPLACE", "SELECT", "WITH"}:
            categoria = f"DML ({token})"
        elif token in {"PRAGMA", "EXPLAIN"}:
            categoria = f"CONSULTA ({token})"
        else:
            categoria = f"SQL ({token or 'OTRO'})"
        resultado = {**base, "category": categoria}
        tokens = [_primer_token(c) for c in comandos]
        if any(t in {"BEGIN", "COMMIT", "ROLLBACK", "SAVEPOINT", "RELEASE", "END"} for t in tokens):
            return {**resultado, "message": "[ERROR SQL] La transacción es administrada automáticamente.", "elapsed_ms": 0.0}
        if len(comandos) > 1 and any(t == "PRAGMA" for t in tokens):
            return {**resultado, "message": "[ERROR SQL] Ejecuta PRAGMA por separado del script.", "elapsed_ms": 0.0}
        columnas: list[str] = []
        filas: list[list[Any]] = []
        filas_modificadas = 0
        cursor = self.connection.cursor()
        transaccion = not (len(comandos) == 1 and token == "PRAGMA")
        try:
            if transaccion:
                self.connection.execute("BEGIN")
            for sentencia in comandos:
                cursor.execute(sentencia)
                if cursor.description is not None:
                    columnas = [campo[0] for campo in cursor.description]
                    filas = [list(fila) for fila in cursor.fetchall()]
                else:
                    columnas, filas = [], []
                if cursor.rowcount > 0:
                    filas_modificadas += cursor.rowcount
            if transaccion:
                self.connection.commit()
            elapsed = round((perf_counter() - inicio) * 1000, 2)
            if columnas:
                mensaje = f"[OK - {categoria}] Se recuperaron {len(filas)} registro(s) en {elapsed} ms."
            else:
                mensaje = f"[OK - {categoria}] {len(comandos)} sentencia(s) ejecutada(s); {filas_modificadas} fila(s) afectada(s). ({elapsed} ms)"
            return {
                **resultado, "success": True, "message": mensaje,
                "columns": columnas, "rows": filas, "elapsed_ms": elapsed,
            }
        except sqlite3.Error as error:
            if transaccion:
                self.connection.rollback()
            return {
                **resultado,
                "message": f"[ERROR SQL - {categoria}] {error}",
                "elapsed_ms": round((perf_counter() - inicio) * 1000, 2),
            }
        finally:
            cursor.close()

    def list_tables(self) -> list[str]:
        """Muestra únicamente las tablas de usuario, no sqlite_sequence."""
        if self.connection is None:
            return []
        return [fila[0] for fila in self.connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        ).fetchall()]
