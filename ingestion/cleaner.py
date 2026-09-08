"""Province and sector name standardization."""

PROVINCE_ALIASES = {
    "milan": "Milano",
    "milano": "Milano",
    "mi": "Milano",
    "bergamo": "Bergamo",
    "brescia": "Brescia",
    "monza": "Monza e Brianza",
    "monza e brianza": "Monza e Brianza",
    "brianza": "Monza e Brianza",
    "varese": "Varese",
}

SECTOR_ALIASES = {
    "textile": "Textile Manufacturing",
    "textile manufacturing": "Textile Manufacturing",
    "manufacturing": "Manufacturing",
    "commercio": "Retail Trade",
    "retail": "Retail Trade",
    "precision machining": "Precision Machining",
    "agri-food": "Agri-Food",
    "agri food": "Agri-Food",
}


def standardize_province(value: str) -> str:
    if not value:
        return "Milano"
    key = value.strip().lower()
    return PROVINCE_ALIASES.get(key, value.strip().title())


def standardize_sector(value: str) -> str:
    if not value:
        return "Manufacturing"
    key = value.strip().lower()
    return SECTOR_ALIASES.get(key, value.strip().title())
