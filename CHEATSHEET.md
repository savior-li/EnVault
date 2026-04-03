# EnVault Cheatsheet

## Comandos Esenciales

```bash
envault backup              # Respaldo completo
envault backup /path       # Respaldo directorio
envault backup --encrypt   # Con cifrado
envault backup --format zip  # Formato zip

envault restore <archivo>   # Restaurar
envault restore a.tar.gz /tmp/restore  # A directorio

envault list               # Ver instantáneas
envault prune 5            # Mantener 5

envault init               # Crear config
envault config             # Ver config
```

## Configuración Rápida

```yaml
backup_dirs:
  - path: ~/.openclaw
    name: openclaw

exclude_patterns:
  - "*.log"
  - "__pycache__"
  - "node_modules"

compression: tar.gz
encryption:
  enabled: false
cloud_upload:
  catbox: true
  tmpfiles: true
```

## Variables de Entorno

```bash
export RESTIC_PASSWORD="password"
export GPG_PASSWORD="password"
export ENVAULT_LANG=es
```

## Patrones de Exclusión

| Patrón | Descripción |
|--------|-------------|
| `*.log` | Archivos de log |
| `*.tmp` | Archivos temporales |
| `__pycache__` | Caché Python |
| `.git` | Repositorios Git |
| `node_modules` | Dependencias npm |

## Compresión

| Formato | Compresión | Velocidad |
|---------|------------|-----------|
| tar.gz | Media | Rápida |
| tar.bz2 | Alta | Media |
| tar.xz | Muy alta | Lenta |
| zip | Media | Media |

## Cloud Storage

| Servicio | URL | Tamaño | Auth |
|----------|-----|--------|------|
| Catbox | catbox.moe | 200MB | No |
| Tmpfiles | tmpfiles.org | 200MB | No |
| Uguu | uguu.se | - | No |
| Gofile | gofile.io | Sin límite | Sí |

## Restic

```bash
# Ver instantáneas
restic snapshots --repo ~/.envault/restic

# Restaurar
restic restore latest --repo ~/.envault/restic --target /ruta

# Verificar
restic check --repo ~/.envault/restic

# Clave
restic init --repo ~/.envault/restic
```

## Cron

```bash
# Cada hora
0 * * * * /path/to/envault backup

# Cada 10 min
*/10 * * * * /path/to/envault backup

# Diario 3am
0 3 * * * /path/to/envault backup
```

## GPG

```bash
# Cifrar
gpg --symmetric archivo.tar.gz

# Descifrar
gpg --decrypt archivo.tar.gz.gpg > archivo.tar.gz

# Con receptor
gpg --recipient email@.com --encrypt archivo.tar.gz
```

## Solución de Problemas

```bash
# Modo debug
bash -x envault backup

# Ver logs
cat ~/.envault/logs/backup.log

# Verificar permisos
ls -la ~/.envault/
chmod 700 ~/.envault
```