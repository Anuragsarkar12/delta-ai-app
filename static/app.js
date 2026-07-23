document.addEventListener("DOMContentLoaded", () => {
    const computeBtn = document.getElementById("compute-btn");
    const baseFile = document.getElementById("base-file");
    const revisedFile = document.getElementById("revised-file");
    const loader = document.getElementById("loader");
    const reportSection = document.getElementById("report-section");
    
    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");
    const chatHistory = document.getElementById("chat-history");

    let isSystemReady = false;

    // Handle File Upload and Delta Computation
    computeBtn.addEventListener("click", async () => {
        if (!baseFile.files[0] || !revisedFile.files[0]) {
            alert("Please select both a Base and Revised PDF.");
            return;
        }

        computeBtn.style.display = "none";
        loader.style.display = "block";

        const formData = new FormData();
        formData.append("base_file", baseFile.files[0]);
        formData.append("revised_file", revisedFile.files[0]);

        try {
            const response = await fetch("/api/upload", {
                method: "POST",
                body: formData
            });

            if (!response.ok) throw new Error("Processing failed.");

            const deltaReport = await response.json();
            displayDeltaReport(deltaReport);
            
            // Enable Chat
            isSystemReady = true;
            chatInput.disabled = false;
            sendBtn.disabled = false;
            
            addMessage("system-msg", "Delta computed successfully! The documents and report have been indexed. What would you like to know?");

        } catch (error) {
            alert("Error computing delta: " + error.message);
        } finally {
            computeBtn.style.display = "block";
            loader.style.display = "none";
        }
    });

    function displayDeltaReport(report) {
        reportSection.style.display = "block";
        
        let added = 0, removed = 0, modified = 0;
        const changesList = document.getElementById("changes-list");
        changesList.innerHTML = "";

        report.changes.forEach(change => {
            if (change.change_type === "added") added++;
            if (change.change_type === "removed") removed++;
            if (change.change_type === "modified") modified++;

            const div = document.createElement("div");
            div.className = `change-item ${change.change_type}`;
            div.innerHTML = `<b>Page ${change.page_number}</b>: ${change.description}`;
            changesList.appendChild(div);
        });

        document.getElementById("stat-added").innerText = added;
        document.getElementById("stat-removed").innerText = removed;
        document.getElementById("stat-modified").innerText = modified;
    }

    // Handle Chat
    const handleChat = async () => {
        const query = chatInput.value.trim();
        if (!query || !isSystemReady) return;

        addMessage("user-msg", query);
        chatInput.value = "";
        chatInput.disabled = true;
        sendBtn.disabled = true;
        
        // Show loading bubble
        const loadingId = addMessage("ai-msg", "<div class='pulse'></div>");

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query: query })
            });

            if (!response.ok) throw new Error("Chat failed.");

            const data = await response.json();
            updateMessage(loadingId, data.answer, data.citations);

        } catch (error) {
            updateMessage(loadingId, "Sorry, I encountered an error answering that.");
        } finally {
            chatInput.disabled = false;
            sendBtn.disabled = false;
            chatInput.focus();
        }
    };

    sendBtn.addEventListener("click", handleChat);
    chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") handleChat();
    });

    function addMessage(type, content) {
        const id = "msg-" + Date.now();
        const div = document.createElement("div");
        div.className = `message ${type}`;
        div.id = id;
        
        div.innerHTML = `<div class="msg-bubble">${content}</div>`;
        chatHistory.appendChild(div);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        return id;
    }

    function updateMessage(id, text, citations = []) {
        const msgDiv = document.getElementById(id);
        if (msgDiv) {
            let html = `<div class="msg-bubble">${text}`;
            if (citations.length > 0) {
                html += `<div class="citations">`;
                citations.forEach(c => {
                    html += `<span class="citation-chip">${c}</span>`;
                });
                html += `</div>`;
            }
            html += `</div>`;
            msgDiv.innerHTML = html;
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }
    }
});
