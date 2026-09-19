"""
modules/schema.py  --  the single source of truth for WHAT we extract.

* FIELDS          : the 7 fields the hackathon compares.
* LABEL_ALIASES   : every way a document might *label* each field.
                    "Port of Loading", "POL", "Load Port" -> port_of_loading.

To support a new label you saw in a document, add it to LABEL_ALIASES below.
Nothing else needs to change. Case, punctuation, spaces, (brackets) and
Chinese text are ignored when labels are matched, so you only need one
spelling per variant.
"""

FIELDS = [
    "shipper",
    "consignee",
    "notify_party",
    "port_of_loading",
    "port_of_discharge",
    "container_count",
    "gross_weight_kg",
]

PARTY_FIELDS = ("shipper", "consignee", "notify_party")
PORT_FIELDS = ("port_of_loading", "port_of_discharge")

# Sentinel: labels we recognise but must NOT use (e.g. NET weight is not GROSS weight).
IGNORE = "_ignore"

LABEL_ALIASES = {
    "shipper": [
        "Shipper",
        "Shipper/Exporter",
        "Shipper (Principal or Seller)",
    ],
    "consignee": [
        "Consignee",
        "Consignee (Non-Negotiable)",
        "To the Order of",      # BLs often say this instead of "Consignee"
        "To Order of",
    ],
    "notify_party": [
        "Notify",
        "Notify Party",
        "Notify Party/Intermediate Consignee",
    ],
    "port_of_loading": [
        "Port of Loading",
        "Port of Loading (POL)",
        "POL",
        "Load Port",
        "Loading Port",
    ],
    "port_of_discharge": [
        "Port of Discharge",
        "Port of Discharge (POD)",
        "POD",
        "Discharge Port",
    ],
    "container_count": [
        "No. of Containers",
        "No. of Containers or Packages",
        "Total Containers",
        "Container Count",
        "Containers",
        "Number of Containers",
    ],
    "gross_weight_kg": [
        "Gross Weight",
        "Gross Weight (KG)",
        "Gross Wt (kgs)",
        "Gross Weight毛重(KGS)",
        "Total Gross Wt (kgs)",
        "Total Gross Weight",
    ],
    IGNORE: [
        "Net Weight",
        "Net Wt",
        "Tare Weight",
    ],
}

# Words in a document title that tell us what kind of document it is.
# Checked in order against the first few lines of the document.
TITLE_RULES = [
    ("OTHER:CERTIFICATE_OF_ORIGIN", ["certificate of origin"]),
    ("OTHER:INVOICE", ["commercial invoice", "proforma invoice", "tax invoice"]),
    ("OTHER:PACKING_LIST", ["packing list"]),
    ("SI", ["shipping instruction", "bl instruction", "bill of lading instruction"]),
    ("BL", ["bill of lading", "bl draft", "draft bl"]),
]