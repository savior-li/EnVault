# Manual de EnVault

## Tabla de Contenidos

1. [Introducción](#introducción)
2. [Instalación](#instalación)
3. [Inicio Rápido](#inicio-rápido)
4. [Configuración](#configuración)
5. [Comandos](#comandos)
6. [Funciones Avanzadas](#funciones-avanzadas)
7. [Respaldo Programado](#respaldo-programado)
8. [Solución de Problemas](#solución-de-problemas)

---

## Introducción

### ¿Qué es EnVault?

EnVault es una herramienta de respaldo para entornos de desarrollo que resuelve:

- Pérdida de datos después de reiniciar entornos en la nube (GitHub Codespaces, Replit)
- Pérdida de configuración por reinicio de sandbox
- Necesidad de sincronizar entornos de desarrollo entre dispositivos

### Características

| Característica | Descripción |
|----------------|-------------|
| Respaldo multi-directorio | Respaldar múltiples directorios |
| Exclusiones inteligentes | Ignorar archivos temporales, logs, etc. |
| Cifrado de respaldo | Protección GPG para datos sensibles |
| Múltiples formatos | tar.gz, tar.bz2, tar.xz, zip |
| Instantáneas incrementales | Restic para versionado eficiente |
| Carga multi-nube | Catbox, Tmpfiles, Uguu, Gofile |
| Multi-idioma | English, 中文, Español |

### Cómo Funciona

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Origen     │ ──▶ │   EnVault    │ ──▶ │  Respaldo Local │
│ ~/.openclaw │     │  (empaquetar+ cifrar)│   ~/.envault/    │
└─────────────┘     └──────────────┘     └─────────────────┘
                                                  │
                    ┌─────────────────────────────┼─────────────────────────────┐
                    ▼                             ▼                             ▼
             ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
             │   Catbox    │            │   Tmpfiles  │            │    Uguu     │
             │ catbox.moe  │            │ tmpfiles.org│            │   uguu.se   │
             └─────────────┘            └─────────────┘            └─────────────┘
```

---

## Instalación

### Requisitos

- Linux / macOS / Windows (WSL)
- Python 3.8+ o Bash 4.0+
- Dependencias: tar, curl, gpg (para cifrado), restic (para instantáneas)

### Instalar

#### Método 1: Descargar Script (Recomendado)

```bash
mkdir -p ~/bin
curl -fsSL https://raw.githubusercontent.com/savior-li/EnVault/main/src/envault.py -o ~/bin/envault
chmod +x ~/bin/envault
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### Método 2: Clonar Repositorio

```bash
git clone https://github.com/savior-li/EnVault.git ~/envault
cd ~/envault
```

#### Método 3: pip Install

```bash
pip install envault
```

### Instalar Dependencias

```bash
# Ubuntu/Debian
apt update && apt install -y tar curl gpg restic

# macOS
brew install curl gpg restic

# Dependencias Python
pip install requests pyyaml
```

---

## Inicio Rápido

### 1. Inicializar Configuración

```bash
envault init
```

Crea configuración en `~/.config/envault/config.yaml`.

### 2. Editar Configuración

```bash
nano ~/.config/envault/config.yaml
```

Ejemplo básico:

```yaml
backup_dirs:
  - path: ~/.openclaw
    name: openclaw
  - path: ~/projects
    name: mis-proyectos

exclude_patterns:
  - "*.log"
  - "__pycache__"
  - "node_modules"
  - ".git"

compression: tar.gz
encryption:
  enabled: false
cloud_upload:
  catbox: true
  tmpfiles: true
```

### 3. Ejecutar Respaldo

```bash
envault backup
```

Salida:

```
[2026-04-03 12:00:00] Starting backup process...
[2026-04-03 12:00:02] Backup complete: /root/.envault/envault-20260403-120002.tar.gz
[2026-04-03 12:00:03] Upload successful: https://catbox.moe/xxx.gz
```

### 4. Ver Enlaces de Respaldo

```bash
cat ~/.envault/links-*.json | tail -1
```

### 5. Restaurar Respaldo

```bash
envault restore ~/.envault/envault-20260403-120002.tar.gz
```

---

## Configuración

### Configuración Completa

```yaml
# Directorios de respaldo
backup_dirs:
  - path: ~/.openclaw
    name: openclaw
  - path: ~/projects/myapp
    name: miapp

# Patrones de exclusión
exclude_patterns:
  - "*.log"
  - "*.tmp"
  - "__pycache__"
  - ".git"
  - "node_modules"
  - ".cache"

# Compresión: tar.gz, tar.bz2, tar.xz, zip
compression: tar.gz

# Cifrado
encryption:
  enabled: false
  # recipient: tu@email.com  # Para cifrado asimétrico

# Carga a la nube (true/false)
cloud_upload:
  catbox: true      # https://catbox.moe (sin auth, 200MB máx)
  tmpfiles: true    # https://tmpfiles.org (sin auth)
  gofile: false     # https://gofile.io (necesita token API)
  uguu: false       # https://uguu.se (sin auth)

# Instantáneas Restic
restic:
  enabled: true
  keep_last: 10

# Idioma: en, zh, es
language: es
```

### Prioridad de Configuración

Línea de comandos > Variables de entorno > Archivo config > Valores por defecto

---

## Comandos

### backup

```bash
envault backup                  # Respaldo completo (usa config)
envault backup /ruta           # Respaldo de directorio específico
envault backup --encrypt       # Habilitar cifrado
envault backup --format zip    # Especificar formato de compresión
envault backup --exclude "*.log"  # Agregar patrón de exclusión
```

### restore

```bash
envault restore respaldo.tar.gz              # Restaurar a predeterminado
envault restore respaldo.tar.gz /destino     # Restaurar a directorio específico
export GPG_PASSWORD="contraseña"
envault restore respaldo.tar.gz.gpg           # Restaurar respaldo cifrado
```

### list

```bash
envault list  # Requiere RESTIC_PASSWORD
```

### prune

```bash
envault prune       # Mantener últimos 10 (predeterminado)
envault prune 5     # Mantener últimos 5
```

### Otros Comandos

```bash
envault init     # Inicializar archivo de configuración
envault config   # Mostrar configuración actual
envault help     # Mostrar ayuda
```

---

## Funciones Avanzadas

### Cifrado GPG

#### Simétrico (Simple)

```bash
envault backup --encrypt
```

#### Asimétrico (Recomendado para equipos)

```bash
# Generar par de claves
gpg --full-generate-key

# Configurar en yaml
encryption:
  enabled: true
  recipient: tu@email.com

# O línea de comandos
envault backup --encrypt --recipient tu@email.com
```

#### Restaurar Descifrado

```bash
export GPG_PASSWORD="contraseña"
envault restore respaldo.tar.gz.gpg
```

### Estrategia Multi-Nube

| Nube | Caso de Uso | Límite | Auth |
|------|-------------|--------|------|
| Catbox | Almacenamiento largo plazo | 200MB/archivo | Ninguna |
| Tmpfiles | Compartisión temporal | 200MB/archivo | Ninguna |
| Uguu | Compartisión temporal | Sin límite claro | Ninguna |
| Gofile | Almacenamiento largo plazo | Sin límite | Token API |

### Instantáneas Restic

```bash
# Inicializar repositorio
export RESTIC_PASSWORD="contraseña"
restic init --repo ~/.envault/restic

# Ver instantáneas
restic snapshots --repo ~/.envault/restic

# Restaurar instantánea específica
restic restore latest --repo ~/.envault/restic --target /ruta/restaurar

# Verificar integridad
restic check --repo ~/.envault/restic
```

---

## Respaldo Programado

### Cron

```bash
crontab -e

# Cada hora
0 * * * * /ruta/a/envault backup >> ~/.envault/logs/cron.log 2>&1

# Cada 10 minutos
*/10 * * * * /ruta/a/envault backup

# Diario a las 3am
0 3 * * * /ruta/a/envault backup
```

### Systemd Timer (Linux)

```ini
# ~/.config/systemd/user/envault.service
[Unit]
Description=EnVault Backup

[Service]
Type=oneshot
Environment=BACKUP_DIR=%h/.envault
Environment=RESTIC_PASSWORD=tu-contraseña
ExecStart=/ruta/a/envault backup
```

```ini
# ~/.config/systemd/user/envault.timer
[Unit]
Description=EnVault Backup Timer

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now envault.timer
systemctl --user list-timers
```

---

## Solución de Problemas

### Problemas Comunes

#### P: "command not found"

```bash
# Verificar PATH
echo $PATH | grep -q "$HOME/bin" && echo "OK" || echo "Agregar a PATH"

# Ejecutar directamente
~/bin/envault backup
```

#### P: Archivo de respaldo muy grande

1. Verificar reglas de exclusión:
```bash
envault config
```

2. Agregar más exclusiones:
```bash
envault backup --exclude "*.mp4" --exclude "node_modules"
```

3. Usar mayor compresión:
```yaml
compression: tar.xz
```

#### P: Carga a la nube falló

1. Verificar red:
```bash
curl -I https://catbox.moe
```

2. Para Gofile, establecer variables:
```bash
export GOFILE_ACCOUNT_ID="tu-account-id"
export GOFILE_TOKEN="tu-token"
envault backup
```

#### P: Descifrado falló

```bash
export GPG_PASSWORD="contraseña"
gpg --batch --decrypt respaldo.tar.gz.gpg 2>&1 | head
```

#### P: Repositorio Restic corrupto

```bash
export RESTIC_PASSWORD="contraseña"
restic check --repo ~/.envault/restic
restic rebuild-index --repo ~/.envault/restic
```

### Modo Debug

```bash
# Versión Bash
bash -x envault backup

# Versión Python
python -v envault.py backup
```

---

## Variables de Entorno

| Variable | Requerido | Descripción |
|----------|-----------|-------------|
| `RESTIC_PASSWORD` | Para instantáneas | Contraseña repositorio Restic |
| `GPG_PASSWORD` | Para descifrar | Contraseña GPG |
| `GOFILE_ACCOUNT_ID` | Para Gofile | ID cuenta Gofile |
| `GOFILE_TOKEN` | Para Gofile | Token API Gofile |
| `ENVAULT_LANG` | No | Idioma (en/zh/es) |
| `BACKUP_DIR` | No | Directorio de respaldo |

---

## Estructura de Archivos

```
~/.envault/
├── restic/                    # Instantáneas Restic
│   ├── config
│   ├── data/
│   ├── index/
│   ├── snapshots/
│   └── ...
├── logs/                     # Archivos de log
├── links-*.json             # Enlaces de carga
└── *.tar.gz                # Respaldos locales

~/.config/envault/
└── config.yaml             # Archivo de configuración
```

---

## Licencia

MIT License

Copyright (c) 2026 EnVault