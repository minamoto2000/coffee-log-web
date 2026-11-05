// Small helpers shared by the experiment pages.

function formatErrorDetail(detail) {
    if (Array.isArray(detail)) {
        return detail
            .map((item) => {
                const loc = (item.loc || []).filter((part) => part !== "body").join(".");
                return loc ? `${loc}: ${item.msg}` : item.msg;
            })
            .join("\n");
    }
    return typeof detail === "string" ? detail : JSON.stringify(detail);
}

// Sends JSON and returns the parsed body, or shows the error and returns null.
async function sendJson(method, url, payload, errorElementId = "error-message") {
    const errorElement = document.getElementById(errorElementId);
    if (errorElement) errorElement.textContent = "";
    const response = await fetch(url, {
        method,
        headers: payload === undefined ? {} : {"Content-Type": "application/json"},
        body: payload === undefined ? undefined : JSON.stringify(payload),
    });
    if (response.ok) {
        return response.status === 204 ? {} : await response.json();
    }
    let message = `${response.status} ${response.statusText}`;
    try {
        const body = await response.json();
        message = `${response.status}: ${formatErrorDetail(body.detail)}`;
    } catch (error) {
        // keep the status line
    }
    if (errorElement) errorElement.textContent = message;
    return null;
}

// "" -> null, otherwise a number. Precision is validated by the API.
function numberOrNull(value) {
    if (value === undefined || value === null || String(value).trim() === "") return null;
    return Number(value);
}

function textOrNull(value) {
    const text = (value || "").trim();
    return text === "" ? null : text;
}

// <input type="datetime-local"> value -> ISO string with an offset.
function localInputToIso(value) {
    return new Date(value).toISOString();
}

function nowForLocalInput() {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 16);
}
