const API_BASE = "http://localhost:8000/api/v1";
// const API_BASE = "https://ai-qgen-1.onrender.com/api/v1";

document.addEventListener("DOMContentLoaded", () => {
    loadSubjects();

    const subjectForm = document.getElementById("subjectForm");
    subjectForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const status = document.getElementById("subjectStatus");
        status.textContent = "Saving...";
        status.style.color = "inherit";
        try {
            const getVal = (id) => {
                const el = document.getElementById(id);
                if (!el) {
                    console.error(`Missing element: ${id}`);
                    throw new Error(`System Error: ID '${id}' not found in page.`);
                }
                return el.value;
            };

            const payload = {
                subject_code: getVal("subCode"),
                name: getVal("subName"),
                branch_name: getVal("branchName"),
                branch_code: getVal("branchCode"),
                sem_year: getVal("semYear"),
                year: getVal("subjectYear")
            };

            const res = await fetch(`${API_BASE}/subjects/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                status.style.color = "#4ade80";
                status.textContent = "Subject Saved Successfully!";
                subjectForm.reset();
                loadSubjects();
            } else {
                throw new Error("Failed to save branch");
            }
        } catch (err) {
            status.style.color = "#f87171";
            status.textContent = "Error: " + err.message;
        }
    });

    const genForm = document.getElementById("genForm");
    const aiProvider = document.getElementById("aiProvider");
    const aiModel = document.getElementById("aiModel");

    // Fetch models on load
    fetchModels(aiProvider.value);

    aiProvider.addEventListener("change", () => {
        fetchModels(aiProvider.value);
    });

    const genTypesContainer = document.getElementById("genTypesContainer");
    const addGenReqBtn = document.getElementById("addGenReqBtn");

    function addGenRequirement() {
        const div = document.createElement("div");
        div.className = "gen-type-item";
        div.style.display = "flex";
        div.style.gap = "10px";
        div.innerHTML = `
            <select class="gt-select" style="flex: 2;">
                <option value="Mixed">Mixed (All Types)</option>
                <option value="MCQ">MCQ (Multiple Choice)</option>
                <option value="FIB">Fill in the Blanks</option>
                <option value="T/F">True / False</option>
                <option value="SA">Short Answer</option>
                <option value="LA">Long Answer</option>
                <option value="CASE">Case-Based</option>
            </select>
            <input type="number" class="gt-num" value="10" min="1" max="100" style="flex: 1;" required>
            <button type="button" class="btn outline-btn" style="padding: 0 10px; border-color: #ef4444; color: #ef4444;" onclick="this.parentElement.remove()">X</button>
        `;
        genTypesContainer.appendChild(div);
    }

    addGenReqBtn.addEventListener("click", addGenRequirement);
    addGenRequirement(); // Auto add first

    genForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const subjectId = document.getElementById("subjectId").value;
        const pdfFile = document.getElementById("syllabusPdf").files[0];
        const difficulty = document.getElementById("difficulty").value;
        const provider = aiProvider.value;
        const modelName = aiModel.value;

        const status = document.getElementById("genStatus");
        const btn = genForm.querySelector(".primary-btn");
        const loader = btn.querySelector(".loader");
        const btnText = btn.querySelector(".btn-text");

        if (!subjectId) {
            alert("Subject required!");
            return;
        }

        // Gather gen requirements
        const typeConfigs = [];
        const genItems = genTypesContainer.querySelectorAll(".gen-type-item");
        genItems.forEach(item => {
            const qt = item.querySelector(".gt-select").value;
            const nq = item.querySelector(".gt-num").value;
            typeConfigs.push({ q_type: qt, num_q: parseInt(nq) });
        });

        if (typeConfigs.length === 0) {
            alert("Please add at least one question requirement type.");
            return;
        }

        const formData = new FormData();
        formData.append("file", pdfFile);
        formData.append("provider", provider);
        formData.append("model_name", modelName);
        formData.append("q_types_config", JSON.stringify(typeConfigs));
        formData.append("difficulty", difficulty);

        btnText.textContent = `Processing with ${modelName}...`;
        loader.classList.remove("hidden");
        status.textContent = "";

        try {
            const res = await fetch(`${API_BASE}/generate/from-pdf/?subject_id=${subjectId}`, {
                method: "POST",
                body: formData
            });
            const data = await res.json();
            if (res.ok) {
                status.style.color = "#4ade80";
                status.textContent = "Success: " + data.message;
            } else {
                throw new Error(data.detail || "Server Error");
            }
        } catch (err) {
            status.style.color = "#f87171";
            status.textContent = "Error: " + err.message;
        } finally {
            btnText.textContent = "Generate Questions (AI)";
            loader.classList.add("hidden");
        }
    });

    const paperForm = document.getElementById("paperForm");
    const dynamicSections = document.getElementById("dynamicSections");
    const addSectionBtn = document.getElementById("addSectionBtn");

    let sectionCount = 0;

    // Auto-add first section
    addDynamicSection();

    addSectionBtn.addEventListener("click", addDynamicSection);

    function addDynamicSection() {
        sectionCount++;
        const sectionId = 'sec_' + Date.now() + '_' + sectionCount;
        const div = document.createElement("div");
        div.className = "dynamic-section-item input-group glass-panel";
        div.style.marginTop = "15px";
        div.style.padding = "15px";
        div.innerHTML = `
            <button type="button" class="remove-section" onclick="this.parentElement.remove()" style="top: 10px; right: 10px;">Remove Section</button>
            <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                <div style="flex: 2;">
                    <label>Section Title</label>
                    <input type="text" class="sec-title" value="Section ${String.fromCharCode(64 + sectionCount)}" required style="width: 100%;">
                </div>
            </div>
            <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                <div style="flex: 1;">
                    <label>Attempt Any (X) / Total</label>
                    <input type="number" class="sec-attempt" value="10" min="1" max="100" required>
                </div>
                <div style="flex: 1;">
                    <label>Marks per Q</label>
                    <input type="number" class="sec-marks" value="1" min="0.5" step="0.5" required>
                </div>
            </div>
            <label style="display:flex; justify-content:space-between; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom:5px;">Inner Question Requirements 
                <button type="button" class="btn outline-btn add-pool-btn" data-target="${sectionId}" style="padding: 2px 8px; font-size: 0.8rem;">+ Add Specific Type Request</button>
            </label>
            <div id="${sectionId}" class="pools-container" style="display: flex; flex-direction: column; gap: 8px; margin-top: 10px;">
            </div>
        `;
        dynamicSections.appendChild(div);

        const btn = div.querySelector('.add-pool-btn');
        btn.addEventListener('click', (e) => {
            const containerId = e.target.getAttribute('data-target');
            addPoolToSection(document.getElementById(containerId));
        });

        addPoolToSection(document.getElementById(sectionId)); // Auto add first pool
    }

    function addPoolToSection(container) {
        const poolDiv = document.createElement("div");
        poolDiv.className = "pool-item";
        poolDiv.style.display = "flex";
        poolDiv.style.gap = "10px";
        poolDiv.innerHTML = `
            <select class="pool-type" style="flex: 2;">
                <option value="Mixed">Mixed</option>
                <option value="MCQ">MCQ</option>
                <option value="FIB">Fill in the Blanks</option>
                <option value="T/F">True / False</option>
                <option value="SA">Short Answer</option>
                <option value="LA">Long Answer</option>
                <option value="CASE">Case-Based</option>
            </select>
            <input type="number" class="pool-num" value="5" min="1" max="100" style="flex: 1;" required>
            <button type="button" class="btn outline-btn" style="padding: 0 10px; border-color: #ef4444; color: #ef4444;" onclick="this.parentElement.remove()">X</button>
        `;
        container.appendChild(poolDiv);
    }

    paperForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const subjectId = document.getElementById("paperSubjectId").value;
        const status = document.getElementById("paperStatus");

        // Gather sections configuration
        const sectionsConfig = [];
        const sectionItems = dynamicSections.querySelectorAll(".dynamic-section-item");

        sectionItems.forEach(item => {
            const secName = item.querySelector(".sec-title").value;
            const attempt = item.querySelector(".sec-attempt").value;
            const marks = item.querySelector(".sec-marks").value;

            const typesConfig = [];
            let totalQ = 0;
            const pools = item.querySelectorAll(".pool-item");
            pools.forEach(p => {
                const qt = p.querySelector(".pool-type").value;
                const num = parseInt(p.querySelector(".pool-num").value);
                typesConfig.push({ q_type: qt, num_q: num });
                totalQ += num;
            });

            sectionsConfig.push({
                name: secName,
                total_q: totalQ,
                attempt_any: parseInt(attempt),
                marks_per_q: parseFloat(marks),
                types_config: typesConfig
            });
        });

        if (sectionsConfig.length === 0) {
            alert("Please add at least one section");
            return;
        }

        status.textContent = "Compiling Paper...";
        status.style.color = "inherit";
        try {
            const res = await fetch(`${API_BASE}/papers/generate/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    subject_id: parseInt(subjectId),
                    exam_title: document.getElementById("paperExamTitle").value,
                    exam_type: document.getElementById("paperExamType").value,
                    total_marks: 100,
                    sections_config: sectionsConfig
                })
            });
            const data = await res.json();
            if (res.ok) {
                status.textContent = "Paper successfully created!";
                status.style.color = "#4ade80";

                // Show links
                const downloadLinks = document.getElementById("downloadLinks");
                downloadLinks.classList.remove("hidden");

                const baseURL = API_BASE.replace("/api/v1", "");
                document.getElementById("docxLink").href = `${baseURL}/${data.paper_file}`;
                document.getElementById("ansLink").href = `${baseURL}/${data.ans_key_file}`;

            } else {
                throw new Error(data.detail);
            }
        } catch (err) {
            status.style.color = "#f87171";
            status.textContent = "Error: " + err.message;
        }
    });

    // Settings Modal Logic
    const settingsBtn = document.getElementById("openSettings");
    const settingsModal = document.getElementById("settingsModal");
    const closeSettings = document.getElementById("closeSettings");

    settingsBtn.addEventListener("click", (e) => {
        e.preventDefault();
        settingsModal.classList.remove("hidden");
    });

    closeSettings.addEventListener("click", () => {
        settingsModal.classList.add("hidden");
    });

    window.addEventListener("click", (e) => {
        if (e.target == settingsModal) {
            settingsModal.classList.add("hidden");
        }
    });

    const settingsForm = document.getElementById("settingsForm");
    settingsForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const dbUrl = document.getElementById("dbUrl").value;
        const stat = document.getElementById("settingsStatus");
        stat.textContent = "Saving...";

        try {
            const res = await fetch(`${API_BASE}/settings/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(dbUrl)
            });
            const data = await res.json();
            if (res.ok) {
                stat.style.color = "#4ade80";
                stat.textContent = "Saved successfully!";
            } else {
                throw new Error(data.detail);
            }
        } catch (err) {
            stat.style.color = "#f87171";
            stat.textContent = "Error: " + err.message;
        }
    });

    // Navigation logic
    const navDashboard = document.getElementById("navDashboard");
    const navAnalytics = document.getElementById("navAnalytics");
    const navHistory = document.getElementById("navHistory");
    
    const dashboardView = document.getElementById("dashboardView");
    const analyticsView = document.getElementById("analyticsView");
    const historyView = document.getElementById("historyView");

    function hideAllViews() {
        dashboardView.classList.add("hidden");
        analyticsView.classList.add("hidden");
        historyView.classList.add("hidden");
    }

    navDashboard.addEventListener("click", (e) => {
        e.preventDefault();
        hideAllViews();
        dashboardView.classList.remove("hidden");
    });

    navAnalytics.addEventListener("click", (e) => {
        e.preventDefault();
        hideAllViews();
        analyticsView.classList.remove("hidden");
    });

    navHistory.addEventListener("click", (e) => {
        e.preventDefault();
        hideAllViews();
        historyView.classList.remove("hidden");
    });

    // Analytics Filtering logic
    const analyticsSubjectFilter = document.getElementById("analyticsSubjectFilter");
    analyticsSubjectFilter.addEventListener("change", () => {
        const subCode = analyticsSubjectFilter.value;
        if (subCode) {
            loadAnalytics(subCode);
        } else {
            document.getElementById("analyticsContent").classList.add("hidden");
            document.getElementById("analyticsEmpty").classList.remove("hidden");
        }
    });
    
    const paperSubjectId = document.getElementById("paperSubjectId");
    paperSubjectId.addEventListener("change", async () => {
        const subId = paperSubjectId.value;
        const preview = document.getElementById("paperAnalyticsPreview");
        if (!subId) {
            preview.classList.add("hidden");
            return;
        }

        // We need the subject_code for the analytics API
        // Quick find from the select option text (or we could have stored it in a map)
        const selectedOption = paperSubjectId.options[paperSubjectId.selectedIndex].text;
        const subCode = selectedOption.split(" - ")[0];
        
        try {
            const res = await fetch(`${API_BASE}/analytics/subject/${subCode}`);
            if (!res.ok) throw new Error();
            const data = await res.json();
            renderMiniAnalytics(data);
            preview.classList.remove("hidden");
        } catch (e) {
            preview.classList.add("hidden");
        }
    });

    function renderMiniAnalytics(data) {
        const container = document.getElementById("paperTypeStats");
        const health = document.getElementById("paperSubjectHealth");
        container.innerHTML = "";
        
        let totalLimit = 0;
        let totalHeld = 0;

        const typeLabels = {
            "MCQ": "Multiple Choice (MCQs)",
            "FIB": "Fill in the Blanks",
            "T/F": "True / False",
            "SA": "Short Answer",
            "LA": "Long Answer",
            "CASE": "Case-Based Questions"
        };

        Object.entries(data.breakdown).forEach(([type, stats]) => {
            totalLimit += stats.total;
            totalHeld += stats.used;
            
            if (stats.total > 0) {
                const perc = (stats.used / stats.total) * 100;
                const remaining = stats.total - stats.used;
                
                // Determine Status
                let statusText = "High Supply";
                let statusClass = "status-high";
                if (perc > 80) {
                    statusText = "Critical";
                    statusClass = "status-critical";
                } else if (perc > 50) {
                    statusText = "Moderate";
                    statusClass = "status-moderate";
                }

                const div = document.createElement("div");
                div.className = "analytics-item-card"; // Reusing the same card style
                div.style.padding = "12px"; // Slightly tighter for the preview
                div.innerHTML = `
                    <div class="analytics-item-header" style="font-size: 0.8rem; margin-bottom: 8px;">
                        <span>${typeLabels[type] || type}</span>
                        <span class="status-indicator ${statusClass}" style="font-size: 0.55rem; padding: 2px 6px;">${statusText}</span>
                    </div>
                    <div style="margin-bottom: 8px; font-weight: 600; color: var(--primary); font-size: 0.85rem;">
                        ${stats.used} / ${stats.total} <span style="font-size: 0.7rem; color: var(--text-muted); font-weight: 400;">(${remaining} remaining)</span>
                    </div>
                    <div class="progress-container" style="height: 6px; margin-bottom: 6px;">
                        <div class="progress-bar" style="width: ${perc}%; background: ${perc > 80 ? 'var(--error)' : 'linear-gradient(90deg, var(--primary), var(--secondary))'};"></div>
                    </div>
                    <div class="percentage-label" style="font-size: 0.7rem;">${perc.toFixed(0)}% consumed</div>
                `;
                container.appendChild(div);
            }
        });

        const overall = totalLimit > 0 ? (totalHeld / totalLimit) * 100 : 0;
        
        document.getElementById("paperTotalPool").textContent = totalLimit;
        document.getElementById("paperTotalUsed").textContent = totalHeld;
        document.getElementById("paperOverallConsumption").textContent = overall.toFixed(1) + "%";

        if (overall > 80) {
            health.textContent = "Low Inventory";
            health.className = "status-indicator status-critical";
        } else if (overall > 50) {
            health.textContent = "Fair Supply";
            health.className = "status-indicator status-moderate";
        } else {
            health.textContent = "Healthy Pool";
            health.className = "status-indicator status-high";
        }
    }
});

async function loadAnalytics(subjectCode) {
    const content = document.getElementById("analyticsContent");
    const empty = document.getElementById("analyticsEmpty");
    const typeBreakdown = document.getElementById("typeBreakdown");
    
    try {
        const res = await fetch(`${API_BASE}/analytics/subject/${subjectCode}`);
        if (!res.ok) throw new Error("Failed to load analytics");
        const data = await res.json();
        
        // Summary stats
        let grandTotal = 0;
        let grandUsed = 0;
        
        const typeLabels = {
            "MCQ": "Multiple Choice (MCQs)",
            "FIB": "Fill in the Blanks",
            "T/F": "True / False",
            "SA": "Short Answer",
            "LA": "Long Answer",
            "CASE": "Case-Based Questions"
        };
        
        typeBreakdown.innerHTML = "";
        Object.entries(data.breakdown).forEach(([type, stats]) => {
            grandTotal += stats.total;
            grandUsed += stats.used;
            
            const remaining = stats.total - stats.used;
            const perc = stats.total > 0 ? ((stats.used / stats.total) * 100).toFixed(0) : 0;
            
            // Determine Status
            let statusText = "High Supply";
            let statusClass = "status-high";
            if (perc > 80) {
                statusText = "Critical";
                statusClass = "status-critical";
            } else if (perc > 50) {
                statusText = "Moderate";
                statusClass = "status-moderate";
            }
            
            const card = document.createElement("div");
            card.className = "analytics-item-card";
            card.innerHTML = `
                <div class="analytics-item-header">
                    <span>${typeLabels[type] || type}</span>
                    <span class="status-indicator ${statusClass}">${statusText}</span>
                </div>
                <div style="margin-bottom: 10px; font-weight: 600; color: var(--primary);">
                    ${stats.used} / ${stats.total} <span style="font-size: 0.8rem; color: var(--text-muted); font-weight: 400;">(${remaining} remaining)</span>
                </div>
                <div class="progress-container">
                    <div class="progress-bar" style="width: ${perc}%; background: ${perc > 80 ? 'var(--error)' : 'linear-gradient(90deg, var(--primary), var(--secondary))'};"></div>
                </div>
                <div class="percentage-label">${perc}% consumed</div>
            `;
            typeBreakdown.appendChild(card);
        });
        
        document.getElementById("totalQuestionsCount").textContent = grandTotal;
        document.getElementById("totalUsedCount").textContent = grandUsed;
        const overallRate = grandTotal > 0 ? ((grandUsed / grandTotal) * 100).toFixed(1) : 0;
        document.getElementById("overallConsumption").textContent = overallRate + "%";
        
        content.classList.remove("hidden");
        empty.classList.add("hidden");
    } catch (err) {
        console.error(err);
        alert("Error loading analytics: " + err.message);
    }
}

async function loadSubjects() {
    try {
        const res = await fetch(`${API_BASE}/subjects/`);
        if (!res.ok) {
            return;
        }
        const subjects = await res.json();

        const sel1 = document.getElementById("subjectId");
        const sel2 = document.getElementById("paperSubjectId");
        const sel3 = document.getElementById("analyticsSubjectFilter");

        sel1.innerHTML = '<option value="">Select a subject</option>';
        sel2.innerHTML = '<option value="">Select a subject</option>';
        sel3.innerHTML = '<option value="">Select a subject</option>';

        subjects.forEach(sub => {
            const opt = `<option value="${sub.id}">${sub.subject_code} - ${sub.name}</option>`;
            sel1.innerHTML += opt;
            sel2.innerHTML += opt;
            
            const optAn = `<option value="${sub.subject_code}">${sub.subject_code} - ${sub.name}</option>`;
            sel3.innerHTML += optAn;
        });
    } catch (err) {
        console.error("Could not load subjects, ensure backend is running.");
    }
}

async function seedMockSubject() {
    try {
        await fetch(`${API_BASE}/subjects/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                subject_code: "CS101",
                name: "Computer Science",
                branch_name: "B.Tech",
                branch_code: "CSE",
                sem_year: "1st Year",
                year: "2026"
            })
        });
        // reload safely
        const res = await fetch(`${API_BASE}/subjects/`);
        const subjects = await res.json();
        const sel1 = document.getElementById("subjectId");
        const sel2 = document.getElementById("paperSubjectId");
        const sel3 = document.getElementById("analyticsSubjectFilter");
        sel1.innerHTML = '<option value="">Select a subject</option>';
        sel2.innerHTML = '<option value="">Select a subject</option>';
        sel3.innerHTML = '<option value="">Select a subject</option>';
        subjects.forEach(sub => {
            const opt = `<option value="${sub.id}">${sub.subject_code} - ${sub.name}</option>`;
            sel1.innerHTML += opt;
            sel2.innerHTML += opt;
            const optAn = `<option value="${sub.subject_code}">${sub.subject_code} - ${sub.name}</option>`;
            sel3.innerHTML += optAn;
        });
    } catch (e) { }
}

async function fetchModels(provider) {
    const aiModel = document.getElementById("aiModel");
    aiModel.innerHTML = '<option value="">Loading models...</option>';
    try {
        const res = await fetch(`${API_BASE}/llm/models/?provider=${provider}`);
        const models = await res.json();
        aiModel.innerHTML = "";
        models.forEach(m => {
            const opt = document.createElement("option");
            opt.value = m.id;
            opt.textContent = m.name;
            aiModel.appendChild(opt);
        });

        // Auto-select first model if available
        if (models.length > 0 && !aiModel.value) {
            aiModel.value = models[0].id;
        }
    } catch (err) {
        aiModel.innerHTML = '<option value="">Error loading models</option>';
        console.error("Failed to fetch models:", err);
    }
}
