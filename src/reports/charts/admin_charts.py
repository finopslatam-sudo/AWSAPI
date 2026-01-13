import matplotlib.pyplot as plt
import tempfile

def generate_users_by_plan_chart(stats) -> str:
    plans = [p["plan"] for p in stats["users_by_plan"]]
    counts = [p["count"] for p in stats["users_by_plan"]]

    path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name

    plt.figure(figsize=(8, 4))
    plt.bar(plans, counts)
    plt.title("Usuarios por plan")
    plt.ylabel("Cantidad")
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()

    return path
