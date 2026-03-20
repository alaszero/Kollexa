#!/bin/bash
# Kollexa - Script de backup de base de datos SQLite
# Uso: bash scripts/backup.sh [directorio_destino]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DB_PATH="${PROJECT_DIR}/instance/kollexa.db"
BACKUP_DIR="${1:-${PROJECT_DIR}/backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/kollexa_${TIMESTAMP}.db"
MAX_BACKUPS=30  # Mantener últimos 30 backups

# Verificar que existe la BD
if [ ! -f "$DB_PATH" ]; then
    echo "ERROR: No se encontró la base de datos en ${DB_PATH}"
    exit 1
fi

# Crear directorio de backups si no existe
mkdir -p "$BACKUP_DIR"

# Hacer backup usando SQLite .backup (seguro incluso con BD en uso)
echo "Creando backup: ${BACKUP_FILE}"
sqlite3 "$DB_PATH" ".backup '${BACKUP_FILE}'"

# Verificar integridad del backup
echo "Verificando integridad..."
INTEGRITY=$(sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;" 2>&1)
if [ "$INTEGRITY" != "ok" ]; then
    echo "ERROR: El backup falló la verificación de integridad"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Comprimir
echo "Comprimiendo..."
gzip "$BACKUP_FILE"
echo "Backup creado: ${BACKUP_FILE}.gz ($(du -h "${BACKUP_FILE}.gz" | cut -f1))"

# Rotación: eliminar backups antiguos
BACKUP_COUNT=$(ls -1 "${BACKUP_DIR}"/kollexa_*.db.gz 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt "$MAX_BACKUPS" ]; then
    EXCESS=$((BACKUP_COUNT - MAX_BACKUPS))
    echo "Eliminando ${EXCESS} backup(s) antiguo(s)..."
    ls -1t "${BACKUP_DIR}"/kollexa_*.db.gz | tail -n "$EXCESS" | xargs rm -f
fi

echo "Backup completado exitosamente."
