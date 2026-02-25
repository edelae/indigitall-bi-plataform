# Configuracion SSH para Deploy Automatico — URGENTE

## Que necesitamos

GitHub Actions necesita conectarse por SSH a la VM de GCP para hacer deploy automatico. Para esto, necesitamos agregar una **clave publica SSH especifica** a la VM.

---

## Quien debe ejecutar esto

**El administrador del proyecto GCP** (quien tenga el permiso `compute.instances.setMetadata` en el proyecto `trax-report-automation`).

---

## Paso a Paso

### Paso 1: Abrir Cloud Shell

1. Ir a: **https://console.cloud.google.com**
2. Iniciar sesion con la cuenta que administra el proyecto
3. Seleccionar el proyecto **`trax-report-automation`**
4. Click en el icono de terminal **`>_`** (Cloud Shell) en la barra superior derecha

```
┌─────────────────────────────────────────────────────┐
│  Google Cloud    trax-report-automation  ▼    >_     │
│                                                 ↑    │
│                                          Cloud Shell │
└─────────────────────────────────────────────────────┘
```

### Paso 2: Verificar el proyecto

En Cloud Shell, ejecutar:

```bash
gcloud config set project trax-report-automation
```

Debe responder:

```
Updated property [core/project].
```

### Paso 3: Ver las SSH keys actuales de la VM

```bash
gcloud compute instances describe indigitall-analytics \
  --zone=southamerica-east1-a \
  --format="value(metadata.items[0].value)"
```

Esto muestra las claves SSH que ya estan en la VM. **No las borres.**

### Paso 4: Agregar la clave de deploy

**IMPORTANTE:** Este comando agrega la nueva clave SIN eliminar las existentes.

Copiar y pegar **exactamente** este bloque:

```bash
# Primero, guardar las keys existentes
gcloud compute instances describe indigitall-analytics \
  --zone=southamerica-east1-a \
  --format="value(metadata.items[0].value)" > /tmp/existing_keys.txt

# Agregar la nueva key de deploy
echo "hsaenz:ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICoIdNSNCpiLaANtvEpTvDWbfg7+GMysRbQo1eqAK2vK github-actions-deploy" >> /tmp/existing_keys.txt

# Aplicar todas las keys (existentes + nueva)
gcloud compute instances add-metadata indigitall-analytics \
  --zone=southamerica-east1-a \
  --metadata-from-file=ssh-keys=/tmp/existing_keys.txt
```

Debe responder:

```
Updated [https://compute.googleapis.com/...].
```

### Paso 5: Verificar

```bash
gcloud compute instances describe indigitall-analytics \
  --zone=southamerica-east1-a \
  --format="value(metadata.items[0].value)" | grep github-actions-deploy
```

Debe mostrar:

```
hsaenz:ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICoIdNSNCpiLaANtvEpTvDWbfg7+GMysRbQo1eqAK2vK github-actions-deploy
```

Si aparece esa linea, **esta listo.**

---

## Metodo Alternativo: Desde la Consola Web (sin terminal)

Si prefieres no usar Cloud Shell:

1. Ir a: **https://console.cloud.google.com/compute/instances?project=trax-report-automation**
2. Click en **`indigitall-analytics`**
3. Click en **"Editar"** (boton arriba)
4. Buscar la seccion **"Claves SSH"**
5. Click en **"Agregar elemento"**
6. Pegar esta clave completa:

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICoIdNSNCpiLaANtvEpTvDWbfg7+GMysRbQo1eqAK2vK hsaenz
```

7. Click en **"Guardar"** al final de la pagina

```
┌──────────────────────────────────────────────────────┐
│  Claves SSH                                          │
│  ┌────────────────────────────────────────────────┐  │
│  │ ssh-rsa AAAA... (clave existente)              │  │
│  └────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────┐  │
│  │ ssh-ed25519 AAAA...K2vK hsaenz    ← NUEVA     │  │
│  └────────────────────────────────────────────────┘  │
│  [+ Agregar elemento]                                │
│                                                      │
│              [Guardar]  [Cancelar]                    │
└──────────────────────────────────────────────────────┘
```

---

## Verificacion final

Una vez agregada la clave, pedirle a Henry que confirme ejecutando:

```bash
ssh -i ~/.ssh/github_actions_deploy hsaenz@34.151.199.149 "whoami && hostname"
```

Si responde `hsaenz` y el hostname de la VM, **todo esta funcionando.**

---

## Datos de referencia

| Dato | Valor |
|---|---|
| Proyecto GCP | `trax-report-automation` |
| Zona | `southamerica-east1-a` |
| Instancia | `indigitall-analytics` |
| IP publica | `34.151.199.149` |
| Usuario SSH | `hsaenz` |
| Clave publica a agregar | `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICoIdNSNCpiLaANtvEpTvDWbfg7+GMysRbQo1eqAK2vK github-actions-deploy` |

---

## Por que es necesario

Esta clave permite que GitHub Actions se conecte automaticamente a la VM para hacer deploy. Sin esta clave, el deploy automatico NO funciona y hay que hacerlo manualmente por SSH cada vez.

La clave **solo da acceso de lectura al deploy script** — no compromete la seguridad del servidor.
