let username = "User";
let loadedMessages = 0;
let currentChatId = null;
let isSending = false;

const api_url = "http://10.0.0.198:5000";
const auth_url = "http://10.0.0.198:5000";

function prechatMessages() {
    return [
        `Hey, ${username}, what'll we create today?`,
        `What's the move, ${username}?`,
        `Any exciting projects today, ${username}?`,
        `Welcome back, ${username}. What's on your mind?`,
        `What are we working on today, ${username}?`,
        `Got any ideas brewing, ${username}?`,
        `Ready to make something awesome, ${username}?`,
        `What's up, ${username}?`,
        `What can I help you with today, ${username}?`,
        `Let's hear your ideas, ${username}.`,
        `Anything interesting you'd like to explore, ${username}?`,
        `What are we building today, ${username}?`,
        `Got a challenge for me, ${username}?`,
        `What brings you here today, ${username}?`,
        `Let's get creative, ${username}. What's the plan?`,
        `Your next idea starts here, ${username}.`,
        `Need a hand with something, ${username}?`,
        `What have you been thinking about, ${username}?`,
        `Let's make some progress today, ${username}.`,
        `What's the plan of action, ${username}?`,
        `Anything I can help you figure out, ${username}?`,
        `So, what are we diving into today, ${username}?`,
        `Got something cool in mind, ${username}?`,
        `I'm ready when you are, ${username}. What's up?`,
        `Let's see what you've got, ${username}.`
    ];
}

function start() {
    loadedMessages = 0;
    checkSavedSession();
}

function randomizeMessage() {
    const message = document.getElementById("prechatmessage");
    const options = prechatMessages();
    const randomIndex = Math.floor(Math.random() * options.length);
    message.textContent = options[randomIndex];
}

function updatePrechatMessage() {
    const message = document.getElementById("prechatmessage");

    if (loadedMessages === 0) {
        message.style.display = "flex";
    } else {
        message.style.display = "none";
    }
}

function displayAuthenticationStatus(message, isError = true) {
    const status = document.getElementById("authenticationstatus");
    status.textContent = message;
    status.style.color = isError ? "#ff4444" : "#00cc66";
}

async function registerUser() {
    const username = document.getElementById("authusername").value.trim();
    const password = document.getElementById("authpassword").value;

    try {
        const response = await fetch(`${auth_url}/register`, {
            method: "POST",
            credentials: "include",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (!response.ok) {
            displayAuthenticationStatus(data.error || data.message || "Registration failed.");
            return;
        }

        loadMain(data.username || username);
    } catch (error) {
        displayAuthenticationStatus("Unable to connect to the server.");
    }
}

async function loginUser() {
    const username = document.getElementById("authusername").value.trim();
    const password = document.getElementById("authpassword").value;

    try {
        const response = await fetch(`${auth_url}/login`, {
            method: "POST",
            credentials: "include",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (!response.ok) {
            displayAuthenticationStatus(data.error || data.message || "Login failed.");
            return;
        }

        loadMain(data.username || username);
    } catch (error) {
        displayAuthenticationStatus("Unable to connect to the server.");
    }
}

function loadMain(name) {
    username = name;

    document.getElementById("accountname").textContent = name;
    document.getElementById("authentication").style.display = "none";
    document.getElementById("main").style.display = "flex";

    startNewChat();
}

async function checkSavedSession() {
    try {
        const response = await fetch(`${auth_url}/session`, {
            method: "GET",
            credentials: "include"
        });

        if (!response.ok) {
            return;
        }

        const data = await response.json();
        loadMain(data.username);
    } catch (error) {
        console.error("Unable to restore login session:", error);
    }
}

async function logoutUser() {
    try {
        const response = await fetch(`${auth_url}/logout`, {
            method: "POST",
            credentials: "include"
        });

        if (!response.ok) {
            displayAuthenticationStatus("Unable to log out.");
            return;
        }

        username = "User";
        currentChatId = null;

        clearMessages();

        document.getElementById("chats").replaceChildren();
        document.getElementById("authusername").value = "";
        document.getElementById("authpassword").value = "";
        document.getElementById("authentication").style.display = "flex";
        document.getElementById("main").style.display = "none";
    } catch (error) {
        displayAuthenticationStatus("Unable to connect to the server.");
    }
}

async function api(path, method = "GET", body = null) {
    const response = await fetch(`${api_url}${path}`, {
        method: method,
        credentials: "include",
        headers: {
            "Content-Type": "application/json"
        },
        body: body ? JSON.stringify(body) : undefined
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || data.message || "Request failed.");
    }

    return data;
}

function makeButton(label, className, onClick) {
    const button = document.createElement("button");
    button.className = className;
    button.textContent = label;
    button.addEventListener("click", onClick);

    return button;
}

function clearMessages() {
    document.querySelectorAll(
        "#messages .usermessage, #messages .tevmessage"
    ).forEach(element => element.remove());

    loadedMessages = 0;
}

function addUserMessage(text) {
    const usermessage = document.createElement("div");
    usermessage.classList.add("usermessage");

    const name = document.createElement("h4");
    name.textContent = username;

    const message = document.createElement("p");
    message.textContent = text;

    usermessage.append(name, message);

    const container = document.querySelector("#messages");
    container.appendChild(usermessage);
    container.scrollTop = container.scrollHeight;

    loadedMessages++;
    updatePrechatMessage();
}

function parseInlineFormatting(text, element) {
    const parts = text.split(/\*\*([\s\S]*?)\*\*/g);

    parts.forEach((part, index) => {
        if (!part) {
            return;
        }

        if (index % 2 === 1) {
            const em = document.createElement("em");
            em.textContent = part;
            element.appendChild(em);
        } else {
            element.append(part);
        }
    });
}

function parseTevContent(text) {
    const container = document.createElement("div");
    container.style.display = "flex";
    container.style.flexDirection = "column";
    container.style.gap = "4px";
    container.style.width = "100%";

    const parts = text.split(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g);

    for (let i = 0; i < parts.length; i++) {
        if (i % 3 === 1) {
            const language = parts[i] || "code";
            const codeText = parts[i + 1] ? parts[i + 1].trim() : "";

            const codeWrapper = document.createElement("div");
            codeWrapper.className = "code-block-wrapper";

            const header = document.createElement("div");
            header.className = "code-header";

            const langSpan = document.createElement("span");
            langSpan.textContent = language;

            const copyBtn = document.createElement("button");
            copyBtn.textContent = "Copy code";
            copyBtn.className = "copy-code-btn";

            copyBtn.addEventListener("click", () => {
                navigator.clipboard.writeText(codeText).then(() => {
                    copyBtn.textContent = "Copied!";
                    setTimeout(() => {
                        copyBtn.textContent = "Copy code";
                    }, 2000);
                });
            });

            header.append(langSpan, copyBtn);

            const pre = document.createElement("pre");
            pre.className = "code-content";

            const code = document.createElement("code");
            code.textContent = codeText;
            pre.appendChild(code);

            codeWrapper.append(header, pre);
            container.appendChild(codeWrapper);

            i++;
        } else {
            const part = parts[i];

            if (!part) {
                continue;
            }

            const lines = part.split("\n");

            lines.forEach(line => {
                const p = document.createElement("p");
                const trimmed = line.trim();

                if (trimmed.startsWith("##")) {
                    const strong = document.createElement("strong");
                    strong.textContent = trimmed.replace(/^##\s*/, "");
                    p.appendChild(strong);
                } else {
                    parseInlineFormatting(line, p);
                }

                container.appendChild(p);
            });
        }
    }

    return container;
}

function tevResponse(text) {
    const tevmessage = document.createElement("div");
    tevmessage.classList.add("tevmessage");

    const name = document.createElement("h4");
    name.textContent = "Tev";

    const contentContainer = document.createElement("div");
    contentContainer.style.width = "100%";
    contentContainer.appendChild(parseTevContent(text));

    tevmessage.append(name, contentContainer);

    const container = document.querySelector("#messages");
    container.appendChild(tevmessage);
    container.scrollTop = container.scrollHeight;
}

function tevStreamingResponse() {
    const tevmessage = document.createElement("div");
    tevmessage.classList.add("tevmessage");

    const name = document.createElement("h4");
    name.textContent = "Tev";

    const contentContainer = document.createElement("div");
    contentContainer.style.width = "100%";

    tevmessage.append(name, contentContainer);

    const container = document.querySelector("#messages");
    container.appendChild(tevmessage);
    container.scrollTop = container.scrollHeight;

    let dotInterval = null;
    let dotCount = 1;
    let hasReceivedContent = false;

    contentContainer.textContent = ".";
    dotInterval = setInterval(() => {
        if (!hasReceivedContent) {
            dotCount = (dotCount % 3) + 1;
            contentContainer.textContent = ".".repeat(dotCount);
            container.scrollTop = container.scrollHeight;
        }
    }, 500);

    return {
        update(text) {
            if (!hasReceivedContent && text.trim() !== "") {
                hasReceivedContent = true;
                if (dotInterval) {
                    clearInterval(dotInterval);
                    dotInterval = null;
                }
            }
            contentContainer.replaceChildren(parseTevContent(text));
            container.scrollTop = container.scrollHeight;
        },
        stop() {
            if (dotInterval) {
                clearInterval(dotInterval);
                dotInterval = null;
            }
        }
    };
}

async function loadChats() {
    const list = document.getElementById("chats");
    const saved = await api("/chats");
    list.replaceChildren();

    if (saved.length === 0) {
        const empty = document.createElement("p");
        empty.textContent = "No chats yet...";
        list.appendChild(empty);
    }

    for (const chat of saved) {
        const row = document.createElement("div");
        row.className = "chat-row";

        const open = makeButton(chat.title, "chat-item", () => openChat(chat.id));
        open.classList.toggle("active", chat.id === currentChatId);

        const renameBtn = makeButton("I", "chat-action", () => {
            const input = document.createElement("input");
            input.type = "text";
            input.className = "chat-item";
            input.style.background = "#1a1a1a";
            input.style.color = "#fff";
            input.style.border = "1px solid #ffc800";
            input.style.outline = "none";
            input.style.padding = "4px 8px";
            input.style.borderRadius = "4px";
            input.value = chat.title;

            row.replaceChild(input, open);
            input.focus();
            input.select();

            let savedState = false;

            async function save() {
                if (savedState) {
                    return;
                }
                savedState = true;

                const newTitle = input.value.trim();
                if (!newTitle || newTitle === chat.title) {
                    row.replaceChild(open, input);
                    return;
                }

                try {
                    await api(`/chats/${chat.id}`, "PATCH", { title: newTitle });
                    chat.title = newTitle;
                    open.textContent = newTitle;
                    row.replaceChild(open, input);
                } catch (error) {
                    alert(`Failed to rename chat: ${error.message}`);
                    row.replaceChild(open, input);
                }
            }

            input.addEventListener("keydown", async (e) => {
                if (e.key === "Enter") {
                    e.preventDefault();
                    await save();
                } else if (e.key === "Escape") {
                    row.replaceChild(open, input);
                }
            });

            input.addEventListener("blur", async () => {
                await save();
            });
        });

        const deleteBtn = makeButton("X", "chat-action", () => deleteChat(chat));

        row.append(open, renameBtn, deleteBtn);
        list.appendChild(row);
    }
}

async function openChat(id) {
    if (isSending) {
        return;
    }

    const saved = await api(`/chats/${id}`);

    currentChatId = id;
    clearMessages();

    for (const row of saved) {
        if (row.role === "user") {
            addUserMessage(row.content);
        } else {
            tevResponse(row.content);
        }
    }

    updatePrechatMessage();
    await loadChats();
}

function startNewChat() {
    if (isSending) {
        return;
    }

    currentChatId = null;

    clearMessages();
    randomizeMessage();
    updatePrechatMessage();

    loadChats().catch(console.error);

    document.getElementById("message-input").focus();
}

async function deleteChat(chat) {
    if (isSending || !confirm(`Delete "${chat.title}"?`)) {
        return;
    }

    await api(`/chats/${chat.id}`, "DELETE");

    if (chat.id === currentChatId) {
        startNewChat();
        return;
    }

    await loadChats();
}

async function sendMessage() {
    const input = document.getElementById("message-input");
    const inputValue = input.value.trim();

    if (!inputValue || isSending) {
        return;
    }

    isSending = true;

    input.value = "";
    autoGrowInput();
    addUserMessage(inputValue);

    const streamer = tevStreamingResponse();

    try {
        if (!currentChatId) {
            const created = await api("/chats", "POST");
            currentChatId = created.id;
        }

        const response = await fetch(`${api_url}/tev_response`, {
            method: "POST",
            credentials: "include",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: inputValue,
                chat_id: currentChatId
            })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || data.message || "Request failed.");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        let fullText = "";

        while (true) {
            const { value, done } = await reader.read();

            if (done) {
                break;
            }

            fullText += decoder.decode(value, { stream: true });

            if (fullText.includes("[Error:") && (
                fullText.toLowerCase().includes("rate") ||
                fullText.toLowerCase().includes("limit") ||
                fullText.toLowerCase().includes("large") ||
                fullText.toLowerCase().includes("quota") ||
                fullText.toLowerCase().includes("token") ||
                fullText.toLowerCase().includes("exceed")
            )) {
                streamer.update("Out of storage. Please try again later!");
            } else {
                streamer.update(fullText);
            }
        }

        await loadChats();
    } catch (error) {
        console.error("Error contacting Tev:", error);
        streamer.update(`Error: ${error.message}`);
    } finally {
        isSending = false;
        streamer.stop();
        input.focus();
    }
}

function autoGrowInput() {
    const input = document.getElementById("message-input");
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 150)}px`;
}

start();

document.getElementById("new-chat").addEventListener("click", startNewChat);

const messageInput = document.getElementById("message-input");

messageInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
        return;
    }

    if (event.key === "Enter" && event.shiftKey) {
        event.preventDefault();

        const start = this.selectionStart;
        const end = this.selectionEnd;
        const value = this.value;

        this.value = value.substring(0, start) + "\n" + value.substring(end);
        this.selectionStart = this.selectionEnd = start + 1;

        autoGrowInput();
    }
});

messageInput.addEventListener("input", autoGrowInput);
