# Re-export InventoryScanner so callers can import from this package directly.
# e.g.:  from src.aws.scanners import InventoryScanner
from src.aws.inventory_scanner import InventoryScanner

__all__ = ["InventoryScanner"]
