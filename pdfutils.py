"""Utilities for PDF generation from submitted form nodes."""

import os
import re
from datetime import datetime
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor, grey
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

COLOR_MAP = {
    "red": "#d72638",
    "green": "#2b9348",
    "lightgreen": "#55a630",
    "blue": "#1d4ed8",
    "lightblue": "#0ea5e9",
    "yellow": "#ca8a04",
    "orange": "#ea580c",
    "cyan": "#0891b2",
    "magenta": "#be185d",
    "black": "#111827",
    "white": "#f8fafc",
    "gray": "#4b5563",
    "lightgray": "#9ca3af",
}

CURRENT_PROGRAM_NAME = "OpenModuli"


def _ensure_pdfs_dir():
    """Ensure the pdfs directory exists."""
    pdfs_dir = os.path.join(os.path.dirname(__file__), "pdfs")
    os.makedirs(pdfs_dir, exist_ok=True)
    return pdfs_dir


def set_program_name(program_name: str):
    global CURRENT_PROGRAM_NAME
    CURRENT_PROGRAM_NAME = (program_name or "").strip() or "OpenModuli"


def create_pdf_from_form_data(
    form_name: str,
    form_attributes: dict,
    nodes: list[dict[str, Any]],
    submitted_values: dict[str, Any] | None = None,
):
    """
    Generate a PDF from parsed form nodes and save it to disk.
    
    Args:
        form_name: Name of the form (e.g., 'iscrizione_corso')
        form_attributes: Form metadata (title, id, version, lang, submit_label)
        nodes: Parsed and resolved nodes from parse_fxml
        
    Returns:
        dict with keys:
            - success (bool): Whether PDF was created successfully
            - pdf_path (str): Path to saved PDF file if successful
            - error (str): Error message if failed
            - pdf_url (str): Download URL path
    """
    try:
        pdfs_dir = _ensure_pdfs_dir()
        
        # Create filename with timestamp and compiler identity from submitted form values.
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        compiler_identity = _extract_compiler_identity(submitted_values or {})
        pdf_filename = f"{form_name}_{compiler_identity}_{timestamp}.pdf"
        pdf_path = os.path.join(pdfs_dir, pdf_filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )
        
        # Build content
        story: list[Any] = []
        styles = getSampleStyleSheet()
        
        # Add custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=HexColor('#1a3a4a'),
            spaceAfter=6,
            alignment=1,  # Center
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=4,
            leading=13,
        )
        
        label_style = ParagraphStyle(
            'Label',
            parent=styles['Normal'],
            fontSize=10,
            textColor=HexColor('#555555'),
            fontName='Helvetica-Bold',
        )

        section_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=HexColor('#1a3a4a'),
            spaceBefore=8,
            spaceAfter=8,
        )

        text_style = ParagraphStyle(
            'InlineText',
            parent=styles['Normal'],
            fontSize=10,
            leading=13,
            spaceAfter=5,
        )

        value_style = ParagraphStyle(
            'FieldValue',
            parent=styles['Normal'],
            fontSize=10,
            leading=13,
            textColor=HexColor('#111827'),
        )
        
        # Title
        form_title = form_attributes.get('title', form_name)
        story.append(Paragraph(form_title, title_style))
        story.append(Spacer(1, 0.15 * inch))
        
        # Submission info
        submission_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        info_text = f"Inviato il: <b>{submission_time}</b>"
        if form_attributes.get('id'):
            info_text += f" | ID: <b>{form_attributes.get('id')}</b>"
        story.append(Paragraph(info_text, normal_style))
        story.append(Spacer(1, 0.2 * inch))
        
        _render_nodes(
            story,
            nodes or [],
            section_style=section_style,
            label_style=label_style,
            text_style=text_style,
            value_style=value_style,
        )
        
        # Build PDF
        doc.build(story, onFirstPage=_add_footer, onLaterPages=_add_footer)
        
        return {
            "success": True,
            "pdf_path": pdf_path,
            "pdf_filename": pdf_filename,
            "pdf_url": f"/pdfs/{pdf_filename}",
            "error": None,
        }
        
    except Exception as e:
        return {
            "success": False,
            "pdf_path": None,
            "pdf_filename": None,
            "error": str(e),
        }


def _add_footer(canvas_obj, doc):
    """Add footer to each page."""
    canvas_obj.saveState()
    
    # Footer text
    footer_text = f"Modulo generato con {CURRENT_PROGRAM_NAME} - Iscrizione Online"
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(grey)
    
    # Page number
    canvas_obj.drawString(
        0.5 * inch,
        0.4 * inch,
        footer_text
    )
    
    canvas_obj.drawRightString(
        doc.pagesize[0] - 0.5 * inch,
        0.4 * inch,
        f"Pag. {doc.page}"
    )
    
    canvas_obj.restoreState()


def _extract_compiler_identity(submitted_values: dict[str, Any]) -> str:
    # Bound to the dedicated top-of-form compiler fields.
    first_name = _clean_input(submitted_values.get("nome_compilante"))
    last_name = _clean_input(submitted_values.get("cognome_compilante"))

    if first_name and last_name:
        return f"{_slugify_filename_part(first_name)}_{_slugify_filename_part(last_name)}"
    if first_name:
        return _slugify_filename_part(first_name)
    if last_name:
        return _slugify_filename_part(last_name)
    return "anonimo"


def _clean_input(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _slugify_filename_part(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = re.sub(r"[^a-z0-9_-]", "", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-_")
    return normalized or "anonimo"


def _render_nodes(story, nodes, section_style, label_style, text_style, value_style):
    for node in nodes:
        node_type = node.get("type")

        if node_type == "section":
            title = node.get("title")
            if title:
                story.append(Paragraph(escape(str(title)), section_style))
            _render_nodes(
                story,
                node.get("children", []),
                section_style=section_style,
                label_style=label_style,
                text_style=text_style,
                value_style=value_style,
            )
            story.append(Spacer(1, 0.06 * inch))
            continue

        if node_type == "row":
            row_children = node.get("children", [])
            if not row_children:
                continue

            child_flowables = [
                _render_single_node(child, label_style, text_style, value_style)
                for child in row_children
            ]
            child_flowables = [flow for flow in child_flowables if flow is not None]
            if not child_flowables:
                continue

            col_widths = _compute_row_widths(row_children)
            row_table = Table([child_flowables], colWidths=col_widths)
            row_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            story.append(row_table)
            story.append(Spacer(1, 0.05 * inch))
            continue

        if node_type == "conditional":
            _render_nodes(
                story,
                node.get("children", []),
                section_style=section_style,
                label_style=label_style,
                text_style=text_style,
                value_style=value_style,
            )
            continue

        if node_type == "pagebreak":
            story.append(Spacer(1, 0.12 * inch))
            story.append(Paragraph("<font color='#6b7280'><i>--- Pagebreak ---</i></font>", text_style))
            story.append(Spacer(1, 0.12 * inch))
            continue

        single = _render_single_node(node, label_style, text_style, value_style)
        if single is not None:
            story.append(single)
            story.append(Spacer(1, 0.04 * inch))


def _render_single_node(node, label_style, text_style, value_style):
    node_type = node.get("type")

    if node_type == "text":
        markup = _text_segments_to_markup(node.get("segments", []))
        return Paragraph(markup, text_style)

    if node_type in {
        "textfield", "textarea", "numberfield", "datefield", "emailfield", "phonefield",
        "selectfield", "radiogroup", "checkfield", "computed", "printvar"
    }:
        label = escape(str(node.get("label") or node.get("name") or "Campo"))
        value = escape(_field_display_value(node))

        label_par = Paragraph(label, label_style)
        value_par = Paragraph(value.replace("\n", "<br/>"), value_style)

        value_box = Table([[value_par]], colWidths=[None])
        value_box.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.7, HexColor('#9ca3af')),
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#f8fafc')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))

        block = Table([[label_par], [value_box]], colWidths=[None])
        block.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        return block

    return None


def _compute_row_widths(children):
    usable_width = 7.0 * inch
    parsed = []

    for child in children:
        raw_width = str(child.get("width", "")).strip()
        if raw_width.endswith("%"):
            try:
                pct = float(raw_width[:-1])
            except ValueError:
                pct = 0
            parsed.append(max(0.0, pct))
        else:
            parsed.append(0.0)

    if sum(parsed) <= 0:
        return [usable_width / max(1, len(children))] * len(children)

    total_pct = sum(parsed)
    if total_pct <= 0:
        total_pct = 100.0
    return [(pct / total_pct) * usable_width for pct in parsed]


def _field_display_value(node):
    node_type = node.get("type")

    if node_type == "checkfield":
        checked = bool(node.get("current_value"))
        return "[X] Selezionato" if checked else "[ ] Non selezionato"

    if node_type == "computed":
        value = node.get("resolved_value")
        return "" if value is None else str(value)

    if node_type == "printvar":
        value = node.get("value")
        return "" if value is None else str(value)

    value = node.get("current_value")
    if value is None or value == "":
        return ""
    return str(value)


def _text_segments_to_markup(segments):
    if not segments:
        return ""

    chunks = []
    for segment in segments:
        text = escape(str(segment.get("text", ""))).replace("\n", "<br/>")
        classes = segment.get("classes", [])
        chunks.append(_apply_segment_classes(text, classes))
    return "".join(chunks)


def _apply_segment_classes(text, classes):
    rendered = text

    if "fmt-h3" in classes:
        rendered = f"<font size='14'><b>{rendered}</b></font>"
    if "fmt-b" in classes:
        rendered = f"<b>{rendered}</b>"
    if "fmt-i" in classes:
        rendered = f"<i>{rendered}</i>"
    if "fmt-u" in classes:
        rendered = f"<u>{rendered}</u>"
    if "fmt-s" in classes:
        rendered = f"<strike>{rendered}</strike>"

    color_class = next((c for c in classes if c.startswith("clr-")), None)
    if color_class:
        color_name = color_class.replace("clr-", "", 1)
        color = COLOR_MAP.get(color_name)
        if color:
            rendered = f"<font color='{color}'>{rendered}</font>"

    return rendered
