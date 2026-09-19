"""
modules/schema.py

Single source of truth for the seven required shipping fields.

The aliases intentionally include:
    - industry terminology
    - abbreviations
    - common PDF extraction variants
    - OCR variants
    - international shipping terminology
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

PARTY_FIELDS = (
    "shipper",
    "consignee",
    "notify_party",
)

PORT_FIELDS = (
    "port_of_loading",
    "port_of_discharge",
)

IGNORE = "_ignore"


# ---------------------------------------------------------------------------
# Field aliases
# ---------------------------------------------------------------------------

LABEL_ALIASES = {

    # -----------------------------------------------------------------------
    # SHIPPER
    # -----------------------------------------------------------------------

    "shipper": [
        "Shipper",
        "Shipper/Exporter",
        "Shipper / Exporter",
        "Exporter",
        "Exporter Name",
        "Shipper Name",
        "Principal Shipper",
        "Principal or Seller",
        "Shipper (Principal or Seller)",
        "Seller",
        "Consignor",
    ],

    # -----------------------------------------------------------------------
    # CONSIGNEE
    # -----------------------------------------------------------------------

    "consignee": [
        "Consignee",
        "Consignee Name",
        "Consignee (Non-Negotiable)",
        "Consignee / Importer",
        "Importer",
        "Importer Name",
        "Receiver",
        "Receiver Name",
        "To the Order of",
        "To Order of",
        "Order of",
    ],

    # -----------------------------------------------------------------------
    # NOTIFY PARTY
    # -----------------------------------------------------------------------

    "notify_party": [
        "Notify",
        "Notify Party",
        "Notify Party Name",
        "Notify Party/Intermediate Consignee",
        "Notify Party / Intermediate Consignee",
        "Notify/Intermediate Consignee",
        "Intermediate Consignee",
        "Intermediate Consignee Name",
    ],

    # -----------------------------------------------------------------------
    # PORT OF LOADING
    # -----------------------------------------------------------------------

    "port_of_loading": [
        "Port of Loading",
        "Port of Loading (POL)",
        "POL",
        "P.O.L",
        "P O L",
        "Load Port",
        "Loading Port",
        "Port Loading",
        "Place of Loading",
        "Place of Receipt",
        "Port of Shipment",
        "Shipment Port",
        "Origin Port",
        "Port of Origin",
        "Departure Port",
        "Loading Place",
        "Port of Loading/Shipment",
    ],

    # -----------------------------------------------------------------------
    # PORT OF DISCHARGE
    # -----------------------------------------------------------------------

    "port_of_discharge": [
        "Port of Discharge",
        "Port of Discharge (POD)",
        "POD",
        "P.O.D",
        "P O D",
        "Discharge Port",
        "Port Discharge",
        "Place of Discharge",
        "Destination Port",
        "Port of Destination",
        "Arrival Port",
        "Discharging Port",
        "Final Port",
        "Final Destination Port",
    ],

    # -----------------------------------------------------------------------
    # CONTAINER COUNT
    # -----------------------------------------------------------------------

    "container_count": [
        "No. of Containers",
        "No of Containers",
        "No. Of Container",
        "Number of Containers",
        "Number Of Container",
        "Container Count",
        "Containers Count",
        "Total Containers",
        "Total Container",
        "Container Quantity",
        "Container Qty",
        "Qty of Containers",
        "Quantity of Containers",
        "No. Containers",
        "No Containers",
        "Containers",
        "Equipment Quantity",
        "Equipment Qty",
        "Equipment Count",
    ],

    # -----------------------------------------------------------------------
    # GROSS WEIGHT
    # -----------------------------------------------------------------------

    "gross_weight_kg": [
        "Gross Weight",
        "Gross Weight (KG)",
        "Gross Weight (KGS)",
        "Gross Wt",
        "Gross Wt (KG)",
        "Gross Wt (KGS)",
        "Gross Wt Kgs",
        "Gross Mass",
        "Total Gross Weight",
        "Total Gross Wt",
        "Total Gross Wt (kgs)",
        "Cargo Gross Weight",
        "Cargo Gross Wt",
        "Shipment Gross Weight",
        "Shipment Gross Wt",
        "Weight Gross",
        "Gross Weight 毛重",
        "Gross Weight毛重(KGS)",
        "Gross Mass (KG)",
        "Gross Mass (KGS)",
    ],

    # -----------------------------------------------------------------------
    # NEVER use these as gross weight
    # -----------------------------------------------------------------------

    IGNORE: [
        "Net Weight",
        "Net Wt",
        "Net Mass",
        "Net Weight (KG)",
        "Net Weight (KGS)",
        "Tare Weight",
        "Tare Wt",
        "Tare Mass",
        "Container Tare",
        "Cargo Net Weight",
    ],
}


# ---------------------------------------------------------------------------
# Document-type rules
# ---------------------------------------------------------------------------

TITLE_RULES = [

    (
        "OTHER:CERTIFICATE_OF_ORIGIN",
        [
            "certificate of origin",
            "certificate of origin form",
            "country of origin certificate",
        ],
    ),

    (
        "OTHER:INVOICE",
        [
            "commercial invoice",
            "commercial invoice",
            "proforma invoice",
            "pro forma invoice",
            "tax invoice",
            "invoice",
        ],
    ),

    (
        "OTHER:PACKING_LIST",
        [
            "packing list",
            "packing slip",
            "packing details",
        ],
    ),

    (
        "SI",
        [
            "shipping instruction",
            "shipping instructions",
            "shipping instruction form",
            "bl instruction",
            "bill of lading instruction",
            "shipping instruction details",
        ],
    ),

    (
        "BL",
        [
            "bill of lading",
            "billoflading",
            "b/l",
            "b l",
            "bl draft",
            "draft bl",
            "draft bill of lading",
            "original bill of lading",
            "house bill of lading",
            "master bill of lading",
        ],
    ),
]