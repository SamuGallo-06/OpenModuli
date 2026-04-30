# OpenModuli - Open Source, Self-Hosted Form Builder and Management System.
# Copyright (C) 2025 Samuele Gallicani
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


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

ORGANIZATION_NAME = "OpenModuli"
CURRENT_PDFS_DIR = os.path.join(os.path.dirname(__file__), "pdfs")
CURRENT_ENTITY_NAME = "OpenModuli"
CURRENT_ENTITY_CONTACTS = ""
CURRENT_ENTITY_ADDRESS = ""
CURRENT_ENTITY_PHONE = ""
CURRENT_LOGO_PATH = ""
CURRENT_BACKGROUND_IMAGE = ""
CURRENT_PRIMARY_COLOR = "#1a3a4a"
CURRENT_SECONDARY_COLOR = "#555555"


def _ensure_pdfs_dir():
    """Ensure the pdfs directory exists."""
    os.makedirs(CURRENT_PDFS_DIR, exist_ok=True)
    return CURRENT_PDFS_DIR


def set_program_name(program_name: str):
    global ORGANIZATION_NAME
    ORGANIZATION_NAME = (program_name or "").strip() or "OpenModuli"


def set_pdf_path(pdf_path: str):
    global CURRENT_PDFS_DIR
    relative_path = (pdf_path or "pdfs").strip() or "pdfs"
    CURRENT_PDFS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), relative_path))


def set_branding(
    entity_name: str = "",
    logo_path: str = "",
    primary_color: str = "",
    secondary_color: str = "",
    background_image: str = "",
    contacts: str = "",
    address: str = "",
    phone: str = "",
):
    global CURRENT_ENTITY_NAME, CURRENT_ENTITY_CONTACTS, CURRENT_ENTITY_ADDRESS, CURRENT_ENTITY_PHONE
    global CURRENT_LOGO_PATH, CURRENT_BACKGROUND_IMAGE, CURRENT_PRIMARY_COLOR, CURRENT_SECONDARY_COLOR

    CURRENT_ENTITY_NAME = (entity_name or "OpenModuli").strip() or "OpenModuli"
    CURRENT_LOGO_PATH = (logo_path or "").strip()
    CURRENT_BACKGROUND_IMAGE = (background_image or "").strip()
    CURRENT_ENTITY_CONTACTS = (contacts or "").strip()
    CURRENT_ENTITY_ADDRESS = (address or "").strip()
    CURRENT_ENTITY_PHONE = (phone or "").strip()
    CURRENT_PRIMARY_COLOR = (primary_color or "#1a3a4a").strip() or "#1a3a4a"
    CURRENT_SECONDARY_COLOR = (secondary_color or "#555555").strip() or "#555555"


def _resolve_color(value: str, fallback: str) -> str:
    if not value:
        return fallback
    value = value.strip()
    if value.startswith("#"):
        return value
    return COLOR_MAP.get(value.lower(), fallback)


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
        os.makedirs(os.path.join(pdfs_dir, form_name), exist_ok=True)
        # Create filename with timestamp and compiler identity from submitted form values.
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        compiler_identity = _extract_compiler_identity(submitted_values or {})
        pdf_filename = f"{form_name}_{compiler_identity}_{timestamp}.pdf"
        pdf_path = os.path.join(pdfs_dir, form_name, pdf_filename)
        
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
            textColor=HexColor(_resolve_color(CURRENT_PRIMARY_COLOR, '#1a3a4a')),
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
            textColor=HexColor(_resolve_color(CURRENT_SECONDARY_COLOR, '#555555')),
            fontName='Helvetica-Bold',
        )

        section_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=HexColor(_resolve_color(CURRENT_PRIMARY_COLOR, '#1a3a4a')),
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
            "pdf_url": f"/pdfs/{form_name}/{pdf_filename}",
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
    footer_parts = [f"Modulo generato con OpenModuli, Emesso da {ORGANIZATION_NAME}"]
    if CURRENT_ENTITY_NAME and CURRENT_ENTITY_NAME != ORGANIZATION_NAME:
        footer_parts.append(CURRENT_ENTITY_NAME)
    if CURRENT_ENTITY_ADDRESS:
        footer_parts.append(CURRENT_ENTITY_ADDRESS)
    if CURRENT_ENTITY_CONTACTS:
        footer_parts.append(CURRENT_ENTITY_CONTACTS)
    if CURRENT_ENTITY_PHONE:
        footer_parts.append(CURRENT_ENTITY_PHONE)
    footer_text = " - ".join(footer_parts)
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
