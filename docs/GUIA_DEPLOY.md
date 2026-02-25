# Guia de Deploy — inDigitall BI Platform

## Resumen

La plataforma se despliega automaticamente al hacer `git push` a la rama `main`. Tambien se puede hacer deploy manual desde GitHub o desde cualquier dispositivo con acceso a Git.

---

## Metodo 1: Deploy Automatico (GitHub Actions)

### Como funciona

```
git push origin main  →  GitHub Actions  →  SSH a VM  →  App actualizada
```

Cada push a `main` dispara automaticamente:
1. Pull del codigo en la VM
2. Build del contenedor Docker
3. Restart de los servicios
4. Migraciones de base de datos
5. Health check
6. Pipeline ETL (transform_bridge)

### Verificar el deploy

1. Ir a: **https://github.com/henrysaenz-rocket/indigitall-bi-plataform/actions**
2. Ver el workflow "Deploy to GCP VM"
3. Debe mostrar un check verde si fue exitoso

### Deploy manual desde GitHub (sin terminal)

1. Ir a: **https://github.com/henrysaenz-rocket/indigitall-bi-plataform/actions**
2. Click en **"Deploy to GCP VM"** en el panel izquierdo
3. Click en **"Run workflow"** → **"Run workflow"**
4. Esperar ~2 minutos

Este metodo funciona desde **cualquier dispositivo con navegador** (PC, tablet, celular).

---

## Metodo 2: Deploy desde Terminal (cualquier PC)

### Requisitos

- Git instalado
- Acceso al repositorio (push a `main`)

### Pasos

```bash
# 1. Clonar (solo la primera vez)
git clone https://github.com/henrysaenz-rocket/indigitall-bi-plataform.git
cd indigitall-bi-plataform

# 2. Hacer cambios, commit y push
git add .
git commit -m "Descripcion del cambio"
git push origin main
# → GitHub Actions se encarga del deploy automaticamente
```

### Desde un PC nuevo (sin el repo clonado)

```bash
# Autenticarse con GitHub CLI
gh auth login

# Clonar y push
git clone https://github.com/henrysaenz-rocket/indigitall-bi-plataform.git
cd indigitall-bi-plataform
# ... hacer cambios ...
git push origin main
```

---

## Metodo 3: Deploy directo a la VM (SSH)

### Requisitos

- gcloud CLI instalado y autenticado (`gcloud auth login`)
- Permisos SSH en el proyecto GCP `trax-report-automation`

### Pasos

```bash
# Conectarse a la VM
gcloud compute ssh indigitall-analytics \
  --project=trax-report-automation \
  --zone=southamerica-east1-a

# Dentro de la VM, ejecutar deploy
cd /opt/indigitall-analytics
bash scripts/deploy/deploy.sh
```

### Deploy remoto (sin entrar a la VM)

```bash
gcloud compute ssh indigitall-analytics \
  --project=trax-report-automation \
  --zone=southamerica-east1-a \
  --command="cd /opt/indigitall-analytics && bash scripts/deploy/deploy.sh"
```

---

## Sincronizacion entre repos

El proyecto tiene dos repositorios conectados:

| Repo | Rol | URL |
|---|---|---|
| **henrysaenz-rocket** (origin) | Tu fork — push aqui | github.com/henrysaenz-rocket/indigitall-bi-plataform |
| **edelae** (upstream) | Repo original de Ernesto | github.com/edelae/indigitall-bi-plataform |

### Sincronizar con el repo de Ernesto

```bash
# Traer cambios de Ernesto
git fetch upstream
git merge upstream/main
git push origin main  # → dispara deploy automatico

# Enviar cambios a Ernesto
git push upstream main
```

---

## Infraestructura

| Componente | Detalle |
|---|---|
| **VM** | `indigitall-analytics` (GCP, zona `southamerica-east1-a`) |
| **IP** | `34.151.199.149` |
| **Proyecto GCP** | `trax-report-automation` |
| **Reverse Proxy** | Caddy (TLS automatico con Let's Encrypt) |
| **Contenedores** | Docker Compose |
| **CI/CD** | GitHub Actions (`deploy.yml`) |

### URLs de produccion

| Servicio | URL |
|---|---|
| App BI | `https://analytics.abstractstudio.co` |
| n8n | `https://n8n-indigitall.abstractstudio.co` |
| Studio | `https://studio-indigitall.abstractstudio.co` |

---

## Que hace el script de deploy (deploy.sh)

```
[1/5] git pull --ff-only
[2/5] docker compose build --no-cache app
[3/5] docker compose up -d
[4/5] Migraciones (create_tables)
[5/5] ETL pipeline (transform_bridge.py)
+ Health check (localhost:8050/health)
+ Log en deploy.log
```

Tiempo estimado: ~2 minutos.

---

## Troubleshooting

### El deploy fallo en GitHub Actions

1. Ir a **Actions** → click en el workflow fallido → ver logs
2. Errores comunes:
   - `missing server host` → los secrets no estan configurados
   - `Permission denied` → la SSH key no esta en la VM
   - `Timeout` → la VM esta apagada o sin red

### La app no responde despues del deploy

```bash
# Conectarse a la VM y revisar logs
gcloud compute ssh indigitall-analytics \
  --project=trax-report-automation \
  --zone=southamerica-east1-a

# Dentro de la VM:
cd /opt/indigitall-analytics
docker compose logs app --tail 50
docker compose ps
```

### Hacer rollback

```bash
# En tu PC local
git revert HEAD
git push origin main
# → GitHub Actions despliega la version anterior
```

---

## Configuracion inicial (una sola vez)

### GitHub Secrets (ya configurados)

| Secret | Estado |
|---|---|
| `GCP_SSH_PRIVATE_KEY` | Configurado |
| `GCP_VM_HOST` | Configurado (`34.151.199.149`) |
| `GCP_VM_USER` | Configurado (`hsaenz`) |

### Pendiente: SSH Key en la VM

Ernesto debe ejecutar:

```bash
gcloud compute instances add-metadata indigitall-analytics \
  --project=trax-report-automation \
  --zone=southamerica-east1-a \
  --metadata=ssh-keys="hsaenz:ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCwnYMUWVPDc6X4Ln2blhzheFvnD+Fgf/p9YgD6eL17SRO9scWMHUh8eaL/4YVhArlbBdVPIYJ5Yf8La84aRqdrMTlBJzEFxUINdvTublxA9bj1ELysfk3o8lPhMy0QHFCAMYCLaJpvd5OLIqHFJSYN6U2BwVZuSGWOolz/IacSrp2r767l9HMLPQzn76s2MNvKyvVLJb7S6RrX5ucTy119wgC7lZjsXlMyO5DeiTWOp4R+k+bsyHqRjvfWqSkg95cuvqM6YvC/JxabXqftEuTTQCbiY2OAlrUFyQVtJi1rdNoxUkkm5bpVEANSusRgIMxTaPips68SMHyiLnGaLdu9 hsaenz@rocketst.co
hsaenz:ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICoIdNSNCpiLaANtvEpTvDWbfg7+GMysRbQo1eqAK2vK github-actions-deploy"
```

Una vez hecho esto, el deploy automatico funciona sin intervencion.
