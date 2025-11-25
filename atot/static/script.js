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

    // ✅ 모델 실행: 순차적으로 ATOT → Backend 파이프라인 실행
    runBtn.addEventListener("click", async () => {
        runBtn.disabled = true;
        modelResult.innerHTML = '<p>⏳ 1/2 음성 처리 중...</p>';

        try {
            const audioEl = document.getElementById("uploaded_audio");
            const textEl  = document.getElementById("submitted_text");

            const fd = new FormData();

            if (audioEl) {
                fd.append("mode", "audio");
            } else if (textEl) {
                fd.append("mode", "text");
                fd.append("user_input", textEl.textContent.trim());
            } else {
                modelResult.innerHTML = `<p style="color:#c00;">최근에 제출된 오디오/텍스트가 없습니다.</p>`;
                runBtn.disabled = false;
                return;
            }

            // ====== STEP 1: ATOT 모델 실행 ======
            const res = await fetch("/run-model", { method: "POST", body: fd });
            const text = await res.text();

            let data;
            try { 
                data = JSON.parse(text); 
            } catch { 
                modelResult.innerHTML = `<p style="color:#c00;">JSON 파싱 실패: ${text}</p>`; 
                runBtn.disabled = false;
                return; 
            }

            if (!res.ok || !data.ok) {
                modelResult.innerHTML = `<p style="color:#c00;">${data.error || "모델 실행 오류"}</p>`;
                runBtn.disabled = false;
                return;
            }

            // ATOT 결과 표시
            const details = (data.result && data.result.details) || {};
            const audioUrl = details.audio_url || "";
            const receivedText = details.received_text || "";

            let html = `
                <div class="card">
                    <h4>✅ 1단계: 음성 처리 완료</h4>
                    <p><strong>인식된 텍스트:</strong> ${escapeHtml(receivedText)}</p>
                    ${audioUrl ? `<p><strong>오디오:</strong> ${escapeHtml(audioUrl)}</p>` : ''}
                </div>
            `;
            modelResult.innerHTML = html;

            // ====== STEP 2: 전체 파이프라인 실행 (TTOT + TTS + DB) ======
            modelResult.innerHTML += '<p style="margin-top:16px;">⏳ 2/2 전체 파이프라인 실행 중 (응답 생성 + TTS + DB 저장)...</p>';
            
            try {
                const pipelineRes = await fetch("http://127.0.0.1:5000/run-full-pipeline", { 
                    method: "POST",
                    headers: { 'Content-Type': 'application/json' }
                });
                
                const pipelineData = await pipelineRes.json();
                
                if (pipelineData.success) {
                    modelResult.innerHTML += `
                        <div class="card" style="margin-top:12px; background:#e8f5e9;">
                            <h4>✅ 전체 파이프라인 완료!</h4>
                            
                            <div style="margin-top:12px;">
                                <h5>📥 입력 (ATOT 결과):</h5>
                                <p><strong>음성 파일:</strong> ${pipelineData.final_data.input_wav || 'N/A'}</p>
                                <p><strong>인식된 텍스트:</strong> ${escapeHtml(pipelineData.final_data.atot_text || '')}</p>
                            </div>
                            
                            <div style="margin-top:12px;">
                                <h5>💬 AI 응답 (TTOT 결과):</h5>
                                <p style="background:#f5f5f5; padding:8px; border-radius:4px;">${escapeHtml(pipelineData.final_data.ttot_text || '')}</p>
                            </div>
                            
                            <div style="margin-top:12px;">
                                <h5>🔊 음성 출력 (TTS 결과):</h5>
                                ${pipelineData.step3_tts.success 
                                    ? `<p>✅ 오디오 파일 생성 완료: <strong>${pipelineData.final_data.output_wav}</strong></p>`
                                    : `<p>⚠️ TTS 실패: ${pipelineData.step3_tts.tts_error || 'Unknown'}</p>`
                                }
                            </div>
                            
                            <p style="margin-top:12px;"><strong>사용자 ID:</strong> ${pipelineData.user_id}</p>
                        </div>
                    `;
                } else {
                    modelResult.innerHTML += `
                        <div class="card" style="margin-top:12px; background:#ffebee;">
                            <h4>❌ 파이프라인 실패</h4>
                            <p style="color:#c00;"><strong>발생한 오류:</strong></p>
                            <ul style="color:#c00;">
                                ${pipelineData.errors.map(err => `<li>${escapeHtml(err)}</li>`).join('')}
                            </ul>
                            ${pipelineData.step1_atot ? `<p><strong>ATOT:</strong> ${pipelineData.step1_atot.success ? '✅' : '❌'}</p>` : ''}
                            ${pipelineData.step2_ttot ? `<p><strong>TTOT:</strong> ${pipelineData.step2_ttot.success ? '✅' : '❌'}</p>` : ''}
                            ${pipelineData.step3_tts ? `<p><strong>TTS:</strong> ${pipelineData.step3_tts.success ? '✅' : '❌'}</p>` : ''}
                        </div>
                    `;
                }
            } catch (pipelineErr) {
                modelResult.innerHTML += `
                    <div class="card" style="margin-top:12px; background:#ffebee;">
                        <h4>❌ Backend 서버 연결 오류</h4>
                        <p style="color:#c00;">${pipelineErr.message}</p>
                        <p style="font-size:0.9em;">Backend 서버(port 5000)가 실행 중인지 확인하세요.</p>
                    </div>
                `;
            }

        } catch (err) {
            modelResult.innerHTML = `<p style="color:#c00;">오류 발생: ${err.message}</p>`;
        } finally {
            runBtn.disabled = false;
        }
    });

    function escapeHtml(str) {
        return String(str).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
    }
});