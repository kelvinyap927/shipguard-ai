"""Simulated Member-B extractor for the SDOC v2 dataset (txt/pdf/docx/xlsx) - FOR TESTING MEMBER C ONLY.
Purpose: exercise Member C on REAL formats. Returns raw labels + raw values (no canonicalisation)."""
import re, subprocess, io, os
import openpyxl, docx

LABELS = {
 "shipper": ["Shipper","Shipper/Exporter","Shipper (Principal or Seller)","SHIPPER","Seller","Exporter"],
 "consignee": ["Consignee","Consignee (Non-Negotiable)","CONSIGNEE","To the Order of","Buyer"],
 "notify_party": ["Notify Party","Notify","Notify Party/Intermediate Consignee","NOTIFY PARTY"],
 "port_of_loading": ["Port of Loading","Port of Loading (POL)","Load Port","POL","PORT OF LOADING"],
 "port_of_discharge": ["Port of Discharge","Port of Discharge (POD)","Discharge Port","POD","PORT OF DISCHARGE"],
 "container_count": ["No. of Containers","Total Containers","No. of Containers or Packages","Container Count"],
 "gross_weight_kg": ["Gross Weight (KG)","Gross Wt (kgs)","Gross Weight毛重(KGS)","GROSS WEIGHT","Gross Weight (KGS)"],
}
ALL = sorted({(l.casefold(), f) for f, ls in LABELS.items() for l in ls}, key=lambda x: -len(x[0]))

def label_field(raw_label):
    s = re.sub(r"\s*\([^)]*[\u4e00-\u9fff][^)]*\)", "", raw_label)   # strip (发货人) etc
    s0 = s.strip().casefold()
    for l, f in ALL:
        if s0 == l: return f
    s1 = re.sub(r"^total\s+", "", s0)
    for l, f in ALL:
        if s1 == l: return f
    return None

def doc_kind(text):
    head = " ".join(text.strip().splitlines()[:4]).casefold() if text.strip() else ""
    for k, name in [("commercial invoice","commercial_invoice"),("packing list","packing_list"),
                    ("certificate of origin","certificate_of_origin"),
                    ("bill of lading instruction","shipping_instruction"),("bl instruction","shipping_instruction"),
                    ("shipping instruction","shipping_instruction"),("bill of lading","bill_of_lading")]:
        if k in head: return name
    return None

def parse_txt(text, with_addr):
    out = {}; last = None
    for ln in text.splitlines():
        if ln.startswith("  ") and last and with_addr and ln.strip():
            out[last] = out[last] + "\n" + ln.strip(); continue
        m = re.match(r"^([^:]+?):\s?(.*)$", ln)
        if m:
            lab, val = m.group(1), m.group(2)
            if label_field(lab): out[lab] = val; last = lab; continue
        last = None
    return out

def parse_pdf_text(text, with_addr):
    out = {}; lines = text.replace("\f","\n").replace("\u25a0","").splitlines(); i = 0
    lines = [l for l in lines if l.strip() != "Party/Intermediate Consignee"]
    lines = [re.sub(r"^(TOTAL\s+Gross Weight)\(KGS\)", r"\1 (KGS)", l) for l in lines]
    alts = "|".join(re.escape(l) for l,_ in ALL)
    rx = re.compile(r"^((?:TOTAL\s+)?(?:%s))(?:\s*:\s*|\s+)(\S.*)$" % alts, re.I)
    while i < len(lines):
        m = rx.match(lines[i])
        if m and label_field(m.group(1)):
            lab, val = m.group(1), m.group(2).strip(); i += 1
            while with_addr and i < len(lines) and lines[i].startswith(" ") and lines[i].strip() and not rx.match(lines[i]):
                val += "\n" + lines[i].strip(); i += 1
            if val.startswith("Party/Intermediate Consignee"):
                val = re.sub(r"^Party/Intermediate Consignee\s*", "", val)
                if not val and i < len(lines) and lines[i].strip():
                    val = lines[i].strip(); i += 1
                    while with_addr and i < len(lines) and lines[i].startswith(" ") and lines[i].strip():
                        val += "\n" + lines[i].strip(); i += 1
                    if not with_addr:
                        while i < len(lines) and lines[i].startswith(" ") and lines[i].strip(): i += 1
            out[lab] = val
        elif label_field(lines[i].strip()) and i+1 < len(lines) and lines[i+1].startswith(" "):
            lab = lines[i].strip(); i += 1; val = ""
            while i < len(lines) and lines[i].startswith(" ") and lines[i].strip():
                if with_addr or not val: val += ("\n" if val else "") + lines[i].strip()
                i += 1
            out[lab] = val
        else: i += 1
    return out

def read(path, with_addr=True):
    """returns (fields, meta) ; meta.readable False when nothing usable."""
    ext = os.path.splitext(path)[1].lower()
    meta = {"readable": True}; text = ""
    try:
        if ext == ".txt":
            text = open(path, encoding="utf-8", errors="replace").read()
            if not text.strip(): raise ValueError("empty")
            fields = parse_txt(text, with_addr)
        elif ext == ".pdf":
            r = subprocess.run(["pdftotext","-layout",path,"-"],capture_output=True,text=True)
            text = r.stdout
            if r.returncode != 0 or not text.strip(): raise ValueError("no text layer / cannot open")
            fields = parse_pdf_text(text, with_addr)
        elif ext == ".docx":
            d = docx.Document(path); fields = {}
            text = "\n".join(p.text for p in d.paragraphs)
            for t in d.tables:
                for row in t.rows:
                    c = [x.text for x in row.cells]
                    if len(c) >= 2 and label_field(c[0]):
                        fields[c[0].strip()] = c[1] if with_addr else c[1].split("\n")[0]
        elif ext == ".xlsx":
            wb = openpyxl.load_workbook(path); ws = wb.active; fields = {}
            text = "\n".join(str(c.value) for row in ws.iter_rows() for c in row if c.value is not None)
            for row in ws.iter_rows(values_only=True):
                if row[0] is not None and label_field(str(row[0])):
                    v = row[1]
                    if not with_addr and isinstance(v, str): v = v.split(" | ")[0]
                    fields[str(row[0]).strip()] = v
        else: raise ValueError("unsupported")
    except Exception as e:
        return {}, {"readable": False, "status": "unreadable", "error": str(e)}
    meta["document_type"] = doc_kind(text)
    meta["raw_text"] = text
    return fields, meta
