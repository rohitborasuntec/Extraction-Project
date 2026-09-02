"""
NJ Medical Debarment Data Extractor
====================================

WHY THIS SCRIPT IS DIFFERENT FROM THE OLD ONE
-----------------------------------------------
The old script drove a real browser (Selenium) to the HTML *search results*
page and then tried to figure out, line by line, which bit of text was a
name, which was a street, which was a city, using a pile of regexes
(is_address_line, is_firm_name, is_individual_name, ...). That approach is
fundamentally fragile because the HTML table just dumps everything as
loosely-joined <br>-separated text with no field boundaries -- the script
has to *guess* the boundaries, and guesses are wrong surprisingly often:

  - Street names that start with an ordinal number ("3RD STREET",
    "22ND AVENUE") don't match the "digit + letter" address regex, so they
    get misclassified as names instead of addresses.
  - When an address is split across "street" and "city, state zip" as two
    separate <br> lines, the old code only ever grabs addresses[0] and
    reuses that ONE address for every name found in the cell -- so if a
    cell lists a firm AND an individual, or two unrelated debarred
    entities, they all wrongly end up with the same street/city.
  - Prison/facility names ("ALLENWOOD USP", "TERRE HAUTE USP") don't look
    like an address OR a firm OR an individual name, so they leak out as
    their own bogus "entity" rows.
  - Because of the above, ~77% of rows in the last run ended up with a
    missing State and ~82% missing a ZIP code.

None of that is a bug you can regex your way out of -- it's a wrong choice
of source. New Jersey's own Treasury site publishes this exact data as a
"%"-delimited flat file with a DOCUMENTED, FIXED set of 22 columns (see
https://www.nj.gov/treasury/revenue/debarment/debarsearch-medical.shtml,
under "Download"). Every field -- firm name, individual name, firm
street/city/state/zip, individual street/city/state/zip, NPI, category,
action, reason code, etc. -- is already separated for us. There is nothing
to guess. This script downloads that file directly and just splits on "%".

Source data file (confirmed live 2026-09-02):
  https://www.nj.gov/treasury/treasfiles/debarment/Debarment-MEDICAL2.txt

A tab-delimited twin also exists (Debarment-MEDICAL.txt) if "%" ever shows
up inside a real field and causes trouble -- see FALLBACK_URL below.
"""

import csv
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional

import requests

PRIMARY_URL = "https://www.nj.gov/treasury/treasfiles/debarment/Debarment-MEDICAL2.txt"
FALLBACK_URL = "https://www.nj.gov/treasury/treasfiles/debarment/Debarment-MEDICAL.txt"  # tab-delimited
SOURCE_PAGE = "https://www.nj.gov/treasury/revenue/debarment/debarsearch-medical.shtml"

# Documented column order (Column # 1-22 on the source page), in order.
FIELDS = [
    "firm_name",           # 1
    "individual_name",     # 2
    "vendor_id",            # 3
    "firm_street",          # 4
    "firm_city",             # 5
    "firm_state",            # 6
    "firm_zip",              # 7
    "firm_plus4",            # 8
    "npi_number",            # 9
    "individual_street",     # 10
    "individual_city",       # 11
    "individual_state",      # 12
    "individual_zip",        # 13
    "individual_plus4",      # 14
    "category",               # 15
    "action",                 # 16
    "reason_code",            # 17
    "debarring_dept_code",    # 18
    "debarring_agency_code",  # 19
    "effective_date",         # 20
    "expiration_date",        # 21
    "permanent_debarment",    # 22
]

REASON_CODES = {
    "A": "Criminal Offense",
    "B": "Organized Crime Contract",
    "C": "Antitrust / Anti-Kickback",
    "D": "Election Law Offense",
    "E": "Discrimination Law",
    "F": "Wage & Hour Violation",
    "G": "Industry Law Violation",
    "H": "Failure To Perform",
    "I": "Poor Performance",
    "J": "Contingent Fees",
    "K": "Other",
}

DEBARRING_DEPT_CODES = {
    "20": "EDA",
    "46": "DHSS",
    "54": "DHS",
    "62": "LABOR",
    "66": "LPS",
    "78": "DOT",
    "82": "TREASURY",
}

DEBARRING_AGENCY_CODES = {
    "0018": "Schools Development Authority",
    "0997": "Schools Development Authority",
    "1000": "Criminal Justice",
    "1050": "Consumer Affairs Board of Medical Examiners",
    "1321": "Consumer Affairs Board of Architects",
    "2050": "Treasury Purchase Bureau",
    "2065": "Treasury Property Management and Construction",
    "2800": "School Construction Corporation",
    "4210": "Health & Senior Services",
    "4550": "Workplace Standards",
    "6000": "NJ Turnpike Authority",
    "6120": "Contract Administration",
    "7540": "Medical Assistance (Medicaid)",
    "8020": "Housing and Mortgage Finance Agency",
}


def fetch_raw_text(url: str) -> str:
    """Download the delimited file. Tries utf-8 first, falls back to
    cp1252/latin-1 since older state government text dumps sometimes use
    Windows-1252 (e.g. curly apostrophes)."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; NJDebarmentFetcher/1.0)"}
    resp = requests.get(url, headers=headers, timeout=60)
    resp.raise_for_status()
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return resp.content.decode(enc)
        except UnicodeDecodeError:
            continue
    # last resort: replace undecodable bytes rather than crash
    return resp.content.decode("utf-8", errors="replace")


def parse_line(line: str) -> Optional[Dict[str, str]]:
    """Split one '%'-delimited line into the documented fields. Returns
    None for blank lines. Any extra trailing empty fields the file has
    beyond the documented 22 are ignored; if a line somehow has FEWER
    fields than expected it is padded with '' rather than raising, and a
    warning is printed so short/malformed lines are still visible."""
    line = line.rstrip("\r\n")
    if not line.strip():
        return None

    parts = line.split("%")
    # NOTE: parts[0] already lines up with FIELDS[0] (firm_name) with no
    # adjustment needed. When there's no firm name, the line simply starts
    # with '%', which makes split() produce '' as parts[0] -- that empty
    # string correctly *is* the empty firm_name field, not an artifact to
    # discard. (An earlier version of this function stripped it, which
    # silently shifted every field over by one -- verified and fixed via
    # a direct test against real sample rows before shipping this.)

    if len(parts) < len(FIELDS):
        parts = parts + [""] * (len(FIELDS) - len(parts))
        print(f"[Warn] Line had fewer fields than expected ({len(parts)} < {len(FIELDS)}): {line[:80]!r}")

    row = {name: parts[i].strip() for i, name in enumerate(FIELDS)}
    return row


def clean_zip(z: str) -> str:
    z = z.strip()
    return z


def decode_row(raw: Dict[str, str], source_url: str) -> List[Dict[str, str]]:
    """Turn one parsed line into 1 or 2 output rows: one for the firm (if a
    firm name is present) and one for the individual (if an individual
    name is present). Some lines list both -- e.g. a firm action that also
    names the individual owner/pharmacist -- and unlike the old script,
    each gets ITS OWN correct address instead of both sharing one guess."""

    reason = REASON_CODES.get(raw["reason_code"], raw["reason_code"])
    dept = DEBARRING_DEPT_CODES.get(raw["debarring_dept_code"], raw["debarring_dept_code"])
    agency = DEBARRING_AGENCY_CODES.get(raw["debarring_agency_code"], raw["debarring_agency_code"])
    action_by = f"{dept} - {agency}".strip(" -") if (dept or agency) else ""

    common = {
        "Category": raw["category"],
        "Action": raw["action"],
        "Reason Code": raw["reason_code"],
        "Reason": reason,
        "NPI Number": raw["npi_number"],
        "Action By": action_by,
        "Effective Date": raw["effective_date"],
        "Expiration Date": raw["expiration_date"],
        "Permanent Debarment": raw["permanent_debarment"],
        "Country": "USA",
        "Source Link": source_url,
    }

    out_rows = []

    firm_name = raw["firm_name"]
    individual_name = raw["individual_name"]

    if firm_name:
        out_rows.append({
            "Name of Entity": firm_name,
            "Alias Name": individual_name,  # associated individual, if any
            "Street": raw["firm_street"],
            "City": raw["firm_city"],
            "State": raw["firm_state"],
            "Pincode": clean_zip(raw["firm_zip"]),
            "Plus4": raw["firm_plus4"],
            "Entity Type": "Organization/Firm",
            **common,
        })

    if individual_name:
        out_rows.append({
            "Name of Entity": individual_name,
            "Alias Name": firm_name,  # associated firm, if any
            "Street": raw["individual_street"],
            "City": raw["individual_city"],
            "State": raw["individual_state"],
            "Pincode": clean_zip(raw["individual_zip"]),
            "Plus4": raw["individual_plus4"],
            "Entity Type": "Individual",
            **common,
        })

    if not out_rows:
        print(f"[Warn] Line had neither firm nor individual name, skipping: {raw}")

    return out_rows


OUTPUT_COLUMNS = [
    "Name of Entity", "Alias Name", "Category", "Action", "Street", "City",
    "State", "Pincode", "Plus4", "Country", "Reason Code", "Reason",
    "NPI Number", "Action By", "Effective Date", "Expiration Date",
    "Permanent Debarment", "Source Link", "Entity Type",
]


def main():
    print("=" * 80)
    print("NJ MEDICAL DEBARMENT DATA EXTRACTOR (structured-file version)")
    print("=" * 80)

    url = PRIMARY_URL
    try:
        print(f"[Fetch] Downloading {url}")
        raw_text = fetch_raw_text(url)
    except requests.RequestException as e:
        print(f"[Error] Primary URL failed ({e}); trying tab-delimited fallback...")
        url = FALLBACK_URL
        raw_text = fetch_raw_text(url).replace("\t", "%")  # normalize to '%' splitting
        print("[Note] Fallback file is tab-delimited; if any field legitimately "
              "contains a literal '%' this normalization could misparse it. "
              "Prefer fixing network/access to the primary file if this path is hit often.")

    lines = raw_text.splitlines()
    print(f"[Fetch] Downloaded {len(lines)} lines")

    all_rows: List[Dict[str, str]] = []
    parsed_lines = 0
    skipped_lines = 0

    for line in lines:
        raw = parse_line(line)
        if raw is None:
            continue
        parsed_lines += 1
        rows = decode_row(raw, url)
        if not rows:
            skipped_lines += 1
            continue
        all_rows.extend(rows)

    print(f"[Process] Parsed {parsed_lines} source lines -> {len(all_rows)} output rows "
          f"({skipped_lines} lines skipped for having no name at all)")

    if not all_rows:
        print("[Final] No data collected!")
        return

    out_filename = f"nj_medical_debarment_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(out_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    print(f"[Final] Saved {len(all_rows)} rows to {out_filename}")

    # ---- quick sanity/quality report -------------------------------------------------
    missing_state = sum(1 for r in all_rows if not r["State"])
    missing_zip = sum(1 for r in all_rows if not r["Pincode"])
    missing_city = sum(1 for r in all_rows if not r["City"])
    firms = sum(1 for r in all_rows if r["Entity Type"] == "Organization/Firm")
    individuals = sum(1 for r in all_rows if r["Entity Type"] == "Individual")

    print("\n[Quality] Missing State: {}/{} ({:.1f}%)".format(
        missing_state, len(all_rows), 100 * missing_state / len(all_rows)))
    print("[Quality] Missing ZIP:   {}/{} ({:.1f}%)".format(
        missing_zip, len(all_rows), 100 * missing_zip / len(all_rows)))
    print("[Quality] Missing City:  {}/{} ({:.1f}%)".format(
        missing_city, len(all_rows), 100 * missing_city / len(all_rows)))
    print(f"[Quality] Entity types: Organization/Firm={firms}, Individual={individuals}")

    print("\n[Final] Sample of extracted data (first 10 rows):")
    for r in all_rows[:10]:
        print(f"  {r['Name of Entity'][:40]:<40} | {r['Street'][:25]:<25} | "
              f"{r['City'][:18]:<18} | {r['State']:<3} | {r['Pincode']:<5} | {r['Entity Type']}")


if __name__ == "__main__":
    main()
