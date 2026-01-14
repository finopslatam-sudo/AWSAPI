import csv
import io
from datetime import datetime


def build_admin_csv(stats: dict) -> bytes:
    """
    Genera un CSV administrativo profesional para FinOpsLatam.
    Compatible con Excel / Google Sheets.
    """

    output = io.StringIO()
    writer = csv.writer(output)

    # =====================================================
    # HEADER CORPORATIVO
    # =====================================================
    writer.writerow(["FinOpsLatam — Reporte Administrativo"])
    writer.writerow([
        "Generado el",
        datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC"),
    ])
    writer.writerow([])

    # =====================================================
    # RESUMEN GENERAL (KPIs)
    # =====================================================
    writer.writerow(["RESUMEN GENERAL"])
    writer.writerow(["Usuarios totales", stats.get("total_users", 0)])
    writer.writerow(["Usuarios activos", stats.get("active_users", 0)])
    writer.writerow(["Usuarios inactivos", stats.get("inactive_users", 0)])
    writer.writerow([])

    # =====================================================
    # USUARIOS POR ESTADO (PORCENTAJE)
    # =====================================================
    total_users = (
        stats.get("active_users", 0)
        + stats.get("inactive_users", 0)
    )

    writer.writerow(["USUARIOS POR ESTADO (PORCENTAJE)"])
    writer.writerow(["Estado", "Porcentaje"])

    if total_users > 0:
        active_pct = round(
            (stats.get("active_users", 0) / total_users) * 100,
            2,
        )
        inactive_pct = round(100 - active_pct, 2)
    else:
        active_pct = inactive_pct = 0

    writer.writerow(["Activos", f"{active_pct}%"])
    writer.writerow(["Inactivos", f"{inactive_pct}%"])
    writer.writerow([])

    # =====================================================
    # USUARIOS POR PLAN
    # =====================================================
    writer.writerow(["USUARIOS POR PLAN"])
    writer.writerow(["Plan", "Cantidad"])

    for plan in stats.get("users_by_plan", []):
        writer.writerow([
            plan.get("plan", ""),
            plan.get("count", 0),
        ])

    writer.writerow([])

    # =====================================================
    # FOOTER LEGAL
    # =====================================================
    writer.writerow([
        "© 2026 FinOpsLatam — Información confidencial. Uso exclusivo interno."
    ])

    return output.getvalue().encode("utf-8")
