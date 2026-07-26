(function (window, document) {
    "use strict";

    function createGeoPicker(config) {
        const {
            triggerEl,
            labelEl,
            panelEl,
            breadcrumbEl,
            levelsContainerEl,
            validateBtnEl,
            clearBtnEl,
            cityHiddenEl,
            countryHiddenEl,
            mode,
            countries,
            getExternalCountry,
            getExternalCountryLabel,
            onExternalCountryChange,
            initialCountryCode,
            initialCityId,
            defaultLabel,
            autoSubmit,
            submit,
            apiUnitsUrl,
            apiChainUrl,
        } = config;

        let committed = { countryCode: "", countryName: "", chain: [] };
        let browse = { countryCode: "", countryName: "", chain: [] };

        function buildLabel(state) {
            if (state.chain.length > 0) {
                return state.chain.slice().reverse().map(function (u) { return u.name; }).join(", ");
            }
            if (state.countryCode) {
                return state.countryName || state.countryCode;
            }
            return defaultLabel;
        }

        function updateTriggerLabel() {
            labelEl.textContent = buildLabel(committed);
        }

        function writeHidden(state) {
            if (countryHiddenEl) {
                countryHiddenEl.value = state.countryCode || "";
            }

            const lastUnit = state.chain.length > 0 ? state.chain[state.chain.length - 1] : null;
            const value = lastUnit ? String(lastUnit.id) : "";

            if (cityHiddenEl.tagName === "SELECT") {
                if (value) {
                    let option = cityHiddenEl.querySelector('option[value="' + value + '"]');
                    if (!option) {
                        option = document.createElement("option");
                        option.value = value;
                        option.textContent = lastUnit.name;
                        cityHiddenEl.appendChild(option);
                    }
                }
                cityHiddenEl.value = value;
            } else {
                cityHiddenEl.value = value;
            }
        }
        function closePanel() {
            panelEl.hidden = true;
        }

        function commit(state) {
            committed = { countryCode: state.countryCode, countryName: state.countryName, chain: state.chain.slice() };
            writeHidden(committed);
            updateTriggerLabel();
            closePanel();
            if (autoSubmit && submit) {
                submit();
            }
        }

        function clearAll() {
            const empty = {
                countryCode: mode === "form" ? browse.countryCode : "",
                countryName: mode === "form" ? browse.countryName : "",
                chain: [],
            };
            commit(empty);
        }

        function renderBreadcrumb() {
            if (!breadcrumbEl) {
                return;
            }
            breadcrumbEl.innerHTML = "";

            const parts = [];
            if (browse.countryCode) {
                parts.push(browse.countryName || browse.countryCode);
            }
            browse.chain.forEach(function (unit) {
                parts.push(unit.name);
            });

            if (parts.length === 0) {
                breadcrumbEl.textContent = "Aucune s\u00e9lection";
                return;
            }

            parts.forEach(function (text, index) {
                if (index > 0) {
                    const sepEl = document.createElement("span");
                    sepEl.textContent = " \u203A ";
                    sepEl.className = "geo-breadcrumb-sep";
                    breadcrumbEl.appendChild(sepEl);
                }
                const crumb = document.createElement("span");
                crumb.className = "geo-breadcrumb-crumb" + (index === parts.length - 1 ? " current" : "");
                crumb.textContent = text;
                breadcrumbEl.appendChild(crumb);
            });
        }

        function removeLevelsFrom(levelIndex) {
            const fields = levelsContainerEl.querySelectorAll("[data-level-index]");
            fields.forEach(function (field) {
                if (parseInt(field.dataset.levelIndex, 10) >= levelIndex) {
                    field.remove();
                }
            });
        }

        function resetLevelAndBelow(levelIndex) {
            removeLevelsFrom(levelIndex);
            browse.chain = browse.chain.slice(0, levelIndex - 1);
            renderBreadcrumb();

            const field = levelsContainerEl.querySelector('[data-level-index="' + levelIndex + '"]');
            if (field) {
                const select = field.querySelector("select");
                if (select) {
                    select.value = "";
                }
                const clearIcon = field.querySelector(".geo-level-clear");
                if (clearIcon) {
                    clearIcon.hidden = true;
                }
            }
        }

        function attachClearIcon(field, levelIndex) {
            const clearIcon = document.createElement("span");
            clearIcon.className = "geo-level-clear";
            clearIcon.textContent = "\u00d7";
            clearIcon.setAttribute("role", "button");
            clearIcon.setAttribute("aria-label", "Effacer ce niveau");
            clearIcon.hidden = true;
            clearIcon.addEventListener("click", function (e) {
                e.stopPropagation();
                resetLevelAndBelow(levelIndex);
            });
            field.appendChild(clearIcon);
            return clearIcon;
        }

        function renderGeoLevel(levelIndex, parentId) {
            const url = parentId
                ? apiUnitsUrl + "?parent=" + parentId
                : apiUnitsUrl + "?country=" + browse.countryCode;

            fetch(url)
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (!data.units || data.units.length === 0) {
                        return;
                    }

                    const field = document.createElement("div");
                    field.className = "geo-level-field";
                    field.dataset.levelIndex = levelIndex;

                    const label = document.createElement("label");
                    label.textContent = data.level_name;

                    const selectRow = document.createElement("div");
                    selectRow.className = "geo-level-select-row";

                    const select = document.createElement("select");
                    const emptyOption = document.createElement("option");
                    emptyOption.value = "";
                    emptyOption.textContent = "\u2014";
                    select.appendChild(emptyOption);

                    const preselected = browse.chain[levelIndex - 1];

                    data.units.forEach(function (unit) {
                        const opt = document.createElement("option");
                        opt.value = unit.id;
                        opt.textContent = unit.name;
                        if (preselected && String(preselected.id) === String(unit.id)) {
                            opt.selected = true;
                        }
                        select.appendChild(opt);
                    });

                    field.appendChild(label);
                    selectRow.appendChild(select);
                    const clearIcon = attachClearIcon(selectRow, levelIndex);
                    field.appendChild(selectRow);
                    levelsContainerEl.appendChild(field);

                    if (preselected) {
                        clearIcon.hidden = false;
                    }

                    select.addEventListener("change", function () {
                        removeLevelsFrom(levelIndex + 1);
                        browse.chain = browse.chain.slice(0, levelIndex - 1);

                        if (select.value) {
                            const chosenName = select.options[select.selectedIndex].textContent;
                            browse.chain.push({ id: select.value, name: chosenName });
                            clearIcon.hidden = false;
                            renderBreadcrumb();
                            renderGeoLevel(levelIndex + 1, select.value);
                        } else {
                            clearIcon.hidden = true;
                            renderBreadcrumb();
                        }
                    });

                    if (preselected) {
                        renderGeoLevel(levelIndex + 1, preselected.id);
                    }
                });
        }

        function renderCountrySelect() {
            const field = document.createElement("div");
            field.className = "geo-level-field";
            field.dataset.levelIndex = 0;

            const label = document.createElement("label");
            label.textContent = "Pays";

            const selectRow = document.createElement("div");
            selectRow.className = "geo-level-select-row";

            const select = document.createElement("select");
            const emptyOption = document.createElement("option");
            emptyOption.value = "";
            emptyOption.textContent = "S\u00e9lectionner un pays";
            select.appendChild(emptyOption);

            countries.forEach(function (c) {
                const opt = document.createElement("option");
                opt.value = c.code;
                opt.textContent = c.label;
                if (browse.countryCode === c.code) {
                    opt.selected = true;
                }
                select.appendChild(opt);
            });

            field.appendChild(label);
            selectRow.appendChild(select);
            const clearIcon = attachClearIcon(selectRow, 0);
            field.appendChild(selectRow);
            levelsContainerEl.appendChild(field);

            if (browse.countryCode) {
                clearIcon.hidden = false;
            }

            select.addEventListener("change", function () {
                removeLevelsFrom(1);
                browse.chain = [];
                browse.countryCode = select.value;
                browse.countryName = select.value
                    ? select.options[select.selectedIndex].textContent
                    : "";

                clearIcon.hidden = !select.value;
                renderBreadcrumb();

                if (browse.countryCode) {
                    renderGeoLevel(1, null);
                }
            });
        }

        function openPanel() {
            browse = { countryCode: committed.countryCode, countryName: committed.countryName, chain: committed.chain.slice() };
            levelsContainerEl.innerHTML = "";
            panelEl.hidden = false;
            renderBreadcrumb();

            if (mode === "search") {
                renderCountrySelect();
                if (browse.countryCode) {
                    renderGeoLevel(1, null);
                }
            } else {
                browse.countryCode = getExternalCountry ? getExternalCountry() : "";
                browse.countryName = getExternalCountryLabel ? getExternalCountryLabel() : browse.countryCode;
                renderBreadcrumb();

                if (browse.countryCode) {
                    renderGeoLevel(1, null);
                } else {
                    const msg = document.createElement("p");
                    msg.className = "geo-list-empty";
                    msg.textContent = "Choisissez d\u2019abord un pays.";
                    levelsContainerEl.appendChild(msg);
                }
            }
        }

        triggerEl.addEventListener("click", function (e) {
            e.stopPropagation();
            if (panelEl.hidden) {
                openPanel();
            } else {
                closePanel();
            }
        });

        panelEl.addEventListener("click", function (e) {
            e.stopPropagation();
        });

        validateBtnEl.addEventListener("click", function (e) {
            e.preventDefault();
            commit(browse);
        });

        clearBtnEl.addEventListener("click", function (e) {
            e.preventDefault();
            clearAll();
        });

        function resetForNewCountry(countryCode, countryName) {
            committed = { countryCode: countryCode || "", countryName: countryName || "", chain: [] };
            writeHidden(committed);
            updateTriggerLabel();
        }

        function restoreFromInitialState() {
            if (initialCityId) {
                fetch(apiChainUrl + "?unit=" + initialCityId)
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        if (data.chain && data.chain.length > 0) {
                            committed = {
                                countryCode: data.country_code,
                                countryName: data.country_name,
                                chain: data.chain,
                            };
                            writeHidden(committed);
                            updateTriggerLabel();
                        }
                    });
                return;
            }

            if (initialCountryCode) {
                const match = countries ? countries.find(function (c) { return c.code === initialCountryCode; }) : null;
                committed = {
                    countryCode: initialCountryCode,
                    countryName: match ? match.label : (getExternalCountryLabel ? getExternalCountryLabel() : initialCountryCode),
                    chain: [],
                };
                writeHidden(committed);
                updateTriggerLabel();
            } else {
                updateTriggerLabel();
            }
        }

        restoreFromInitialState();

        if (mode === "form" && onExternalCountryChange) {
            onExternalCountryChange(function (newCountryCode, newCountryName) {
                resetForNewCountry(newCountryCode, newCountryName);
            });
        }

        return { getCommitted: function () { return committed; } };
    }

    window.GeoPicker = { create: createGeoPicker };
})(window, document);