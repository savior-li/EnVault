# EnVault

**Herramienta de respaldo para entornos de desarrollo - instantáneas y carga a la nube**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Bash](https://img.shields.io/badge/Bash-4.0+-green.svg)](https://www.gnu.org/software/bash/)

Resuelve el problema de pérdida de datos después de reiniciar el entorno de desarrollo/sandbox.

## Características Principales

- **Respaldo multi-directorio** - Configuración YAML para múltiples directorios
- **Exclusiones inteligentes** - Ignora automáticamente `*.log`, `node_modules`, etc.
- **Cifrado de respaldo** - GPG simétrico/asimétrico
- **Múltiples formatos** - tar.gz, tar.bz2, tar.xz, zip
- **Instantáneas incrementales** - Restic para ahorro de espacio
- **Carga multi-nube** - Catbox, Tmpfiles, Gofile, Uguu
- **Multi-idioma** - English, 中文, Español

## Inicio Rápido

```bash
# 1. Instalar
curl -fsSL https://raw.githubusercontent.com/savior-li/backup-tool/main/src/envault.py -o ~/bin/envault
chmod +x ~/bin/envault

# 2. Inicializar configuración
envault init

# 3. Editar configuración
nano ~/.config/envault/config.yaml

# 4. Ejecutar respaldo
envault backup
```

## Plataformas Soportadas

| Plataforma | Soporte |
|-----------|---------|
| Linux | ✅ |
| macOS | ✅ |
| Windows (WSL) | ✅ |

## Documentación

- [Inicio Rápido](#inicio-rápido)
- [Manual Completo](MANUAL_es.md) - Configuración detallada, referencia de comandos, funciones avanzadas
- [English Manual](MANUAL_en.md)
- [中文手册](MANUAL_zh.md)

## Comandos

| Comando | Descripción |
|---------|-------------|
| `envault backup` | Respaldo completo (usa config) |
| `envault backup /ruta` | Respaldar directorio específico |
| `envault backup --encrypt` | Respaldo cifrado |
| `envault restore <archivo>` | Restaurar respaldo |
| `envault list` | Ver instantáneas Restic |
| `envault prune [n]` | Limpiar instantáneas antiguas |
| `envault init` | Inicializar configuración |
| `envault config` | Ver configuración |

## Variables de Entorno

| Variable | Requerido | Descripción |
|---------|-----------|-------------|
| `RESTIC_PASSWORD` | Para instantáneas | Contraseña repositorio Restic |
| `GPG_PASSWORD` | Para descifrar | Contraseña GPG |
| `GOFILE_ACCOUNT_ID` | Gofile | ID cuenta Gofile |
| `GOFILE_TOKEN` | Gofile | Token API Gofile |
| `ENVAULT_LANG` | No | Idioma (en/zh/es) |

## Dependencias

| Dependencia | Requerido | Descripción |
|-------------|-----------|-------------|
| tar | Sí | Compresión |
| curl | Sí | Cliente HTTP |
| gpg | Para cifrado | GPG |
| restic | Instantáneas | Respaldo incremental |
| python3 | Recomendado | Versión Python |
| requests | Versión Python | Biblioteca HTTP |
| pyyaml | Versión Python | Análisis YAML |

## License

MIT License

Copyright (c) 2026 EnVault