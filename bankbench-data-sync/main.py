"""
Modulo: main.py
Descrizione: Unico punto di bootstrap. Delega all'entrypoint CLI dell'adapter inbound.
"""
from __future__ import annotations

from bankbench_data_sync.adapters.inbound.cli.run import main

if __name__ == "__main__":
    main()
