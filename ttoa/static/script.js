document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("textForm");
    const runBtn = document.getElementById("runModelBtn");
    const modelResult = document.getElementById("modelResult");

    form.addEventListener("submit", async (e) => {
        e.preventDefault(); // 기본 form 전송 방지

        const formData = new FormData(form);

        const response = await fetch("/submit", {
            method: "POST",
            body: formData
        });

        const html = await response.text();
        document.open();
        document.write(html);
        document.close();
    });

    // ✅ 모델 실행: JSON 받아서 partial 업데이트
    runBtn.addEventListener("click", async () => {
        runBtn.disabled = true;
        modelResult.textContent = "모델 실행 중...";

        try {
            const audioEl = document.getElementById("uploaded_audio");
            const textEl  = document.getElementById("submitted_text");

            const fd = new FormData();

            if (audioEl) {
                // 오디오가 보이면 오디오 모드
                fd.append("mode", "audio");
            } else if (textEl) {
                // 텍스트가 보이면 텍스트 모드
                fd.append("mode", "text");
                fd.append("user_input", textEl.textContent.trim());
            } else {
                modelResult.innerHTML = `<p style="color:#c00;">최근에 제출된 오디오/텍스트가 없습니다.</p>`;
                return;
            }

            const res  = await fetch("/run-model", { method: "POST", body: fd });
            const text = await res.text();

            let data;
            try { data = JSON.parse(text); }
            catch { modelResult.innerHTML = `<p style="color:#c00;">JSON 아님: ${text}</p>`; return; }

            if (!res.ok || !data.ok) {
                modelResult.innerHTML = `<p style="color:#c00;">${data.error || "모델 실행 오류"}</p>`;
                return;
            }

            const picked  = data.picked || {};
            const details = (data.result && data.result.details) || {};

            const audioUrl = details.audio_url || ""; // ✅ model.py가 내려주는 /static/... URL
            const receivedText = details.received_text || "";

            const finalPicked = audioUrl ? "audio" : "text";

            let html = `
                <div class="card">
                    <p><strong>선택:</strong> ${finalPicked === "audio" ? "오디오" : "텍스트"}</p>
                    ${finalPicked === "audio"
                        ? `
                            ${audioUrl
                                ? `
                                    <div style="margin-top:8px;">
                                      <p><strong>모델 출력(오디오):</strong></p>
                                      <audio controls src="${audioUrl}"></audio>
                                      <p class="small">${escapeHtml(audioUrl)}</p>
                                    </div>
                                `
                                : `<p><strong>파일:</strong> ${details.audio_name || ""} (${details.audio_size_bytes || 0} bytes)</p>`
                            }
                        `
                        : `<p><strong>텍스트:</strong> ${escapeHtml(receivedText)}</p>`
                    }
                    <p><strong>상태:</strong> ${data.result?.status || "unknown"}</p>
                    <p><strong>메모:</strong> ${details.note || ""}</p>
                </div>
            `;

            modelResult.innerHTML = html;
        } catch (err) {
          modelResult.innerHTML = `<p style="color:#c00;">${err}</p>`;
        } finally {
          runBtn.disabled = false;
        }
    });

    function escapeHtml(str) {
        return String(str).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
    }
});