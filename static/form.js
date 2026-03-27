(function () {
    const form = document.querySelector(".fxml-form");
    if (!form) {
        return;
    }

    const conditionals = JSON.parse(form.dataset.conditionals || "[]");
    const variableDefs = JSON.parse(form.dataset.variableDefs || "[]");
    const runtimeUrl = form.dataset.runtimeUrl || "";
    const varsPanel = document.getElementById("python-vars-dict");

    const fieldValues = {};

    function toDateStruct(isoDate) {
        if (!isoDate) {
            return null;
        }

        const parts = String(isoDate).split("-").map(Number);
        if (parts.length !== 3 || parts.some(Number.isNaN)) {
            return null;
        }

        return {
            year: parts[0],
            month: parts[1],
            day: parts[2],
            iso: String(isoDate),
        };
    }

    function tupleCmp(left, right, op) {
        const l0 = left?.[0];
        const l1 = left?.[1];
        const r0 = right?.[0];
        const r1 = right?.[1];

        if ([l0, l1, r0, r1].some((v) => v === undefined || v === null)) {
            return false;
        }

        if (l0 < r0) {
            return op === "<" || op === "<=" || op === "!=";
        }
        if (l0 > r0) {
            return op === ">" || op === ">=" || op === "!=";
        }
        if (l1 < r1) {
            return op === "<" || op === "<=" || op === "!=";
        }
        if (l1 > r1) {
            return op === ">" || op === ">=" || op === "!=";
        }

        return op === "==" || op === "<=" || op === ">=";
    }

    function transformExprToJs(expr) {
        if (!expr) {
            return "false";
        }

        let transformed = String(expr);

        transformed = transformed.replace(/\bnot\b/g, "!");
        transformed = transformed.replace(/\band\b/g, "&&");
        transformed = transformed.replace(/\bor\b/g, "||");
        transformed = transformed.replace(/\bTrue\b/g, "true");
        transformed = transformed.replace(/\bFalse\b/g, "false");

        transformed = transformed.replace(
            /\(\s*([^(),]+)\s*,\s*([^()]+)\s*\)\s*(<=|>=|<|>|==|!=)\s*\(\s*([^(),]+)\s*,\s*([^()]+)\s*\)/g,
            "__tupleCmp([$1, $2], [$4, $5], '$3')"
        );

        transformed = transformed.replace(/\$([A-Za-z_][A-Za-z0-9_]*)/g, "__get('$1')");

        return transformed;
    }

    function evaluateWithContext(expr, context) {
        const jsExpr = transformExprToJs(expr);

        try {
            const fn = new Function(
                "ctx",
                "__tupleCmp",
                "with (ctx) { return (" + jsExpr + "); }"
            );
            return fn(context, tupleCmp);
        } catch (error) {
            return false;
        }
    }

    function normalizeFieldValue(element) {
        const type = element.dataset.fieldType || "";

        if (type === "checkfield") {
            return !!element.checked;
        }

        if (type === "numberfield") {
            if (element.value === "") {
                return null;
            }
            const parsed = Number(element.value);
            return Number.isNaN(parsed) ? null : parsed;
        }

        if (type === "datefield") {
            return toDateStruct(element.value);
        }

        if (type === "radiogroup") {
            if (!element.checked) {
                return undefined;
            }
            return element.value;
        }

        return element.value;
    }

    function refreshFieldValues() {
        const controls = form.querySelectorAll("[name]");
        controls.forEach((el) => {
            const name = el.name;
            if (!name || el.disabled) {
                return;
            }

            const value = normalizeFieldValue(el);
            if (value === undefined) {
                if (!(name in fieldValues)) {
                    fieldValues[name] = null;
                }
                return;
            }

            fieldValues[name] = value;
        });
    }

    function buildVariableDict() {
        const today = new Date();
        const variables = {};

        const context = {
            today: {
                year: today.getFullYear(),
                month: today.getMonth() + 1,
                day: today.getDate(),
            },
            now: today,
            ...fieldValues,
        };

        variableDefs.forEach((definition) => {
            const value = evaluateWithContext(definition.expr, {
                ...context,
                ...variables,
            });
            variables[definition.name] = value;
        });

        return variables;
    }

    function evaluateCondition(expr) {
        const variables = buildVariableDict();
        const context = {
            ...fieldValues,
            ...variables,
            __get(name) {
                if (name in variables) {
                    return variables[name];
                }
                if (name in fieldValues) {
                    return fieldValues[name];
                }
                return null;
            },
        };

        const result = evaluateWithContext(expr, context);
        return !!result;
    }

    function updateBlockFieldsState(block, isVisible) {
        const controls = block.querySelectorAll("input, select, textarea");
        controls.forEach((el) => {
            if (el.dataset.requiredOriginal === undefined) {
                el.dataset.requiredOriginal = el.required ? "true" : "false";
            }

            if (isVisible) {
                el.disabled = false;
                if (el.dataset.requiredOriginal === "true") {
                    el.required = true;
                }
            } else {
                el.disabled = true;
                el.required = false;
            }
        });
    }

    function evaluateAllConditionals() {
        refreshFieldValues();

        const blocks = form.querySelectorAll(".conditional-block[data-if]");
        blocks.forEach((block, index) => {
            const expr = conditionals[index]?.if || block.dataset.if || "";
            const visible = evaluateCondition(expr);
            block.style.display = visible ? "" : "none";
            updateBlockFieldsState(block, visible);
        });
    }

    function collectPayloadValues() {
        const values = {};
        const controls = form.querySelectorAll("input, select, textarea");

        controls.forEach((el) => {
            if (!el.name || el.disabled || el.dataset.fieldType === "computed") {
                return;
            }

            if (el.type === "radio") {
                if (el.checked) {
                    values[el.name] = el.value;
                }
                return;
            }

            if (el.type === "checkbox") {
                if (el.checked) {
                    values[el.name] = "on";
                }
                return;
            }

            values[el.name] = el.value;
        });

        return values;
    }

    async function syncRuntimeWithBackend() {
        if (!runtimeUrl) {
            return;
        }

        try {
            const response = await fetch(runtimeUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ values: collectPayloadValues() }),
            });

            if (!response.ok) {
                return;
            }

            const payload = await response.json();

            if (varsPanel) {
                varsPanel.textContent = JSON.stringify(payload.variables || {}, null, 2);
            }

            const printvars = payload.printvars || {};
            form.querySelectorAll("[data-printvar]").forEach((el) => {
                const key = el.dataset.printvar;
                el.textContent = key && key in printvars ? String(printvars[key] ?? "") : "";
            });

            const computed = payload.computed || {};
            form.querySelectorAll("input[data-field-type='computed'][name]").forEach((el) => {
                if (el.name in computed) {
                    el.value = String(computed[el.name] ?? "");
                }
            });
        } catch (error) {
            // Keep the UI responsive even if runtime sync fails.
        }
    }

    let runtimeSyncTimer = null;
    function scheduleRuntimeSync() {
        if (runtimeSyncTimer) {
            clearTimeout(runtimeSyncTimer);
        }
        runtimeSyncTimer = setTimeout(syncRuntimeWithBackend, 120);
    }

    function attachListeners() {
        const controls = form.querySelectorAll("input, select, textarea");
        controls.forEach((el) => {
            el.addEventListener("input", () => {
                evaluateAllConditionals();
                scheduleRuntimeSync();
            });
            el.addEventListener("change", () => {
                evaluateAllConditionals();
                scheduleRuntimeSync();
            });
        });
    }

    attachListeners();
    evaluateAllConditionals();
    syncRuntimeWithBackend();
})();
