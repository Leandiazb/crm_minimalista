from nicegui import app, ui
import sqlite3
import csv
import io
import hashlib
import secrets
from datetime import datetime


# ============================================================
# CONFIGURACIÓN
# ============================================================

DB_NAME = 'crm.db'


# ============================================================
# BASE DE DATOS
# ============================================================

def conectar_db():
    return sqlite3.connect(DB_NAME)


def inicializar_db():

    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            empresa TEXT,
            email TEXT,
            telefono TEXT,
            estado TEXT DEFAULT 'Lead',
            notas TEXT,
            ultimo_contacto TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            nombre TEXT NOT NULL,
            rol TEXT DEFAULT 'usuario'
        )
    """)

    conn.commit()
    conn.close()

    crear_usuario_admin()


# ============================================================
# HASH DE CONTRASEÑAS
# ============================================================

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    hash_val = hashlib.sha256(
        (salt + password).encode('utf-8')
    ).hexdigest()
    return salt, hash_val


def verificar_password(password, salt, hash_val):
    _, nuevo_hash = hash_password(password, salt)
    return nuevo_hash == hash_val


# ============================================================
# USUARIOS - BASE DE DATOS
# ============================================================

def crear_usuario_admin():

    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM usuarios"
    )

    cantidad = cursor.fetchone()[0]

    if cantidad == 0:

        salt, hash_val = hash_password('admin123')

        cursor.execute("""
            INSERT INTO usuarios
            (username, password_hash, salt, nombre, rol)
            VALUES (?, ?, ?, ?, ?)
        """, (
            'admin',
            hash_val,
            salt,
            'Administrador',
            'admin'
        ))

        conn.commit()

    conn.close()


def obtener_usuario(username):

    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            username,
            password_hash,
            salt,
            nombre,
            rol
        FROM usuarios
        WHERE username = ?
    """, (username,))

    usuario = cursor.fetchone()

    conn.close()

    return usuario


def obtener_usuario_por_id(user_id):

    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            username,
            password_hash,
            salt,
            nombre,
            rol
        FROM usuarios
        WHERE id = ?
    """, (user_id,))

    usuario = cursor.fetchone()

    conn.close()

    return usuario


def obtener_todos_usuarios():

    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            username,
            nombre,
            rol
        FROM usuarios
        ORDER BY nombre
    """)

    usuarios = cursor.fetchall()

    conn.close()

    return usuarios


def crear_usuario(datos):

    conn = conectar_db()
    cursor = conn.cursor()

    salt, hash_val = hash_password(datos['password'])

    cursor.execute("""
        INSERT INTO usuarios
        (username, password_hash, salt, nombre, rol)
        VALUES (?, ?, ?, ?, ?)
    """, (
        datos['username'],
        hash_val,
        salt,
        datos['nombre'],
        datos['rol']
    ))

    conn.commit()
    conn.close()


def eliminar_usuario(user_id):

    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM usuarios WHERE id = ?",
        (user_id,)
    )

    conn.commit()
    conn.close()


def cambiar_password(user_id, nueva_password):

    conn = conectar_db()
    cursor = conn.cursor()

    salt, hash_val = hash_password(nueva_password)

    cursor.execute("""
        UPDATE usuarios
        SET password_hash = ?, salt = ?
        WHERE id = ?
    """, (hash_val, salt, user_id))

    conn.commit()
    conn.close()


# ============================================================
# AUTENTICACIÓN
# ============================================================

def verificar_autenticacion():
    return 'username' in app.storage.user


def requerir_autenticacion():
    if not verificar_autenticacion():
        ui.navigate.to('/login')
        return False
    return True


def es_admin():
    return app.storage.user.get('rol') == 'admin'


# ============================================================
# DATOS DE DEMOSTRACIÓN
# ============================================================

def cargar_datos_demo():

    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM clientes"
    )

    cantidad = cursor.fetchone()[0]

    if cantidad == 0:

        clientes = [
            (
                'María González',
                'González & Asociados',
                'maria@ejemplo.com',
                '11-5555-1234',
                'Cliente',
                'Cliente recurrente. Interesada en ampliar el servicio.',
                '2026-08-18'
            ),
            (
                'Juan Pérez',
                'Pérez Construcciones',
                'juan@ejemplo.com',
                '11-5555-5678',
                'Contactado',
                'Solicitó información sobre nuestros servicios.',
                '2026-08-15'
            ),
            (
                'Laura Martínez',
                'LM Design',
                'laura@ejemplo.com',
                '11-5555-9012',
                'Lead',
                'Llegó por recomendación.',
                '2026-08-12'
            ),
            (
                'Carlos Rodríguez',
                'Rodríguez SRL',
                'carlos@ejemplo.com',
                '11-5555-3456',
                'Inactivo',
                'No respondió a los últimos contactos.',
                '2026-07-28'
            ),
        ]

        cursor.executemany("""
            INSERT INTO clientes
            (
                nombre,
                empresa,
                email,
                telefono,
                estado,
                notas,
                ultimo_contacto
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, clientes)

        conn.commit()

    conn.close()


# ============================================================
# CONSULTAR CLIENTES
# ============================================================

def obtener_clientes(busqueda=''):

    conn = conectar_db()
    cursor = conn.cursor()

    if busqueda:

        texto = f'%{busqueda}%'

        cursor.execute("""
            SELECT
                id,
                nombre,
                empresa,
                email,
                telefono,
                estado,
                notas,
                ultimo_contacto
            FROM clientes
            WHERE
                nombre LIKE ?
                OR empresa LIKE ?
                OR email LIKE ?
            ORDER BY nombre
        """, (
            texto,
            texto,
            texto
        ))

    else:

        cursor.execute("""
            SELECT
                id,
                nombre,
                empresa,
                email,
                telefono,
                estado,
                notas,
                ultimo_contacto
            FROM clientes
            ORDER BY nombre
        """)

    clientes = cursor.fetchall()

    conn.close()

    return clientes


# ============================================================
# ESTADÍSTICAS
# ============================================================

def obtener_estadisticas():

    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM clientes"
    )

    total = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM clientes
        WHERE estado = 'Lead'
    """)

    leads = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM clientes
        WHERE estado = 'Contactado'
    """)

    contactados = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM clientes
        WHERE estado = 'Cliente'
    """)

    clientes = cursor.fetchone()[0]

    conn.close()

    return (
        total,
        leads,
        contactados,
        clientes
    )


def obtener_estadisticas_completas():

    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM clientes"
    )
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM clientes WHERE estado = 'Lead'")
    leads = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM clientes WHERE estado = 'Contactado'")
    contactados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM clientes WHERE estado = 'Cliente'")
    clientes_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM clientes WHERE estado = 'Inactivo'")
    inactivos = cursor.fetchone()[0]

    conn.close()

    return total, leads, contactados, clientes_count, inactivos


# ============================================================
# CREAR CLIENTE
# ============================================================

def crear_cliente(datos):

    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO clientes
        (
            nombre,
            empresa,
            email,
            telefono,
            estado,
            notas,
            ultimo_contacto
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        datos['nombre'],
        datos['empresa'],
        datos['email'],
        datos['telefono'],
        datos['estado'],
        datos['notas'],
        datos['ultimo_contacto']
    ))

    conn.commit()
    conn.close()


# ============================================================
# ACTUALIZAR CLIENTE
# ============================================================

def actualizar_cliente(cliente_id, datos):

    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE clientes
        SET
            nombre = ?,
            empresa = ?,
            email = ?,
            telefono = ?,
            estado = ?,
            notas = ?,
            ultimo_contacto = ?
        WHERE id = ?
    """, (
        datos['nombre'],
        datos['empresa'],
        datos['email'],
        datos['telefono'],
        datos['estado'],
        datos['notas'],
        datos['ultimo_contacto'],
        cliente_id
    ))

    conn.commit()
    conn.close()


# ============================================================
# ELIMINAR CLIENTE
# ============================================================

def eliminar_cliente(cliente_id):

    conn = conectar_db()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM clientes WHERE id = ?",
        (cliente_id,)
    )

    conn.commit()
    conn.close()


# ============================================================
# CONVERTIR CLIENTES EN FILAS
# ============================================================

def obtener_filas(busqueda=''):

    filas = []

    for cliente in obtener_clientes(busqueda):

        filas.append({
            'id': cliente[0],
            'nombre': cliente[1],
            'empresa': cliente[2] or '-',
            'email': cliente[3] or '-',
            'telefono': cliente[4] or '-',
            'estado': cliente[5],
            'ultimo_contacto': cliente[7] or '-',
        })

    return filas


# ============================================================
# EXPORTAR CLIENTES A CSV
# ============================================================

def exportar_csv():

    clientes = obtener_clientes()

    archivo = io.StringIO()

    escritor = csv.writer(
        archivo,
        delimiter=';'
    )

    escritor.writerow([
        'ID',
        'Nombre',
        'Empresa',
        'Email',
        'Telefono',
        'Estado',
        'Notas',
        'Ultimo contacto'
    ])

    for cliente in clientes:

        escritor.writerow([
            cliente[0],
            cliente[1],
            cliente[2] or '',
            cliente[3] or '',
            cliente[4] or '',
            cliente[5] or '',
            cliente[6] or '',
            cliente[7] or ''
        ])

    contenido = archivo.getvalue()

    ui.download(
        contenido.encode('utf-8-sig'),
        'clientes.csv'
    )

    ui.notify(
        'CSV exportado correctamente',
        type='positive'
    )


# ============================================================
# ESTILOS GLASSMORPHISM
# ============================================================

CSS = """

/* ============================================================
   VARIABLES
   ============================================================ */

:root {
    --glass-bg: rgba(255, 255, 255, 0.62);
    --glass-bg-strong: rgba(255, 255, 255, 0.78);
    --glass-border: rgba(255, 255, 255, 0.75);

    --primary: #6366f1;
    --primary-dark: #4f46e5;
    --secondary: #8b5cf6;

    --text-primary: #17172b;
    --text-secondary: #6b7280;

    --shadow:
        0 20px 50px rgba(79, 70, 229, 0.10);

    --shadow-hover:
        0 25px 60px rgba(79, 70, 229, 0.18);
}


/* ============================================================
   BASE
   ============================================================ */

html,
body {
    min-height: 100%;
    margin: 0;
}

body {

    font-family:
        Inter,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Arial,
        sans-serif;

    color: var(--text-primary);

    background:

        radial-gradient(
            circle at 10% 10%,
            rgba(139, 92, 246, 0.22),
            transparent 28%
        ),

        radial-gradient(
            circle at 90% 15%,
            rgba(59, 130, 246, 0.18),
            transparent 25%
        ),

        radial-gradient(
            circle at 50% 100%,
            rgba(99, 102, 241, 0.15),
            transparent 35%
        ),

        linear-gradient(
            135deg,
            #eef2ff 0%,
            #f8fafc 45%,
            #eef2ff 100%
        );

    background-attachment: fixed;
}


/* ============================================================
   SCROLLBAR
   ============================================================ */

::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.2);
}

::-webkit-scrollbar-thumb {
    background: rgba(99, 102, 241, 0.35);
    border-radius: 20px;
}


/* ============================================================
   HEADER GLASS
   ============================================================ */

.app-header {

    height: 70px;

    background:
        rgba(255, 255, 255, 0.58);

    backdrop-filter:
        blur(20px);

    -webkit-backdrop-filter:
        blur(20px);

    border-bottom:
        1px solid rgba(255, 255, 255, 0.7);

    box-shadow:
        0 10px 30px rgba(31, 41, 55, 0.06);

    position: relative;
    z-index: 100;
}


/* ============================================================
   LOGO
   ============================================================ */

.logo-container {

    display: flex;
    align-items: center;
    gap: 11px;
}


.logo-icon {

    width: 40px;
    height: 40px;

    border-radius: 13px;

    background:
        linear-gradient(
            135deg,
            #6366f1,
            #8b5cf6
        );

    display: flex;
    align-items: center;
    justify-content: center;

    color: white;

    box-shadow:
        0 10px 25px rgba(99, 102, 241, 0.28);

    flex-shrink: 0;
}


.logo-text {

    font-size: 19px;
    font-weight: 800;

    color: #17172b;

    letter-spacing: -0.5px;
}


.logo-text span {

    background:
        linear-gradient(
            90deg,
            #6366f1,
            #8b5cf6
        );

    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}


/* ============================================================
   NAVBAR
   ============================================================ */

.nav-button {

    color: #555b73 !important;

    font-weight: 650;

    border-radius: 12px;

    transition:
        all 0.2s ease;
}


.nav-button:hover {

    color: #6366f1 !important;

    background:
        rgba(99, 102, 241, 0.08);

    transform:
        translateY(-1px);
}


/* ============================================================
   CONTENEDOR PRINCIPAL
   ============================================================ */

.page-container {

    position: relative;
}


/* ============================================================
   TÍTULOS
   ============================================================ */

.page-title {

    font-size: 32px;

    font-weight: 850;

    letter-spacing: -1px;

    color: #17172b;
}


.page-subtitle {

    color: #6b7280;

    font-size: 14px;

    line-height: 1.6;
}


/* ============================================================
   GLASS CARD GENERAL
   ============================================================ */

.glass-card {

    background:
        var(--glass-bg);

    backdrop-filter:
        blur(18px);

    -webkit-backdrop-filter:
        blur(18px);

    border:
        1px solid var(--glass-border);

    border-radius:
        22px;

    box-shadow:
        var(--shadow);

    transition:
        transform 0.25s ease,
        box-shadow 0.25s ease,
        background 0.25s ease;
}


.glass-card:hover {

    box-shadow:
        var(--shadow-hover);
}


/* ============================================================
   ESTADÍSTICAS
   ============================================================ */

.stat-card {

    position: relative;

    overflow: hidden;

    background:
        rgba(255, 255, 255, 0.58);

    backdrop-filter:
        blur(18px);

    -webkit-backdrop-filter:
        blur(18px);

    border:
        1px solid rgba(255, 255, 255, 0.78);

    border-radius:
        20px;

    padding:
        21px;

    box-shadow:
        0 15px 40px rgba(31, 41, 55, 0.07);

    transition:
        all 0.25s ease;
}


.stat-card::before {

    content: "";

    position: absolute;

    width: 90px;
    height: 90px;

    right: -35px;
    top: -35px;

    border-radius: 50%;

    background:
        rgba(99, 102, 241, 0.10);
}


.stat-card:hover {

    transform:
        translateY(-4px);

    box-shadow:
        0 20px 45px rgba(79, 70, 229, 0.14);
}


.stat-label {

    color: #737991;

    font-size: 13px;

    font-weight: 600;

    position: relative;
}


.stat-value {

    font-size: 31px;

    font-weight: 850;

    color: #17172b;

    margin-top: 5px;

    position: relative;
}


/* ============================================================
   TABLA GLASS
   ============================================================ */

.table-container {

    background:
        rgba(255, 255, 255, 0.60);

    backdrop-filter:
        blur(18px);

    -webkit-backdrop-filter:
        blur(18px);

    border:
        1px solid rgba(255, 255, 255, 0.78);

    border-radius:
        22px;

    overflow: hidden;

    box-shadow:
        0 20px 50px rgba(31, 41, 55, 0.08);
}


/* ============================================================
   INPUTS
   ============================================================ */

.q-field--outlined .q-field__control {

    border-radius:
        13px;

    background:
        rgba(255, 255, 255, 0.50);
}


.q-field--outlined .q-field__control:before {

    border-color:
        rgba(99, 102, 241, 0.18);
}


.q-field--outlined .q-field__control:hover:before {

    border-color:
        rgba(99, 102, 241, 0.40);
}


.q-field--outlined.q-field--focused
.q-field__control:after {

    border-color:
        #6366f1;
}


/* ============================================================
   BOTONES
   ============================================================ */

.q-btn {

    border-radius:
        12px;

    font-weight:
        650;

    text-transform:
        none;

    letter-spacing:
        0;
}


.q-btn.bg-primary {

    background:
        linear-gradient(
            135deg,
            #6366f1,
            #8b5cf6
        ) !important;

    box-shadow:
        0 8px 20px rgba(99, 102, 241, 0.25);

    transition:
        all 0.2s ease;
}


.q-btn.bg-primary:hover {

    transform:
        translateY(-2px);

    box-shadow:
        0 12px 25px rgba(99, 102, 241, 0.35);
}


/* ============================================================
   TABLA QUASAR
   ============================================================ */

.q-table {

    background:
        transparent !important;

    color:
        #34384d;
}


.q-table thead tr {

    background:
        rgba(99, 102, 241, 0.045);
}


.q-table thead th {

    color:
        #777d95;

    font-size:
        11px;

    font-weight:
        800;

    letter-spacing:
        0.7px;

    border-bottom:
        1px solid rgba(99, 102, 241, 0.08);
}


.q-table tbody tr {

    transition:
        background 0.2s ease;
}


.q-table tbody tr:hover {

    background:
        rgba(99, 102, 241, 0.055);
}


.q-table tbody td {

    border-color:
        rgba(99, 102, 241, 0.06);

    padding-top:
        14px;

    padding-bottom:
        14px;
}


/* ============================================================
   BADGES
   ============================================================ */

.q-badge {

    border-radius:
        999px;

    font-weight:
        700;

    padding:
        5px 10px;
}


/* ============================================================
   DIÁLOGOS
   ============================================================ */

.q-dialog__inner > .q-card {

    background:
        rgba(255, 255, 255, 0.80);

    backdrop-filter:
        blur(25px);

    -webkit-backdrop-filter:
        blur(25px);

    border:
        1px solid rgba(255, 255, 255, 0.9);

    border-radius:
        24px;

    box-shadow:
        0 30px 80px rgba(31, 41, 55, 0.20);
}


/* ============================================================
   AYUDA
   ============================================================ */

.help-card {

    background:
        rgba(255, 255, 255, 0.58);

    backdrop-filter:
        blur(18px);

    -webkit-backdrop-filter:
        blur(18px);

    border:
        1px solid rgba(255, 255, 255, 0.78);

    border-radius:
        22px;

    padding:
        26px;

    box-shadow:
        0 15px 40px rgba(31, 41, 55, 0.07);

    transition:
        all 0.25s ease;
}


.help-card:hover {

    transform:
        translateY(-2px);

    box-shadow:
        0 20px 45px rgba(79, 70, 229, 0.12);
}


.help-number {

    width: 36px;
    height: 36px;

    min-width: 36px;

    border-radius: 12px;

    background:
        linear-gradient(
            135deg,
            rgba(99, 102, 241, 0.14),
            rgba(139, 92, 246, 0.18)
        );

    color:
        #6366f1;

    display:
        flex;

    align-items:
        center;

    justify-content:
        center;

    font-weight:
        850;
}


.help-title {

    font-size:
        18px;

    font-weight:
        780;

    color:
        #202036;
}


.help-text {

    color:
        #70758a;

    line-height:
        1.65;
}


/* ============================================================
   EMBUDO
   ============================================================ */

.funnel-container {

    display:
        flex;

    flex-direction:
        column;

    align-items:
        center;

    gap:
        12px;

    width:
        100%;
}


/* ============================================================
   EMBUDO - TARJETAS
   ============================================================ */

.funnel-stage {

    position:
        relative;

    border-radius:
        20px;

    padding:
        21px 28px;

    min-height:
        90px;

    display:
        flex;

    align-items:
        center;

    justify-content:
        space-between;

    box-sizing:
        border-box;

    border:
        1px solid;

    backdrop-filter:
        blur(15px);

    -webkit-backdrop-filter:
        blur(15px);

    box-shadow:
        0 12px 30px rgba(31, 41, 55, 0.06);

    transition:
        all 0.25s ease;
}


.funnel-stage:hover {

    transform:
        scale(1.015);

    box-shadow:
        0 18px 38px rgba(31, 41, 55, 0.10);
}


/* ============================================================
   LEAD
   ============================================================ */

.funnel-stage.funnel-lead {

    background:
        rgba(255, 237, 213, 0.60);

    border-color:
        rgba(251, 146, 60, 0.35);
}


.funnel-stage.funnel-lead .funnel-stage-title {

    color:
        #c2410c;
}


.funnel-stage.funnel-lead .funnel-stage-description {

    color:
        #9a3412;
}


.funnel-stage.funnel-lead .funnel-count {

    color:
        #ea580c;
}


/* ============================================================
   CONTACTADO
   ============================================================ */

.funnel-stage.funnel-contactado {

    background:
        rgba(219, 234, 254, 0.60);

    border-color:
        rgba(59, 130, 246, 0.32);
}


.funnel-stage.funnel-contactado .funnel-stage-title {

    color:
        #1d4ed8;
}


.funnel-stage.funnel-contactado .funnel-stage-description {

    color:
        #1e40af;
}


.funnel-stage.funnel-contactado .funnel-count {

    color:
        #2563eb;
}


/* ============================================================
   CLIENTE
   ============================================================ */

.funnel-stage.funnel-cliente {

    background:
        rgba(220, 252, 231, 0.60);

    border-color:
        rgba(34, 197, 94, 0.32);
}


.funnel-stage.funnel-cliente .funnel-stage-title {

    color:
        #15803d;
}


.funnel-stage.funnel-cliente .funnel-stage-description {

    color:
        #166534;
}


.funnel-stage.funnel-cliente .funnel-count {

    color:
        #16a34a;
}


/* ============================================================
   INACTIVO
   ============================================================ */

.funnel-stage.funnel-inactivo {

    background:
        rgba(243, 244, 246, 0.62);

    border-color:
        rgba(107, 114, 128, 0.28);
}


.funnel-stage.funnel-inactivo .funnel-stage-title {

    color:
        #4b5563;
}


.funnel-stage.funnel-inactivo .funnel-stage-description {

    color:
        #6b7280;
}


.funnel-stage.funnel-inactivo .funnel-count {

    color:
        #6b7280;
}


/* ============================================================
   ANCHOS EMBUDO
   ============================================================ */

.funnel-lead {
    width: 90%;
}

.funnel-contactado {
    width: 72%;
}

.funnel-cliente {
    width: 54%;
}

.funnel-inactivo {
    width: 36%;
}


/* ============================================================
   CONTENIDO EMBUDO
   ============================================================ */

.funnel-stage-inner {

    width:
        100%;

    display:
        flex;

    align-items:
        center;

    justify-content:
        space-between;
}


.funnel-stage-title {

    font-size:
        16px;

    font-weight:
        800;
}


.funnel-stage-description {

    font-size:
        13px;
}


.funnel-count {

    font-size:
        30px;

    font-weight:
        850;
}


/* ============================================================
   FOOTER
   ============================================================ */

.app-footer {

    width:
        100%;

    padding:
        24px 32px;

    border-top:
        1px solid rgba(255, 255, 255, 0.7);

    background:
        rgba(255, 255, 255, 0.40);

    backdrop-filter:
        blur(18px);

    -webkit-backdrop-filter:
        blur(18px);

    box-sizing:
        border-box;
}


.footer-content {

    width:
        100%;

    max-width:
        1120px;

    margin:
        0 auto;
}


.footer-brand {

    font-size:
        14px;

    font-weight:
        750;

    color:
        #3f4358;
}


.footer-brand span {

    color:
        #6366f1;
}


.footer-text {

    font-size:
        12px;

    color:
        #85899c;
}


.footer-version {

    font-size:
        11px;

    color:
        #777c91;

    padding:
        5px 10px;

    border:
        1px solid rgba(99, 102, 241, 0.15);

    border-radius:
        999px;

    background:
        rgba(255, 255, 255, 0.40);
}


/* ============================================================
   LOGIN
   ============================================================ */

.login-page {

    min-height: 100vh;

    display: flex;

    align-items: center;

    justify-content: center;

    padding: 24px;
}


.login-card {

    background:
        rgba(255, 255, 255, 0.65);

    backdrop-filter:
        blur(24px);

    -webkit-backdrop-filter:
        blur(24px);

    border:
        1px solid rgba(255, 255, 255, 0.82);

    border-radius:
        28px;

    box-shadow:
        0 30px 80px rgba(31, 41, 55, 0.15);

    padding:
        40px;

    width:
        420px;

    max-width:
        95vw;
}


.login-card .logo-icon {

    width: 56px;

    height: 56px;

    border-radius: 18px;

    margin: 0 auto;
}


.login-card .logo-icon .q-icon {

    font-size: 28px;
}


.login-title {

    font-size: 26px;

    font-weight: 850;

    color: #17172b;

    text-align: center;

    letter-spacing: -0.5px;
}


.login-subtitle {

    color: #737991;

    font-size: 14px;

    text-align: center;

    line-height: 1.6;
}


.login-hint {

    background:
        rgba(99, 102, 241, 0.06);

    border:
        1px solid rgba(99, 102, 241, 0.12);

    border-radius:
        14px;

    padding:
        12px 16px;

    margin-top: 16px;
}


.login-hint-label {

    color: #6366f1;

    font-size: 11px;

    font-weight: 750;

    letter-spacing: 0.5px;

    text-transform: uppercase;
}


.login-hint-text {

    color: #6b7280;

    font-size: 13px;

    margin-top: 2px;
}


.login-error {

    background:
        rgba(239, 68, 68, 0.08);

    border:
        1px solid rgba(239, 68, 68, 0.18);

    border-radius:
        12px;

    padding:
        10px 14px;

    color: #dc2626;

    font-size: 13px;

    font-weight: 600;
}


/* ============================================================
   USER AVATAR
   ============================================================ */

.user-avatar {

    width: 36px;

    height: 36px;

    min-width: 36px;

    border-radius: 12px;

    background:
        linear-gradient(
            135deg,
            #6366f1,
            #8b5cf6
        );

    color: white;

    display: flex;

    align-items: center;

    justify-content: center;

    font-weight: 800;

    font-size: 14px;
}


.user-info-name {

    font-size: 13px;

    font-weight: 700;

    color: #25253a;
}


.user-info-role {

    font-size: 11px;

    color: #737991;

    font-weight: 600;

    text-transform: uppercase;

    letter-spacing: 0.5px;
}


/* ============================================================
   RESPONSIVE
   ============================================================ */

@media (max-width: 900px) {

    .page-title {
        font-size: 27px;
    }

    .funnel-lead {
        width: 100%;
    }

    .funnel-contactado {
        width: 88%;
    }

    .funnel-cliente {
        width: 75%;
    }

    .funnel-inactivo {
        width: 62%;
    }
}


@media (max-width: 650px) {

    .app-header {
        height: auto;
        min-height: 64px;
    }

    .logo-text {
        display: none;
    }

    .nav-button {
        min-width: 42px;
    }

    .nav-button .q-btn__content > span {
        display: none;
    }

    .page-title {
        font-size: 25px;
    }

    .stat-card {
        padding: 17px;
    }

    .stat-value {
        font-size: 26px;
    }

    .funnel-stage {
        width: 100% !important;
    }

    .funnel-stage-description {
        max-width: 170px;
    }

    .app-footer {
        padding:
            20px 18px;
    }

    .user-info-name,
    .user-info-role {
        display: none;
    }
}

"""


# ============================================================
# LOGO
# ============================================================

def construir_logo():

    with ui.row().classes(
        'logo-container'
    ):

        with ui.element('div').classes(
            'logo-icon'
        ):

            ui.icon(
                'groups'
            ).classes(
                'text-2xl'
            )

        with ui.element('div').classes(
            'logo-text'
        ):

            ui.html(
                'simple<span>CRM</span>'
            )


# ============================================================
# NAVBAR
# ============================================================

def construir_navbar():

    with ui.header().classes(
        'app-header px-6'
    ):

        with ui.row().classes(
            'w-full items-center'
        ):

            construir_logo()

            ui.space()

            ui.button(
                'Clientes',
                icon='people',
                on_click=lambda: ui.navigate.to('/')
            ).props(
                'flat'
            ).classes(
                'nav-button'
            )

            ui.button(
                'Embudo',
                icon='filter_alt',
                on_click=lambda: ui.navigate.to('/embudo')
            ).props(
                'flat'
            ).classes(
                'nav-button'
            )

            ui.button(
                'Ayuda',
                icon='help_outline',
                on_click=lambda: ui.navigate.to('/ayuda')
            ).props(
                'flat'
            ).classes(
                'nav-button'
            )

            if es_admin():

                ui.button(
                    'Usuarios',
                    icon='manage_accounts',
                    on_click=lambda: ui.navigate.to('/usuarios')
                ).props(
                    'flat'
                ).classes(
                    'nav-button'
                )

            ui.separator().props(
                'vertical'
            ).classes(
                'mx-2'
            ).style(
                'height: 28px; background: rgba(99,102,241,0.15);'
            )

            with ui.row().classes(
                'items-center gap-2'
            ):

                with ui.element('div').classes(
                    'user-avatar'
                ):

                    ui.label(
                        app.storage.user.get(
                            'nombre', '?'
                        )[0].upper()
                    )

                with ui.column().classes(
                    'gap-0'
                ):

                    ui.label(
                        app.storage.user.get(
                            'nombre', ''
                        )
                    ).classes(
                        'user-info-name'
                    )

                    ui.label(
                        app.storage.user.get(
                            'rol', ''
                        )
                    ).classes(
                        'user-info-role'
                    )

            ui.button(
                icon='logout',
                on_click=cerrar_sesion
            ).props(
                'flat round'
            ).classes(
                'nav-button'
            ).tooltip(
                'Cerrar sesión'
            )


# ============================================================
# FOOTER
# ============================================================

def construir_footer():

    with ui.element('footer').classes(
        'app-footer'
    ):

        with ui.row().classes(
            'footer-content items-center justify-between'
        ):

            with ui.row().classes(
                'items-center gap-2'
            ):

                ui.html(
                    'simple<span>CRM</span>'
                ).classes(
                    'footer-brand'
                )

                ui.label(
                    '·'
                ).classes(
                    'footer-text'
                )

                ui.label(
                    'CRM simple y práctico'
                ).classes(
                    'footer-text'
                )

            ui.label(
                'v1.0.0'
            ).classes(
                'footer-version'
            )


# ============================================================
# CERRAR SESIÓN
# ============================================================

def cerrar_sesion():

    app.storage.user.clear()

    ui.notify(
        'Sesión cerrada',
        type='info'
    )

    ui.navigate.to('/login')


# ============================================================
# FORMULARIO DE CLIENTE
# ============================================================

def abrir_formulario(cliente_id=None):

    cliente = None

    if cliente_id:

        conn = conectar_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                nombre,
                empresa,
                email,
                telefono,
                estado,
                notas,
                ultimo_contacto
            FROM clientes
            WHERE id = ?
        """, (
            cliente_id,
        ))

        cliente = cursor.fetchone()

        conn.close()

    titulo = (
        'Nuevo cliente'
        if cliente is None
        else 'Editar cliente'
    )

    with ui.dialog() as dialog:

        with ui.card().classes(
            'w-[520px] max-w-[95vw] p-7'
        ):

            with ui.row().classes(
                'items-center gap-3 mb-2'
            ):

                with ui.element('div').classes(
                    'logo-icon'
                ):

                    ui.icon(
                        'person'
                    )

                ui.label(
                    titulo
                ).classes(
                    'text-2xl font-bold'
                )

            ui.label(
                'Completá la información básica del contacto.'
            ).classes(
                'text-sm text-gray-500 mb-5'
            )

            nombre = ui.input(
                'Nombre *',
                value=cliente[1] if cliente else ''
            ).props(
                'outlined'
            ).classes(
                'w-full'
            )

            empresa = ui.input(
                'Empresa',
                value=cliente[2] if cliente else ''
            ).props(
                'outlined'
            ).classes(
                'w-full'
            )

            email = ui.input(
                'Email',
                value=cliente[3] if cliente else ''
            ).props(
                'outlined'
            ).classes(
                'w-full'
            )

            telefono = ui.input(
                'Teléfono',
                value=cliente[4] if cliente else ''
            ).props(
                'outlined'
            ).classes(
                'w-full'
            )

            estado = ui.select(
                [
                    'Lead',
                    'Contactado',
                    'Cliente',
                    'Inactivo'
                ],
                label='Estado',
                value=cliente[5]
                if cliente
                else 'Lead'
            ).props(
                'outlined'
            ).classes(
                'w-full'
            )

            ultimo_contacto = ui.date(
                value=(
                    cliente[7]
                    if cliente and cliente[7]
                    else datetime.now().strftime(
                        '%Y-%m-%d'
                    )
                )
            ).props(
                'outlined'
            ).classes(
                'w-full'
            )

            notas = ui.textarea(
                'Notas',
                value=cliente[6]
                if cliente
                else ''
            ).props(
                'outlined'
            ).classes(
                'w-full'
            )

            with ui.row().classes(
                'w-full justify-end gap-2 mt-5'
            ):

                ui.button(
                    'Cancelar',
                    on_click=dialog.close
                ).props(
                    'flat'
                )

                def guardar():

                    if not nombre.value.strip():

                        ui.notify(
                            'El nombre es obligatorio',
                            type='negative'
                        )

                        return

                    datos = {
                        'nombre': nombre.value.strip(),
                        'empresa': empresa.value.strip(),
                        'email': email.value.strip(),
                        'telefono': telefono.value.strip(),
                        'estado': estado.value,
                        'notas': notas.value.strip(),
                        'ultimo_contacto':
                            ultimo_contacto.value,
                    }

                    if cliente is None:

                        crear_cliente(datos)

                        ui.notify(
                            'Cliente creado correctamente',
                            type='positive'
                        )

                    else:

                        actualizar_cliente(
                            cliente[0],
                            datos
                        )

                        ui.notify(
                            'Cliente actualizado',
                            type='positive'
                        )

                    dialog.close()

                    ui.navigate.to('/')

                ui.button(
                    'Guardar',
                    icon='save',
                    on_click=guardar
                ).props(
                    'unelevated color=primary'
                )

    dialog.open()


# ============================================================
# CONFIRMAR ELIMINACIÓN
# ============================================================

def confirmar_eliminacion(
    cliente_id,
    nombre
):

    with ui.dialog() as dialog:

        with ui.card().classes(
            'p-7 w-[400px] max-w-[95vw]'
        ):

            with ui.row().classes(
                'items-center gap-3'
            ):

                with ui.element('div').classes(
                    'help-number'
                ):

                    ui.icon(
                        'delete'
                    )

                ui.label(
                    'Eliminar cliente'
                ).classes(
                    'text-xl font-bold'
                )

            ui.label(
                f'¿Seguro que querés eliminar a {nombre}?'
            ).classes(
                'text-gray-600 mt-3'
            )

            with ui.row().classes(
                'w-full justify-end gap-2 mt-6'
            ):

                ui.button(
                    'Cancelar',
                    on_click=dialog.close
                ).props(
                    'flat'
                )

                def eliminar():

                    eliminar_cliente(
                        cliente_id
                    )

                    dialog.close()

                    ui.notify(
                        'Cliente eliminado',
                        type='positive'
                    )

                    ui.navigate.to('/')

                ui.button(
                    'Eliminar',
                    icon='delete',
                    on_click=eliminar
                ).props(
                    'unelevated color=negative'
                )

    dialog.open()


# ============================================================
# PÁGINA: LOGIN
# ============================================================

@ui.page('/login')
def pagina_login():

    if verificar_autenticacion():
        ui.navigate.to('/')
        return

    ui.add_head_html(
        f'<style>{CSS}</style>'
    )

    with ui.element('div').classes(
        'login-page w-full'
    ):

        with ui.element('div').classes(
            'login-card'
        ):

            with ui.column().classes(
                'items-center gap-4 mb-6'
            ):

                with ui.element('div').classes(
                    'logo-icon'
                ):

                    ui.icon(
                        'groups'
                    ).classes(
                        'text-3xl'
                    )

                ui.label(
                    'Iniciar sesión'
                ).classes(
                    'login-title'
                )

                ui.label(
                    'Ingresá tus credenciales para acceder al CRM.'
                ).classes(
                    'login-subtitle'
                )

            error_container = ui.column().classes(
                'w-full'
            )

            username_input = ui.input(
                'Usuario',
                placeholder='Ej: admin'
            ).props(
                'outlined'
            ).classes(
                'w-full'
            )

            password_input = ui.input(
                'Contraseña',
                placeholder='Tu contraseña',
                password=True,
                password_toggle_button=True
            ).props(
                'outlined'
            ).classes(
                'w-full'
            )

            ui.button(
                'Ingresar',
                icon='login',
                on_click=lambda: intentar_login(
                    username_input.value,
                    password_input.value,
                    error_container
                )
            ).props(
                'unelevated color=primary'
            ).classes(
                'w-full mt-2'
            )

            with ui.element('div').classes(
                'login-hint'
            ):

                ui.label(
                    'Credenciales por defecto'
                ).classes(
                    'login-hint-label'
                )

                ui.label(
                    'Usuario: admin · Contraseña: admin123'
                ).classes(
                    'login-hint-text'
                )

            with ui.row().classes(
                'w-full justify-center mt-6'
            ):

                ui.html(
                    'simple<span>CRM</span>'
                ).style(
                    'font-size: 15px; font-weight: 750; color: #3f4358;'
                )

                ui.label(
                    'v1.0.0'
                ).classes(
                    'footer-version ml-2'
                )

    def enter_key(e):
        intentar_login(
            username_input.value,
            password_input.value,
            error_container
        )

    username_input.on('keydown.enter', enter_key)
    password_input.on('keydown.enter', enter_key)


def intentar_login(
    username,
    password,
    error_container
):

    error_container.clear()

    if not username.strip() or not password.strip():

        with error_container:

            ui.label(
                'Completá usuario y contraseña'
            ).classes(
                'login-error w-full'
            )

        return

    usuario = obtener_usuario(username.strip())

    if usuario is None:

        with error_container:

            ui.label(
                'Usuario no encontrado'
            ).classes(
                'login-error w-full'
            )

        return

    if not verificar_password(
        password,
        usuario[3],
        usuario[2]
    ):

        with error_container:

            ui.label(
                'Contraseña incorrecta'
            ).classes(
                'login-error w-full'
            )

        return

    app.storage.user['id'] = usuario[0]
    app.storage.user['username'] = usuario[1]
    app.storage.user['nombre'] = usuario[4]
    app.storage.user['rol'] = usuario[5]

    ui.notify(
        f'Bienvenido, {usuario[4]}',
        type='positive'
    )

    ui.navigate.to('/')


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

@ui.page('/')
def pagina_clientes():

    if not requerir_autenticacion():
        return

    ui.add_head_html(
        f'<style>{CSS}</style>'
    )

    construir_navbar()

    with ui.column().classes(
        'w-full min-h-screen flex flex-col'
    ):

        with ui.column().classes(
            'w-full flex-grow'
        ):

            with ui.column().classes(
                'w-full max-w-7xl mx-auto p-8 gap-6'
            ):

                # ============================================
                # ENCABEZADO
                # ============================================

                with ui.row().classes(
                    'w-full items-center justify-between'
                ):

                    with ui.column().classes(
                        'gap-0'
                    ):

                        ui.label(
                            'Clientes'
                        ).classes(
                            'page-title'
                        )

                        ui.label(
                            'Gestioná tus contactos de forma simple.'
                        ).classes(
                            'page-subtitle'
                        )

                    with ui.row().classes(
                        'items-center gap-2'
                    ):

                        ui.button(
                            'Exportar CSV',
                            icon='download',
                            on_click=exportar_csv
                        ).props(
                            'outline color=primary'
                        )

                        ui.button(
                            'Nuevo cliente',
                            icon='add',
                            on_click=lambda: abrir_formulario()
                        ).props(
                            'unelevated color=primary'
                        ).classes(
                            'px-5'
                        )

                # ============================================
                # ESTADÍSTICAS
                # ============================================

                with ui.grid(
                    columns=4
                ).classes(
                    'w-full gap-4'
                ):

                    with ui.card().classes(
                        'stat-card'
                    ):

                        ui.label(
                            'Total de contactos'
                        ).classes(
                            'stat-label'
                        )

                        total_label = ui.label(
                            '0'
                        ).classes(
                            'stat-value'
                        )

                    with ui.card().classes(
                        'stat-card'
                    ):

                        ui.label(
                            'Leads'
                        ).classes(
                            'stat-label'
                        )

                        leads_label = ui.label(
                            '0'
                        ).classes(
                            'stat-value'
                        )

                    with ui.card().classes(
                        'stat-card'
                    ):

                        ui.label(
                            'Contactados'
                        ).classes(
                            'stat-label'
                        )

                        contactados_label = ui.label(
                            '0'
                        ).classes(
                            'stat-value'
                        )

                    with ui.card().classes(
                        'stat-card'
                    ):

                        ui.label(
                            'Clientes'
                        ).classes(
                            'stat-label'
                        )

                        clientes_label = ui.label(
                            '0'
                        ).classes(
                            'stat-value'
                        )

                # ============================================
                # TABLA
                # ============================================

                with ui.column().classes(
                    'table-container w-full'
                ):

                    with ui.row().classes(
                        'w-full items-center p-4'
                    ):

                        busqueda = ui.input(
                            placeholder=(
                                'Buscar por nombre, empresa o email...'
                            )
                        ).props(
                            'outlined dense clearable'
                        ).classes(
                            'w-full max-w-md'
                        )

                        ui.space()

                        ui.button(
                            icon='refresh',
                            on_click=lambda: setattr(
                                tabla, 'rows',
                                obtener_filas(busqueda.value or '')
                            )
                        ).props(
                            'flat round'
                        )

                    columnas = [
                        {
                            'name': 'nombre',
                            'label': 'CONTACTO',
                            'field': 'nombre',
                            'align': 'left',
                        },
                        {
                            'name': 'empresa',
                            'label': 'EMPRESA',
                            'field': 'empresa',
                            'align': 'left',
                        },
                        {
                            'name': 'email',
                            'label': 'EMAIL',
                            'field': 'email',
                            'align': 'left',
                        },
                        {
                            'name': 'telefono',
                            'label': 'TELÉFONO',
                            'field': 'telefono',
                            'align': 'left',
                        },
                        {
                            'name': 'estado',
                            'label': 'ESTADO',
                            'field': 'estado',
                            'align': 'left',
                        },
                        {
                            'name': 'ultimo_contacto',
                            'label': 'ÚLTIMO CONTACTO',
                            'field': 'ultimo_contacto',
                            'align': 'left',
                        },
                        {
                            'name': 'acciones',
                            'label': '',
                            'field': 'acciones',
                            'align': 'right',
                        },
                    ]

                    tabla = ui.table(
                        columns=columnas,
                        rows=obtener_filas(),
                        row_key='id'
                    ).classes(
                        'w-full'
                    )

                    tabla.add_slot(
                        'body-cell-nombre',
                        r'''
                        <q-td :props="props">

                            <div
                                style="
                                    font-weight: 750;
                                    color: #25253a;
                                "
                            >
                                {{ props.row.nombre }}
                            </div>

                        </q-td>
                        '''
                    )

                    tabla.add_slot(
                        'body-cell-estado',
                        r'''
                        <q-td :props="props">

                            <q-badge
                                :color="
                                    props.row.estado === 'Cliente'
                                    ? 'positive'
                                    : props.row.estado === 'Lead'
                                    ? 'orange'
                                    : props.row.estado === 'Contactado'
                                    ? 'blue'
                                    : 'grey'
                                "
                                :label="props.row.estado"
                                outline
                            />

                        </q-td>
                        '''
                    )

                    tabla.add_slot(
                        'body-cell-acciones',
                        r'''
                        <q-td :props="props">

                            <q-btn
                                flat
                                round
                                dense
                                icon="edit"
                                color="primary"
                                @click="$parent.$emit('editar', props.row)"
                            />

                            <q-btn
                                flat
                                round
                                dense
                                icon="delete"
                                color="negative"
                                @click="$parent.$emit('eliminar', props.row)"
                            />

                        </q-td>
                        '''
                    )

                    tabla.on(
                        'editar',
                        lambda e: abrir_formulario(
                            e.args['id']
                        )
                    )

                    tabla.on(
                        'eliminar',
                        lambda e: confirmar_eliminacion(
                            e.args['id'],
                            e.args['nombre']
                        )
                    )

                    def buscar():
                        texto = busqueda.value or ''
                        tabla.rows = obtener_filas(texto)

                    busqueda.on(
                        'update:model-value',
                        lambda e: buscar()
                    )

                    busqueda.on(
                        'update:model-value',
                        lambda e: buscar()
                    )

                # ============================================
                # ACTUALIZAR ESTADÍSTICAS
                # ============================================

                total, leads, contactados, clientes = (
                    obtener_estadisticas()
                )

                total_label.set_text(
                    str(total)
                )

                leads_label.set_text(
                    str(leads)
                )

                contactados_label.set_text(
                    str(contactados)
                )

                clientes_label.set_text(
                    str(clientes)
                )

        construir_footer()


# ============================================================
# PÁGINA: EMBUDO DE VENTAS
# ============================================================

@ui.page('/embudo')
def pagina_embudo():

    if not requerir_autenticacion():
        return

    ui.add_head_html(
        f'<style>{CSS}</style>'
    )

    construir_navbar()

    with ui.column().classes(
        'w-full min-h-screen flex flex-col'
    ):

        with ui.column().classes(
            'w-full flex-grow'
        ):

            with ui.column().classes(
                'w-full max-w-6xl mx-auto p-8 gap-6'
            ):

                # ============================================
                # ENCABEZADO
                # ============================================

                with ui.column().classes(
                    'gap-1'
                ):

                    ui.label(
                        'Embudo de ventas'
                    ).classes(
                        'page-title'
                    )

                    ui.label(
                        'Visualizá cómo avanzan tus contactos '
                        'a través del proceso comercial.'
                    ).classes(
                        'page-subtitle'
                    )

                # ============================================
                # RESUMEN
                # ============================================

                total, leads, contactados, clientes_count, inactivos = (
                    obtener_estadisticas_completas()
                )

                with ui.grid(
                    columns=5
                ).classes(
                    'w-full gap-4'
                ):

                    for titulo, valor in [
                        ('Total', total),
                        ('Leads', leads),
                        ('Contactados', contactados),
                        ('Clientes', clientes_count),
                        ('Inactivos', inactivos)
                    ]:

                        with ui.card().classes(
                            'stat-card'
                        ):

                            ui.label(
                                titulo
                            ).classes(
                                'stat-label'
                            )

                            ui.label(
                                str(valor)
                            ).classes(
                                'stat-value'
                            )

                # ============================================
                # EMBUDO
                # ============================================

                with ui.card().classes(
                    'glass-card w-full p-8'
                ):

                    with ui.column().classes(
                        'funnel-container'
                    ):

                        # ------------------------------------
                        # LEADS
                        # ------------------------------------

                        with ui.element(
                            'div'
                        ).classes(
                            'funnel-stage funnel-lead'
                        ):

                            with ui.element(
                                'div'
                            ).classes(
                                'funnel-stage-inner'
                            ):

                                with ui.column().classes(
                                    'gap-1'
                                ):

                                    ui.label(
                                        'Leads'
                                    ).classes(
                                        'funnel-stage-title'
                                    )

                                    ui.label(
                                        'Nuevos contactos interesados'
                                    ).classes(
                                        'funnel-stage-description'
                                    )

                                ui.label(
                                    str(leads)
                                ).classes(
                                    'funnel-count'
                                )

                        # ------------------------------------
                        # CONTACTADOS
                        # ------------------------------------

                        with ui.element(
                            'div'
                        ).classes(
                            'funnel-stage funnel-contactado'
                        ):

                            with ui.element(
                                'div'
                            ).classes(
                                'funnel-stage-inner'
                            ):

                                with ui.column().classes(
                                    'gap-1'
                                ):

                                    ui.label(
                                        'Contactados'
                                    ).classes(
                                        'funnel-stage-title'
                                    )

                                    ui.label(
                                        'Se estableció primer contacto'
                                    ).classes(
                                        'funnel-stage-description'
                                    )

                                ui.label(
                                    str(contactados)
                                ).classes(
                                    'funnel-count'
                                )

                        # ------------------------------------
                        # CLIENTES
                        # ------------------------------------

                        with ui.element(
                            'div'
                        ).classes(
                            'funnel-stage funnel-cliente'
                        ):

                            with ui.element(
                                'div'
                            ).classes(
                                'funnel-stage-inner'
                            ):

                                with ui.column().classes(
                                    'gap-1'
                                ):

                                    ui.label(
                                        'Clientes'
                                    ).classes(
                                        'funnel-stage-title'
                                    )

                                    ui.label(
                                        'Cerraron compra o contrato'
                                    ).classes(
                                        'funnel-stage-description'
                                    )

                                ui.label(
                                    str(clientes_count)
                                ).classes(
                                    'funnel-count'
                                )

                        # ------------------------------------
                        # INACTIVOS
                        # ------------------------------------

                        with ui.element(
                            'div'
                        ).classes(
                            'funnel-stage funnel-inactivo'
                        ):

                            with ui.element(
                                'div'
                            ).classes(
                                'funnel-stage-inner'
                            ):

                                with ui.column().classes(
                                    'gap-1'
                                ):

                                    ui.label(
                                        'Inactivos'
                                    ).classes(
                                        'funnel-stage-title'
                                    )

                                    ui.label(
                                        'Sin respuesta reciente'
                                    ).classes(
                                        'funnel-stage-description'
                                    )

                                ui.label(
                                    str(inactivos)
                                ).classes(
                                    'funnel-count'
                                )

        construir_footer()


# ============================================================
# PÁGINA: AYUDA
# ============================================================

@ui.page('/ayuda')
def pagina_ayuda():

    if not requerir_autenticacion():
        return

    ui.add_head_html(
        f'<style>{CSS}</style>'
    )

    construir_navbar()

    with ui.column().classes(
        'w-full min-h-screen flex flex-col'
    ):

        with ui.column().classes(
            'w-full flex-grow'
        ):

            with ui.column().classes(
                'w-full max-w-4xl mx-auto p-8 gap-6'
            ):

                # ============================================
                # ENCABEZADO
                # ============================================

                with ui.column().classes(
                    'gap-1'
                ):

                    ui.label(
                        'Ayuda'
                    ).classes(
                        'page-title'
                    )

                    ui.label(
                        'Aprendé a usar simpleCRM en pocos pasos.'
                    ).classes(
                        'page-subtitle'
                    )

                # ============================================
                # GUÍA
                # ============================================

                pasos = [
                    {
                        'numero': '1',
                        'titulo': 'Agregá tus contactos',
                        'texto': (
                            'Hacé clic en "Nuevo cliente" para '
                            'cargar un contacto. Completá el nombre '
                            '(obligatorio), empresa, email, teléfono '
                            'y el estado inicial (Lead por defecto).'
                        )
                    },
                    {
                        'numero': '2',
                        'titulo': 'Gestioná los estados',
                        'texto': (
                            'Cada cliente tiene un estado: Lead, '
                            'Contactado, Cliente o Inactivo. '
                            'Editá el cliente para avanzarlo en el '
                            'embudo comercial a medida que '
                            'progresá la relación.'
                        )
                    },
                    {
                        'numero': '3',
                        'titulo': 'Buscá y filtrá',
                        'texto': (
                            'Usá la barra de búsqueda para encontrar '
                            'contactos por nombre, empresa o email. '
                            'Los resultados se actualizan en tiempo '
                            'real mientras escribís.'
                        )
                    },
                    {
                        'numero': '4',
                        'titulo': 'Exportá tus datos',
                        'texto': (
                            'Hacé clic en "Exportar CSV" para '
                            'descargar todos tus contactos en un '
                            'archivo CSV compatible con Excel y '
                            'Google Sheets.'
                        )
                    },
                    {
                        'numero': '5',
                        'titulo': 'Visualizá el embudo',
                        'texto': (
                            'La página "Embudo" te muestra de forma '
                            'visual cómo están distribuidos tus '
                            'contactos en cada etapa del proceso '
                            'comercial.'
                        )
                    },
                    {
                        'numero': '6',
                        'titulo': 'Gestioná usuarios',
                        'texto': (
                            'Si sos administrador, podés acceder a '
                            '"Usuarios" en el menú para crear, '
                            'eliminar y gestionar contraseñas de '
                            'otros usuarios del sistema.'
                        )
                    },
                ]

                for paso in pasos:

                    with ui.card().classes(
                        'help-card w-full'
                    ):

                        with ui.row().classes(
                            'items-start gap-4'
                        ):

                            with ui.element(
                                'div'
                            ).classes(
                                'help-number'
                            ):

                                ui.label(
                                    paso['numero']
                                )

                            with ui.column().classes(
                                'gap-1'
                            ):

                                ui.label(
                                    paso['titulo']
                                ).classes(
                                    'help-title'
                                )

                                ui.label(
                                    paso['texto']
                                ).classes(
                                    'help-text'
                                )

        construir_footer()


# ============================================================
# PÁGINA: USUARIOS (solo admin)
# ============================================================

@ui.page('/usuarios')
def pagina_usuarios():

    if not requerir_autenticacion():
        return

    if not es_admin():

        ui.notify(
            'No tenés permisos para acceder a esta página',
            type='negative'
        )

        ui.navigate.to('/')

        return

    ui.add_head_html(
        f'<style>{CSS}</style>'
    )

    construir_navbar()

    with ui.column().classes(
        'w-full min-h-screen flex flex-col'
    ):

        with ui.column().classes(
            'w-full flex-grow'
        ):

            with ui.column().classes(
                'w-full max-w-5xl mx-auto p-8 gap-6'
            ):

                # ============================================
                # ENCABEZADO
                # ============================================

                with ui.row().classes(
                    'w-full items-center justify-between'
                ):

                    with ui.column().classes(
                        'gap-0'
                    ):

                        ui.label(
                            'Usuarios'
                        ).classes(
                            'page-title'
                        )

                        ui.label(
                            'Gestioná los usuarios que tienen acceso al CRM.'
                        ).classes(
                            'page-subtitle'
                        )

                    ui.button(
                        'Nuevo usuario',
                        icon='person_add',
                        on_click=lambda: abrir_formulario_usuario()
                    ).props(
                        'unelevated color=primary'
                    ).classes(
                        'px-5'
                    )

                # ============================================
                # TABLA DE USUARIOS
                # ============================================

                with ui.column().classes(
                    'table-container w-full'
                ):

                    columnas = [
                        {
                            'name': 'username',
                            'label': 'USUARIO',
                            'field': 'username',
                            'align': 'left',
                        },
                        {
                            'name': 'nombre',
                            'label': 'NOMBRE',
                            'field': 'nombre',
                            'align': 'left',
                        },
                        {
                            'name': 'rol',
                            'label': 'ROL',
                            'field': 'rol',
                            'align': 'left',
                        },
                        {
                            'name': 'acciones',
                            'label': '',
                            'field': 'acciones',
                            'align': 'right',
                        },
                    ]

                    filas = []

                    for u in obtener_todos_usuarios():

                        filas.append({
                            'id': u[0],
                            'username': u[1],
                            'nombre': u[2],
                            'rol': u[3],
                        })

                    tabla_usuarios = ui.table(
                        columns=columnas,
                        rows=filas,
                        row_key='id'
                    ).classes(
                        'w-full'
                    )

                    tabla_usuarios.add_slot(
                        'body-cell-username',
                        r'''
                        <q-td :props="props">

                            <div style="
                                display: flex;
                                align-items: center;
                                gap: 10px;
                            ">
                                <div style="
                                    width: 34px;
                                    height: 34px;
                                    min-width: 34px;
                                    border-radius: 10px;
                                    background: linear-gradient(135deg, #6366f1, #8b5cf6);
                                    color: white;
                                    display: flex;
                                    align-items: center;
                                    justify-content: center;
                                    font-weight: 800;
                                    font-size: 13px;
                                ">
                                    {{ props.row.nombre ? props.row.nombre[0].toUpperCase() : "?" }}
                                </div>
                                <span style="font-weight: 650; color: #25253a;">
                                    {{ props.row.username }}
                                </span>
                            </div>

                        </q-td>
                        '''
                    )

                    tabla_usuarios.add_slot(
                        'body-cell-rol',
                        r'''
                        <q-td :props="props">

                            <q-badge
                                :color="
                                    props.row.rol === 'admin'
                                    ? 'purple'
                                    : 'grey'
                                "
                                :label="
                                    props.row.rol === 'admin'
                                    ? 'Admin'
                                    : 'Usuario'
                                "
                                outline
                            />

                        </q-td>
                        '''
                    )

                    tabla_usuarios.add_slot(
                        'body-cell-acciones',
                        r'''
                        <q-td :props="props">

                            <q-btn
                                flat
                                round
                                dense
                                icon="key"
                                color="primary"
                                @click="$parent.$emit('cambiar_pass', props.row)"
                            >
                                <q-tooltip>Cambiar contraseña</q-tooltip>
                            </q-btn>

                            <q-btn
                                flat
                                round
                                dense
                                icon="delete"
                                color="negative"
                                @click="$parent.$emit('eliminar_usuario', props.row)"
                            >
                                <q-tooltip>Eliminar usuario</q-tooltip>
                            </q-btn>

                        </q-td>
                        '''
                    )

                    tabla_usuarios.on(
                        'cambiar_pass',
                        lambda e: abrir_cambiar_password(
                            e.args['id'],
                            e.args['nombre']
                        )
                    )

                    tabla_usuarios.on(
                        'eliminar_usuario',
                        lambda e: confirmar_eliminacion_usuario(
                            e.args['id'],
                            e.args['nombre'],
                            e.args['username']
                        )
                    )

        construir_footer()


# ============================================================
# FORMULARIO DE USUARIO (nuevo)
# ============================================================

def abrir_formulario_usuario():

    with ui.dialog() as dialog:

        with ui.card().classes(
            'w-[480px] max-w-[95vw] p-7'
        ):

            with ui.row().classes(
                'items-center gap-3 mb-2'
            ):

                with ui.element('div').classes(
                    'logo-icon'
                ):

                    ui.icon(
                        'person_add'
                    )

                ui.label(
                    'Nuevo usuario'
                ).classes(
                    'text-2xl font-bold'
                )

            ui.label(
                'Creá una nueva cuenta de acceso al CRM.'
            ).classes(
                'text-sm text-gray-500 mb-5'
            )

            username_input = ui.input(
                'Usuario *',
                placeholder='Ej: jmartinez'
            ).props(
                'outlined'
            ).classes(
                'w-full'
            )

            nombre_input = ui.input(
                'Nombre completo *',
                placeholder='Ej: Juan Martínez'
            ).props(
                'outlined'
            ).classes(
                'w-full'
            )

            password_input = ui.input(
                'Contraseña *',
                placeholder='Mínimo 4 caracteres',
                password=True,
                password_toggle_button=True
            ).props(
                'outlined'
            ).classes(
                'w-full'
            )

            rol_input = ui.select(
                ['admin', 'usuario'],
                label='Rol',
                value='usuario'
            ).props(
                'outlined'
            ).classes(
                'w-full'
            )

            with ui.row().classes(
                'w-full justify-end gap-2 mt-5'
            ):

                ui.button(
                    'Cancelar',
                    on_click=dialog.close
                ).props(
                    'flat'
                )

                def guardar():

                    if not username_input.value.strip():

                        ui.notify(
                            'El usuario es obligatorio',
                            type='negative'
                        )

                        return

                    if not nombre_input.value.strip():

                        ui.notify(
                            'El nombre es obligatorio',
                            type='negative'
                        )

                        return

                    if not password_input.value or len(
                        password_input.value
                    ) < 4:

                        ui.notify(
                            'La contraseña debe tener al menos 4 caracteres',
                            type='negative'
                        )

                        return

                    existente = obtener_usuario(
                        username_input.value.strip()
                    )

                    if existente:

                        ui.notify(
                            'Ese nombre de usuario ya existe',
                            type='negative'
                        )

                        return

                    crear_usuario({
                        'username': username_input.value.strip(),
                        'nombre': nombre_input.value.strip(),
                        'password': password_input.value,
                        'rol': rol_input.value,
                    })

                    ui.notify(
                        'Usuario creado correctamente',
                        type='positive'
                    )

                    dialog.close()

                    ui.navigate.to('/usuarios')

                ui.button(
                    'Crear usuario',
                    icon='person_add',
                    on_click=guardar
                ).props(
                    'unelevated color=primary'
                )

    dialog.open()


# ============================================================
# CAMBIAR CONTRASEÑA
# ============================================================

def abrir_cambiar_password(user_id, nombre):

    with ui.dialog() as dialog:

        with ui.card().classes(
            'w-[420px] max-w-[95vw] p-7'
        ):

            with ui.row().classes(
                'items-center gap-3 mb-2'
            ):

                with ui.element('div').classes(
                    'help-number'
                ):

                    ui.icon(
                        'key'
                    )

                ui.label(
                    'Cambiar contraseña'
                ).classes(
                    'text-xl font-bold'
                )

            ui.label(
                f'Ingresá la nueva contraseña para {nombre}.'
            ).classes(
                'text-gray-600 mt-2 mb-4'
            )

            nueva_pass = ui.input(
                'Nueva contraseña *',
                placeholder='Mínimo 4 caracteres',
                password=True,
                password_toggle_button=True
            ).props(
                'outlined'
            ).classes(
                'w-full'
            )

            with ui.row().classes(
                'w-full justify-end gap-2 mt-5'
            ):

                ui.button(
                    'Cancelar',
                    on_click=dialog.close
                ).props(
                    'flat'
                )

                def guardar():

                    if not nueva_pass.value or len(
                        nueva_pass.value
                    ) < 4:

                        ui.notify(
                            'La contraseña debe tener al menos 4 caracteres',
                            type='negative'
                        )

                        return

                    cambiar_password(
                        user_id,
                        nueva_pass.value
                    )

                    ui.notify(
                        'Contraseña actualizada',
                        type='positive'
                    )

                    dialog.close()

                ui.button(
                    'Guardar',
                    icon='save',
                    on_click=guardar
                ).props(
                    'unelevated color=primary'
                )

    dialog.open()


# ============================================================
# CONFIRMAR ELIMINACIÓN DE USUARIO
# ============================================================

def confirmar_eliminacion_usuario(
    user_id,
    nombre,
    username
):

    if user_id == app.storage.user.get('id'):

        ui.notify(
            'No podés eliminar tu propio usuario',
            type='negative'
        )

        return

    with ui.dialog() as dialog:

        with ui.card().classes(
            'p-7 w-[400px] max-w-[95vw]'
        ):

            with ui.row().classes(
                'items-center gap-3'
            ):

                with ui.element('div').classes(
                    'help-number'
                ):

                    ui.icon(
                        'delete'
                    )

                ui.label(
                    'Eliminar usuario'
                ).classes(
                    'text-xl font-bold'
                )

            ui.label(
                f'¿Seguro que querés eliminar al usuario "{username}" ({nombre})?'
            ).classes(
                'text-gray-600 mt-3'
            )

            with ui.row().classes(
                'w-full justify-end gap-2 mt-6'
            ):

                ui.button(
                    'Cancelar',
                    on_click=dialog.close
                ).props(
                    'flat'
                )

                def eliminar():

                    eliminar_usuario(user_id)

                    dialog.close()

                    ui.notify(
                        'Usuario eliminado',
                        type='positive'
                    )

                    ui.navigate.to('/usuarios')

                ui.button(
                    'Eliminar',
                    icon='delete',
                    on_click=eliminar
                ).props(
                    'unelevated color=negative'
                )

    dialog.open()


# ============================================================
# INICIO
# ============================================================

inicializar_db()
cargar_datos_demo()

ui.run(
    title='simpleCRM',
    favicon='👥',
    port=8080,
    reload=False,
    storage_secret='simpleCRM_secret_key_2024'
)

# ui.run(
#     host='0.0.0.0'
#     port=8080,
# )