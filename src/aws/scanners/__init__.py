"""Scanner package exports (lazy to avoid circular imports)."""

__all__ = ["InventoryScanner"]


def __getattr__(name):
    if name == "InventoryScanner":
        from src.aws.inventory_scanner import InventoryScanner
        return InventoryScanner
    raise AttributeError(name)
