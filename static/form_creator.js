(function () {
    const shell = document.querySelector(".creator-shell");
    if (!shell) {
        return;
    }

    const initialForm = (shell.dataset.initialForm || "").trim();
    const formList = document.getElementById("form-list");
    const reloadButton = document.getElementById("reload-forms");
    const newButton = document.getElementById("new-form");
    const validateButton = document.getElementById("validate-form");
    const saveButton = document.getElementById("save-form");
    const previewButton = document.getElementById("preview-form");
    const nameInput = document.getElementById("form-name-input");
    const editor = document.getElementById("fxml-editor");
    const modeTitle = document.getElementById("editor-mode-title");
    const toggleModeButton = document.getElementById("toggle-editor-mode");
    const codePane = document.getElementById("code-editor-pane");
    const visualPane = document.getElementById("visual-editor-pane");
    const visualFormTitle = document.getElementById("visual-form-title");
    const visualSubmitLabel = document.getElementById("visual-submit-label");
    const visualConfirmationText = document.getElementById("visual-confirmation-text");
    const visualSectionTitle = document.getElementById("visual-section-title");
    const addSectionButton = document.getElementById("add-section");
    const addRootPagebreakButton = document.getElementById("add-root-pagebreak");
    const visualSections = document.getElementById("visual-sections");
    const status = document.getElementById("editor-status");
    const output = document.getElementById("validation-output");

    const FIELD_TYPES = [
        "textfield",
        "textarea",
        "numberfield",
        "datefield",
        "emailfield",
        "phonefield",
        "selectfield",
        "radiogroup",
        "checkfield",
    ];

    const COLOR_MAP = {
        red: "#dc2626",
        green: "#15803d",
        lightgreen: "#65a30d",
        blue: "#1d4ed8",
        lightblue: "#0ea5e9",
        yellow: "#ca8a04",
        orange: "#ea580c",
        cyan: "#0891b2",
        magenta: "#be185d",
        black: "#111827",
        gray: "#4b5563",
        lightgray: "#9ca3af",
    };

    let currentForm = "";
    let dirty = false;
    let editorMode = "code";
    let visualModel = buildDefaultVisualModel();
    let pendingScriptUpload = null;

    function buildDefaultVisualModel() {
        return {
            title: "Nuovo Modulo",
            submitLabel: "Invia",
            confirmationText: "Grazie per aver inviato il modulo!",
            rootBlocks: [
                {
                    kind: "section",
                    title: "Sezione",
                    blocks: [
                        {
                            kind: "row",
                            items: [
                                {
                                    kind: "field",
                                    fieldType: "textfield",
                                    name: "nome",
                                    label: "Nome",
                                    required: true,
                                    placeholder: "",
                                    width: "",
                                    maxlength: "",
                                    min: "",
                                    max: "",
                                    step: "",
                                    rows: "",
                                    optionsText: "",
                                },
                            ],
                        },
                    ],
                },
            ],
        };
    }

    function setStatus(message, tone) {
        status.textContent = message || "";
        status.className = "editor-status";
        if (tone) {
            status.classList.add(tone);
        }
    }

    function setValidationOutput(value) {
        output.textContent = value;
    }

    function autoResizeEditor() {
        editor.style.height = "auto";
        editor.style.height = `${editor.scrollHeight}px`;
    }

    function normalizeName(name) {
        return String(name || "").trim();
    }

    function isValidName(name) {
        return /^[A-Za-z0-9_-]+$/.test(name);
    }

    function normalizeToken(value, fallback) {
        const token = String(value || "").trim().replace(/\s+/g, "_").toLowerCase();
        if (!token) {
            return fallback;
        }
        return token.replace(/[^a-z0-9_-]/g, "") || fallback;
    }

    function markDirty(nextDirty) {
        dirty = !!nextDirty;
        if (dirty) {
            setStatus("Hai modifiche non salvate.", "warn");
        }
    }

    function escapeXmlAttr(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;");
    }

    function escapeXmlText(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;");
    }

    function parseOptionsText(raw) {
        return String(raw || "")
            .split("\n")
            .map((line) => line.trim())
            .filter(Boolean)
            .map((line) => {
                const parts = line.split(":");
                if (parts.length < 2) {
                    return {
                        value: line,
                        text: line,
                    };
                }
                const value = parts.shift().trim();
                const text = parts.join(":").trim();
                return {
                    value: value || text,
                    text: text || value,
                };
            });
    }

    function parseFieldNode(node) {
        const fieldType = node.tagName.toLowerCase();
        const options = [];

        if (fieldType === "selectfield" || fieldType === "radiogroup") {
            Array.from(node.children).forEach((opt) => {
                if (opt.tagName.toLowerCase() !== "option") {
                    return;
                }
                options.push({
                    value: opt.getAttribute("value") || "",
                    text: (opt.textContent || "").trim(),
                });
            });
        }

        return {
            kind: "field",
            fieldType: fieldType,
            name: node.getAttribute("name") || "",
            label: node.getAttribute("label") || "",
            required: (node.getAttribute("required") || "false") === "true",
            placeholder: node.getAttribute("placeholder") || "",
            width: node.getAttribute("width") || "",
            maxlength: node.getAttribute("maxlength") || "",
            min: node.getAttribute("min") || "",
            max: node.getAttribute("max") || "",
            step: node.getAttribute("step") || "",
            rows: node.getAttribute("rows") || "",
            optionsText: options.map((opt) => `${opt.value}:${opt.text}`).join("\n"),
        };
    }

    function serializeNode(node) {
        return new XMLSerializer().serializeToString(node);
    }

    function getInnerXml(node) {
        const serializer = new XMLSerializer();
        return Array.from(node.childNodes).map((child) => serializer.serializeToString(child)).join("");
    }

    function fxmlTextToRichHtml(raw) {
        const parser = new DOMParser();
        const xml = parser.parseFromString(`<root>${raw || ""}</root>`, "application/xml");
        if (xml.querySelector("parsererror")) {
            return escapeHtml(raw || "");
        }

        function walk(node) {
            if (node.nodeType === Node.TEXT_NODE) {
                return escapeHtml(node.nodeValue || "");
            }

            if (node.nodeType !== Node.ELEMENT_NODE) {
                return "";
            }

            const tag = node.tagName.toLowerCase();
            const inner = Array.from(node.childNodes).map(walk).join("");

            if (tag === "b") {
                return `<strong>${inner}</strong>`;
            }
            if (tag === "i") {
                return `<em>${inner}</em>`;
            }
            if (tag === "u") {
                return `<u>${inner}</u>`;
            }
            if (tag === "s") {
                return `<s>${inner}</s>`;
            }
            if (tag === "h3") {
                return `<h3>${inner}</h3>`;
            }
            if (tag === "n") {
                return "<br>";
            }
            if (tag in COLOR_MAP) {
                return `<span data-color="${tag}" style="color:${COLOR_MAP[tag]}">${inner}</span>`;
            }

            return inner;
        }

        return Array.from(xml.documentElement.childNodes).map(walk).join("");
    }

    function colorFromNode(node) {
        if (node.dataset && node.dataset.color && COLOR_MAP[node.dataset.color]) {
            return node.dataset.color;
        }

        const styleColor = (node.style && node.style.color ? node.style.color : "").trim().toLowerCase();
        const normalized = styleColor.replace(/\s+/g, "");

        if (!normalized) {
            return "";
        }

        const rgbToTag = {
            "rgb(220,38,38)": "red",
            "rgb(21,128,61)": "green",
            "rgb(101,163,13)": "lightgreen",
            "rgb(29,78,216)": "blue",
            "rgb(14,165,233)": "lightblue",
            "rgb(202,138,4)": "yellow",
            "rgb(234,88,12)": "orange",
            "rgb(8,145,178)": "cyan",
            "rgb(190,24,93)": "magenta",
            "rgb(17,24,39)": "black",
            "rgb(75,85,99)": "gray",
            "rgb(156,163,175)": "lightgray",
        };

        if (rgbToTag[normalized]) {
            return rgbToTag[normalized];
        }

        const hexToTag = Object.entries(COLOR_MAP).find((entry) => entry[1].toLowerCase() === normalized);
        return hexToTag ? hexToTag[0] : "";
    }

    function richHtmlToFxml(html) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(`<root>${html || ""}</root>`, "text/html");
        const root = doc.body.firstElementChild;

        function walk(node) {
            if (node.nodeType === Node.TEXT_NODE) {
                return escapeXmlText((node.nodeValue || "").replace(/\u00a0/g, " "));
            }

            if (node.nodeType !== Node.ELEMENT_NODE) {
                return "";
            }

            const tag = node.tagName.toLowerCase();
            const inner = Array.from(node.childNodes).map(walk).join("");

            if (tag === "strong" || tag === "b") {
                return `<b>${inner}</b>`;
            }
            if (tag === "em" || tag === "i") {
                return `<i>${inner}</i>`;
            }
            if (tag === "u") {
                return `<u>${inner}</u>`;
            }
            if (tag === "s" || tag === "strike") {
                return `<s>${inner}</s>`;
            }
            if (tag === "h3") {
                return `<h3>${inner}</h3>`;
            }
            if (tag === "br") {
                return "<n/>";
            }
            if (tag === "div" || tag === "p") {
                return `${inner}<n/>`;
            }

            const colorTag = colorFromNode(node);
            if (colorTag) {
                return `<${colorTag}>${inner}</${colorTag}>`;
            }

            return inner;
        }

        const converted = Array.from(root.childNodes).map(walk).join("");
        return converted.replace(/(<n\/>)$/g, "");
    }

    function parseRowNode(node) {
        const items = [];

        Array.from(node.children).forEach((child) => {
            const tag = child.tagName.toLowerCase();

            if (tag === "text") {
                items.push({
                    kind: "text",
                    html: fxmlTextToRichHtml(getInnerXml(child)),
                });
                return;
            }

            if (FIELD_TYPES.includes(tag)) {
                items.push(parseFieldNode(child));
                return;
            }

            if (tag === "printvar") {
                items.push({
                    kind: "printvar",
                    name: child.getAttribute("name") || "",
                });
                return;
            }

            if (tag === "computed") {
                items.push({
                    kind: "computed",
                    name: child.getAttribute("name") || "",
                    label: child.getAttribute("label") || "",
                    value: child.getAttribute("value") || "",
                });
                return;
            }

            if (tag === "script") {
                items.push({
                    kind: "script",
                    file: child.getAttribute("file") || "",
                });
                return;
            }

            items.push({
                kind: "raw",
                xml: serializeNode(child),
            });
        });

        return {
            kind: "row",
            items: items,
        };
    }

    function parseSectionNode(node) {
        const section = {
            kind: "section",
            title: node.getAttribute("title") || "",
            blocks: [],
        };

        Array.from(node.children).forEach((child) => {
            const tag = child.tagName.toLowerCase();
            if (tag === "row") {
                section.blocks.push(parseRowNode(child));
                return;
            }
            if (tag === "pagebreak") {
                section.blocks.push({ kind: "pagebreak" });
                return;
            }

            section.blocks.push({
                kind: "raw",
                xml: serializeNode(child),
            });
        });

        return section;
    }

    function parseXmlToVisualModel(xmlText) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(xmlText, "application/xml");
        const parseError = doc.querySelector("parsererror");
        if (parseError) {
            return {
                error: "XML non valido",
            };
        }

        const form = doc.documentElement;
        if (!form || form.tagName.toLowerCase() !== "form") {
            return {
                error: "Elemento radice non valido: atteso <form>",
            };
        }

        const model = {
            title: form.getAttribute("title") || "Nuovo Modulo",
            submitLabel: form.getAttribute("submit_label") || "Invia",
            confirmationText: form.getAttribute("confirmation_text") || "Grazie per aver inviato il modulo!",
            rootBlocks: [],
        };

        Array.from(form.children).forEach((child) => {
            const tag = child.tagName.toLowerCase();

            if (tag === "section") {
                model.rootBlocks.push(parseSectionNode(child));
                return;
            }

            if (tag === "pagebreak") {
                model.rootBlocks.push({ kind: "pagebreak" });
                return;
            }

            model.rootBlocks.push({
                kind: "raw",
                xml: serializeNode(child),
            });
        });

        if (!model.rootBlocks.length) {
            model.rootBlocks.push(buildDefaultVisualModel().rootBlocks[0]);
        }

        return {
            model: model,
        };
    }

    function fieldXmlLines(field, level) {
        const indent = " ".repeat(level);
        const attrs = [];

        if (field.name) {
            attrs.push(`name="${escapeXmlAttr(field.name)}"`);
        }
        if (field.label) {
            attrs.push(`label="${escapeXmlAttr(field.label)}"`);
        }
        if (field.required) {
            attrs.push("required=\"true\"");
        }

        ["placeholder", "width", "maxlength", "min", "max", "step", "rows"].forEach((key) => {
            if (field[key]) {
                attrs.push(`${key}="${escapeXmlAttr(field[key])}"`);
            }
        });

        if (field.fieldType === "selectfield" || field.fieldType === "radiogroup") {
            const options = parseOptionsText(field.optionsText);
            const lines = [];
            lines.push(`${indent}<${field.fieldType} ${attrs.join(" ")}>`);
            options.forEach((opt) => {
                lines.push(
                    `${indent}  <option value="${escapeXmlAttr(opt.value)}">${escapeXmlText(opt.text)}</option>`
                );
            });
            lines.push(`${indent}</${field.fieldType}>`);
            return lines;
        }

        return [`${indent}<${field.fieldType} ${attrs.join(" ")} />`];
    }

    function pushXmlBlock(lines, block, level) {
        const indent = " ".repeat(level);

        if (block.kind === "pagebreak") {
            lines.push(`${indent}<pagebreak />`);
            return;
        }

        if (block.kind === "raw") {
            block.xml
                .split("\n")
                .map((line) => line.trimEnd())
                .forEach((line) => lines.push(`${indent}${line}`));
            return;
        }

        if (block.kind === "row") {
            lines.push(`${indent}<row>`);
            block.items.forEach((item) => {
                const itemIndent = " ".repeat(level + 4);
                if (item.kind === "text") {
                    lines.push(`${itemIndent}<text>${richHtmlToFxml(item.html)}</text>`);
                    return;
                }
                if (item.kind === "field") {
                    fieldXmlLines(item, level + 4).forEach((line) => lines.push(line));
                    return;
                }
                if (item.kind === "printvar") {
                    lines.push(`${itemIndent}<printvar name="${escapeXmlAttr(item.name)}" />`);
                    return;
                }
                if (item.kind === "computed") {
                    lines.push(
                        `${itemIndent}<computed name="${escapeXmlAttr(item.name)}" label="${escapeXmlAttr(item.label)}" value="${escapeXmlAttr(item.value)}" />`
                    );
                    return;
                }
                if (item.kind === "script") {
                    lines.push(`${itemIndent}<script file="${escapeXmlAttr(item.file || "")}" />`);
                    return;
                }
                if (item.kind === "raw") {
                    item.xml
                        .split("\n")
                        .map((line) => line.trimEnd())
                        .forEach((line) => lines.push(`${itemIndent}${line}`));
                }
            });
            lines.push(`${indent}</row>`);
            return;
        }

        if (block.kind === "section") {
            lines.push(`${indent}<section title="${escapeXmlAttr(block.title || "")}">`);
            block.blocks.forEach((child) => pushXmlBlock(lines, child, level + 4));
            lines.push(`${indent}</section>`);
        }
    }

    function buildXmlFromVisualModel(model) {
        const lines = [];
        lines.push(
            `<form title="${escapeXmlAttr(model.title || "Nuovo Modulo")}" submit_label="${escapeXmlAttr(model.submitLabel || "Invia")}" confirmation_text="${escapeXmlAttr(model.confirmationText || "Grazie per aver inviato il modulo!")}">`
        );
        model.rootBlocks.forEach((block) => pushXmlBlock(lines, block, 4));
        lines.push("</form>");
        return lines.join("\n");
    }

    function getRootBlock(rootIndex) {
        if (!Number.isInteger(rootIndex) || rootIndex < 0 || rootIndex >= visualModel.rootBlocks.length) {
            return null;
        }
        return visualModel.rootBlocks[rootIndex];
    }

    function getSectionBlock(rootIndex, blockIndex) {
        const root = getRootBlock(rootIndex);
        if (!root || root.kind !== "section") {
            return null;
        }
        if (!Number.isInteger(blockIndex) || blockIndex < 0 || blockIndex >= root.blocks.length) {
            return null;
        }
        return root.blocks[blockIndex];
    }

    function getItem(rootIndex, blockIndex, itemIndex) {
        const row = getSectionBlock(rootIndex, blockIndex);
        if (!row || row.kind !== "row") {
            return null;
        }
        if (!Number.isInteger(itemIndex) || itemIndex < 0 || itemIndex >= row.items.length) {
            return null;
        }
        return row.items[itemIndex];
    }

    function countScriptItems() {
        let count = 0;
        visualModel.rootBlocks.forEach((rootBlock) => {
            if (!rootBlock || rootBlock.kind !== "section") {
                return;
            }
            rootBlock.blocks.forEach((block) => {
                if (!block || block.kind !== "row") {
                    return;
                }
                block.items.forEach((item) => {
                    if (item && item.kind === "script") {
                        count += 1;
                    }
                });
            });
        });
        return count;
    }

    function getFirstScriptItem() {
        for (const rootBlock of visualModel.rootBlocks) {
            if (!rootBlock || rootBlock.kind !== "section") {
                continue;
            }
            for (const block of rootBlock.blocks) {
                if (!block || block.kind !== "row") {
                    continue;
                }
                for (const item of block.items) {
                    if (item && item.kind === "script") {
                        return item;
                    }
                }
            }
        }
        return null;
    }

    function renderVisualModel() {
        visualFormTitle.value = visualModel.title || "";
        visualSubmitLabel.value = visualModel.submitLabel || "";
        visualConfirmationText.value = visualModel.confirmationText || "";
        visualSections.innerHTML = "";

        if (!visualModel.rootBlocks.length) {
            const empty = document.createElement("p");
            empty.textContent = "Nessun blocco presente. Aggiungi una sezione.";
            visualSections.appendChild(empty);
            return;
        }

        visualModel.rootBlocks.forEach((rootBlock, rootIndex) => {
            if (rootBlock.kind === "section") {
                const card = document.createElement("article");
                card.className = "visual-section-card";

                const sectionHead = document.createElement("div");
                sectionHead.className = "visual-section-head";
                sectionHead.innerHTML = `
                    <strong>Sezione ${rootIndex + 1}</strong>
                    <input type="text" data-role="section-title" data-root="${rootIndex}" value="${escapeHtml(rootBlock.title || "")}" placeholder="Titolo sezione" />
                    <div class="visual-section-tools">
                        <button type="button" data-action="add-row" data-root="${rootIndex}">+ Row</button>
                        <button type="button" data-action="add-pagebreak" data-root="${rootIndex}">+ Pagebreak</button>
                        <button type="button" data-action="delete-root" data-root="${rootIndex}" class="visual-danger">Rimuovi sezione</button>
                    </div>
                `;
                card.appendChild(sectionHead);

                rootBlock.blocks.forEach((block, blockIndex) => {
                    if (block.kind === "pagebreak") {
                        const pb = document.createElement("div");
                        pb.className = "visual-pagebreak";
                        pb.innerHTML = `
                            <strong>Pagebreak</strong>
                            <div class="visual-item-tools">
                                <button type="button" data-action="delete-section-block" data-root="${rootIndex}" data-block="${blockIndex}" class="visual-danger">Rimuovi</button>
                            </div>
                        `;
                        card.appendChild(pb);
                        return;
                    }

                    if (block.kind === "raw") {
                        const raw = document.createElement("div");
                        raw.className = "visual-raw-block";
                        raw.innerHTML = `
                            <div class="visual-raw-title">Blocco non editabile in visuale</div>
                            <div>${escapeHtml(block.xml)}</div>
                        `;
                        card.appendChild(raw);
                        return;
                    }

                    const rowCard = document.createElement("div");
                    rowCard.className = "visual-row-card";
                    rowCard.innerHTML = `
                        <div class="visual-row-label">Row ${blockIndex + 1}</div>
                        <div class="visual-row-tools">
                            <button type="button" data-action="add-item-text" data-root="${rootIndex}" data-block="${blockIndex}">+ Testo</button>
                            <button type="button" data-action="add-item-field" data-root="${rootIndex}" data-block="${blockIndex}">+ Campo</button>
                            <button type="button" data-action="add-item-printvar" data-root="${rootIndex}" data-block="${blockIndex}">+ Printvar</button>
                            <button type="button" data-action="add-item-computed" data-root="${rootIndex}" data-block="${blockIndex}">+ Computed</button>
                            <button type="button" data-action="add-item-script" data-root="${rootIndex}" data-block="${blockIndex}">+ Script</button>
                            <button type="button" data-action="delete-section-block" data-root="${rootIndex}" data-block="${blockIndex}" class="visual-danger">Rimuovi row</button>
                        </div>
                    `;

                    const itemsWrap = document.createElement("div");
                    itemsWrap.className = "visual-items";

                    block.items.forEach((item, itemIndex) => {
                        const itemCard = document.createElement("div");
                        itemCard.className = "visual-item-card";

                        if (item.kind === "text") {
                            itemCard.innerHTML = `
                                <div class="visual-item-tools visual-richtext-toolbar">
                                    <button type="button" data-action="fmt" data-cmd="bold" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}"><b>B</b></button>
                                    <button type="button" data-action="fmt" data-cmd="italic" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}"><i>I</i></button>
                                    <button type="button" data-action="fmt" data-cmd="underline" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}"><u>U</u></button>
                                    <button type="button" data-action="fmt" data-cmd="strikeThrough" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}"><s>S</s></button>
                                    <button type="button" data-action="fmt-h3" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}">H3</button>
                                    <select data-role="text-color" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}">
                                        <option value="">Colore</option>
                                        ${Object.keys(COLOR_MAP).map((color) => `<option value="${color}">${color}</option>`).join("")}
                                    </select>
                                    <button type="button" data-action="remove-item" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" class="visual-danger">Rimuovi</button>
                                </div>
                                <div class="visual-richtext-editor" contenteditable="true" data-role="richtext" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}">${item.html || ""}</div>
                                <div class="visual-help">Testo formattato: supporta grassetto, corsivo, sottolineato, barrato, H3 e colori.</div>
                            `;
                            itemsWrap.appendChild(itemCard);
                            return;
                        }

                        if (item.kind === "field") {
                            itemCard.innerHTML = `
                                <div class="visual-item-grid">
                                    <label>Tipo
                                        <select data-role="field-prop" data-prop="fieldType" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}">
                                            ${FIELD_TYPES.map((type) => `<option value="${type}"${item.fieldType === type ? " selected" : ""}>${type}</option>`).join("")}
                                        </select>
                                    </label>
                                    <label>Nome
                                        <input data-role="field-prop" data-prop="name" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" value="${escapeHtml(item.name || "")}" />
                                    </label>
                                    <label>Label
                                        <input data-role="field-prop" data-prop="label" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" value="${escapeHtml(item.label || "")}" />
                                    </label>
                                    <label>Placeholder
                                        <input data-role="field-prop" data-prop="placeholder" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" value="${escapeHtml(item.placeholder || "")}" />
                                    </label>
                                    <label>Width
                                        <input data-role="field-prop" data-prop="width" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" value="${escapeHtml(item.width || "")}" />
                                    </label>
                                    <label>Required
                                        <select data-role="field-prop" data-prop="required" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}">
                                            <option value="false"${item.required ? "" : " selected"}>false</option>
                                            <option value="true"${item.required ? " selected" : ""}>true</option>
                                        </select>
                                    </label>
                                    <label>Maxlength
                                        <input data-role="field-prop" data-prop="maxlength" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" value="${escapeHtml(item.maxlength || "")}" />
                                    </label>
                                    <label>Min
                                        <input data-role="field-prop" data-prop="min" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" value="${escapeHtml(item.min || "")}" />
                                    </label>
                                    <label>Max
                                        <input data-role="field-prop" data-prop="max" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" value="${escapeHtml(item.max || "")}" />
                                    </label>
                                    <label>Step
                                        <input data-role="field-prop" data-prop="step" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" value="${escapeHtml(item.step || "")}" />
                                    </label>
                                    <label>Rows (textarea)
                                        <input data-role="field-prop" data-prop="rows" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" value="${escapeHtml(item.rows || "")}" />
                                    </label>
                                    <label style="grid-column:1/-1;">Options (select/radio, formato value:Testo per riga)
                                        <textarea data-role="field-prop" data-prop="optionsText" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" rows="3">${escapeHtml(item.optionsText || "")}</textarea>
                                    </label>
                                </div>
                                <div class="visual-item-tools">
                                    <button type="button" data-action="remove-item" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" class="visual-danger">Rimuovi campo</button>
                                </div>
                            `;
                            itemsWrap.appendChild(itemCard);
                            return;
                        }

                        if (item.kind === "printvar") {
                            itemCard.innerHTML = `
                                <div class="visual-item-grid">
                                    <label>Nome variabile
                                        <input data-role="printvar-name" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" value="${escapeHtml(item.name || "")}" />
                                    </label>
                                </div>
                                <div class="visual-item-tools">
                                    <button type="button" data-action="remove-item" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" class="visual-danger">Rimuovi printvar</button>
                                </div>
                            `;
                            itemsWrap.appendChild(itemCard);
                            return;
                        }

                        if (item.kind === "computed") {
                            itemCard.innerHTML = `
                                <div class="visual-item-grid">
                                    <label>Nome
                                        <input data-role="computed-prop" data-prop="name" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" value="${escapeHtml(item.name || "")}" />
                                    </label>
                                    <label>Label
                                        <input data-role="computed-prop" data-prop="label" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" value="${escapeHtml(item.label || "")}" />
                                    </label>
                                    <label style="grid-column:1/-1;">Value ($var)
                                        <input data-role="computed-prop" data-prop="value" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" value="${escapeHtml(item.value || "")}" />
                                    </label>
                                </div>
                                <div class="visual-item-tools">
                                    <button type="button" data-action="remove-item" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" class="visual-danger">Rimuovi computed</button>
                                </div>
                            `;
                            itemsWrap.appendChild(itemCard);
                            return;
                        }

                        if (item.kind === "script") {
                            itemCard.innerHTML = `
                                <div class="visual-item-grid">
                                    <label style="grid-column:1/-1;">File script
                                        <input type="file" accept=".py" data-role="script-file" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" />
                                    </label>
                                    <label style="grid-column:1/-1;">Nome file
                                        <input data-role="script-prop" data-prop="file" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" value="${escapeHtml(item.file || "")}" placeholder="es. valida_documento.py" />
                                    </label>
                                </div>
                                <div class="visual-item-tools">
                                    <button type="button" data-action="remove-item" data-root="${rootIndex}" data-block="${blockIndex}" data-item="${itemIndex}" class="visual-danger">Rimuovi script</button>
                                </div>
                            `;
                            itemsWrap.appendChild(itemCard);
                            return;
                        }

                        const rawItem = document.createElement("div");
                        rawItem.className = "visual-raw-block";
                        rawItem.innerHTML = `
                            <div class="visual-raw-title">Elemento non editabile</div>
                            <div>${escapeHtml(item.xml || "")}</div>
                        `;
                        itemsWrap.appendChild(rawItem);
                    });

                    rowCard.appendChild(itemsWrap);
                    card.appendChild(rowCard);
                });

                visualSections.appendChild(card);
                return;
            }

            if (rootBlock.kind === "pagebreak") {
                const rootPb = document.createElement("div");
                rootPb.className = "visual-pagebreak";
                rootPb.innerHTML = `
                    <strong>Pagebreak (radice)</strong>
                    <div class="visual-item-tools">
                        <button type="button" data-action="delete-root" data-root="${rootIndex}" class="visual-danger">Rimuovi</button>
                    </div>
                `;
                visualSections.appendChild(rootPb);
                return;
            }

            const rawRoot = document.createElement("div");
            rawRoot.className = "visual-raw-block";
            rawRoot.innerHTML = `
                <div class="visual-raw-title">Blocco radice non editabile (preservato)</div>
                <div>${escapeHtml(rootBlock.xml || "")}</div>
            `;
            visualSections.appendChild(rawRoot);
        });
    }

    function syncCodeFromVisual() {
        editor.value = buildXmlFromVisualModel(visualModel);
        autoResizeEditor();
    }

    function syncVisualFromCode() {
        const result = parseXmlToVisualModel(editor.value);
        if (result.error) {
            setStatus(`Modalità visuale non disponibile: ${result.error}`, "warn");
            return false;
        }

        visualModel = result.model;
        renderVisualModel();
        return true;
    }

    function updateAndSync() {
        renderVisualModel();
        syncCodeFromVisual();
        markDirty(true);
    }

    function setEditorMode(nextMode) {
        editorMode = nextMode;

        if (nextMode === "visual") {
            if (!syncVisualFromCode()) {
                return;
            }
            codePane.classList.add("is-hidden");
            visualPane.classList.remove("is-hidden");
            visualPane.setAttribute("aria-hidden", "false");
            modeTitle.textContent = "Editor Visuale";
            toggleModeButton.textContent = "Passa a editor Codice";
            setStatus("Modalità visuale attiva.", "ok");
            return;
        }

        syncCodeFromVisual();
        codePane.classList.remove("is-hidden");
        visualPane.classList.add("is-hidden");
        visualPane.setAttribute("aria-hidden", "true");
        modeTitle.textContent = "Editor Codice XML";
        toggleModeButton.textContent = "Passa a editor Visuale";
        setStatus("Modalità codice attiva.", "ok");
    }

    function addDefaultSection() {
        const nextIndex = visualModel.rootBlocks.filter((b) => b.kind === "section").length + 1;
        const title = (visualSectionTitle.value || "").trim() || `Sezione ${nextIndex}`;
        visualModel.rootBlocks.push({
            kind: "section",
            title: title,
            blocks: [
                {
                    kind: "row",
                    items: [],
                },
            ],
        });
        updateAndSync();
    }

    function renderFormList(forms) {
        formList.innerHTML = "";

        if (!forms.length) {
            const empty = document.createElement("li");
            empty.textContent = "Nessun modulo presente.";
            formList.appendChild(empty);
            return;
        }

        forms.forEach((name) => {
            const item = document.createElement("li");
            const button = document.createElement("button");
            button.type = "button";
            button.textContent = name;
            if (name === currentForm) {
                button.classList.add("active");
            }
            button.addEventListener("click", () => loadForm(name));
            item.appendChild(button);
            formList.appendChild(item);
        });
    }

    async function fetchJson(url, options) {
        const response = await fetch(url, options);
        const payload = await response.json().catch(() => ({}));

        if (!response.ok) {
            const message = payload.error?.message || payload.error || "Richiesta non riuscita";
            throw new Error(message);
        }

        return payload;
    }

    async function refreshFormsList() {
        try {
            const payload = await fetchJson("/api/fxml/forms");
            renderFormList(payload.forms || []);
        } catch (error) {
            setStatus("Impossibile caricare l'elenco moduli.", "err");
        }
    }

    async function loadForm(name) {
        if (!name) {
            return;
        }

        if (dirty) {
            const proceed = window.confirm("Ci sono modifiche non salvate. Continuare?");
            if (!proceed) {
                return;
            }
        }

        try {
            const payload = await fetchJson("/api/fxml/forms/" + encodeURIComponent(name));
            currentForm = name;
            pendingScriptUpload = null;
            nameInput.value = name;
            editor.value = payload.content || "";
            autoResizeEditor();
            syncVisualFromCode();
            markDirty(false);
            setStatus("Modulo caricato: " + name, "ok");
            setValidationOutput("Modulo caricato. Premi Valida per controllare il contenuto.");
            refreshFormsList();
        } catch (error) {
            setStatus("Errore caricamento: " + error.message, "err");
        }
    }

    async function validateCurrentContent() {
        if (editorMode === "visual") {
            syncCodeFromVisual();
        }

        const content = editor.value;
        if (!content.trim()) {
            setStatus("Inserisci prima un contenuto FXML.", "warn");
            setValidationOutput("Nessun contenuto da validare.");
            return false;
        }

        try {
            const payload = await fetchJson("/api/fxml/validate", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ content: content }),
            });

            if (payload.valid) {
                setStatus("FXML valido.", "ok");
                setValidationOutput("Validazione completata con successo.");
                return true;
            }

            setStatus("FXML non valido.", "err");
            setValidationOutput(JSON.stringify(payload.error || {}, null, 2));
            return false;
        } catch (error) {
            setStatus("Validazione fallita.", "err");
            setValidationOutput(String(error.message || error));
            return false;
        }
    }

    async function saveCurrentForm() {
        if (editorMode === "visual") {
            syncCodeFromVisual();
        }

        const requestedName = normalizeName(nameInput.value);

        if (!requestedName) {
            setStatus("Inserisci un nome modulo.", "warn");
            return null;
        }

        if (!isValidName(requestedName)) {
            setStatus("Nome non valido: usa solo lettere, numeri, _ e -.", "err");
            return null;
        }

        const valid = await validateCurrentContent();
        if (!valid) {
            return null;
        }

        try {
            let payload = await fetchJson("/api/fxml/forms/" + encodeURIComponent(requestedName), {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ content: editor.value }),
            });

            if (pendingScriptUpload && pendingScriptUpload.file) {
                const formData = new FormData();
                formData.append("script_file", pendingScriptUpload.file);

                const scriptPayload = await fetchJson(
                    "/api/fxml/forms/" + encodeURIComponent(requestedName) + "/script",
                    {
                        method: "POST",
                        body: formData,
                    }
                );

                const scriptItem = getFirstScriptItem();
                if (scriptItem) {
                    scriptItem.file = scriptPayload.script_path || scriptPayload.script_file || "";
                    syncCodeFromVisual();

                    payload = await fetchJson("/api/fxml/forms/" + encodeURIComponent(requestedName), {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({ content: editor.value }),
                    });
                }

                pendingScriptUpload = null;
            }

            currentForm = payload.name || requestedName;
            nameInput.value = currentForm;
            markDirty(false);
            setStatus("Modulo salvato correttamente.", "ok");
            setValidationOutput("File salvato: forms/" + currentForm + ".fxml");
            refreshFormsList();
            return payload;
        } catch (error) {
            setStatus("Errore salvataggio: " + error.message, "err");
            return null;
        }
    }

    function addItemToRow(rootIndex, blockIndex, item) {
        const row = getSectionBlock(rootIndex, blockIndex);
        if (!row || row.kind !== "row") {
            return;
        }
        row.items.push(item);
        updateAndSync();
    }

    function applyRichTextCommand(target) {
        const cmd = target.dataset.cmd;
        const rootIndex = Number(target.dataset.root);
        const blockIndex = Number(target.dataset.block);
        const itemIndex = Number(target.dataset.item);
        const editorNode = visualSections.querySelector(
            `[data-role='richtext'][data-root='${rootIndex}'][data-block='${blockIndex}'][data-item='${itemIndex}']`
        );

        if (!editorNode || !cmd) {
            return;
        }

        editorNode.focus();
        document.execCommand(cmd, false);

        const item = getItem(rootIndex, blockIndex, itemIndex);
        if (!item || item.kind !== "text") {
            return;
        }
        item.html = editorNode.innerHTML;
        syncCodeFromVisual();
        markDirty(true);
    }

    reloadButton.addEventListener("click", refreshFormsList);

    newButton.addEventListener("click", () => {
        if (dirty) {
            const proceed = window.confirm("Scartare le modifiche correnti?");
            if (!proceed) {
                return;
            }
        }

        currentForm = "";
        pendingScriptUpload = null;
        nameInput.value = "";
        visualModel = buildDefaultVisualModel();
        renderVisualModel();
        syncCodeFromVisual();
        markDirty(false);
        setStatus("Nuovo modulo pronto.", "ok");
        setValidationOutput("Template iniziale caricato.");
        refreshFormsList();
    });

    validateButton.addEventListener("click", validateCurrentContent);
    saveButton.addEventListener("click", saveCurrentForm);

    previewButton.addEventListener("click", async () => {
        const payload = await saveCurrentForm();
        if (!payload || !payload.preview_url) {
            return;
        }
        window.open(payload.preview_url, "_blank");
    });

    editor.addEventListener("input", () => {
        markDirty(true);
        autoResizeEditor();
    });
    nameInput.addEventListener("input", () => markDirty(true));

    toggleModeButton.addEventListener("click", () => {
        const next = editorMode === "code" ? "visual" : "code";
        setEditorMode(next);
    });

    visualFormTitle.addEventListener("input", () => {
        visualModel.title = visualFormTitle.value;
        syncCodeFromVisual();
        markDirty(true);
    });

    visualSubmitLabel.addEventListener("input", () => {
        visualModel.submitLabel = visualSubmitLabel.value;
        syncCodeFromVisual();
        markDirty(true);
    });

    visualConfirmationText.addEventListener("input", () => {
        visualModel.confirmationText = visualConfirmationText.value;
        syncCodeFromVisual();
        markDirty(true);
    });

    addSectionButton.addEventListener("click", addDefaultSection);

    addRootPagebreakButton.addEventListener("click", () => {
        visualModel.rootBlocks.push({ kind: "pagebreak" });
        updateAndSync();
    });

    visualSections.addEventListener("click", (event) => {
        const target = event.target.closest("button");
        if (!target) {
            return;
        }

        const action = target.dataset.action;
        const rootIndex = Number(target.dataset.root);
        const blockIndex = Number(target.dataset.block);
        const itemIndex = Number(target.dataset.item);

        if (action === "fmt" || action === "fmt-h3") {
            if (action === "fmt-h3") {
                const editorNode = visualSections.querySelector(
                    `[data-role='richtext'][data-root='${rootIndex}'][data-block='${blockIndex}'][data-item='${itemIndex}']`
                );
                if (editorNode) {
                    editorNode.focus();
                    document.execCommand("formatBlock", false, "h3");
                    const item = getItem(rootIndex, blockIndex, itemIndex);
                    if (item && item.kind === "text") {
                        item.html = editorNode.innerHTML;
                        syncCodeFromVisual();
                        markDirty(true);
                    }
                }
            } else {
                applyRichTextCommand(target);
            }
            return;
        }

        if (action === "add-row") {
            const section = getRootBlock(rootIndex);
            if (section && section.kind === "section") {
                section.blocks.push({ kind: "row", items: [] });
                updateAndSync();
            }
            return;
        }

        if (action === "add-pagebreak") {
            const section = getRootBlock(rootIndex);
            if (section && section.kind === "section") {
                section.blocks.push({ kind: "pagebreak" });
                updateAndSync();
            }
            return;
        }

        if (action === "delete-root") {
            if (Number.isInteger(rootIndex)) {
                visualModel.rootBlocks.splice(rootIndex, 1);
                if (!visualModel.rootBlocks.length) {
                    visualModel.rootBlocks.push(buildDefaultVisualModel().rootBlocks[0]);
                }
                updateAndSync();
            }
            return;
        }

        if (action === "delete-section-block") {
            const section = getRootBlock(rootIndex);
            if (section && section.kind === "section" && Number.isInteger(blockIndex)) {
                section.blocks.splice(blockIndex, 1);
                if (!section.blocks.length) {
                    section.blocks.push({ kind: "row", items: [] });
                }
                updateAndSync();
            }
            return;
        }

        if (action === "add-item-text") {
            addItemToRow(rootIndex, blockIndex, { kind: "text", html: "Testo" });
            return;
        }

        if (action === "add-item-field") {
            addItemToRow(rootIndex, blockIndex, {
                kind: "field",
                fieldType: "textfield",
                name: normalizeToken(`campo_${Date.now()}`, "campo"),
                label: "Campo",
                required: false,
                placeholder: "",
                width: "",
                maxlength: "",
                min: "",
                max: "",
                step: "",
                rows: "",
                optionsText: "",
            });
            return;
        }

        if (action === "add-item-printvar") {
            addItemToRow(rootIndex, blockIndex, { kind: "printvar", name: "variabile" });
            return;
        }

        if (action === "add-item-computed") {
            addItemToRow(rootIndex, blockIndex, {
                kind: "computed",
                name: "computed_val",
                label: "Computed",
                value: "$variabile",
            });
            return;
        }

        if (action === "add-item-script") {
            if (countScriptItems() >= 1) {
                setStatus("Puoi aggiungere al massimo uno script per modulo.", "warn");
                return;
            }
            addItemToRow(rootIndex, blockIndex, {
                kind: "script",
                file: "",
            });
            return;
        }

        if (action === "remove-item") {
            const row = getSectionBlock(rootIndex, blockIndex);
            if (row && row.kind === "row" && Number.isInteger(itemIndex)) {
                const removedItem = row.items[itemIndex];
                row.items.splice(itemIndex, 1);
                if (removedItem && removedItem.kind === "script") {
                    pendingScriptUpload = null;
                }
                updateAndSync();
            }
        }
    });

    visualSections.addEventListener("change", (event) => {
        const target = event.target;
        const role = target.dataset.role;
        const rootIndex = Number(target.dataset.root);
        const blockIndex = Number(target.dataset.block);
        const itemIndex = Number(target.dataset.item);

        if (role === "text-color") {
            const color = target.value;
            const editorNode = visualSections.querySelector(
                `[data-role='richtext'][data-root='${rootIndex}'][data-block='${blockIndex}'][data-item='${itemIndex}']`
            );
            if (!editorNode) {
                return;
            }

            editorNode.focus();
            const hex = color && COLOR_MAP[color] ? COLOR_MAP[color] : "#111827";
            document.execCommand("foreColor", false, hex);

            const item = getItem(rootIndex, blockIndex, itemIndex);
            if (item && item.kind === "text") {
                item.html = editorNode.innerHTML;
                syncCodeFromVisual();
                markDirty(true);
            }
        }
    });

    visualSections.addEventListener("input", (event) => {
        const target = event.target;
        const role = target.dataset.role;
        const rootIndex = Number(target.dataset.root);
        const blockIndex = Number(target.dataset.block);
        const itemIndex = Number(target.dataset.item);

        if (role === "section-title") {
            const section = getRootBlock(rootIndex);
            if (section && section.kind === "section") {
                section.title = target.value;
                syncCodeFromVisual();
                markDirty(true);
            }
            return;
        }

        if (role === "richtext") {
            const item = getItem(rootIndex, blockIndex, itemIndex);
            if (item && item.kind === "text") {
                item.html = target.innerHTML;
                syncCodeFromVisual();
                markDirty(true);
            }
            return;
        }

        if (role === "field-prop") {
            const item = getItem(rootIndex, blockIndex, itemIndex);
            if (!item || item.kind !== "field") {
                return;
            }

            const prop = target.dataset.prop;
            if (!prop) {
                return;
            }

            if (prop === "required") {
                item.required = target.value === "true";
            } else if (prop === "name") {
                item.name = normalizeToken(target.value, "campo");
                target.value = item.name;
            } else {
                item[prop] = target.value;
            }

            syncCodeFromVisual();
            markDirty(true);
            return;
        }

        if (role === "printvar-name") {
            const item = getItem(rootIndex, blockIndex, itemIndex);
            if (item && item.kind === "printvar") {
                item.name = normalizeToken(target.value, "variabile");
                target.value = item.name;
                syncCodeFromVisual();
                markDirty(true);
            }
            return;
        }

        if (role === "computed-prop") {
            const item = getItem(rootIndex, blockIndex, itemIndex);
            if (item && item.kind === "computed") {
                const prop = target.dataset.prop;
                if (prop === "name") {
                    item.name = normalizeToken(target.value, "computed");
                    target.value = item.name;
                } else if (prop) {
                    item[prop] = target.value;
                }
                syncCodeFromVisual();
                markDirty(true);
            }
            return;
        }

        if (role === "script-prop") {
            const item = getItem(rootIndex, blockIndex, itemIndex);
            if (item && item.kind === "script") {
                const prop = target.dataset.prop;
                if (prop === "file") {
                    item.file = target.value.trim();
                    target.value = item.file;
                }
                syncCodeFromVisual();
                markDirty(true);
            }
            return;
        }

        if (role === "script-file") {
            const item = getItem(rootIndex, blockIndex, itemIndex);
            if (item && item.kind === "script") {
                const selectedFile = target.files && target.files[0] ? target.files[0] : null;
                const file = selectedFile ? selectedFile.name : "";
                item.file = file;
                pendingScriptUpload = selectedFile ? { file: selectedFile } : null;

                const fileNameInput = visualSections.querySelector(
                    `[data-role='script-prop'][data-prop='file'][data-root='${rootIndex}'][data-block='${blockIndex}'][data-item='${itemIndex}']`
                );
                if (fileNameInput) {
                    fileNameInput.value = file;
                }

                syncCodeFromVisual();
                markDirty(true);
            }
        }
    });

    refreshFormsList().then(() => {
        renderVisualModel();
        if (initialForm) {
            loadForm(initialForm);
            return;
        }

        syncCodeFromVisual();
        autoResizeEditor();
        setStatus("Pronto per creare o importare un modulo.", "ok");
        setValidationOutput("Seleziona un modulo esistente o crea un nuovo modulo.");
    });
})();
