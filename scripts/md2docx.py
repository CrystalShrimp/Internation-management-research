"""Convert paper.md (subset of markdown) to paper/paper.docx with embedded figures."""
import re
from pathlib import Path
import docx
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH


def add_runs(par, text):
    # handle **bold**, *italic*, `code`
    tokens = re.split(r"(\*\*.*?\*\*|\*.*?\*|`[^`]*`)", text)
    for tok in tokens:
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**"):
            r = par.add_run(tok[2:-2]); r.bold = True
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            r = par.add_run(tok[1:-1]); r.italic = True
        elif tok.startswith("`") and tok.endswith("`"):
            r = par.add_run(tok[1:-1]); r.font.name = "Consolas"; r.font.size = Pt(9)
        else:
            par.add_run(tok)


def convert(md_path, docx_path, base_dir):
    lines = Path(md_path).read_text(encoding="utf-8").split("\n")
    doc = docx.Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(11)
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("# "):
            h = doc.add_heading(line[2:].strip(), level=0)
        elif line.startswith("## "):
            doc.add_heading(line[3:].strip(), level=1)
        elif line.startswith("### "):
            doc.add_heading(line[4:].strip(), level=2)
        elif line.strip() == "---":
            pass
        elif line.startswith("|"):
            # collect table block
            tbl = []
            while i < len(lines) and lines[i].startswith("|"):
                tbl.append(lines[i]); i += 1
            i -= 1
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in tbl]
            rows = [r for r in rows if not all(set(c) <= set("-: ") for c in r)]
            if rows:
                t = doc.add_table(rows=len(rows), cols=len(rows[0]))
                t.style = "Light Grid Accent 1"
                for ri, r in enumerate(rows):
                    for ci, c in enumerate(r):
                        cell = t.cell(ri, ci)
                        cell.text = ""
                        p = cell.paragraphs[0]
                        add_runs(p, c.replace("**", ""))
                        if ri == 0:
                            for run in p.runs:
                                run.bold = True
                        for run in p.runs:
                            run.font.size = Pt(8.5)
        elif line.startswith("!["):
            m = re.match(r"!\[(.*?)\]\((.*?)\)", line.strip())
            if m:
                img = base_dir / m.group(2)
                if img.exists():
                    doc.add_picture(str(img), width=Inches(6.2))
                    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif line.startswith("*") and line.endswith("*") and line.count("*") == 2:
            p = doc.add_paragraph()
            r_ = p.add_run(line.strip("*")); r_.italic = True; r_.font.size = Pt(9.5)
        elif line.strip():
            p = doc.add_paragraph()
            add_runs(p, line)
        i += 1
    doc.save(docx_path)
    print("saved", docx_path)


if __name__ == "__main__":
    convert("paper/paper.md", "paper/paper.docx", Path("paper"))
