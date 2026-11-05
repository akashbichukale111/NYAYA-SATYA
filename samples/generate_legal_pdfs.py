import os
import sys

def create_pdf(filepath, title, subtitle, metadata_rows, sections, signature_left, signature_right):
    """Generate a standard, valid PDF 1.4 document with clean formatting."""
    
    # We construct a PDF with stream objects
    # Page dimensions: A4 is 595 x 842 points
    
    content_lines = []
    
    # Header
    content_lines.append("BT")
    content_lines.append("/F1 16 Tf")
    content_lines.append("50 800 Td")
    content_lines.append(f"({title}) Tj")
    content_lines.append("ET")
    
    content_lines.append("BT")
    content_lines.append("/F2 11 Tf")
    content_lines.append("50 782 Td")
    content_lines.append(f"({subtitle}) Tj")
    content_lines.append("ET")
    
    # Horizontal rule
    content_lines.append("0.5 w")
    content_lines.append("50 772 m 545 772 l S")
    
    # Metadata Table
    y = 752
    for label, val in metadata_rows:
        content_lines.append("BT")
        content_lines.append("/F1 10 Tf")
        content_lines.append(f"50 {y} Td")
        content_lines.append(f"({label}:) Tj")
        content_lines.append("ET")
        
        content_lines.append("BT")
        content_lines.append("/F2 10 Tf")
        content_lines.append(f"180 {y} Td")
        content_lines.append(f"({val}) Tj")
        content_lines.append("ET")
        y -= 18
        
    y -= 10
    content_lines.append(f"50 {y} m 545 {y} l S")
    y -= 25
    
    # Sections
    for sec_title, paragraphs in sections:
        content_lines.append("BT")
        content_lines.append("/F1 12 Tf")
        content_lines.append(f"50 {y} Td")
        content_lines.append(f"({sec_title}) Tj")
        content_lines.append("ET")
        y -= 18
        
        for para in paragraphs:
            content_lines.append("BT")
            content_lines.append("/F2 10 Tf")
            content_lines.append(f"50 {y} Td")
            # Escape parentheses in text
            clean_p = para.replace("(", "\\(").replace(")", "\\)")
            content_lines.append(f"({clean_p}) Tj")
            content_lines.append("ET")
            y -= 16
        y -= 12
        
    # Signatures
    y = max(y, 100)
    content_lines.append("BT")
    content_lines.append("/F1 10 Tf")
    content_lines.append(f"50 {y} Td")
    content_lines.append(f"({signature_left}) Tj")
    content_lines.append("ET")
    
    content_lines.append("BT")
    content_lines.append("/F1 10 Tf")
    content_lines.append(f"340 {y} Td")
    content_lines.append(f"({signature_right}) Tj")
    content_lines.append("ET")
    
    stream_content = "\n".join(content_lines).encode("latin1")
    stream_len = len(stream_content)
    
    objects = []
    # Obj 1: Catalog
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    # Obj 2: Pages
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    # Obj 3: Page
    objects.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>")
    # Obj 4: Content Stream
    objects.append(f"<< /Length {stream_len} >>\nstream\n".encode("latin1") + stream_content + b"\nendstream")
    # Obj 5: Font Bold (Helvetica-Bold)
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    # Obj 6: Font Regular (Helvetica)
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    
    pdf_bytes = bytearray(b"%PDF-1.4\n")
    xref = [0]
    
    for i, obj in enumerate(objects, 1):
        xref.append(len(pdf_bytes))
        pdf_bytes.extend(f"{i} 0 obj\n".encode("latin1"))
        pdf_bytes.extend(obj)
        pdf_bytes.extend(b"\nendobj\n")
        
    startxref = len(pdf_bytes)
    pdf_bytes.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin1"))
    pdf_bytes.extend(b"0000000000 65535 f \n")
    for offset in xref[1:]:
        pdf_bytes.extend(f"{offset:010d} 00000 n \n".encode("latin1"))
        
    pdf_bytes.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{startxref}\n%%EOF\n".encode("latin1"))
    
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(pdf_bytes)
    print(f"Generated PDF: {filepath} ({len(pdf_bytes)} bytes)")

# 1. Document 1: FIR Record
create_pdf(
    filepath=r"D:\NYAYA-SATYA\unwind-live-verified-main\samples\FIR_No_0482_2023_State_v_Rajesh_Kumar.pdf",
    title="DELHI POLICE -- FIRST INFORMATION REPORT",
    subtitle="Court Record Copy - Tis Hazari District Courts, Delhi",
    metadata_rows=[
        ("Police Station", "P.S. Kashmere Gate, Central District, Delhi"),
        ("FIR Number", "0482 / 2023"),
        ("e-Courts CNR", "DLCT01-004820-2024"),
        ("Acts & Sections", "IPC Sec. 420 [Cheating], Sec. 406 [Breach of Trust], Sec. 120-B"),
        ("Accused Person", "Rajesh Kumar S/o Late Ram Lal Kumar"),
        ("Date of Arrest", "16-March-2023 [Continuous Undertrial Detention: 428 Days]"),
        ("DLSA Advocate", "Adv. Meenakshi Sundaram [Legal Aid Helpline: 15100]")
    ],
    sections=[
        ("I. BRIEF STATEMENT OF ALLEGATIONS", [
            "Commercial forwarding contract breach concerning transit of electronics consignment.",
            "Complainant alleges dispatch was scheduled for 12-March-2023 but goods delivered late.",
            "Accused arrested on 16-March-2023 and remanded to judicial custody at Tihar Jail No. 4."
        ]),
        ("II. EVIDENTIARY EXHIBITS & DISCREPANCIES (NYAYA-SATYA AUDIT)", [
            "Exhibit E-01: Warehouse manifest logs dispatch initiation on 12-March-2023.",
            "Exhibit E-02: Freight docket proves carrier took custody on 14-March-2023 [48h gap].",
            "Exhibit E-03: Bank ledger verifies advance payment was deposited into corporate escrow.",
            "Digital Twin Finding: Missing intermediate warehousing logs between 12-14 March 2023."
        ]),
        ("III. STATUTORY DETENTION AUDIT", [
            "Maximum prescribed penalty under IPC Sec 406 is 3 years [1,095 days].",
            "Detention duration as of 18-October-2024: 428 days [exceeds 1/3rd threshold: 365 days].",
            "Statutory bail eligibility under Section 479(1) BNSS is ACTIVE and MANDATORY."
        ])
    ],
    signature_left="Station House Officer, P.S. Kashmere Gate",
    signature_right="Chief Metropolitan Magistrate, Tis Hazari"
)

# 2. Document 2: Statutory Bail Petition
create_pdf(
    filepath=r"D:\NYAYA-SATYA\unwind-live-verified-main\samples\Statutory_Bail_Petition_Sec_479_BNSS.pdf",
    title="IN THE COURT OF CHIEF METROPOLITAN MAGISTRATE",
    subtitle="Tis Hazari Courts, Delhi | Bail App No. 129/2024 | CNR: DLCT01-004820-2024",
    metadata_rows=[
        ("Applicant", "Rajesh Kumar S/o Late Ram Lal Kumar [In Tihar Jail No. 4]"),
        ("Respondent", "State [NCT of Delhi] through SHO, P.S. Kashmere Gate"),
        ("Applicable Law", "Section 479 Bharatiya Nagarik Suraksha Sanhita [BNSS], 2023"),
        ("Constitutional Basis", "Article 21, Constitution of India [Right to Speedy Justice]"),
        ("Undertrial Period", "428 Days undergone [Statutory 1/3rd limit is 365 days]"),
        ("Legal Aid Counsel", "Adv. Meenakshi Sundaram [DLSA Central Panel, Reg D/1842/2012]")
    ],
    sections=[
        ("1. FACTUAL MATRIX & FIRST-TIME OFFENDER STATUS", [
            "The Applicant is a first-time undertrial offender with zero prior criminal history.",
            "Arrested on 16-March-2023 in connection with FIR 0482/2023 for alleged IPC 406/420.",
            "Charge sheet filed; trial proceedings have suffered 9 non-merit adjournments."
        ]),
        ("2. MANDATORY STATUTORY RELIEF UNDER SECTION 479 BNSS", [
            "Section 479(1) First Proviso BNSS guarantees mandatory release on statutory bail",
            "where a first-time offender has served one-third of the maximum prison term.",
            "Maximum penalty under Sec 406 IPC is 3 years [1,095 days]. 1/3rd is 365 days.",
            "Applicant has served 428 days, exceeding the statutory requirement by 63 days."
        ]),
        ("3. PRAYER TO HON'BLE COURT", [
            "It is most respectfully prayed that this Hon'ble Court admit the Applicant to",
            "Statutory Bail on furnishing reasonable personal bond to the satisfaction of Court."
        ])
    ],
    signature_left="Adv. Meenakshi Sundaram (DLSA)",
    signature_right="Applicant (Through Superintendent, Tihar)"
)
