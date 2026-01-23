import csv
import io
from datetime import datetime
from collections import Counter


def build_admin_csv(stats: dict) -> bytes:
    """
    Genera un CSV administrativo para FinOpsLatam.

    Reporte enfocado en CLIENTES y PLANES,
    no en usuarios individuales.
    """

    clients = stats.get("clients", [])

    total_clients = len(clients)
    active_clients = len([c for c in clients if c["is_active"]])
    inactive_clients = total_clients - active_clients

    plans_counter = Counter(
        c["plan"] or "Sin plan"
        for c in clients
    )

    output = io.StringIO()
    writer = csv.writer(output)

    # =====================================================
    # HEADER
    # =====================================================
    writer.writerow(["FinOpsLatam — Reporte Administrativo"])
    writer.writerow([
        "Generado el",
        datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC"),
    ])
    writer.writerow([])

    # =====================================================
    # RESUMEN GENERAL
    # =====================================================
    writer.writerow(["RESUMEN GENERAL"])
    writer.writerow(["Clientes totales", total_clients])
    writer.writerow(["Clientes activos", active_clients])
    writer.writerow(["Clientes inactivos", inactive_clients])
    writer.writerow([])

    # =====================================================
    # CLIENTES POR ESTADO (PORCENTAJE)
    # =====================================================
    writer.writerow(["CLIENTES POR ESTADO (PORCENTAJE)"])
    writer.writerow(["Estado", "Porcentaje"])

    if total_clients > 0:
        active_pct = round((active_clients / total_clients) * 100, 2)
        inactive_pct = round(100 - active_pct, 2)
    else:
        active_pct = inactive_pct = 0

    writer.writerow(["Activos", f"{active_pct}%"])
    writer.writerow(["Inactivos", f"{inactive_pct}%"])
    writer.writerow([])

    # =====================================================
    # CLIENTES POR PLAN
    # =====================================================
    writer.writerow(["CLIENTES POR PLAN"])
    writer.writerow(["Plan", "Cantidad de clientes"])

    for plan, count in plans_counter.items():
        writer.writerow([plan, count])

    writer.writerow([])

    # =====================================================
    # FOOTER
    # =====================================================
    writer.writerow([
        "© 2026 FinOpsLatam — Información confidencial. Uso exclusivo interno."
    ])

    return output.getvalue().encode("utf-8")
