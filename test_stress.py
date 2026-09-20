"""
Stress test: the same shipment written in many different ways.   Run:   python test_stress.py
If you add a new label wording to modules/schema.py, add a line here too.
"""
from modules.field_extractor import extract_fields
from modules.schema import FIELDS

EXPECT = {"shipper": "ACMELTD", "consignee": "FOOGMBH", "notify_party": "FOOGMBH", "port_of_loading": "NANTONG",
          "port_of_discharge": "KARACHI", "container_count": 3, "gross_weight_kg": 22000}


def doc(lines):
    return "SHIPPING INSTRUCTION\n" + "\n".join(lines) + "\n"


def with_weight(v):
    return doc(["Shipper: ACME LTD", "Consignee: FOO GMBH", "Notify: FOO GMBH", "Port of Loading: NANTONG",
                "Port of Discharge: KARACHI", "Containers: 3 x 40'HC", f"Gross Weight: {v}"])


def with_containers(v):
    return doc(["Shipper: ACME LTD", "Consignee: FOO GMBH", "Notify: FOO GMBH", "Port of Loading: NANTONG",
                "Port of Discharge: KARACHI", f"Containers: {v}", "Gross Weight: 22,000 KG"])


CASES = {
    # ---- other label wordings
    "labels_A": doc(["Shipper Name: ACME LTD", "Consignee Name: FOO GMBH", "Notify Party Name: FOO GMBH", "Port of Load: NANTONG, CHINA",
                     "Port of Unloading: KARACHI, PAKISTAN", "Number of Containers: 3 x 40'HC", "G.W.: 22,000 KGS"]),
    "labels_B": doc(["Exporter: ACME LTD", "Consigned To: FOO GMBH", "Notify: FOO GMBH", "Departure Port: NANTONG, CHINA",
                     "Destination Port: KARACHI, PAKISTAN", "Container Qty: 3 x 40'HC", "Gross Wt.: 22,000 KGS"]),
    "labels_C": doc(["SHIPPER: ACME LTD", "CONSIGNEE: FOO GMBH", "NOTIFY PARTY: FOO GMBH", "PLACE OF LOADING: NANTONG, CHINA",
                     "PLACE OF DISCHARGE: KARACHI, PAKISTAN", "NO. OF CONTAINER(S): 3 x 40'HC", "TOTAL G.W. (KGS): 22,000"]),
    "labels_D": doc(["Shipper: ACME LTD", "Consignee: FOO GMBH", "Notify: FOO GMBH", "Port of Loading: NANTONG, CHINA",
                     "Port of Destination: KARACHI, PAKISTAN", "Containers: 3 x 40'HC", "Total Gross Weight (KGS): 22,000"]),
    # ---- layouts
    "next_line": doc(["Shipper:", "  ACME LTD", "  1 MAIN RD", "Consignee:", "  FOO GMBH", "Notify:", "  FOO GMBH", "Port of Loading:",
                      "  NANTONG", "Port of Discharge:", "  KARACHI", "Containers:", "  3 x 40'HC", "Gross Weight:", "  22,000 KG"]),
    "pipes": doc(["| Shipper | ACME LTD |", "| Consignee | FOO GMBH |", "| Notify | FOO GMBH |", "| Port of Loading | NANTONG |",
                  "| Port of Discharge | KARACHI |", "| Containers | 3 x 40'HC |", "| Gross Weight | 22,000 KG |"]),
    "tabs": doc(["Shipper\tACME LTD", "Consignee\tFOO GMBH", "Notify\tFOO GMBH", "Port of Loading\tNANTONG", "Port of Discharge\tKARACHI",
                 "Containers\t3 x 40'HC", "Gross Weight\t22,000 KG"]),
    "spaced_colon": doc(["Shipper : ACME LTD", "Consignee : FOO GMBH", "Notify : FOO GMBH", "Port of Loading : NANTONG",
                         "Port of Discharge : KARACHI", "Containers : 3 x 40'HC", "Gross Weight : 22,000 KG"]),
    "dots": doc(["Shipper ........ ACME LTD", "Consignee ...... FOO GMBH", "Notify .......... FOO GMBH", "Port of Loading .. NANTONG",
                 "Port of Discharge  KARACHI", "Containers ...... 3 x 40'HC", "Gross Weight .... 22,000 KG"]),
    "lowercase": doc(["shipper: acme ltd", "consignee: foo gmbh", "notify: foo gmbh", "port of loading: nantong",
                      "port of discharge: karachi", "containers: 3 x 40'hc", "gross weight: 22,000 kg"]),
    "numbered": doc(["1. Shipper: ACME LTD", "2. Consignee: FOO GMBH", "3. Notify: FOO GMBH", "4. Port of Loading: NANTONG",
                     "5. Port of Discharge: KARACHI", "6. Containers: 3 x 40'HC", "7. Gross Weight: 22,000 KG"]),
    "net_before_gross": doc(["Shipper: ACME LTD", "Consignee: FOO GMBH", "Notify: FOO GMBH", "Port of Loading: NANTONG",
                             "Port of Discharge: KARACHI", "Containers: 3 x 40'HC", "Net Weight: 21,000 KG", "Gross Weight: 22,000 KG"]),
}
# ---- weights written in different ways
for name, v in {"w_decimals": "22,000.00 KGS", "w_nospace": "22000KGS", "w_tonnes": "22.0 MT", "w_space_thousands": "22 000 KG",
                "w_dot_thousands": "22.000 KG", "w_trailing_dot": "22,000 Kgs."}.items():
    CASES[name] = with_weight(v)
# ---- container counts written in different ways
for name, v in {"c_compact": "3X40HC", "c_highcube": "3 x 40' High Cube", "c_plain": "3", "c_word_unit": "3 CONTAINERS",
                "c_zero_pad": "03 x 20GP", "c_words": "Three (3) x 40HC", "c_mixed": "1 x 20'GP + 2 x 40'HC"}.items():
    CASES[name] = with_containers(v)

failures = []
for name, text in CASES.items():
    r = extract_fields(text)
    for f in FIELDS:
        got, want = r["keys"][f], EXPECT[f]
        ok = (got == want) if isinstance(want, int) else (got is not None and want in str(got).replace(" ", ""))
        if not ok:
            failures.append((name, f, r["fields"][f]))
for name, f, got in failures:
    print("FAIL", name, f, "->", got)
assert not failures, f"{len(failures)} wrong values"

# ---- safety: a typo-tolerant match must NEVER turn 'unloading' into 'loading'
r = extract_fields(doc(["Shipper: A", "Port of Unloading: KARACHI", "Port of Loadng: NANTONG"]))
assert r["keys"]["port_of_discharge"] == "KARACHI" and r["keys"]["port_of_loading"] == "NANTONG", r["keys"]
r = extract_fields(doc(["Shipper: A", "Port of Unloadng: KARACHI"]))          # typo'd 'unloading' must not become 'loading'
assert r["keys"]["port_of_loading"] is None

print(f"all {len(CASES)} variants + safety checks passed")