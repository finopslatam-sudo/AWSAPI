# AWSAPI
1️⃣ README.md — Repositorio Oficial (técnico-operativo)

👉 Este archivo vive en la raíz del repo
👉 Público / semi-público
👉 Enfocado a desarrolladores técnicos

📘 FinOpsLatam Backend API

Backend oficial de FinOpsLatam, plataforma SaaS FinOps multi-tenant para auditoría y optimización de costos en la nube.

🚀 Stack Tecnológico

Framework: Flask (Python)

Arquitectura: API REST

Autenticación: JWT

ORM: SQLAlchemy + Alembic

Base de datos: PostgreSQL

Exports: PDF / CSV / XLSX

Infra: Gunicorn + systemd

🧠 Conceptos Clave

Multi-tenant real (clientes completamente aislados)

Usuarios ≠ Clientes

Planes desacoplados vía suscripciones

Backend como única fuente de verdad

Frontend sin lógica de permisos

📁 Estructura del Proyecto
AWSAPI/
├── app.py
├── requirements.txt
├── migrations/
└── src/
    ├── auth_system.py
    ├── models/
    ├── routes/
    ├── services/
    ├── reports/
    │   ├── admin/
    │   ├── client/
    │   └── exporters/
    └── assets/

🔐 Autenticación

JWT stateless

Claims incluidos:

global_role

client_role

client_id

Endpoints principales:

POST /api/auth/login
POST /api/auth/change-password
POST /api/auth/forgot-password

🧩 Roles
Globales

root

support

Cliente

owner

finops_admin

viewer

📌 Todos los permisos se validan en backend.

📊 Reportes
Admin
/api/v1/reports/admin/pdf
/api/v1/reports/admin/csv
/api/v1/reports/admin/xlsx

Cliente
/api/v1/reports/client/pdf
/api/v1/reports/client/csv
/api/v1/reports/client/xlsx

⚙️ Instalación Local
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask db upgrade
python app.py

📦 Dependencias

Ver requirements.txt (oficial y alineado a producción).

🏁 Estado

✅ Producción
✅ Escalable
✅ Listo para auditoría

2️⃣ Documentación para Inversionistas (NO técnica)

👉 Pitch técnico-estratégico
👉 Lenguaje negocio
👉 Ideal para deck / PDF

FinOpsLatam — Plataforma SaaS FinOps
¿Qué es FinOpsLatam?

FinOpsLatam es una plataforma SaaS FinOps que permite a empresas:

auditar costos en la nube

identificar desperdicios

optimizar recursos

generar reportes ejecutivos profesionales

🧩 Diferenciadores Técnicos

Arquitectura multi-tenant real

Aislamiento completo por cliente

Reportes ejecutivos listos para CFO / CTO

Preparado para escala regional

🔐 Seguridad & Compliance

Autenticación JWT

Roles estrictos

Eventos de seguridad auditables

No exposición de datos entre clientes

📈 Escalabilidad

Agregar clientes sin tocar base de datos

Nuevos planes sin migraciones

Nuevos servicios cloud desacoplados

🏁 Estado del Producto

Backend en producción

Arquitectura madura

Lista para crecimiento comercial

Sin deuda técnica estructural

3️⃣ Guía de Onboarding para Nuevos Developers

👉 Documento interno
👉 Reduce errores
👉 Acelera incorporación

👋 Bienvenido al Backend FinOpsLatam

Antes de escribir código, lee esto completo.

🧠 Reglas Fundamentales

❌ NO acceder a DB desde routes
❌ NO validar permisos en frontend
❌ NO mezclar lógica de negocio con reportes

✅ Todo pasa por services
✅ JWT manda
✅ Cliente ≠ Usuario

🔁 Flujo Mental Correcto
Route → Service → Model → Response


Reportes:

Stats Provider → Exporter

📍 Dónde agregar cosas
Necesitas…	Ve a…
Nuevo endpoint	routes/
Nueva lógica	services/
Nuevo reporte	reports/
Nuevo modelo	models/
🧪 Testing Manual
curl -H "Authorization: Bearer <token>" \
     http://localhost:5001/api/admin/stats

⚠️ Archivos sensibles (NO tocar)

models/*

exporters/*

auth_system.py

4️⃣ Documentación Técnica para Auditoría / Certificación

👉 Formal, precisa, verificable
👉 Ideal para ISO / SOC / auditoría externa

Arquitectura

API REST stateless

Separación estricta de capas

No lógica de negocio en frontend

Seguridad

JWT firmado

Expiración controlada

Eventos críticos notificados por email

Password hashing (bcrypt)

Multi-tenancy

Separación por client_id

Validación obligatoria en backend

Imposible cruzar datos entre clientes

Trazabilidad

Eventos de seguridad centralizados

Logging estructurado

Accesos root auditables

Gestión de Dependencias

Todas declaradas en requirements.txt

Entorno virtual obligatorio

Versiones fijadas

Estado Final

✔ Cumple principios de aislamiento
✔ Cumple separación de responsabilidades
✔ Listo para revisión externa