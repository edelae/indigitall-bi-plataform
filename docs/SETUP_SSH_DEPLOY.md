# Configuracion SSH para Deploy Automatico

## Que necesitamos

GitHub Actions necesita conectarse por SSH a la VM de GCP para hacer deploy automatico. Para esto, necesitamos agregar **dos claves publicas SSH** a la VM.

---

## Quien debe ejecutar esto

**El administrador del proyecto GCP** (quien tenga el permiso `compute.instances.setMetadata` en el proyecto `trax-report-automation`).

> Los usuarios con rol Viewer o Editor limitado **NO** pueden hacer esto.
> Se necesita el rol **Compute Instance Admin** o **Owner** del proyecto.

---

## PROBLEMA ACTUAL

Las claves SSH que estan en la VM tienen **saltos de linea incorrectos** y por eso no funcionan. Hay que **borrar las existentes** y volver a agregarlas correctamente.

**Regla clave:** Cada clave SSH debe estar en **UNA SOLA LINEA** sin saltos ni espacios extras.

---

## Opcion A: Desde la Consola Web (RECOMENDADO — sin terminal)

### Paso 1: Abrir la instancia

1. Ir a este link directo:

   **https://console.cloud.google.com/compute/instances?project=trax-report-automation**

2. Iniciar sesion con la **cuenta administradora** del proyecto

3. En la lista de instancias, click en **`indigitall-analytics`**

```
┌─────────────────────────────────────────────────────────────┐
│  Instancias de VM                                           │
│                                                             │
│  Nombre                  Zona                  IP externa   │
│  ─────────────────────── ───────────────────── ──────────── │
│  indigitall-analytics    southamerica-east1-a  34.151.199.. │
│  ↑                                                          │
│  Click aqui                                                 │
└─────────────────────────────────────────────────────────────┘
```

### Paso 2: Entrar en modo edicion

1. En la pagina de detalle de la instancia, click en **"EDITAR"** (boton arriba)

```
┌─────────────────────────────────────────────────────────────┐
│  indigitall-analytics                                       │
│                                                             │
│  [EDITAR]   [RESTABLECER]   [DETENER]                       │
│   ↑                                                         │
│   Click aqui                                                │
└─────────────────────────────────────────────────────────────┘
```

### Paso 3: Corregir las claves SSH

1. Bajar hasta la seccion **"Claves SSH"**
2. **Borrar TODAS las claves** existentes (estan corruptas con saltos de linea)
   - Click en la **X** al lado de cada clave para eliminarla

```
┌─────────────────────────────────────────────────────────────┐
│  Claves SSH                                                 │
│                                                             │
│  ┌──────────────────────────────────────────────────┐  [X]  │
│  │ ssh-rsa AAAA... (clave rota — BORRAR)            │       │
│  └──────────────────────────────────────────────────┘       │
│  ┌──────────────────────────────────────────────────┐  [X]  │
│  │ ssh-ed25519 AAAA... (clave rota — BORRAR)        │       │
│  └──────────────────────────────────────────────────┘       │
│                                                             │
│  [+ Agregar elemento]                                       │
└─────────────────────────────────────────────────────────────┘
```

3. Click en **"+ Agregar elemento"**
4. Pegar la **CLAVE 1** (todo en UNA sola linea, sin saltos):

```
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCwnYMUWVPDc6X4Ln2blhzheFvnD+Fgf/p9YgD6eL17SRO9scWMHUh8eaL/4YVhArlbBdVPIYJ5Yf8La84aRqdrMTlBJzEFxUINdvTublxA9bj1ELysfk3o8lPhMy0QHFCAMYCLaJpvd5OLIqHFJSYN6U2BwVZuSGWOolz/IacSrp2r767l9HMLPQzn76s2MNvKyvVLJb7S6RrX5ucTy119wgC7lZjsXlMyO5DeiTWOp4R+k+bsyHqRjvfWqSkg95cuvqM6YvC/JxabXqftEuTTQCbiY2OAlrUFyQVtJi1rdNoxUkkm5bpVEANSusRgIMxTaPips68SMHyiLnGaLdu9 hsaenz@rocketst.co
```

> La consola debe detectar automaticamente el usuario "hsaenz" a la izquierda.

5. Click en **"+ Agregar elemento"** otra vez
6. Pegar la **CLAVE 2** (todo en UNA sola linea):

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICoIdNSNCpiLaANtvEpTvDWbfg7+GMysRbQo1eqAK2vK hsaenz
```

> La consola debe detectar automaticamente el usuario "hsaenz" a la izquierda.

El resultado debe verse asi:

```
┌─────────────────────────────────────────────────────────────┐
│  Claves SSH                                                 │
│                                                             │
│  ┌──────────────────────────────────────────────────┐  [X]  │
│  │ hsaenz   ssh-rsa AAAA...du9 hsaenz@rocketst.co  │       │
│  └──────────────────────────────────────────────────┘       │
│  ┌──────────────────────────────────────────────────┐  [X]  │
│  │ hsaenz   ssh-ed25519 AAAA...K2vK hsaenz          │       │
│  └──────────────────────────────────────────────────┘       │
│                                                             │
│  [+ Agregar elemento]                                       │
└─────────────────────────────────────────────────────────────┘
```

### Paso 4: Guardar

1. Bajar hasta el final de la pagina
2. Click en **"GUARDAR"**

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│              [GUARDAR]        [CANCELAR]                    │
│               ↑                                             │
│               Click aqui                                    │
└─────────────────────────────────────────────────────────────┘
```

Debe aparecer un mensaje verde: **"La instancia se actualizo correctamente"**

---

## Opcion B: Desde Cloud Shell (alternativa con terminal)

### Paso 1: Abrir Cloud Shell

1. Ir a: **https://console.cloud.google.com**
2. Iniciar sesion con la cuenta administradora
3. Seleccionar el proyecto **`trax-report-automation`**
4. Click en el icono de terminal **`>_`** (Cloud Shell) en la barra superior derecha

```
┌─────────────────────────────────────────────────────┐
│  Google Cloud    trax-report-automation  ▼    >_     │
│                                                 ↑    │
│                                          Cloud Shell │
└─────────────────────────────────────────────────────┘
```

### Paso 2: Ejecutar estos comandos

Copiar y pegar **todo este bloque** en Cloud Shell:

```bash
# Configurar proyecto
gcloud config set project trax-report-automation

# Crear archivo con las 2 claves (formato correcto, una por linea)
cat > /tmp/ssh_keys.txt << 'EOF'
hsaenz:ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCwnYMUWVPDc6X4Ln2blhzheFvnD+Fgf/p9YgD6eL17SRO9scWMHUh8eaL/4YVhArlbBdVPIYJ5Yf8La84aRqdrMTlBJzEFxUINdvTublxA9bj1ELysfk3o8lPhMy0QHFCAMYCLaJpvd5OLIqHFJSYN6U2BwVZuSGWOolz/IacSrp2r767l9HMLPQzn76s2MNvKyvVLJb7S6RrX5ucTy119wgC7lZjsXlMyO5DeiTWOp4R+k+bsyHqRjvfWqSkg95cuvqM6YvC/JxabXqftEuTTQCbiY2OAlrUFyQVtJi1rdNoxUkkm5bpVEANSusRgIMxTaPips68SMHyiLnGaLdu9 hsaenz@rocketst.co
hsaenz:ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICoIdNSNCpiLaANtvEpTvDWbfg7+GMysRbQo1eqAK2vK github-actions-deploy
EOF

# Reemplazar las claves en la VM
gcloud compute instances add-metadata indigitall-analytics \
  --zone=southamerica-east1-a \
  --metadata-from-file=ssh-keys=/tmp/ssh_keys.txt
```

### Paso 3: Verificar

```bash
gcloud compute instances describe indigitall-analytics \
  --zone=southamerica-east1-a \
  --format="value(metadata.items[0].value)"
```

Debe mostrar exactamente 2 lineas (sin saltos dentro de cada clave):

```
hsaenz:ssh-rsa AAAAB3NzaC1yc2EAAAA...du9 hsaenz@rocketst.co
hsaenz:ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA...K2vK github-actions-deploy
```

---

## Errores comunes

### "No se pudo editar la instancia" / "Permission denied"

Tu cuenta no tiene el permiso `compute.instances.setMetadata`. Solo el **administrador/owner** del proyecto GCP puede hacerlo.

### Las claves no funcionan despues de guardar

Verificar que cada clave este en **UNA sola linea**. Si al pegarla quedo en multiples lineas (con Enter en el medio), borrarla y volver a pegarla. Se puede verificar que no haya saltos de linea revisando que el campo muestre solo 2 claves, no 5 o 6.

### SSH sigue diciendo "Permission denied"

Revisar que el usuario sea `hsaenz` (aparece a la izquierda de cada clave en la consola). Si aparece un usuario diferente, la clave no fue reconocida correctamente.

---

## Verificacion final

Una vez guardadas las claves, avisarle a Henry para que ejecute:

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

### Claves a agregar

**Clave 1 — Acceso SSH de hsaenz (gcloud):**

```
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCwnYMUWVPDc6X4Ln2blhzheFvnD+Fgf/p9YgD6eL17SRO9scWMHUh8eaL/4YVhArlbBdVPIYJ5Yf8La84aRqdrMTlBJzEFxUINdvTublxA9bj1ELysfk3o8lPhMy0QHFCAMYCLaJpvd5OLIqHFJSYN6U2BwVZuSGWOolz/IacSrp2r767l9HMLPQzn76s2MNvKyvVLJb7S6RrX5ucTy119wgC7lZjsXlMyO5DeiTWOp4R+k+bsyHqRjvfWqSkg95cuvqM6YvC/JxabXqftEuTTQCbiY2OAlrUFyQVtJi1rdNoxUkkm5bpVEANSusRgIMxTaPips68SMHyiLnGaLdu9 hsaenz@rocketst.co
```

**Clave 2 — Deploy automatico (GitHub Actions):**

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICoIdNSNCpiLaANtvEpTvDWbfg7+GMysRbQo1eqAK2vK hsaenz
```

---

## Por que es necesario

Estas claves permiten:

1. **Clave RSA**: Que Henry pueda conectarse a la VM con `gcloud compute ssh`
2. **Clave ED25519**: Que GitHub Actions haga deploy automatico al hacer push a main

Sin estas claves, cada deploy requiere acceso manual a la consola de GCP.
